#!/usr/bin/env bash
set -euo pipefail
COUNT="${1:-10}"
[[ "$COUNT" =~ ^[0-9]+$ ]] && (( COUNT >= 1 && COUNT <= 120 )) || { echo "Usage: ./scripts/probe.sh [1..120 packets]" >&2; exit 2; }
sudo docker inspect clab-macflap-v2-host-c >/dev/null 2>&1 || { echo "V2 host-c not deployed" >&2; exit 1; }
echo "Host C (198.18.0.13) -> trusted Host A (198.18.0.11), $COUNT ICMP packets"
sudo docker exec clab-macflap-v2-host-c ping -n -I eth1 -c "$COUNT" -i 0.5 -W 1 198.18.0.11
