# Workflow tag standard

Common tags: `project:berca-poc`, `team:tps`. Every standardized workflow also has
`env`, `domain`, `workflow_role`, and `use_case`.

| Workflow | domain | workflow_role | use_case |
| --- | --- | --- | --- |
| Operational Scenario Controller | application | scenario-controller | operational-scenarios |
| Investigate and Remediate Operational Conditions | application | incident-response | operational-conditions |
| Investigate Network MAC Flapping | network | investigation | mac-flapping |
| RHEL CVE Approval-Gated Remediation | security | incident-response | security-remediation |

Preserve actual environment and service scope. `automation:aap` identifies the AAP
workflows; `automation:bits-agent` identifies the bounded network evidence agent.
Generic controllers/responses no longer carry only `scenario:memory-hot-add`.
Dedicated MAC flapping retains `scenario:mac-flapping`. Workflow metadata uses
`workflow_role`, while monitor metadata keeps `monitor_role`.

Examples for the Workflow Automation search bar:

```text
tag:"project:berca-poc" AND status:published
tag:"workflow_role:scenario-controller" AND status:published
tag:"workflow_role:incident-response" AND status:published
tag:"domain:network"
```

2026-11-06 verification: six workflow tag sets updated. Step definitions, triggers,
publication state and run-as mode were unchanged. No workflows executed.
The unpublished Operational Conditions `(copy)` workflow
`41d820de-3514-43c3-842a-ef56437848e8` rejected edits because the connected user
lacks edit permission; it retains its old tags. Its owner can apply the same
Operational Conditions tag set. Exact saved tags and IDs are recorded in
`datadog/workflows/tag-standardization.json`.
