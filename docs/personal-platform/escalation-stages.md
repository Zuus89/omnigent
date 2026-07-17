---
type: doc
title: "Workspace isolation — escalation stages (triggers BINDING, human-ruled)"
status: living
created: "2026-07-17"
---

# Workspace isolation — escalation stages

> The Stage-1 product-layer escalation doc required by the `workspace-layer` task (alpha
> PF-5). **Source of truth:** the FROZEN spec `claude_tasks/workspace-layer.md`
> (§"Design decision", §"Escalation stages") — council-resolved 2026-07-16, triggers
> human-ruled and BINDING. This doc transcribes that model as a standalone reference; if it
> ever diverges from the spec, the spec governs.

## The baseline: A2′ (default) + A1 (escalation, ceiling ≤1)

- **A2′** — every workspace is its own Unix user (`ws-<slug>`, own group) inside the single
  code-server container. The kernel — not convention — denies cross-workspace reads, and a
  blocked attempt raises an observable permission-denied, recorded by host `auditd`. An
  indivisible bundle: per-workspace uids + no root inside the container (master-key
  principle: root belongs only to the vps-infra architect, host-side) + the launch wrapper
  `ws-launch` treated and tested as a security control.
- **A1** — a workspace that earns it (contract / data-at-rest / higher trust) escalates to
  its **own code-server instance** (own port/volume). Bounded at **≤1** on current hardware:
  one instance idles at ~807 MiB, and the binding constraint is the 2 vCPUs (the global
  ceiling of ~3–4 concurrent Claude sessions spans both containers). A1 buys isolation,
  not capacity.

**Honest scope:** A2′ hardens the **agent** path. The **human-terminal** path remains
convention-enforced until Stage 2b (below).

## Escalation stages (triggers BINDING)

| Stage | What | Trigger |
|-------|------|---------|
| **2a** | Workspace switcher in the VS Code extension (then web UI), reading the product registry (`deploy/personal-platform/workspaces.yaml`). | Second real client onboarded. |
| **2b** | Harden the human-terminal path: force per-workspace profile; no `coder` shell fallback in a client folder. | Any cross-workspace access event, or the terminal gap proving real in use. |
| **3** | Activate the `workspace_id` partition on upstream's dormant seam (collaboration driver). **Hard precondition:** `personal` migrates off id 0 and 0 becomes a rejected sentinel before any read-side filtering ships (sequenced with — not contradicting — the council's ruling 6: history stays until Stage 3, whose precondition then migrates it). | Collaboration phase starts, or a client audit / data-at-rest requirement. |

## Data-at-rest gate (binding)

Before the **first client workspace** is added, the data-at-rest posture must be resolved
explicitly: under A2′ the commingled-DB concern is moot while the Omnigent server stays
stopped; if a client needs physical separation, that client is the **A1** escalation.
**Onboarding a client without this ruling is a governance violation.**

## Related

- Frozen spec: `claude_tasks/workspace-layer.md` (authoritative).
- Council resolution: `claude_tasks/council/workspace-isolation-amendment.md`.
- Measured permission model: `claude_tasks/reviews/workspace-layer_infra-report.md`.
- Operational procedure for adding a workspace: `deploy/personal-platform/runbook-add-workspace.md`.
