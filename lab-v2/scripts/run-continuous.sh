#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
DELAY="${FLAP_DELAY:-0.4}"
DURATION="${MAX_SECONDS:-600}"  # bounded safety limit: 10 minutes
[[ "$DELAY" =~ ^[0-9]+([.][0-9]+)?$ ]] || { echo "FLAP_DELAY must be numeric" >&2; exit 2; }
[[ "$DURATION" =~ ^[0-9]+$ ]] && (( DURATION >= 10 && DURATION <= 1800 )) || { echo "MAX_SECONDS must be 10..1800" >&2; exit 2; }
for node in host-a host-b host-c; do sudo docker inspect "clab-macflap-v2-$node" >/dev/null 2>&1 || { echo "Missing v2 $node" >&2; exit 1; }; done
trap 'echo; echo "Traffic generator stopped; verify forwarding before claiming recovery."' INT TERM
echo "Starting continuous duplicate-MAC traffic (max ${DURATION}s). Press Ctrl+C to stop."
echo "Trusted Host A e1/1; spoofing Host B e1/2; MAC 02:00:00:00:00:aa"
started=$SECONDS
round=0
while (( SECONDS - started < DURATION )); do
  round=$((round + 1))
  # Real Host A sends matching source MAC, while Host B spoofs it.
  sudo docker exec clab-macflap-v2-host-a python3 /opt/lab/send_frame.py --mac 02:00:00:00:00:aa --sender-ip 198.18.0.11
  sleep "$DELAY"
  sudo docker exec clab-macflap-v2-host-b python3 /opt/lab/send_frame.py --mac 02:00:00:00:00:aa --sender-ip 198.18.0.99
  sleep "$DELAY"
  if (( round % 10 == 0 )); then echo "Rounds: $round; generator still active"; fi
done
echo "Reached MAX_SECONDS=$DURATION. Generator stopped automatically for lab safety."
