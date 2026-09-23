# 03 AWS Resources

Status: PASS for current CloudFormation inventory.

Using `aws --profile veribid-deploy cloudformation describe-stack-resources --region us-east-1 --stack-name VeriBidStack`, the deployed stack was readable and included Amplify, API Gateway, Lambda, Step Functions, S3, DynamoDB, Cognito and IAM resources. The stack status was `UPDATE_COMPLETE`. CDK assembly comparison showed existing S3, DynamoDB, Cognito, Step Functions, API Gateway and Amplify resources were preserved; only Lambda code objects changed.
