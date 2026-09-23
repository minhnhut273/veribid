# 05 Agent AWS Action

Status: READY.

The agent used the non-root profile to read `VeriBidStack`, compare the CI CDK assembly with the deployed template, deploy the Lambda code update, and then probe the public application, `/demo`, API health and an anonymous protected API route. Results were stack `UPDATE_COMPLETE`, no stateful-resource replacement, HTTP 200, HTTP 200, HTTP 200 and HTTP 401 respectively.
