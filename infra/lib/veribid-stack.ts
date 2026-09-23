import * as path from 'node:path';
import * as cdk from 'aws-cdk-lib';
import { Duration, RemovalPolicy, Stack, StackProps } from 'aws-cdk-lib';
import * as amplify from 'aws-cdk-lib/aws-amplify';
import * as apigwv2 from 'aws-cdk-lib/aws-apigatewayv2';
import * as authorizers from 'aws-cdk-lib/aws-apigatewayv2-authorizers';
import * as integrations from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import { Construct } from 'constructs';

export class VeriBidStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    const bedrockModelId = this.node.tryGetContext('bedrockModelId') as string | undefined;
    const bedrockModelArn = this.node.tryGetContext('bedrockModelArn') as string | undefined;
    const bedrockModelArns = ((this.node.tryGetContext('bedrockModelArns') as string | undefined) ?? '')
      .split(',')
      .map((value) => value.trim())
      .filter(Boolean);
    const bedrockModelName = bedrockModelId?.split('/').pop()?.replace(/^global\./, '');
    const bedrockGlobalFoundationModelArn = bedrockModelName
      ? `arn:aws:bedrock:::foundation-model/${bedrockModelName}`
      : undefined;
    const promptCacheEnabled = this.node.tryGetContext('promptCacheEnabled') === true
      || this.node.tryGetContext('promptCacheEnabled') === 'true';
    const frontendOrigin = (this.node.tryGetContext('frontendOrigin') as string | undefined) ?? 'https://main.d2jw7e2fbiu6od.amplifyapp.com';

    const uploads = new s3.Bucket(this, 'UploadsBucket', {
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      versioned: true,
      removalPolicy: RemovalPolicy.RETAIN,
      autoDeleteObjects: false,
      cors: [{
        allowedMethods: [s3.HttpMethods.PUT, s3.HttpMethods.HEAD],
        allowedOrigins: [frontendOrigin],
        allowedHeaders: ['Content-Type'],
        exposedHeaders: ['ETag'],
        maxAge: 300,
      }],
    });

    const records = new dynamodb.Table(this, 'RecordsTable', {
      partitionKey: { name: 'pk', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'sk', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true },
      deletionProtection: false,
      removalPolicy: RemovalPolicy.RETAIN,
    });

    const userPool = new cognito.UserPool(this, 'UserPool', {
      userPoolName: 'veribid-users',
      selfSignUpEnabled: true,
      signInAliases: { email: true },
      autoVerify: { email: true },
      standardAttributes: { email: { required: true, mutable: true } },
      passwordPolicy: {
        minLength: 12,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: true,
      },
      removalPolicy: RemovalPolicy.RETAIN,
    });

    const userPoolClient = userPool.addClient('WebClient', {
      generateSecret: false,
      authFlows: { userSrp: true },
      disableOAuth: true,
      preventUserExistenceErrors: true,
      refreshTokenValidity: Duration.days(30),
    });

    const backendCode = lambda.Code.fromAsset(path.join(__dirname, '../../backend'), {
      bundling: {
        image: cdk.DockerImage.fromRegistry('python:3.13-slim'),
        command: ['sh', '-c', 'pip install --no-cache-dir -r requirements.txt -t /asset-output && cp -r . /asset-output'],
      },
    });

    const workerFunction = new lambda.Function(this, 'WorkflowWorker', {
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'worker.handler',
      code: backendCode,
      timeout: Duration.minutes(5),
      memorySize: 1024,
      environment: {
        TABLE_NAME: records.tableName,
        UPLOADS_BUCKET: uploads.bucketName,
        BEDROCK_MODEL_ID: bedrockModelId ?? '',
        PROMPT_CACHE_ENABLED: promptCacheEnabled ? 'true' : 'false',
      },
    });

    if (bedrockModelArn) {
      workerFunction.addToRolePolicy(new iam.PolicyStatement({
        actions: ['bedrock:GetInferenceProfile', 'bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream'],
        resources: [bedrockModelArn, ...bedrockModelArns, ...(bedrockGlobalFoundationModelArn ? [bedrockGlobalFoundationModelArn] : [])],
      }));
    }

    const workerTask = new tasks.LambdaInvoke(this, 'RunWorkflowWorker', {
      lambdaFunction: workerFunction,
      payload: sfn.TaskInput.fromJsonPathAt('$'),
      outputPath: '$.Payload',
    });
    workerTask.addRetry({
      errors: ['States.TaskFailed'],
      interval: Duration.seconds(2),
      backoffRate: 2,
      maxAttempts: 2,
    });
    workerTask.addCatch(new sfn.Fail(this, 'WorkflowFailed', {
      cause: 'The workflow worker failed after bounded retries',
    }), { resultPath: '$.error' });

    const workflow = new sfn.StateMachine(this, 'EvaluationStateMachine', {
      stateMachineName: 'veribid-evaluation',
      definitionBody: sfn.DefinitionBody.fromChainable(workerTask),
      stateMachineType: sfn.StateMachineType.STANDARD,
    });

    const healthFunction = new lambda.Function(this, 'ApiFunction', {
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'api.handler',
      code: backendCode,
      timeout: Duration.seconds(10),
      memorySize: 256,
      environment: {
        SERVICE_NAME: 'veribid-api',
        SERVICE_VERSION: '0.1.0',
        TABLE_NAME: records.tableName,
        UPLOADS_BUCKET: uploads.bucketName,
        STATE_MACHINE_ARN: workflow.stateMachineArn,
      },
    });

    records.grantReadWriteData(healthFunction);
    healthFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['s3:GetObject', 's3:PutObject'],
      resources: [uploads.arnForObjects('evaluations/*')],
    }));
    workflow.grantStartExecution(healthFunction);
    records.grantReadWriteData(workerFunction);
    workerFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['s3:GetObject'],
      resources: [uploads.arnForObjects('evaluations/*')],
    }));
    workerFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['cloudwatch:PutMetricData'],
      resources: ['*'],
      conditions: { StringEquals: { 'cloudwatch:namespace': 'VeriBid' } },
    }));

    const api = new apigwv2.HttpApi(this, 'HttpApi', {
      apiName: 'veribid-api',
      createDefaultStage: true,
      corsPreflight: {
        allowHeaders: ['content-type', 'authorization', 'idempotency-key'],
        allowMethods: [apigwv2.CorsHttpMethod.GET, apigwv2.CorsHttpMethod.POST, apigwv2.CorsHttpMethod.PUT, apigwv2.CorsHttpMethod.OPTIONS],
        allowOrigins: [frontendOrigin],
        maxAge: Duration.minutes(10),
      },
    });
    const defaultStage = api.defaultStage?.node.defaultChild as apigwv2.CfnStage | undefined;
    if (defaultStage) {
      defaultStage.defaultRouteSettings = {
        throttlingBurstLimit: 50,
        throttlingRateLimit: 25,
      };
    }
    const apiIntegration = new integrations.HttpLambdaIntegration('ApiIntegration', healthFunction);
    const cognitoAuthorizer = new authorizers.HttpJwtAuthorizer('CognitoJwtAuthorizer', userPool.userPoolProviderUrl, {
      jwtAudience: [userPoolClient.userPoolClientId],
    });
    api.addRoutes({
      path: '/api/v1/health',
      methods: [apigwv2.HttpMethod.GET],
      integration: apiIntegration,
    });
    api.addRoutes({
      path: '/api/v1/demo',
      methods: [apigwv2.HttpMethod.GET],
      integration: apiIntegration,
    });
    api.addRoutes({
      path: '/api/v1/evaluations',
      methods: [apigwv2.HttpMethod.POST],
      integration: apiIntegration,
      authorizer: cognitoAuthorizer,
    });
    api.addRoutes({
      path: '/api/v1/evaluations/{evaluation_id}',
      methods: [apigwv2.HttpMethod.GET],
      integration: apiIntegration,
      authorizer: cognitoAuthorizer,
    });
    api.addRoutes({
      path: '/api/v1/evaluations/{evaluation_id}/documents',
      methods: [apigwv2.HttpMethod.GET, apigwv2.HttpMethod.POST],
      integration: apiIntegration,
      authorizer: cognitoAuthorizer,
    });
    api.addRoutes({
      path: '/api/v1/evaluations/{evaluation_id}/documents/{document_id}/complete-upload',
      methods: [apigwv2.HttpMethod.POST],
      integration: apiIntegration,
      authorizer: cognitoAuthorizer,
    });
    api.addRoutes({
      path: '/api/v1/evaluations/{evaluation_id}/requirements',
      methods: [apigwv2.HttpMethod.GET],
      integration: apiIntegration,
      authorizer: cognitoAuthorizer,
    });
    api.addRoutes({
      path: '/api/v1/evaluations/{evaluation_id}/requirements/extract',
      methods: [apigwv2.HttpMethod.POST],
      integration: apiIntegration,
      authorizer: cognitoAuthorizer,
    });
    api.addRoutes({
      path: '/api/v1/evaluations/{evaluation_id}/runs',
      methods: [apigwv2.HttpMethod.POST],
      integration: apiIntegration,
      authorizer: cognitoAuthorizer,
    });
    api.addRoutes({
      path: '/api/v1/evaluations/{evaluation_id}/runs/{run_id}',
      methods: [apigwv2.HttpMethod.GET],
      integration: apiIntegration,
      authorizer: cognitoAuthorizer,
    });
    api.addRoutes({
      path: '/api/v1/evaluations/{evaluation_id}/matrix',
      methods: [apigwv2.HttpMethod.GET],
      integration: apiIntegration,
      authorizer: cognitoAuthorizer,
    });
    api.addRoutes({
      path: '/api/v1/evaluations/{evaluation_id}/results/{evaluation_result_id}',
      methods: [apigwv2.HttpMethod.GET],
      integration: apiIntegration,
      authorizer: cognitoAuthorizer,
    });
    api.addRoutes({
      path: '/api/v1/evaluations/{evaluation_id}/results/{evaluation_result_id}/reviews',
      methods: [apigwv2.HttpMethod.POST],
      integration: apiIntegration,
      authorizer: cognitoAuthorizer,
    });
    api.addRoutes({
      path: '/api/v1/evaluations/{evaluation_id}/exports',
      methods: [apigwv2.HttpMethod.POST],
      integration: apiIntegration,
      authorizer: cognitoAuthorizer,
    });
    api.addRoutes({
      path: '/api/v1/evaluations/{evaluation_id}/exports/{export_id}',
      methods: [apigwv2.HttpMethod.GET],
      integration: apiIntegration,
      authorizer: cognitoAuthorizer,
    });

    const amplifyApp = new amplify.CfnApp(this, 'AmplifyApp', {
      name: 'veribid',
      platform: 'WEB',
      description: 'VeriBid public demo and authenticated workspace',
      environmentVariables: [
        { name: 'VITE_API_BASE_URL', value: api.url ?? '' },
        { name: 'VITE_USER_POOL_ID', value: userPool.userPoolId },
        { name: 'VITE_USER_POOL_CLIENT_ID', value: userPoolClient.userPoolClientId },
      ],
      customRules: [{
        source: '</^[^.]+$|\\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json|webp)$)([^.]+$)/>',
        target: '/index.html',
        status: '200',
      }],
    });

    const amplifyBranch = new amplify.CfnBranch(this, 'AmplifyMainBranch', {
      appId: amplifyApp.attrAppId,
      branchName: 'main',
      stage: 'PRODUCTION',
      enableAutoBuild: false,
      framework: 'React',
    });
    amplifyBranch.addResourceDependency(amplifyApp);

    new cdk.CfnOutput(this, 'ApiUrl', { value: api.url ?? '', description: 'HTTP API base URL' });
    new cdk.CfnOutput(this, 'HealthUrl', { value: `${api.url ?? ''}api/v1/health`, description: 'Public API health URL' });
    new cdk.CfnOutput(this, 'UploadsBucketName', { value: uploads.bucketName });
    new cdk.CfnOutput(this, 'RecordsTableName', { value: records.tableName });
    new cdk.CfnOutput(this, 'UserPoolId', { value: userPool.userPoolId });
    new cdk.CfnOutput(this, 'UserPoolClientId', { value: userPoolClient.userPoolClientId });
    new cdk.CfnOutput(this, 'StateMachineArn', { value: workflow.stateMachineArn });
    new cdk.CfnOutput(this, 'AmplifyAppId', { value: amplifyApp.attrAppId });
    new cdk.CfnOutput(this, 'AmplifyDefaultDomain', { value: `https://main.${amplifyApp.attrDefaultDomain}` });

    healthFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['cloudwatch:PutMetricData'],
      resources: ['*'],
      conditions: { StringEquals: { 'cloudwatch:namespace': 'VeriBid' } },
    }));
  }
}
