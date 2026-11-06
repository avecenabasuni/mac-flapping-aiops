# MAC flapping recovery workflow

The published workflow follows Observe → Investigate → Authorize → Execute → Verify.
Execute remains an inactive AAP placeholder. It never launches a job or changes ports.

| Stage | Current behavior |
| --- | --- |
| Observe | Monitor 340593559 detects scoped Nokia duplicate-MAC logs. |
| Investigate | Custom Bits agent reviews validated, bounded evidence. |
| Authorize | Fresh eligible lab detections request Slack Approve/Reject. |
| Execute | Approved decision records JOB_NOT_CONFIGURED for sw1 ethernet-1/2. |
| Verify | Reads current monitor, SNMP admin/oper, C→A packet loss and collector heartbeat. |
| Stop/escalate | RECOVERY_NOT_VERIFIED goes to #datadog-automation; no retry or further action. |

Reject and unavailable decisions stop without Execute. Recovery cannot pass while
AAP and post-execution duplicate-MAC/device checks remain placeholders. Even green
telemetry, monitor OK and zero-loss ping do not override missing execution evidence.
Metrics must have exactly one scoped series and a numeric sample no older than 180
seconds. Missing, duplicate, stale, future or null samples cannot pass verification.

The workflow records checks for e1/2 admin/oper down, e1/1 and e1/3 admin/oper up,
independent zero-loss probe, collector freshness and monitor state. Missing proof of
successful AAP execution, duplicate entries/MAC table after hold-down, and observations
after the approved execution are explicitly recorded as failed criteria. No success
notification exists while these integrations are inactive.

Verification read errors also stop/escalate with incomplete evidence. Slack delivery
failure produces ESCALATION_DELIVERY_FAILED in the final workflow output; it does not
claim that escalation was delivered. The terminal output contains approval, execution,
verification, recovery, notification errors and remediation_executed=false.

24 local fixtures cover chronology, approval, stale/missing verification data,
all-green telemetry without device proof, and escalation failure. Controlled Datadog
runs test approved live reads, rejection, verification read failure and escalation
delivery failure. All Slack actions are overridden in these tests; actual Slack
delivery/click and one-hour approval expiry are not verified by them.

Before AAP activation, connect a fixed approved isolation job, independent read-only
device verification, bounded settling/recheck policy, and a new approval using current
device evidence. Old placeholder approvals must never be replayed into real execution.
