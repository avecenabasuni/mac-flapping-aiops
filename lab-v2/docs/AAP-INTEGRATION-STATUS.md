# AAP integration published — 2026-11-08

Workflow beb71b61-bff9-460d-ad37-853ae9cc778e is published with 91 steps and no saved
draft. It uses the user-confirmed POC_AAP_CONNECTION_REMEDIATION connection.

Read-only run 9fa1e151-7419-442a-92c8-c3459cff53f8 verified HTTP 200 and start=true
for JT 38–41. Every template matches the documented repository playbook, inventory 7
and project 37. JT39 has ask_variables_on_launch=true. No job was launched for this
access check. Earlier 403 access failures were resolved after AAP Execute access
was assigned to the connection account.

The approved path runs JT38 Collect Evidence → JT39 Isolate Host B → JT40 Verify
Device → JT41 Verify Forwarding. Fixed template identity/playbook/inventory/project,
start permission and approved variables are checked. Each job is polled every ten
seconds for at most 60 checks. Launch POSTs have zero retries. Failed or ambiguous
responses stop the sequence, preserve any returned job ID, and escalate to Slack.
JT42 Restore Host B remains manual-only. Scenario Controller generator choices
remain placeholders because no start/stop generator Job Template exists.

31 local tests passed, including strict template/job identity, ignored extra-vars,
approval, bounded polling, partial execution and escalation behavior. Controlled
routing tests mocked job launches/poll outcomes/Slack; a real approved isolation and
verification sequence has not yet been run by Codex.

Current Verify Device asserts the three port states and prints bridge-table evidence.
It does not assert duplicate-MAC/hold-down clearance. Recovery therefore remains
UNVERIFIED and escalates until this proof and independent post-execution evidence
are established. Green telemetry is not substituted for this missing proof.

The main workflow JSON is the current published export. The .aap-draft.json file is
a historical preparation snapshot marked SUPERSEDED_BY_PUBLISHED_WORKFLOW. Exact
access and publication evidence is in datadog/workflows/aap-publication-evidence.json.
Credentials stay in Datadog Connections; never add tokens to workflow JSON or git.
