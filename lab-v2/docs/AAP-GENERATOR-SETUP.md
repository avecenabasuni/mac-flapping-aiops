# AAP generator Job Templates

The templates now exist: **Start JT45** and **Stop JT46**. Read-only checks confirm
project37/inventory7, Ubuntu credential9 and prompted variables. The Scenario
Controller has a validated **98-step saved draft**, but its published version still
has the original placeholders. The draft has not been published or fault-tested:
the selected connection's account, `svc-datadog-fault-control` (user4), still
receives HTTP403 when reading prerequisite JT41 and JT42.

In AAP, open **JT41 → Access → Add → Users → svc-datadog-fault-control → Execute**
and save; repeat on JT42. Granting access only to `svc-datadog-remediation` does
not authorize this selected connection. The account already has Execute on
JT45/46, but cannot edit templates. After access is verified, publish and test the
saved controller draft. No new token is needed.

The draft retains all application scenario steps. Its network branches use the
user-selected existing connection under a separate `NETWORK_AAP` label, verify
the Linux credential against JT41 and require complete generator job artifacts.
Seven local scenario fixtures passed. A read-only runtime test (all launch steps
disabled and Slack mocked) confirmed fail-closed routing on the current403;
it did not execute AAP jobs. See the saved draft and binding evidence under
`datadog/workflows/`.

First sync AAP project **37** with the repository's **main** branch. The two new
playbooks must appear in its playbook selector. Use JT41 (Verify Forwarding) as
the reference for the project's name, execution environment and Linux credential.

| Setting | Start | Stop |
| --- | --- | --- |
| Name | Start MAC Flapping Generator | Stop MAC Flapping Generator |
| Job type | Run | Run |
| Project | Project 37, same as JT41 | Same |
| Inventory | Inventory 7, same as JT41 | Same |
| Playbook | `lab-v2/ansible/start-generator.yml` | `lab-v2/ansible/stop-generator.yml` |
| Execution Environment | Same as JT41; ansible-core 2.14 or newer | Same |
| Machine credential | Linux SSH/become credential from JT41 | Same |
| Limit | `lab_linux` | `lab_linux` |
| Privilege escalation | Enabled | Enabled |
| Variables: Prompt on launch | Enabled | Enabled |
| Concurrent jobs | Disabled | Disabled |
| Job slicing | 1 | 1 |
| Job timeout | 180 seconds | 180 seconds |
| Schedule | None | None |

Use these **Extra Variables** on both templates:

```yaml
lab_id: macflap-v2
scenario_approved: true
```

`lab_linux` must resolve to exactly one Ubuntu Containerlab host. The playbooks
refuse multi-host execution. This is the Linux Machine credential, not the SR
Linux credential used by JT38–40/JT42. Its account must be able to become root
noninteractively, as required for Docker and systemd management.

Give `svc-datadog-fault-control` Read and Execute access to both new templates and
the resource access needed to launch them. Reuse the inventory/credential access
already working for JT41. The service account does not need administrator access.
Do not paste credentials into the playbooks, template variables or repository.

## Behavior and acceptance

Start installs a root-owned Python script and the disabled-at-boot
`network-aiops-mac-flapping.service` on Ubuntu. The service sends fixed
duplicate-source MAC `02:00:00:00:00:aa` frames through `eth1` in only
`clab-macflap-v2-host-a` and `clab-macflap-v2-host-b`, using their existing
`/opt/lab/send_frame.py`. Both endpoint containers must already be running.
No repository checkout on Ubuntu is required: AAP copies the script/unit from
its synced project.

The job waits for systemd readiness after the first successful frame from each
endpoint, then returns while the generator continues for **600 seconds**. There
is a separate 610-second systemd runtime cap. Repeating Start while the service
is active does not restart it or extend its duration. Start does not restore a
disabled e1/2; JT42 is a separate explicit step before injection.

Stop stops only this managed service, checks inactive state and PID 0, and returns
even if it was already stopped. It does not stop an independently launched
`run-continuous.sh` loop. Stop any such terminal loop before switching to this
controller-managed generator. Stop does not enable e1/2 or claim recovery.

Successful jobs publish AAP artifacts for the controller to verify:

| Artifact | Start | Stop |
| --- | --- | --- |
| `macflap_generator_state` | `running` | `stopped` |
| `macflap_lab_id` | `macflap-v2` | `macflap-v2` |
| `macflap_generator_service` | `network-aiops-mac-flapping.service` | Same |
| `macflap_generator_main_pid` | Positive PID | 0 |

The saved draft uses the supplied IDs in these explicit controller paths
are explicit manual actions:

- `mac-flapping`: JT46 Stop Generator → JT42 restore e1/2 → JT45 Start Generator.
- `reset-mac-flapping`: JT46 Stop Generator → JT42 restore e1/2 → JT41 verify forwarding.

These paths are not live yet. Existing recovery remains approval-gated. AAP job
completion alone does not establish Datadog detection or verified recovery.
First real Start execution should be coordinated as a lab fault test; it can
produce a real monitor alert and a new Slack approval request.

## Validation

Offline fixtures cover fixed endpoint/MAC targeting, duration limits, stop,
Docker timeouts, missing/stopped containers and systemd readiness. AAP execution
with the actual Linux credential remains the required integration test.

Pre-publication checks passed: 31 Python regression tests (including seven
generator fixtures), syntax checks for both playbooks with ansible-core 2.16.14,
and systemd unit verification in Linux. These are not a live AAP/lab execution.

The readiness handshake follows the official
[systemd service contract](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html).
