"""Exercise the actual e1/2 monitor expression over SNMP's state combinations."""
import json
import re
import unittest
from pathlib import Path


class IsolationMonitor(unittest.TestCase):
    def test_only_admin_enabled_non_up_states_alert(self):
        root = Path(__file__).resolve().parents[2]
        path = root / "datadog/monitors/lab-v2/switch-e1-2-unexpected.json"
        query = json.loads(path.read_text())["query"]
        expression = query.split("):", 1)[1].rsplit(" > ", 1)[0]
        expression = re.sub(r"max:snmp.ifOperStatus\{[^}]+\}", "oper", expression)
        expression = re.sub(r"max:snmp.ifAdminStatus\{[^}]+\}", "admin", expression)
        functions = {"__builtins__": {}, "clamp_min": max, "clamp_max": min}
        for admin in (1, 2, 3):
            for oper in range(1, 8):
                with self.subTest(admin=admin, oper=oper):
                    actual = eval(expression, functions, {"admin": admin, "oper": oper})
                    self.assertEqual(actual > 0, admin == 1 and oper != 1)


if __name__ == "__main__":
    unittest.main()
