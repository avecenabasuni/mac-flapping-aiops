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

39 offline fixtures passed. Controlled routing tests mocked AAP/Slack and the final
gate; a live read-only verifier test rejected recovery with no job proof. The first real alert/approval/AAP sequence succeeded; its clear logs exposed a cutoff
bug. The corrected read-only verifier replay passed on real telemetry and original
approval/job evidence without rerunning AAP. See the exact incident evidence and
cutoff explanation in [verifier policy](TELEMETRY-VERIFIER.md). Real execution of
JT39 requires a new eligible alert and explicit Approve in Slack; publication alone
did not launch a job or change a port.

The original instance finished at 01:20:56Z with runtime SUCCEEDED but business result RECOVERY_NOT_VERIFIED. Its old cutoff excluded the matching clears; the ten-minute bound expired and Slack escalation succeeded. At that point, only the corrected replay had passed; the later fresh full test is recorded below.

## Fresh full recovery test passed — Nov 8, 2026

Actual monitor-triggered run 15951b0a-c1e1-45b8-9604-5c1dae1462e1 completed at 02:34:35Z with runtime SUCCEEDED and result RECOVERY_VERIFIED. Real Slack approval led to successful jobs 332/JT38, 334/JT39, 336/JT40 and 338/JT41. All 13 telemetry criteria passed at 02:34:31.249Z, including matching clears emitted during isolation, stable isolated/trusted port states, zero forwarding loss, fresh collector, monitor OK and five-minute quiet observation. Slack_Recovery_Verified succeeded in #datadog-automation with ts1794105274.450979. This run used no action overrides or mocked notifications.

JT42/job330 restored e1/2 before this test under explicit user authorization. The successful test left e1/2 isolated; no automatic restore followed. Verified scope remains containment and forwarding with Datadog log clearance; a direct empty device MAC table or physical loop clearance is not claimed. Exact evidence: datadog/workflows/live-end-to-end-recovery-evidence.json. The earlier false-negative run remains historical evidence of the cutoff defect.
