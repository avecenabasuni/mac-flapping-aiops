"""Observe the fixed macflap-v2 lab; never start/stop containers or change ports."""
import json
import math
import re
from datetime import datetime, timezone

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.subprocess_output import get_subprocess_output


CONTAINERS = (
    "clab-macflap-v2-sw1",
    "clab-macflap-v2-host-a",
    "clab-macflap-v2-host-b",
    "clab-macflap-v2-host-c",
)
PREFIX = "network_aiops.lab."


def percent(text):
    match = re.fullmatch(r"([0-9]+(?:[.][0-9]+)?)%", text.strip())
    if not match:
        raise ValueError("Missing or invalid percentage")
    value = float(match[1])
    if not math.isfinite(value):
        raise ValueError("Non-finite percentage")
    return value


def memory_bytes(text):
    match = re.fullmatch(r"\s*([0-9]+(?:[.][0-9]+)?)\s*([A-Za-z]+)\s*", text)
    units = {"B": 1, "kB": 1000, "KB": 1000, "MB": 1000**2, "GB": 1000**3,
             "TB": 1000**4, "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3, "TiB": 1024**4}
    if not match or match[2] not in units:
        raise ValueError("Invalid Docker memory size")
    value = float(match[1]) * units[match[2]]
    if not math.isfinite(value):
        raise ValueError("Non-finite memory size")
    return value


def parse_ping(text, expected_packets=3):
    summaries = re.findall(
        r"(?m)^(\d+) packets transmitted, (\d+)(?: packets)? received,"
        r" ([0-9]+(?:[.][0-9]+)?)% packet loss(?:,|$)", text)
    if len(summaries) != 1:
        raise ValueError("Expected one complete ping summary")
    transmitted, received, printed_loss = summaries[0]
    transmitted, received = int(transmitted), int(received)
    if transmitted != expected_packets or not 0 <= received <= transmitted:
        raise ValueError("Incomplete or invalid ping sample")
    loss = 100.0 * (transmitted - received) / transmitted
    if abs(float(printed_loss) - loss) > 1:
        raise ValueError("Inconsistent ping summary")
    latency = re.findall(
        r"(?m)^(?:rtt|round-trip) min/avg/max/(?:mdev|stddev) = "
        r"([0-9.]+)/([0-9.]+)/([0-9.]+)/([0-9.]+) ms\s*$", text)
    avg_ms = None
    if received:
        if len(latency) != 1:
            raise ValueError("Missing or ambiguous RTT")
        avg_ms = float(latency[0][1])
        if not math.isfinite(avg_ms) or avg_ms < 0:
            raise ValueError("Invalid RTT")
    return loss, avg_ms


class LabObservability(AgentCheck):
    def _run(self, args):
        # GNU timeout bounds Docker/socket failures as well as the probe.
        return get_subprocess_output(
            ["/usr/bin/timeout", "--kill-after=1s", "8s", "/usr/bin/docker"] + args,
            self.log, raise_on_empty_output=False, log_debug=False)

    def _status(self, name, status, tags, message):
        self.service_check(PREFIX + name, status, tags=tags, message=message)

    def _container(self, name, present, tags):
        tags = tags + ["lab_container:" + name]
        if not present:
            self.gauge(PREFIX + "container.up", 0, tags=tags)
            self._status("container", self.CRITICAL, tags, "Expected lab container is absent")
            return False
        out, _, rc = self._run(["inspect", name])
        if rc != 0:
            raise ValueError("Cannot inspect expected container")
        rows = json.loads(out)
        if len(rows) != 1 or rows[0].get("Name", "").lstrip("/") != name:
            raise ValueError("Unexpected Docker inspect response")
        row, state = rows[0], rows[0].get("State", {})
        running = state.get("Running")
        restarts = row.get("RestartCount")
        if type(running) is not bool or type(restarts) is not int or restarts < 0:
            raise ValueError("Missing container state")
        self.gauge(PREFIX + "container.up", int(running), tags=tags)
        self.gauge(PREFIX + "container.restart_count", restarts, tags=tags)
        status = self.OK if running else self.CRITICAL
        health = state.get("Health", {}).get("Status")
        if health in ("healthy", "unhealthy"):
            self.gauge(PREFIX + "container.healthy", int(health == "healthy"), tags=tags)
            if health == "unhealthy":
                status = self.CRITICAL
        self._status("container", status, tags, "Observed Docker running/health state")
        if running:
            started = datetime.fromisoformat(state["StartedAt"].replace("Z", "+00:00"))
            uptime = (datetime.now(timezone.utc) - started).total_seconds()
            if uptime < 0:
                raise ValueError("Container start time is in the future")
            self.gauge(PREFIX + "container.uptime_seconds", uptime, tags=tags)
        return running

    def _stats(self, running, tags):
        if not running:
            return
        out, _, rc = self._run(["stats", "--no-stream", "--format", "{{json .}}"] + running)
        if rc != 0:
            raise ValueError("Docker stats unavailable")
        rows = [json.loads(line) for line in out.splitlines() if line.strip()]
        by_name = {row["Name"]: row for row in rows}
        if len(rows) != len(running) or set(by_name) != set(running):
            raise ValueError("Incomplete or duplicate Docker stats")
        for name in running:
            row = by_name[name]
            cpu, mem_pct = percent(row["CPUPerc"]), percent(row["MemPerc"])
            used, limit = [memory_bytes(x) for x in row["MemUsage"].split("/")]
            pids = int(row["PIDs"])
            if mem_pct > 100 or limit <= 0 or used > limit or pids < 0:
                raise ValueError("Invalid Docker resource values")
            ct = tags + ["lab_container:" + name]
            for metric, value in (("cpu_pct", cpu), ("memory_pct", mem_pct),
                                  ("memory_used_bytes", used), ("memory_limit_bytes", limit),
                                  ("pids", pids)):
                self.gauge(PREFIX + "container." + metric, value, tags=ct)

    def _probe(self, tags):
        pt = tags + ["probe:host-c-to-host-a"]
        out, _, rc = self._run([
            "exec", "clab-macflap-v2-host-c", "ping", "-n", "-I", "eth1",
            "-c", "3", "-i", "0.2", "-W", "1", "-w", "4", "198.18.0.11"])
        if rc not in (0, 1):
            raise ValueError("Ping execution failed; no connectivity conclusion")
        loss, avg_ms = parse_ping(out)
        if rc != 0 and loss == 0:
            raise ValueError("Ping exit code conflicts with summary")
        self.gauge(PREFIX + "probe.loss_pct", loss, tags=pt)
        if avg_ms is not None:
            self.gauge(PREFIX + "probe.rtt_avg_ms", avg_ms, tags=pt)
        self._status("forwarding", self.OK if loss == 0 else self.CRITICAL, pt,
                     "Independent Host C to Host A ICMP sample; not a recovery declaration")

    def check(self, instance):
        tags = list(instance.get("tags", []))
        # This heartbeat says the check ran, not that the lab is healthy.
        self.gauge(PREFIX + "collector.heartbeat", 1, tags=tags)
        try:
            out, _, rc = self._run(["ps", "-a", "--format", "{{.Names}}"])
            if rc != 0:
                raise ValueError("Cannot read Docker inventory")
            present = set(out.splitlines())
        except Exception:
            self._status("collector", self.CRITICAL, tags, "Docker inventory unavailable")
            for name in CONTAINERS:
                self._status("container", self.UNKNOWN, tags + ["lab_container:" + name],
                             "Docker inventory unavailable; container state unknown")
            self._status("forwarding", self.UNKNOWN, tags + ["probe:host-c-to-host-a"],
                         "Probe not executed")
            return
        errors, running = [], []
        for name in CONTAINERS:
            try:
                if self._container(name, name in present, tags):
                    running.append(name)
            except Exception:
                errors.append("container state unavailable")
                self._status("container", self.UNKNOWN, tags + ["lab_container:" + name],
                             "Container inspection incomplete")
        try:
            self._stats(running, tags)
        except Exception:
            errors.append("container resource stats unavailable")
        try:
            self._probe(tags)
        except Exception:
            errors.append("forwarding probe unavailable")
            self._status("forwarding", self.UNKNOWN, tags + ["probe:host-c-to-host-a"],
                         "Probe could not produce a complete sample")
        self._status("collector", self.WARNING if errors else self.OK, tags,
                     "; ".join(errors) if errors else "Configured telemetry collected")
