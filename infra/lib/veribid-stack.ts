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
import { Construct } from 'constructs';

export class VeriBidStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    const uploads = new s3.Bucket(this, 'UploadsBucket', {
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      versioned: true,
      removalPolicy: RemovalPolicy.RETAIN,
      autoDeleteObjects: false,
      cors: [{
        allowedMethods: [s3.HttpMethods.PUT, s3.HttpMethods.HEAD],
        allowedOrigins: ['*'],
        allowedHeaders: ['*'],
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
      preventUserExistenceErrors: true,
      refreshTokenValidity: Duration.days(30),
    });

    const workflow = new sfn.StateMachine(this, 'EvaluationStateMachine', {
      stateMachineName: 'veribid-evaluation',
      definitionBody: sfn.DefinitionBody.fromChainable(
        new sfn.Pass(this, 'AwaitingEvaluationInput', {
          result: sfn.Result.fromObject({ status: 'READY_FOR_WORKFLOW' }),
        }),
      ),
      stateMachineType: sfn.StateMachineType.STANDARD,
    });

    const healthFunction = new lambda.Function(this, 'ApiFunction', {
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'api.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../backend')),
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
    uploads.grantReadWrite(healthFunction);
    workflow.grantStartExecution(healthFunction);

    const api = new apigwv2.HttpApi(this, 'HttpApi', {
      apiName: 'veribid-api',
      createDefaultStage: true,
      corsPreflight: {
        allowHeaders: ['content-type', 'authorization', 'idempotency-key'],
        allowMethods: [apigwv2.CorsHttpMethod.GET, apigwv2.CorsHttpMethod.POST, apigwv2.CorsHttpMethod.PUT, apigwv2.CorsHttpMethod.OPTIONS],
        allowOrigins: ['*'],
        maxAge: Duration.minutes(10),
      },
    });
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
        source: '/<*>',
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
