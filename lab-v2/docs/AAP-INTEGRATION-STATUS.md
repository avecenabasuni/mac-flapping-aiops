# AAP integration published — 2026-11-08

Workflow beb71b61-bff9-460d-ad37-853ae9cc778e is published with 101 steps and no saved
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

39 local tests passed, including strict template/job identity, ignored extra-vars,
approval, bounded polling, partial execution and escalation behavior. Controlled
routing tests mocked job launches/poll outcomes/Slack; the real user-approved jobs 322/324/326/328 have now all succeeded. The corrected
verifier replay passed all 13 telemetry criteria without repeating those jobs.

Verify Device asserts the three port states and prints bridge-table evidence. Direct
device table clearance is not asserted. Recovery can instead be verified within
the explicitly declared containment/forwarding + Datadog log-clearance scope when
all post-job metric and matching-clear/quiet-window evidence passes. See
[telemetry verifier policy](TELEMETRY-VERIFIER.md). Missing proof still escalates.

The main workflow JSON is the current published export. The .aap-draft.json file is
a historical preparation snapshot marked SUPERSEDED_BY_PUBLISHED_WORKFLOW. Exact
access and publication evidence is in datadog/workflows/aap-publication-evidence.json.
Credentials stay in Datadog Connections; never add tokens to workflow JSON or git.

The original instance finished at 01:20:56Z with runtime SUCCEEDED but business result RECOVERY_NOT_VERIFIED. Its old cutoff excluded the matching clears; the ten-minute bound expired and Slack escalation succeeded. At that point, only the corrected replay had passed; the later fresh full test is recorded below.

## Fresh full recovery test passed — Nov 8, 2026

Actual monitor-triggered run 15951b0a-c1e1-45b8-9604-5c1dae1462e1 completed at 02:34:35Z with runtime SUCCEEDED and result RECOVERY_VERIFIED. Real Slack approval led to successful jobs 332/JT38, 334/JT39, 336/JT40 and 338/JT41. All 13 telemetry criteria passed at 02:34:31.249Z, including matching clears emitted during isolation, stable isolated/trusted port states, zero forwarding loss, fresh collector, monitor OK and five-minute quiet observation. Slack_Recovery_Verified succeeded in #datadog-automation with ts1794105274.450979. This run used no action overrides or mocked notifications.

JT42/job330 restored e1/2 before this test under explicit user authorization. The successful test left e1/2 isolated; no automatic restore followed. Verified scope remains containment and forwarding with Datadog log clearance; a direct empty device MAC table or physical loop clearance is not claimed. Exact evidence: datadog/workflows/live-end-to-end-recovery-evidence.json. The earlier false-negative run remains historical evidence of the cutoff defect.
