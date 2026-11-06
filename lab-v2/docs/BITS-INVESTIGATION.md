# Bits Investigation and chronological evidence validation

Updated 2026-11-06. The published investigation workflow has 23 steps. Its monitor
ID/mention and the Scenario Controller placeholders are unchanged.

## Two different AI roles

- The custom Bits agent produces a quick, structured summary of the bounded
  validated log sample. Its MCP/tool access remains disabled.
- Native Bits Investigation is started through the Workflow action
  com.datadoghq.dd.bitsai.sre.triggerInvestigation for an accepted monitor Alert.
  It investigates independently across available telemetry.

The workflow looks up the same monitor/event before starting native
Investigation. It reuses an existing match. If lookup is incomplete or the native
request fails, it does not invent findings or retry creation blindly; the result
records UNAVAILABLE and the bounded evidence summary continues.

Manual historical replays do not start native investigations. A pinned-source
connector test deliberately used the original monitor event to test creation and
reuse. Test notifications were disabled.

## Chronology fix

CLEAR_EVENT_OBSERVED is not based merely on the presence of a deletion log.

The workflow matches host, MAC, target type and target interface/MAC-VRF. Every
observed detection target must have a deletion strictly later than its latest
detection. Equal timestamps, a newer re-detection, another host/MAC/target, partial
clearing, truncated results, query warnings and unparsed records retain
UNVERIFIED. A deletion-only sample can record clear-event evidence, but it still
does not prove device recovery.

The model is given expected_recovery_status from this deterministic timeline.
The final validator checks against it. Physical-loop confirmation, device
recovery verification and remediation permission remain false.

## Slack behavior

The initial Slack message contains the quick evidence summary and the native
investigation status/link. It does not wait for native Investigation to finish,
and it does not automatically post its final conclusions later. Open the linked
native investigation for those findings.

Report COMPLETED refers to the bounded evidence path. Native status is a separate
field; STARTED does not mean native RCA is complete. Native conclusions and
suggested changes are not passed to AAP or executed by this workflow.

Treat native findings as analyst recommendations. In particular, a MAC-VRF name
is not a second physical interface, and quiet logs/monitor OK cannot establish
forwarding recovery. Confirm device topology, port state and the independent
probe before acting on suggested remediation.

## Verified runs

All workflow tests below suppressed Slack and performed no device/AAP action.

| Test | Instance | Result |
| --- | --- | --- |
| Old deletion followed by newer detection | fd2f331b-99d9-4d5e-a488-f8723500573d | COMPLETED / MAC_FLAPPING_EVIDENCE / UNVERIFIED |
| Native connector with original v2 alert source | 4dd72962-945e-427e-af14-4686ae6fb3a5 | Native STARTED; quick report COMPLETED |
| Same monitor/event replay | e5304793-e32e-464c-ba85-868dd7be02fb | Same native ID reused, trigger step not executed |
| Controlled native lookup failure | a2f62051-5c2b-48a6-a644-4a0fad13ae75 | Native UNAVAILABLE; quick report COMPLETED |

Native investigation:
https://app.datadoghq.com/bits-ai/investigations/39841fa9-9a61-43b8-8b7b-08a2ce1196d5

It was verified as conclusive, finished at 2026-11-06T07:09:09.112753Z.
The initial MCP trigger returned HTTP 500 and created no investigation; the
Workflow action subsequently succeeded.

The exported workflow and fixture tests include the corrected logic:

~~~bash
node --test lab-v2/tests/test_workflow_timeline.cjs
~~~

Eleven Node tests cover ordering, target matching, partial evidence, false clear
claims, invented citations and native lookup behavior. The Python collector and
Ansible verification suite remains separate.

## Deployment

For another Datadog organization, update the monitor/agent IDs and Slack
placeholders in the exported workflow. Validate the spec, publish it, and attach
its mention to the intended monitor. Native Bits Investigation permissions and
available telemetry must be verified in that organization.
