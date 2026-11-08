# AAP generator Job Templates

The templates are live: **Start JT45** and **Stop JT46**. The **98-step Scenario
Controller is published**, using the user-selected connection for
`svc-datadog-fault-control` (user4). Read-only checks confirm Execute access to
JT41/42/45/46, project37/inventory7, Ubuntu credential9 and prompted variables.

Network branches retain all application scenario steps, verify template identity
and the Linux credential against JT41, require generator state artifacts, and
stop on failure without automatic relaunch. Slack messages use #datadog-workflow,
matching the existing controller. Eight local scenario fixtures passed.

The first real Stop job341 failed because the file task lacked root permissions.
The corrected controller explicitly passes sudo/root become variables to the
generator templates. Successful Start then ran jobs343/JT46 →345/JT42 →347/JT45,
and real duplicate-MAC logs appeared from sw1 at04:54:46.854Z. Exact start/reset
results and Slack delivery evidence are in
`datadog/workflows/generator-controller-binding-evidence.json`.

The real reset run also succeeded: jobs349/JT46 →351/JT42 →353/JT41. Stop artifacts
confirmed PID0 and stopped service; SNMP confirmed e1/2 admin/oper up after restore,
and JT41 independently verified forwarding. Both real controller runs delivered
success messages to #datadog-workflow. The reset left the managed generator stopped
and e1/2 up. This is scenario reset evidence, not a RECOVERY_VERIFIED result from
the separately approval-gated recovery workflow. The five-minute log monitor may
remain Alert temporarily after reset while the prior detections leave its window.

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
ansible_become: true
ansible_become_user: root
ansible_become_method: sudo
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

The published controller uses these fixed IDs in explicit controller paths
are explicit manual actions:

- `mac-flapping`: JT46 Stop Generator → JT42 restore e1/2 → JT45 Start Generator.
- `reset-mac-flapping`: JT46 Stop Generator → JT42 restore e1/2 → JT41 verify forwarding.

These paths are live. Existing recovery remains approval-gated. AAP job
completion alone does not establish Datadog detection or verified recovery.
Start execution is a controlled lab fault test; it can
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

## Full test from Scenario Controller through verified recovery — Nov 8

Controller instance2cec29b5-e4ba-4e07-96f5-f8efe88a9343 ran successful jobs355/JT46 →357/JT42 →359/JT45. Real duplicate-MAC logs from sw1 at05:29:12.993Z triggered monitor340593559 and recovery instance07dec5e0-d403-4d0e-ba7c-e6d7db4d30b6. Parsing returned2detections,0unparsed. Authenticated Slack approval was recorded at05:31:06.380Z.

Actual recovery jobs361/JT38,363/JT39,365/JT40 and367/JT41 all succeeded. All13criteria passed at05:39:31.505Z, attempt8; the workflow completed RECOVERY_VERIFIED at05:39:36.013866Z. Actual recovery Slack delivery succeeded to #datadog-automation at05:39:34.901964Z, ts1794116374.741359. No mocked actions, replay, escalation or automatic restore. Verified scope remains containment/forwarding with matching Datadog log clearance, not a physical-loop or directly empty-device-table claim.

At final recheck07:18:02Z, the monitor was OK and the latest e1/2 SNMP oper value was2/down (07:17:46Z). The port remained isolated; a reset/restore requires a separate user request. Exact evidence is in datadog/workflows/scenario-controller-full-recovery-evidence.json.
