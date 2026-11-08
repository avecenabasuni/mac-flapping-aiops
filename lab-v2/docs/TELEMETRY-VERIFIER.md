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
7. The post-isolation log query is complete: no pagination, partial status, warnings,
   or unparsed scoped messages. Up to 1000 logs are accepted; overflow fails closed.
8. Every initial or subsequent detection target has a strictly later matching deletion
   after isolation. Matching uses host, normalized MAC, target type and exact target.
   One target's deletion cannot clear another interface or MAC-VRF target.
9. At least five minutes have elapsed after the latest matching clear, with no new
   duplicate-MAC detection in that quiet window.
10. Observation stays within its deadline and no verification read fails.

Temporary missing proof/stability/quiet-window criteria may be observed again until
the bound. Missing execution/approval proof, incomplete log queries or read failures
stop immediately. On success, Slack announces Telemetry Recovery Verified with the
scope and AAP IDs. Otherwise automation stops and escalates RECOVERY_NOT_VERIFIED.
JT42 restore is never automatic. Slack delivery failures remain explicit in output.

38 local fixtures exercise positive evidence, new detections, wrong targets, incomplete
queries, stale/ambiguous/pre-job samples, deadline expiry, approval/job failures and
notification failure. Controlled runtime routing tests override AAP/Slack and the
final gate: they are not proof of real device recovery. A separate live read-only
test starts directly at verification without AAP proof and must fail closed.
