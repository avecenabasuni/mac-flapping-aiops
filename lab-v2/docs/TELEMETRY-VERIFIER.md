# Datadog telemetry recovery verifier

Recovery scope: containment and independent forwarding with Datadog log-clearance
evidence. RECOVERY_VERIFIED does not assert a physical loop or a direct read of an
empty device duplicate-MAC table.

After the approved fixed AAP sequence, observe read-only telemetry every 30 seconds
for at most 20 attempts and a ten-minute deadline (plus in-flight request time).
No remediation job is relaunched during observation.

All criteria must pass:

1. Authenticated Slack approval is recorded.
2. Isolation JT39 and verification JT40/JT41 have successful, identity-checked job
   records and valid chronological timestamps. JT40 starts after JT39 finishes;
   JT41 starts after JT40 finishes. No AAP integration failure is present.
3. SNMP e1/2 admin/oper are down; e1/1 and e1/3 admin/oper are up.
4. Independent Host C→A loss is 0%, and the collector heartbeat is 1.
5. Each metric has exactly one scoped series, at least two numeric samples spanning
   60 seconds, all collected after the verification jobs, no older than 180 seconds.
   Conflicting equal-time samples, ambiguous series, missing/null/future or stale
   samples cannot satisfy the check. Queries disable gauge interpolation with fill(null).
6. The MAC-flapping monitor is currently OK.
7. The log query starts at the approved isolation job's start time, and is complete:
   no pagination, partial status, warnings,
   or unparsed scoped messages. Up to 1000 logs are accepted; overflow fails closed.
8. Every initial or subsequent detection target has a strictly later matching deletion
   at or after the isolation job starts, including deletions emitted during the job.
   Matching uses host, normalized MAC, target type and exact target.
   One target's deletion cannot clear another interface or MAC-VRF target.
9. At least five minutes have elapsed after the latest matching clear, with no new
   duplicate-MAC detection in that quiet window.
10. Observation stays within its deadline and no verification read fails.

Temporary missing proof/stability/quiet-window criteria may be observed again until
the bound. Missing execution/approval proof, incomplete log queries or read failures
stop immediately. On success, Slack announces Telemetry Recovery Verified with the
scope and AAP IDs. Otherwise automation stops and escalates RECOVERY_NOT_VERIFIED.
JT42 restore is never automatic. Slack delivery failures remain explicit in output.

39 local fixtures exercise positive evidence, new detections, wrong targets, incomplete
queries, stale/ambiguous/pre-job samples, deadline expiry, approval/job failures and
notification failure. Controlled runtime routing tests override AAP/Slack and the
final gate: they are not proof of real device recovery. A separate live read-only
test starts directly at verification without AAP proof and must fail closed.

## First real approved run and cutoff correction

Run 5fa91782-a956-4001-bfcd-c3b3ba9e6393 successfully completed actual AAP jobs
322/JT38, 324/JT39, 326/JT40 and 328/JT41. The first verifier version omitted clear
logs because it began querying at JT39 completion (01:08:10.469911Z), while the
matching deletions were emitted during that job at 01:08:08.723Z. The corrected
window begins at JT39 start, 01:08:01.875730Z, while all metric samples still must
follow completion of the verification jobs. Pre-start deletions remain rejected.

Read-only replay bbcfaa49-543c-405c-8c0c-f7665d8faeed reused the original authenticated
approval and successful job records, queried current real Datadog telemetry, and
passed all 13 criteria at 01:14:31.645Z. It did not rerun AAP jobs or send Slack
messages. This is a corrected verification replay, not a rewritten result for the
original workflow instance. Exact evidence is in first-live-aap-recovery-evidence.json.

The original instance finished at 01:20:56Z with runtime SUCCEEDED but business result RECOVERY_NOT_VERIFIED. Its old cutoff excluded the matching clears; the ten-minute bound expired and Slack escalation succeeded. At that point, only the corrected replay had passed; the later fresh full test is recorded below.

## Fresh full recovery test passed — Nov 8, 2026

Actual monitor-triggered run 15951b0a-c1e1-45b8-9604-5c1dae1462e1 completed at 02:34:35Z with runtime SUCCEEDED and result RECOVERY_VERIFIED. Real Slack approval led to successful jobs 332/JT38, 334/JT39, 336/JT40 and 338/JT41. All 13 telemetry criteria passed at 02:34:31.249Z, including matching clears emitted during isolation, stable isolated/trusted port states, zero forwarding loss, fresh collector, monitor OK and five-minute quiet observation. Slack_Recovery_Verified succeeded in #datadog-automation with ts1794105274.450979. This run used no action overrides or mocked notifications.

JT42/job330 restored e1/2 before this test under explicit user authorization. The successful test left e1/2 isolated; no automatic restore followed. Verified scope remains containment and forwarding with Datadog log clearance; a direct empty device MAC table or physical loop clearance is not claimed. Exact evidence: datadog/workflows/live-end-to-end-recovery-evidence.json. The earlier false-negative run remains historical evidence of the cutoff defect.
