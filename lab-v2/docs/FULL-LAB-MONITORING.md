# Full lab v2 monitoring configuration

Coverage: Ubuntu VM, SW1, Host A/B/C containers, switch interfaces and independent Host C → Host A forwarding. This is a configuration package only. Committing it does not install collectors or activate monitors.

## Coverage and source

| Object | Collected information | Source |
| --- | --- | --- |
| Ubuntu VM | CPU, usable RAM, filesystem usage, uptime, network traffic | Existing host Agent system integrations |
| SW1 container | Running state, CPU, memory, restart count, uptime, PIDs | New lab_observability Agent check / Docker |
| Host A/B/C | Same per-container metrics; Docker health when defined | Same custom check |
| SW1 interfaces | Admin/oper state, traffic and error/discard rates | SNMP / generic-device profile |
| Management telemetry | SNMP collection status | snmp.can_check |
| Host C → Host A | Packet loss and average RTT; three packets every 60 seconds | Custom check, ICMP on eth1 inside Host C |
| Collector | Heartbeat and success/partial/failure status | Custom check |
| Duplicate MAC | Logs, parsing, alert and Bits AI investigation | Existing tested Datadog path |

SW1 CPU/RAM here means its Linux container resource consumption. This does not claim physical chassis, ASIC, fan, optical or temperature telemetry. Additional hardware metrics require actual device support. A running container does not prove application or forwarding health.

## Files

- [Agent collector](../../datadog/agent/checks.d/lab_observability.py)
- [Collector YAML](../../datadog/agent/lab_observability.d/conf.yaml.example)
- [SNMP YAML](../../datadog/agent/snmp.d/conf.yaml.example)
- [Syslog YAML](../../datadog/agent/syslog.d/conf.yaml.example)
- [Agent log-enablement fragment](../../datadog/agent/datadog.yaml.fragment.example)
- [Switch SNMP CLI](../monitoring/sw1-snmp.cli.example)
- [19 draft monitor definitions](../../datadog/monitors/lab-v2/)
- [Dashboard JSON: 21 widgets](../../datadog/dashboards/full-lab-observability.json)
- [SNMP setup details](DEVICE-MONITORING.md)

## Install on Ubuntu yourself

Keep the existing Agent API key, site and working integrations. The YAML fragment is not a replacement for the full datadog.yaml.

From the repository root on the Ubuntu lab VM:

~~~bash
command -v docker timeout
sudo docker inspect clab-macflap-v2-sw1 \
  clab-macflap-v2-host-a clab-macflap-v2-host-b clab-macflap-v2-host-c

sudo install -d /etc/datadog-agent/checks.d
sudo install -d /etc/datadog-agent/conf.d/lab_observability.d
sudo install -m 0644 datadog/agent/checks.d/lab_observability.py \
  /etc/datadog-agent/checks.d/lab_observability.py
sudo install -m 0644 datadog/agent/lab_observability.d/conf.yaml.example \
  /etc/datadog-agent/conf.d/lab_observability.d/conf.yaml
~~~

The collector expects /usr/bin/docker and /usr/bin/timeout (Ubuntu coreutils). Adjust those fixed paths before installing if yours differ. Commands do not use a shell.

The Agent service user needs local Docker access. If using the Docker group on this isolated lab VM, configure it explicitly and restart the service:

~~~bash
sudo usermod -aG docker dd-agent
sudo systemctl restart datadog-agent
sudo -u dd-agent /usr/bin/docker ps
sudo datadog-agent configcheck
sudo datadog-agent check lab_observability
sudo datadog-agent status
~~~

Docker group access grants control over the local Docker daemon, even though this collector only observes state and runs the fixed ping probe. Apply this access change according to the lab host's access policy. If the Agent uses another account, substitute that account.

Configure SNMP and syslog through the linked guide. Do not bind UDP 10514 twice. The custom check already supplies the four lab containers' resource metrics; an extra collector for the same custom metric names is unnecessary. Native Container Explorer/discovery is a separate optional integration; this custom check does not populate that inventory.

## Acceptance before importing monitors

1. Confirm Ubuntu system metrics use host:network-aiops-lab. Replace this hostname in monitor/dashboard JSON if yours differs.
2. Run the check as the Agent; confirm four lab_container groups, CPU/RAM/restart/uptime metrics, and a current collector heartbeat.
3. Confirm probe:host-c-to-host-a results. Docker failures or incomplete ping output produce UNKNOWN and no fabricated packet-loss/latency sample.
4. Confirm SNMP device/interfaces carry lab_id:macflap-v2 and lab_device:sw1. Check that actual interface tags use ethernet-1/1, ethernet-1/2 and ethernet-1/3; adjust queries to actual values.
5. Confirm the separate .rate metrics for errors, discards and octets. Do not apply a per-second threshold to the raw count metric.
6. Import dashboard JSON through the dashboard editor. Monitor JSON files are individual API payloads; adapt them to your import tool. All include draft_status: draft. None were activated by these repository changes.
7. Review existing monitors to avoid duplicate Ubuntu alerts. Tune initial thresholds against the healthy baseline, then publish only the desired monitors. Source groups must report before no-data/group behavior can be verified; API validation alone is insufficient.

## Monitor behavior

The 19 templates cover Ubuntu CPU/RAM/disk/telemetry; container state/CPU/RAM; collector heartbeat/status; forwarding/latency; SNMP collection; trusted/probe port state; unexpected e1/2 state; and inbound/outbound error/discard rates.

The e1/2 expression combines numeric SNMP states: admin=up and oper≠up is unexpected. Admin=down masks this particular condition, including oper-states other than down. This does not mean every shutdown is authorized: inspect the admin-state chart and approval evidence. e1/1 and e1/3 must remain up during containment.

Service-check templates require three consecutive critical/warning samples. A three-packet sample each minute is not a continuous SLA measurement. RTT is emitted only with valid replies; total loss does not fabricate 0 ms. Docker CPU uses one-core percentage (multi-core usage may exceed 100%). Restart count and uptime can reset when a container is recreated.

Quiet MAC logs, a green monitor, or successful ping alone do not establish recovery. Keep device state, independent forwarding, duplicate-MAC/hold-down and approval evidence distinct.

## Validation performed

- 19 monitor definitions passed the Datadog definition validation API.
- 24 distinct dashboard metric queries were accepted by the timeseries query API. Ubuntu queries returned data; new custom/SNMP queries had no series before deployment. This verifies query syntax, not new-source ingestion.
- 24 offline fixture tests cover collector behavior, the Ansible verification conditions and the e1/2 monitor truth table. They do not execute Docker, AAP or the switch.
- Dashboard JSON has not been imported/rendered in the live account.

Run tests from the repository root:

~~~bash
python -m pip install PyYAML Jinja2
python -m unittest discover -s lab-v2/tests -v
~~~

No AAP start/stop/reset job was added. The Scenario Controller placeholders and existing live MAC-flapping monitor/workflow remain unchanged.

## Official references

- https://docs.datadoghq.com/extend/custom_checks/write_agent_check/
- https://docs.datadoghq.com/extend/service_checks/agent_service_checks_submission/
- https://github.com/DataDog/integrations-core/blob/master/snmp/metadata.csv
- https://learn.srlinux.dev/ansible/collection/get/
