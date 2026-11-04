# Datadog integration notes

This GitHub repo's `datadog/` directory already contains a saved Datadog monitor, pipeline, Bits analyst and investigation workflow. **Do not replace those resources blindly.** The existing monitor uses `tags:"service:nokia-srlinux"`, because real Nokia logs can have `service=sr_l2_mac_mgr`. The query requires `"duplicate MAC address"` and `"was detected"`, filtering out deleted events and synthetic Syslog tests.

## Point Nokia v2 to the Agent

The Datadog Agent resides on the Ubuntu Containerlab host. Previously `172.20.20.1` was the v1 Docker management gateway; discover the **v2** gateway dynamically:

```bash
sudo docker inspect clab-macflap-v2-sw1 \
  --format '{{range .NetworkSettings.Networks}}{{println .Gateway .IPAddress}}{{end}}'
```

Check the Agent UDP listener with `sudo datadog-agent status`: Syslog collection should show `Status: OK`. If the v2 gateway is reachable, configure SR Linux remote-server **in the Nokia CLI** using the actual gateway and UDP 10514 (subsystem `bridgetable`, priority `notice`), for example:

```text
enter candidate
set / system logging network-instance mgmt
set / system logging remote-server <V2_GATEWAY> transport udp
set / system logging remote-server <V2_GATEWAY> remote-port 10514
set / system logging remote-server <V2_GATEWAY> subsystem bridgetable priority match-above notice
commit now
```

Remove the literal placeholder brackets when entering commands. If the CLI rejects a line, inspect `info system logging` and SR Linux's schema for your version.

Watch `sudo tcpdump -ni any 'udp dst port 10514'`, then trigger the v2 generator and search `"duplicate MAC address" "was detected"` in Datadog Logs Explorer. A matching log must be seen **from v2 SW1** before claiming v2 ingestion works.

## Alarm vs network recovery

MAC movement protection (stop-learning plus hold-down) can suppress new events while the underlying traffic generator continues. Log monitor recovery means **no new detection log** in its window, not that isolation or forwarding restoration occurred. For end-to-end demo success, show: device interface e1/2 disabled by AAP, Host C ping to Host A recovered, and device MAC table / duplicate state stabilized following hold-down. The existing Datadog investigation workflow is read-only and does NOT perform remediation.
