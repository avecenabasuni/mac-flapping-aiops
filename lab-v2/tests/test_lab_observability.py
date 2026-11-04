"""Fixture tests: no Docker daemon, ping, Agent or network access is needed."""
import importlib.util
import json
import logging
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class FakeAgentCheck:
    OK, WARNING, CRITICAL, UNKNOWN = 0, 1, 2, 3

    def __init__(self):
        self.log = logging.getLogger("test")
        self.metrics = []
        self.statuses = []

    def gauge(self, name, value, tags=None):
        self.metrics.append((name, value, tags))

    def service_check(self, name, status, tags=None, message=None):
        self.statuses.append((name, status, tags, message))


base = types.ModuleType("datadog_checks.base")
base.AgentCheck = FakeAgentCheck
subprocess_module = types.ModuleType("datadog_checks.base.utils.subprocess_output")
subprocess_module.get_subprocess_output = lambda *args, **kwargs: None
modules = {
    "datadog_checks": types.ModuleType("datadog_checks"),
    "datadog_checks.base": base,
    "datadog_checks.base.utils": types.ModuleType("datadog_checks.base.utils"),
    "datadog_checks.base.utils.subprocess_output": subprocess_module,
}
path = Path(__file__).resolve().parents[2] / "datadog/agent/checks.d/lab_observability.py"
spec = importlib.util.spec_from_file_location("lab_observability_test_target", path)
collector = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, modules):
    spec.loader.exec_module(collector)


def ping(received=3):
    loss = 100 * (3 - received) / 3
    summary = f"3 packets transmitted, {received} received, {loss:.0f}% packet loss, time 401ms\n"
    return summary + ("rtt min/avg/max/mdev = 0.100/0.200/0.300/0.010 ms\n" if received else "")


class Parsers(unittest.TestCase):
    def test_ping_healthy(self):
        self.assertEqual(collector.parse_ping(ping()), (0.0, 0.2))

    def test_partial_loss_is_not_zero(self):
        self.assertAlmostEqual(collector.parse_ping(ping(2))[0], 100 / 3)

    def test_total_loss_has_no_fabricated_latency(self):
        self.assertEqual(collector.parse_ping(ping(0)), (100.0, None))

    def test_invalid_or_incomplete_ping_is_rejected(self):
        for output in ["", "permission denied", ping() + ping(),
                       ping().replace("3 packets transmitted", "1 packets transmitted"),
                       ping().replace("3 received", "9 received"),
                       ping().replace("0% packet loss", "80% packet loss"),
                       "3 packets transmitted, 3 received, 0% packet loss"]:
            with self.subTest(output=output):
                with self.assertRaises(ValueError):
                    collector.parse_ping(output)

    def test_cpu_multicore_and_binary_memory(self):
        self.assertEqual(collector.percent("125.5%"), 125.5)
        self.assertEqual(collector.memory_bytes("1.5GiB"), 1.5 * 1024**3)
        self.assertEqual(collector.memory_bytes("64 MB"), 64 * 1000**2)

    def test_invalid_stats_are_rejected(self):
        for text in ["", "NaN%", "-1%", "Infinity%"]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                collector.percent(text)
        with self.assertRaises(ValueError):
            collector.memory_bytes("1 mystery-unit")


