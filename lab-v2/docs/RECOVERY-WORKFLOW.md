# MAC flapping recovery workflow — 2026-11-08

Observe → Investigate → Authorize → Execute → Verify → stop/escalate if unverified.

| Stage | Published behavior |
| --- | --- |
| Observe | Monitor 340593559 detects scoped Nokia duplicate-MAC logs. |
| Investigate | Custom Bits agent reviews bounded, validated evidence and chronology. |
| Authorize | Fresh eligible lab evidence requests authenticated Slack Approve/Reject. |
| Execute | After approval: JT38 collects evidence, then JT39 isolates only sw1 ethernet-1/2. |
| Verify | JT40 asserts device port states; JT41 probes Host C→A; Datadog reads monitor/SNMP/loss/heartbeat. |
| Stop/escalate | Failed jobs, missing evidence or unverified recovery go to #datadog-automation. |

All workflow Slack actions use #datadog-automation as top-level messages, matching
Operational Conditions. Monitor notifications remain in #datadog-monitor. Reject or
unavailable approval stops without an AAP launch. Restore JT42 is never automatic.
No job launch retries or automatic follow-up remediation occur.

Every AAP job checks the fixed template ID, playbook, inventory 7, project 37 and
Execute access before dispatch. Polls check both job and template identity. At most
60 polls occur per job, ten seconds apart. A timeout does not cancel a still-running
AAP job: inspect its status before any manual retry.

Datadog verification requires unique, numeric metric samples no older than 180s.
Missing, stale, duplicate, future and null data cannot pass. It checks e1/2 isolation,
trusted/probe ports up, independent zero-loss forwarding, heartbeat and monitor state.
Successful JT40/JT41 must follow the isolation job. The current device playbook still
does not assert duplicate-MAC/hold-down clearance, so no verified-recovery success
path is enabled. Missing proof yields RECOVERY_NOT_VERIFIED and Slack escalation.
Slack delivery failure yields ESCALATION_DELIVERY_FAILED with escalation_sent=false.

31 offline fixtures passed. Read-only access verification succeeded for all four
templates. Earlier routing tests mocked AAP launches and Slack. Real execution of
JT39 requires a new eligible alert and explicit Approve in Slack; publication alone
did not launch a job or change a port.
