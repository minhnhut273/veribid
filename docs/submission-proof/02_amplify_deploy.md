# 02 Amplify Deployment

Status: PARTIAL.

The current non-root profile read the CloudFormation `AmplifyApp` resource as `UPDATE_COMPLETE`. A direct `amplify:GetBranch` read was denied by the intentionally narrow deployment policy, so no fresh Amplify job status is claimed here. Existing historical deployment evidence remains in the completion report.
