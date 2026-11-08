# Verification regression checks

`test_generator.py` covers the fixed endpoint generator, bounded duration,
startup readiness, stop and command timeout without contacting Docker or AAP.

`node --test lab-v2/tests/test_workflow_scenarios.cjs` exercises the saved generator
controller draft: fixed JT45/46 sequences, template/credential identity checks,
ambiguous launches, missing job artifacts, bounded polling and safe failure.

These offline tests load the conditions from the Ansible playbooks and evaluate
them against fixtures using Jinja2 and Python regex matching. They do not contact
Datadog, AAP, Docker, or SR Linux.

The suite also tests the full-lab collector with a stub AgentCheck and fixture Docker/ping responses: missing/stopped/unhealthy containers, permission failures, incomplete stats, command timeout, partial/total loss and malformed probe output. No actual Docker or ping command is executed by these tests.

From the repository root:

```bash
python -m pip install PyYAML Jinja2
python -m unittest discover -s lab-v2/tests -v
```

Covered cases: exact zero loss, decimal zero, partial/total packet loss, failed
ping, missing or ambiguous ping output, correct containment, every incorrect
port state, and missing/malformed device data.

Device verification requires e1/1 enable/up, e1/2 disable/down, and e1/3 enable/up.
The Nokia get module returns leaf values in request order:
https://learn.srlinux.dev/ansible/collection/get/#result

A successful device check is still separate from Host C to Host A forwarding and
MAC duplication/hold-down inspection. Actual AAP/SR Linux execution remains a
required integration test.

Workflow chronology and POC message fixtures use Node.js separately:

~~~bash
node --test lab-v2/tests/test_workflow_timeline.cjs
~~~

These tests execute the scripts from the exported workflow JSON, with fixture log/agent inputs. They do not contact Datadog or create investigations.

Telemetry verifier fixtures (positive proof and failure cases):

```bash
node --test lab-v2/tests/test_workflow_recovery.cjs
```
