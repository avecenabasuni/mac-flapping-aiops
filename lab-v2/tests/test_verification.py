"""Offline regression checks for the conditions stored in the real playbooks.

These tests evaluate Jinja conditions with fixtures; they do not run AAP or SR Linux.
"""
import re
import unittest
from pathlib import Path

import yaml
from jinja2 import Environment, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]
ENV = Environment(undefined=StrictUndefined)
# Ansible regex_findall uses Python regular-expression matching.
ENV.filters["regex_findall"] = lambda text, pattern: re.findall(pattern, text)


def tasks(filename):
    return yaml.safe_load((ROOT / "ansible" / filename).read_text())[0]["tasks"]


def passes(conditions, **context):
    return all(bool(ENV.compile_expression(condition)(**context)) for condition in conditions)


class ForwardingVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conditions = next(t["until"] for t in tasks("verify-forwarding.yml") if "until" in t)

    def check_loss(self, loss, expected, rc=0):
        probe = {"rc": rc, "stdout": f"5 packets transmitted, 4 received, {loss}% packet loss, time 1600ms"}
        self.assertEqual(passes(self.conditions, probe=probe), expected)

    def test_exact_zero_and_decimal_zero(self):
        for loss in ["0", "0.0", "0.000"]:
            with self.subTest(loss=loss):
                self.check_loss(loss, True)

    def test_partial_and_total_loss_rejected(self):
        for loss in ["0.1", "1", "10", "20", "40", "60", "80", "100"]:
            with self.subTest(loss=loss):
                self.check_loss(loss, False)

    def test_command_error_rejected_even_with_zero_loss(self):
        self.check_loss("0", False, rc=2)

    def test_missing_malformed_and_multiple_summaries_rejected(self):
        for probe in [
            {"rc": 0},
            {"rc": 0, "stdout": ""},
            {"rc": 0, "stdout": "ping failed"},
            {"rc": 0, "stdout": "5 packets transmitted, 0% packet loss\n5 packets transmitted, 20% packet loss"},
        ]:
            with self.subTest(probe=probe):
                self.assertFalse(passes(self.conditions, probe=probe))


class DeviceVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks = tasks("verify.yml")
        cls.conditions = next(t["ansible.builtin.assert"]["that"] for t in cls.tasks
                              if "ansible.builtin.assert" in t)
        cls.healthy = ["enable", "up", "disable", "down", "enable", "up"]

    def test_expected_containment_passes(self):
        self.assertTrue(passes(self.conditions, interface_state={"result": self.healthy}))

    def test_every_wrong_port_state_rejected(self):
        for index in range(len(self.healthy)):
            observed = self.healthy.copy()
            observed[index] = {"enable": "disable", "disable": "enable",
                               "up": "down", "down": "up"}[observed[index]]
            with self.subTest(index=index):
                self.assertFalse(passes(self.conditions, interface_state={"result": observed}))

    def test_missing_truncated_or_malformed_state_rejected(self):
        for state in [{}, {"result": []}, {"result": self.healthy[:-1]},
                      {"result": None}, {"result": "enable up disable down enable up"},
                      {"result": self.healthy + ["extra"]}]:
            with self.subTest(state=state):
                self.assertFalse(passes(self.conditions, interface_state=state))

    def test_leaf_query_order_matches_assertion(self):
        query = next(t["nokia.srlinux.get"]["paths"] for t in self.tasks
                     if t.get("register") == "interface_state")
        self.assertEqual([p["path"] for p in query], [
            "/interface[name=ethernet-1/1]/admin-state",
            "/interface[name=ethernet-1/1]/oper-state",
            "/interface[name=ethernet-1/2]/admin-state",
            "/interface[name=ethernet-1/2]/oper-state",
            "/interface[name=ethernet-1/3]/admin-state",
            "/interface[name=ethernet-1/3]/oper-state",
        ])
        self.assertTrue(all(p["datastore"] == "state" for p in query))


if __name__ == "__main__":
    unittest.main()
