---
type: spec
title: "Workspace layer — identity/credential boundary over N projects"
task: "workspace-layer"
status: draft
created: "2026-07-14"
related_decisions: ["plan.md §Phase 2 (workspace hierarchy)", "kb-three-tier (kb-ws addressing)", "secrets-manager (per-workspace vault scope)"]
---

# Workspace layer — spec (DRAFT, Step 1 approved)

> **Lifecycle state:** Step 1 (Brief) approved by the human 2026-07-14. Full 10-step
> lifecycle, this session. Step 2 (da state profiling) running; Steps 3–6 pending. This
> file becomes the full spec at Step 3 and freezes at Step 6.

## Brief (Step 1 — human-approved, 2026-07-14)

**Goal:** Build the **Workspace** entity as a real identity boundary in our platform: a
workspace groups N projects (repos) under one identity — git, cloud credentials
(Azure/Databricks), MCP OAuth grants, filesystem — and **nothing crosses that boundary by
default**. Workspace = company (the user freelances for several clients); exactly one
exists today (personal), and the entity must make adding the second one trivial when a
real client lands.

**Motivation:** It is the foundation for everything that follows: the three-tier KB needs
`kb-ws-<company>` to have something to point at, the secrets manager needs per-workspace
scoping, and the curator agent needs to know which boundary it must never cross. Omnigent
brings none of this — its "workspace" is a filesystem path per session (our *Project*),
confirmed live in V1. This is the fork's first piece of real custom development.

## Scope / Out of scope / Approach / Acceptance criteria / Risks

TBD at Step 3, grounded in the Step-2 state profile
(`workspace-layer_step2-profile.md`).
