# Live demonstration runbook

## Before the audience arrives

- Build/deploy v2.
- Verify `./scripts/probe.sh 10` succeeds with no fault injection.
- Confirm `ethernet-1/2` is enabled, Nokia MAC-VRF `mac-flap` has three interfaces, and no active MAC duplication.
- Confirm genuine bridge-table Syslog from **v2** is ingested in Datadog. Never substitute `DATADOG_SYSLOG_TEST` as the MAC alarm.
- Have an AAP Job Template tested in check mode, an operator approval step, and a manual rollback ready.
- If a previous test left a MAC-duplication hold-down active, allow it to expire and verify clean baseline before presenting.

## Audience sequence (6–8 minutes)

1. **Healthy baseline** — show Host C→Host A ping and e1/2 enabled.
2. **Inject fault** — Terminal A: `./scripts/run-continuous.sh`. It keeps running until Ctrl+C or maximum 10 minutes.
3. **Detect** — show Nokia duplicate-MAC log and Datadog alert / Bits AI read-only investigation. A MAC duplication is not by itself proof of an L2 loop.
4. **Investigate** — AAP Collect Evidence playbook reads MAC-VRF and interface state. Correlate with log, source MAC, port e1/1/e1/2 and connectivity probe `./scripts/probe.sh 20`.
5. **Approve and contain** — engineer approves isolation of **e1/2 only**. Run AAP Isolate Host B template.
6. **Verify** — show e1/2 administratively disabled, generator *still running*, Host C→Host A probe restored, and no further moved MAC evidence after Nokia's hold-down/aging behavior is understood. Use device table, not just a green monitor.
7. **Close** — AAP and Datadog provide audit trail: detected, diagnosed, approved, isolated, verified.

## Fail-safe / demo contingencies

- If Host C ping does not degrade during MAC duplication, show **MAC duplication event + administratively isolated ingress port** as network containment; do not invent packet loss.
- If Host C ping does not recover immediately, explain `stop-learning` hold-down may preserve a stale forwarding entry for 3 minutes, and wait/check state rather than claiming failure or manually clearing evidence.
- If the Datadog log does not arrive, use Nokia's own output as device evidence, demonstrate forwarding and AAP separately, and call the integration incomplete.
- Do not automatically declare remediation complete from the Datadog log monitor's OK status.

## Rollback and stop

Ctrl+C in Terminal A stops the fault. Manually run approved `ansible/restore-b.yml` to enable e1/2, then verify baseline. Destroy v2 only with `sudo containerlab destroy -t macflap-v2.clab.yml`.
