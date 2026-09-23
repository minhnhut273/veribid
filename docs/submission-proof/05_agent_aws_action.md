# 05 Agent AWS Action

Status: PASS for read-only action.

The agent used the non-root profile to read `VeriBidStack` status/resources and then probed the public application, `/demo`, API health and an anonymous protected API route. Results were stack `UPDATE_COMPLETE`, HTTP 200, HTTP 200, HTTP 200 and HTTP 401 respectively.
