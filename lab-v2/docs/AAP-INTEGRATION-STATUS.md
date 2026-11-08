# AAP integration draft — 2026-11-08

The repository now documents JT 38 Collect Evidence, 39 Isolate Host B, 40 Verify
Device, 41 Verify Forwarding and 42 Restore Host B. Root collection requirements
and the corrected SW1 management IP were incorporated from user commits.

A validated draft is saved on Datadog workflow beb71b61-bff9-460d-ad37-853ae9cc778e.
The live published workflow still uses inactive AAP placeholders. No real AAP job
was launched while preparing this integration.

The draft's approved path runs fixed JT 38 → 39 → 40 → 41, using the existing AAP
connection. Before each launch it checks template ID, exact playbook, inventory,
start permission and acceptance of approved variables. Each job is polled every
10 seconds for at most 60 checks. Launch POSTs have zero retries. A rejected launch,
failed job, timeout or unreadable job stops the sequence and escalates. Any returned
job ID is preserved even if validation fails, because the job may already exist.
JT 42 remains manual-only; no generator start/stop Job Template exists, so Scenario
Controller mac-flapping/reset-mac-flapping choices remain placeholders.

Both existing Scenario Controller and Operational Conditions remediation connections
could reach the controller but returned an empty
filtered template list and then HTTP 403 on direct GET of JT 38. The connected
principal needs Read and Execute access to JT 38-41 and their inventory/credentials.
Secret changes must be made in the existing Datadog connection, not in workflow
JSON, extra-vars or this public repository. Direct network access from the local
Codex machine to the AAP host was unavailable. A newly supplied token has not been
authenticated or saved by Codex.

The user confirmed that POC_AAP_CONNECTION_REMEDIATION is the same connection as
Operational Conditions. A fresh GET /me authenticated successfully (HTTP 200),
while GET of JT 38 still returned HTTP 403. The remaining blocker is AAP role/access
for the principal stored in that connection, not its ID or network reachability.
Give that principal Execute access to the fixed JT 38-41 and required related
resources. Do not broaden it to administrator or automatically activate restore JT 42.
Controlled run 9e8fbf4a-d7bb-4723-ac44-9d2a93855095 confirmed that a real template
permission failure stops before any launch; all Slack/launch actions were mocked.
Six local integration fixtures passed, and the four-job routing path completed in
Datadog with all launches, job statuses, polling and Slack actions mocked. No real
isolation job was launched by these tests.

Verify Device currently asserts the three port states and prints bridge-table
evidence. It does not assert duplicate-MAC/hold-down clearance. The draft therefore
continues to report RECOVERY_NOT_VERIFIED rather than inventing device recovery.
Successful real jobs, actual returned evidence/artifacts and the independent
post-execution telemetry still need to be validated before enabling a success path.

The sanitized draft is in
`datadog/workflows/investigate-network-mac-flapping.aap-draft.json`; the existing
non-draft export remains the published placeholder workflow. Do not publish the
draft until the real AAP template metadata and permissions have been verified.
