# Bits agent workflow and chronological evidence validation

Updated 2026-11-06. The investigation workflow uses 37 steps and the custom Bits agent only.
Native Bits Investigation is no longer started automatically. Earlier native investigations
remain historical records; their conclusions are not inputs to this workflow.

## Live behavior

Monitor 340593559 Alert → validate source → collect scoped logs → strictly parse Nokia
messages → calculate per-target chronology → custom Bits agent → validate output →
POC incident-response Slack summary → eligibility gate → Slack approve/reject →
record decision → inactive Execute → read-only Verify → stop and escalate when
recovery is unverified. AAP is a non-executable placeholder.

The agent receives bounded validated log evidence, not external repository topology.
It cannot execute AAP jobs, change devices, or perform remediation.

## Slack approval placeholder

All workflow messages use #datadog-automation, matching Operational Conditions.
No sendInThread option is set: messages are top-level, as in that workflow.
The monitor notification itself remains separate in #datadog-monitor. Fresh validated automatic
monitor detections for the fixed sw1 / 02:00:00:00:00:aa lab scope request a decision
in #datadog-automation, following Operational Conditions. Incomplete, stale, low-confidence,
cleared, unrelated, and manual evidence does not request approval. The decision gate
does not establish that a shutdown target is safe: it permits a placeholder review only.

- Approve Response (AAP Placeholder): records APPROVED, enters Execute with
  JOB_NOT_CONFIGURED, then Verify and RECOVERY_NOT_VERIFIED escalation.
- Reject Remediation: records REJECTED and REMEDIATION_REJECTED.
- No response for one hour, Slack failure, or invalid response: stops without action.

The proposed future target is fixed sw1 ethernet-1/2 (Host B), never selected by AI
from whichever interface appears in a log. Responder identity is retained in the run.
Job template and job ID are empty; execution backend is NONE. No HTTP/AAP/device
action exists. Old approvals cannot execute a job when AAP is later integrated:
that requires fresh device checks and a new approval.

18 local chronology/approval fixtures passed. Four controlled Datadog runs verify
approve, reject, request-error and ineligible routing with all Slack actions overridden.
These tests do not prove actual Slack button delivery/click behavior or a wall-clock
one-hour expiry. See approval-placeholder-evidence.json for instance IDs and results.

Those runs describe the previous 24-step approval-only version. Current Execute/Verify
behavior and its separate regression results are documented in [RECOVERY-WORKFLOW.md](RECOVERY-WORKFLOW.md).

A deletion clears an observed detection only for the same host, MAC, target type,
and target, with a strictly later timestamp. Older, equal-time, or different-target deletion
does not clear a newer detection. Incomplete, truncated, warned, or unparsed samples cannot
establish complete clearing. CLEAR_EVENT_OBSERVED is log evidence, not device recovery.

## Slack format

The format follows the existing published Operational Conditions v7 AAP workflow:
separator lines, INCIDENT RESPONSE heading, status fields, evidence, safety note,
and Next → read-only checks. EVIDENCE REVIEWED, PAUSED, and INVESTIGATION FAILED
describe investigation results without claiming remediation or verified recovery.

Messages include host, MAC, interfaces, network instance, sample counts, UTC window,
limitations, and monitor/log/workflow/runbook links. All workflow messages use #datadog-automation. Collection and agent failures produce explicit failure summaries.
Recovery or unrelated monitor events are skipped. Tests disable Slack.

## Verification

- Node fixtures: 13 passed, covering chronology, incomplete evidence, invented citations,
  graph integrity, message escaping, and failed/skipped report formatting.
- Real-log replay: 159501cf-38d1-4c05-9990-e91656070276.
- Monitor-source replay: 8f7cabeb-5f55-4f37-9f23-7ba98c60fa27.
- Controlled agent failure: 748f414f-8ab7-4a14-bab4-6cd3bbe45b1b.
- Current runtime results: datadog/workflows/mac-flapping-regression-evidence.json.
- Previous native integration tests are historical, not current behavior.

## Import

Adapt sanitized Slack placeholders and the custom agent ID for the target organization.
Keep the trigger handle and intended monitor mapping consistent.
AAP scenario jobs remain placeholders until the separate AAP phase.
