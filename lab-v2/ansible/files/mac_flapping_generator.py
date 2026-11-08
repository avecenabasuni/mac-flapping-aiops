#!/usr/bin/env python3
"""Bounded duplicate-MAC traffic for the fixed macflap-v2 lab endpoints."""
import argparse
import json
import os
import signal
import socket
import subprocess
import threading
import time

ENDPOINTS = (
    ("clab-macflap-v2-host-a", "198.18.0.11"),
    ("clab-macflap-v2-host-b", "198.18.0.99"),
)
MAC = "02:00:00:00:00:aa"


def notify_ready():
    address = os.environ.get('NOTIFY_SOCKET')
    if address:
        if address.startswith('@'):
            address = '\0' + address[1:]
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
            sock.sendto(b'READY=1', address)


def run(duration, stop, on_started=None):
    if not isinstance(duration, int) or not 10 <= duration <= 1800:
        raise ValueError("Duration must be 10..1800 seconds")
    for container, _ in ENDPOINTS:
        inspected = subprocess.run(
            ["docker", "inspect", container], check=True, capture_output=True,
            text=True, timeout=10,
        )
        rows = json.loads(inspected.stdout)
        if len(rows) != 1 or rows[0].get("Name") != "/" + container or not rows[0].get("State", {}).get("Running"):
            raise RuntimeError("Fixed lab endpoint is missing or stopped: " + container)
    deadline = time.monotonic() + duration
    frames = 0
    while not stop.is_set() and time.monotonic() < deadline:
        for container, sender_ip in ENDPOINTS:
            if stop.is_set() or time.monotonic() >= deadline:
                return frames
            subprocess.run(
                ["docker", "exec", container, "python3", "/opt/lab/send_frame.py",
                 "--interface", "eth1", "--mac", MAC, "--sender-ip", sender_ip],
                check=True, timeout=5,
            )
            frames += 1
            if frames == 2 and on_started:
                on_started()
            stop.wait(min(0.4, max(0, deadline - time.monotonic())))
    return frames


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=600)
    args = parser.parse_args()
    stop = threading.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    frames = run(args.duration, stop, on_started=notify_ready)
    print(json.dumps({"managed_generator_stopped": True, "frames_sent": frames}))


if __name__ == "__main__":
    main()
