# Bits agent workflow and chronological evidence validation

Updated 2026-11-06. The investigation workflow uses 16 steps and the custom Bits agent only.
Native Bits Investigation is no longer started automatically. Earlier native investigations
remain historical records; their conclusions are not inputs to this workflow.

## Live behavior

Monitor 340593559 Alert → validate source → collect scoped logs → strictly parse Nokia
messages → calculate per-target chronology → custom Bits agent → validate output →
POC incident-response Slack summary.

The agent receives bounded validated log evidence, not external repository topology.
It cannot execute AAP jobs, change devices, or perform remediation.

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
limitations, and monitor/log/workflow/runbook links. The existing #datadog-monitor
destination is preserved. Collection and agent failures produce explicit failure summaries.
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
