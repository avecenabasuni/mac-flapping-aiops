#!/usr/bin/env bash
set -euo pipefail
echo "=== V2 topology ==="
sudo containerlab inspect -t "$(dirname "$0")/../macflap-v2.clab.yml"
echo
echo "=== Expected source MACs and interface states ==="
for node in host-a host-b host-c; do
  echo "-- $node --"
  sudo docker exec "clab-macflap-v2-$node" ip -brief link show eth1
  sudo docker exec "clab-macflap-v2-$node" ip -brief addr show eth1
done
echo
echo "=== SR Linux state should be checked with CLI ==="
echo "sudo docker exec -it clab-macflap-v2-sw1 sr_cli"
echo "show interface ethernet-1/2"
echo "show network-instance mac-flap bridge-table mac-duplication duplicate-entries"