class CheckBehavior(unittest.TestCase):
    def setUp(self):
        self.check = collector.LabObservability()

    def respond(self, args):
        command = args[0]
        if command == "ps":
            return "\n".join(collector.CONTAINERS), "", 0
        if command == "inspect":
            return json.dumps([{
                "Name": "/" + args[1], "RestartCount": 2,
                "State": {"Running": True, "StartedAt": "2026-01-01T00:00:00Z"},
            }]), "", 0
        if command == "stats":
            rows = [{"Name": name, "CPUPerc": "12.5%", "MemPerc": "6.25%",
                     "MemUsage": "64MiB / 1GiB", "PIDs": "2"} for name in collector.CONTAINERS]
            return "\n".join(json.dumps(row) for row in rows), "", 0
        if command == "exec":
            self.assertEqual(args[1], "clab-macflap-v2-host-c")
            self.assertEqual(args[-1], "198.18.0.11")
            return ping(), "", 0
        self.fail("Unexpected Docker command: " + repr(args))

    def test_healthy_collection_covers_all_expected_containers(self):
        with patch.object(self.check, "_run", side_effect=self.respond):
            self.check.check({})
        ups = [m for m in self.check.metrics if m[0].endswith("container.up")]
        self.assertEqual(len(ups), 4)
        self.assertTrue(all(m[1] == 1 for m in ups))
        cpus = [m for m in self.check.metrics if m[0].endswith("container.cpu_pct")]
        self.assertEqual(len(cpus), 4)
        self.assertTrue(all(s[1] == self.check.OK for s in self.check.statuses))

    def test_docker_permission_failure_is_unknown_not_container_absent(self):
        with patch.object(self.check, "_run", return_value=("", "permission denied", 1)):
            self.check.check({})
        self.assertFalse(any(m[0].endswith("container.up") for m in self.check.metrics))
        self.assertEqual(self.check.statuses[0][1], self.check.CRITICAL)
        self.assertTrue(all(s[1] == self.check.UNKNOWN for s in self.check.statuses[1:]))

    def test_missing_container_is_critical(self):
        self.assertFalse(self.check._container(collector.CONTAINERS[0], False, []))
        self.assertEqual(self.check.metrics[0][1], 0)
        self.assertEqual(self.check.statuses[0][1], self.check.CRITICAL)

    def test_stopped_container_is_not_healthy(self):
        response = [{"Name": "/" + collector.CONTAINERS[0], "RestartCount": 1,
                     "State": {"Running": False}}]
        with patch.object(self.check, "_run", return_value=(json.dumps(response), "", 0)):
            self.assertFalse(self.check._container(collector.CONTAINERS[0], True, []))
        self.assertEqual(self.check.metrics[0][1], 0)

    def test_unhealthy_healthcheck_is_critical_even_when_running(self):
        response = [{"Name": "/" + collector.CONTAINERS[0], "RestartCount": 0,
                     "State": {"Running": True, "StartedAt": "2026-01-01T00:00:00Z",
                               "Health": {"Status": "unhealthy"}}}]
        with patch.object(self.check, "_run", return_value=(json.dumps(response), "", 0)):
            self.check._container(collector.CONTAINERS[0], True, [])
        self.assertEqual(self.check.statuses[0][1], self.check.CRITICAL)

    def test_packet_loss_is_a_forwarding_incident_not_collector_error(self):
        def respond(args):
            return (ping(2), "", 0) if args[0] == "exec" else self.respond(args)
        with patch.object(self.check, "_run", side_effect=respond):
            self.check.check({})
        forwarding = next(s for s in self.check.statuses if s[0].endswith("forwarding"))
        self.assertEqual(forwarding[1], self.check.CRITICAL)
        self.assertEqual(self.check.statuses[-1][1], self.check.OK)

    def test_probe_error_emits_no_fake_loss_or_latency(self):
        def respond(args):
            return ("", "execution failed", 126) if args[0] == "exec" else self.respond(args)
        with patch.object(self.check, "_run", side_effect=respond):
            self.check.check({})
        self.assertFalse(any(".probe." in m[0] for m in self.check.metrics))
        self.assertEqual(self.check.statuses[-1][1], self.check.WARNING)

    def test_incomplete_stats_do_not_report_collection_success(self):
        def respond(args):
            return ("", "", 0) if args[0] == "stats" else self.respond(args)
        with patch.object(self.check, "_run", side_effect=respond):
            self.check.check({})
        self.assertEqual(self.check.statuses[-1][1], self.check.WARNING)

    def test_command_timeout_is_bounded_without_shell(self):
        with patch.object(collector, "get_subprocess_output", return_value=("", "", 124)) as run:
            self.assertEqual(self.check._run(["ps"])[2], 124)
        command = run.call_args.args[0]
        self.assertEqual(command[:4], ["/usr/bin/timeout", "--kill-after=1s", "8s", "/usr/bin/docker"])


if __name__ == "__main__":
    unittest.main()
