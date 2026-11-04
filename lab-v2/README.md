# Network AIOps MAC Flapping v2 lab

This is the **network runtime** for the separate `mac-flapping-aiops` repository. Existing Datadog monitoring exports at repository root are preserved.

## Topology

```text
       Nokia SR Linux SW1 (MAC-VRF mac-flap)
         | e1/1       | e1/2          | e1/3
       Host A        Host B          Host C
     trusted       spoof source     active probe
    .11 / aa         ... / bb       .13 / cc
      MAC aa       sends as aa      pings .11
```

All three dataplane links are private Containerlab connections; host C measures forwarding to host A while Host B continues sending spoofed frames.

## Install / deploy

```bash
cd ~/mac-flapping-aiops/lab-v2
sudo docker build -t macflap-endpoint:v2 -f endpoint/Dockerfile .
sudo containerlab deploy -t macflap-v2.clab.yml
sudo containerlab inspect -t macflap-v2.clab.yml
chmod +x scripts/*.sh
./scripts/status.sh
./scripts/probe.sh 10
```

## Simulate

In Terminal A, `./scripts/run-continuous.sh`. Default loop delay 0.4 seconds, bounded safety max 600 seconds. Set `MAX_SECONDS=900` to extend to 15 minutes. In Terminal B, `./scripts/probe.sh 20` and then check Nokia CLI:

```bash
sudo docker exec -it clab-macflap-v2-sw1 sr_cli
```

```text
show network-instance mac-flap bridge-table mac-duplication duplicate-entries
show network-instance mac-flap bridge-table mac-table all
show interface ethernet-1/2
```

If no duplicates yet, inspect the actual traffic and interface state before assuming the fault was injected. The Nokia's `stop-learning` hold-down lasts 3 minutes by configuration, so repeated detection isn't guaranteed during that interval.

## AAP

See [Ansible](ansible/README.md) for playbooks, approval gate and device reachability. The additional `verify-forwarding.yml` job uses AAP SSH access to the Ubuntu Docker host for an automatic Host C→Host A reachability check (0% packet loss target, retries while Nokia hold-down expires). The isolation is disabled until an engineer **explicitly approves** it through AAP. A cloned GitHub repo does not create AAP jobs.

## Datadog

See [Datadog](docs/DATADOG.md). Reuse the existing exports in the root `datadog/` folder rather than creating duplicate POC monitors.

## Guides

- [Move from v1 safely](docs/MIGRATE-FROM-V1.md)
- [Live demo sequence](docs/DEMO-RUNBOOK.md)

**Verification status:** static config/code reviewed, **not yet runtime-tested** against the user's new v2 topology or AAP environment.
