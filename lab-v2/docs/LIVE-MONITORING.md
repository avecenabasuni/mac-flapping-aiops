# Live deployment — 2026-11-06

Dashboard: https://app.datadoghq.com/dashboard/rtw-gpm-4t5

The dashboard was created and read back with 21 widgets. It has not been visually
verified in the browser. Ubuntu, SNMP, four container states and C-to-A probe metrics
were present. Custom container CPU/memory/PIDs had no series.

18 additional monitors were created and validated. They are **draft, P5**, because
the creation tool enforces draft mode and manual UI publication. Computer Use could
not determine the Chrome URL and stopped before publication. They do not notify.
The intended source templates retain P3; select P3 when reviewing/publishing.

Use Manage Monitors, filter `tag:lab_id:macflap-v2` and review each draft before
publishing. IDs, exact saved definitions and publication links are in
`datadog/lab-v2-deployment.json`. Do not create duplicates.

The existing global memory monitor 340591132 already covers this Ubuntu host, so
the additional Ubuntu memory template was not created. No existing monitor changed.
The disk query excludes `/dev/loop*` and tmpfs to avoid read-only loop filesystem
usage alerts. e1/2 admin-disabled remains excluded from the unexpected-down monitor.

Initial evaluation: 14 OK, collector Warn, CPU and memory No Data, inbound discards
Alert. These are draft evaluation states, not sent alerts. Inbound discard samples
included the management sub-interface; inspect the source and baseline before tuning.
The collector warning corresponds to missing custom Docker resource metrics and
needs local `docker stats` / Agent-check diagnostics. Container state and ping
collection succeeded; that does not establish complete network recovery.

SNMP configuration containing a community must be readable by the Agent account:

```bash
sudo chown root:dd-agent /etc/datadog-agent/conf.d/snmp.d/conf.yaml
sudo chmod 640 /etc/datadog-agent/conf.d/snmp.d/conf.yaml
```
