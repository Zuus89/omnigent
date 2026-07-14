---
type: spec
title: "Workspace-scoped secrets manager, managed from the platform UI"
task: "secrets-manager"
status: draft
created: "2026-07-14"
related_decisions: ["plan.md §Phase 3 (credential-vs-resource rule)", "kb-three-tier (secrets never in KB)"]
---

# Secrets manager — spec (DRAFT, brief stage)

> **Lifecycle state:** Step 1 (Brief) captured 2026-07-14. Tool selection is pending the
> secrets-management deep-research report (running at capture time). This task needs its
> own session with the full lifecycle; it depends on the Workspace-layer task (vault
> scoping = workspace scoping).

## Brief (Step 1 — human, 2026-07-14)

The platform gets a real secrets manager on the VPS, and it must be **manageable from the
platform's own UI** — the same app being built (Phase-2 extension surface), not via
terminal. Direction agreed in conversation: credential isolation per workspace (workspace
= client company), consistent with plan.md's credential-vs-resource rule (credential =
workspace-scoped; resource = project-scoped).

## Engineering principles locked at brief stage

1. **Engine, not product** (same pattern as code-server): we never build our own crypto or
   secret storage. A proven manager runs on the VPS as the engine; our UI is a thin
   product layer over its API. The manager's own web UI remains available as fallback.
2. **Selection criteria sharpened by the UI requirement:** the chosen tool must have a
   solid HTTP API (list/create/rotate per scope) and per-workspace logical scoping. Ops
   burden for a single operator on a 7GB VPS matters (unseal ergonomics, RAM).
3. **Client-owned credentials stay in client systems** (their Key Vault / their manager) —
   we hold access, not custody; the workspace KB stores pointers. Our manager holds our
   own secrets and platform-level grants. (Hypothesis at capture time — to be confirmed or
   corrected by the deep-research report before the spec is expanded.)
4. Migration path from today's gitignored `.env` files must be part of the spec.

## Scope / Out of scope / Acceptance criteria / Risks

TBD at Steps 2–4, after the research report lands and the Workspace-layer task defines the
workspace entity this scopes to.
