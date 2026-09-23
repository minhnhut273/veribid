# 04 Agent Connected

Status: READY.

`aws --profile veribid-deploy sts get-caller-identity` returned a dedicated IAM user ARN ending in `user/veribid-deploy`, not an account-root ARN. The profile is configured for `us-east-1`; no credential material is stored in this artifact.
