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

Datadog verification now observes fresh post-job SNMP/probe/collector data and complete,
strictly parsed post-isolation logs. Every detection target must have a later matching
deletion; at least five minutes must elapse after the latest clear without new detection.
Observation polls every 30 seconds, with a ten-minute deadline and at most 20 attempts.
All passing proof yields RECOVERY_VERIFIED in the containment/forwarding + log-clearance
scope. Missing proof or read failure stops and escalates; no direct empty-MAC-table or
physical-loop claim is made. See [exact policy](TELEMETRY-VERIFIER.md).

38 offline fixtures passed. Controlled routing tests mocked AAP/Slack and the final
gate; a live read-only verifier test rejected recovery with no job proof. An actual
fault-to-recovery incident has not yet been observed with this version. Real execution of
JT39 requires a new eligible alert and explicit Approve in Slack; publication alone
did not launch a job or change a port.
