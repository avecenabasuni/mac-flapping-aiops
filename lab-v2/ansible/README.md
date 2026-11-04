# Ansible AAP integration

These playbooks use the official `nokia.srlinux` collection over `ansible.netcommon.httpapi` (JSON-RPC). This is **different from** Ansible's SSH shell execution.

## Setup

Install `ansible.netcommon` and `nokia.srlinux` into an AAP Execution Environment or local Python/Ansible environment:

```bash
ansible-galaxy collection install -r ansible/requirements.yml
```

Copy `inventory.example.yml` to a local, gitignored inventory and replace the IP with the IP **reachable from AAP**, not blindly with Docker's management gateway. Give the AAP job a Machine credential with SR Linux JSON-RPC username/password. On this lab image, the Containerlab default configuration usually enables JSON-RPC, but validate access before running any change.

Create three AAP Job Templates: **Collect Evidence**, **Isolate Host B**, **Verify**. Create a separate, manual-only **Restore Host B** template. Use an AAP **Workflow Job Template** with nodes:

1. Collect Evidence
2. AI-assisted diagnosis (Datadog workflow; evidence and classification must be passed through an integration you actually verify)
3. **Approval** node, requiring an operator
4. Isolate Host B (only on approval)
5. Verify device state and invoke independent Host C forwarding probe

For the isolation job, supply AAP extra-vars **after approval**:

```yaml
lab_id: macflap-v2
target_interface: ethernet-1/2
change_approved: true
```

The `change_approved` variable is a **secondary sanity check**, NOT a security boundary. The AAP Approval node, authenticated RBAC and locked-down credentials are authoritative. Never grant arbitrary callers permission to set this variable and launch the change template directly.

Manual dry-run:

```bash
ansible-playbook -i ansible/inventory.local.yml ansible/collect-evidence.yml
ansible-playbook -i ansible/inventory.local.yml ansible/isolate-b.yml --check -e lab_id=macflap-v2 -e target_interface=ethernet-1/2 -e change_approved=true
```

**The change targets only `ethernet-1/2`.** The host A and C ports are not affected. Do not assume an interface admin-state update clears Nokia's MAC duplication protection immediately; hold-down/aging may require time and a separate device-state check.

### AAP connectivity from a different VM

Docker's management addresses (`172.20.20.x` in the user's v1 environment) normally are **not directly routable** from a separate AAP VM. Check:

```bash
sudo docker inspect clab-macflap-v2-sw1 --format '{{range .NetworkSettings.Networks}}{{println .IPAddress .Gateway}}{{end}}'
```

Prefer a **documented, explicitly routed and firewalled management path** from AAP to this lab subnet, or run an AAP Execution Environment with appropriate network reachability. Avoid exposing JSON-RPC broadly, and never commit credentials.

Official docs: https://learn.srlinux.dev/ansible/collection/ and https://learn.srlinux.dev/ansible/collection/config/
