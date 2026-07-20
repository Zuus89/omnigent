---
type: doc
title: "Context Snapshot — Personal AI Platform"
status: snapshot
created: "2026-07-13"
updated: "2026-07-17"
---

# Context Snapshot — Personal AI Platform

> Cold-resume handoff. Current state only — overwritten at every close, not a log.

## Where we are

**Phase 2, task `workspace-layer` (A2′) is CLOSED — the full 10-step lifecycle ran end to
end and the Step-8 frozen alpha test rendered `PASS` (42/42 mandatory checks).** Committed
docs-only at `4d96e51a`, pushed to `origin/main`. Kernel-enforced per-client isolation is
live: the agent runs as **`ws-personal` (uid 1001, gid 2001)** via `ws-launch` (baked,
SHA-256-pinned, E2E-verified). The infra teardown round is clean (canary unchanged, no
container restart at any point; `ws-test` scaffold removed; auditd ruleset intact).

**Nothing is mid-flight on `workspace-layer`.** The next task is a fresh pick from the
Phase-2 queue below.

## What was delivered (workspace-layer, all on `main`)

- `plan.md` §Phase 2 amended (protected, human-approved) to A2′.
- Product registry `deploy/personal-platform/workspaces.yaml` + schema + `scripts/validate_workspaces.py`
  (two-layer validator, pre-commit-wired `--schema-only` + live `$VALIDATE_CMD`). First and
  only entry: `personal` = all 5 repos.
- `ws-launch` privilege-drop wrapper — gate-SAFE, baked at `/usr/local/bin/ws-launch`,
  SHA-pinned, wired as `claudeProcessWrapper` (w-0 confirmed coder-plane).
- Sealed alpha test + final run report (`claude_tasks/reports/workspace-layer_alpha-run.md`,
  `status: pass`). Sealed test carries one authorized post-seal edit: the **scoped C4-a
  re-seal** (human ruling 2026-07-17; topology clause → mechanism-agnostic config-isolation
  property; precedent 220f2db8).
- Infra deliverables (vps-infra, root-plane): image layer, provisioning script, mem 4g /
  cpu 1.5, Omnigent stack stopped-but-preserved, uid-scoped auditd rules, own-group+ACL
  permission model, per-workspace git `includeIf` identity.

## Resume: pick the next Phase-2 task

`workspace-layer` no longer blocks anything. Candidates (Cristóbal sequences):

1. **`kb-three-tier`** — three-tier KB (Global / Workspace / Project) + promotion flow. Now
   **unblocked** by the workspace layer. Brief already captured under `claude_tasks/`.
2. **The three `ws-launch` flags** (each = its own spec + code-reviewer gate + an infra
   SHA re-pin): (a) `ws-launch --shell` [**highest** — the only UX gap: no human workspace
   shell today]; (b) scalable per-workspace persistence via `CLAUDE_CONFIG_DIR`/`GH_CONFIG_DIR`
   under one mounted parent (kills the per-client recreate); (c) `.claude` audit-boundary gap.
3. **`secrets-manager`** — brief captured, but still needs a **human-approved content row in
   `TODO.md`** before it can start.

## Deferred follow-ups (carried from the workspace-layer close — do not lose)

- ✅ **RESOLVED 2026-07-19 — embedded-token exposure in 3 sibling repos:** remediation
  verified complete on both sides. All 5 `ws-personal` repos measured tokenless remote URLs
  + no `.git-credentials` store + single credential path (`gh` OAuth `gho_`, `ls-remote`
  auth OK on all 3 former offenders); the embedded token itself confirmed deleted on GitHub
  by Cristóbal (it was the old fine-grained PAT scoped to exactly those 3 repos). Note for
  other machines: the token-in-URL convention is the **tower's**, not the VPS's.
- **`provision-workspace.sh:148` `chmod 660` fix** (`chmod ug+rw,o-rwx`, preserves x-bit)
  ready to land in **vps-infra PR #4**.
- **A-5:** sealed §3 fixture's latent `date '+%x %T'` (2-digit-year) pattern — a future
  human-ruled fixture correction; non-urgent, changed no verdict.

## Access

- code-server: `https://omnigent-vps.tail05ae76.ts.net:8443` (pw in `/opt/code-server/.env`
  on the VPS).
- Fork: **`/home/coder/repos/personal/omnigent`** (nested — all 5 repos under `personal/`).
  Push to `origin` (`Zuus89/omnigent`) via `gh` OAuth as ws-personal.
- Auth (persisted, ws-personal): gh `/home/ws-personal/.config/gh`; Anthropic
  `/home/ws-personal/.claude/.credentials.json`. Re-auth (if ever) via the AGENT panel only,
  never a `coder` terminal.
- Memory dir: `/home/ws-personal/.claude/projects/-home-coder-repos-personal-omnigent/memory/`.
- Linear initiative "Personal AI Platform"; design mock
  `https://claude.ai/code/artifact/e0c98989-9fc7-4f2a-ad85-8f3de5f15232`.

## Flags / gotchas

- **Session-start protocol** (CLAUDE.md §3) + read the memory dir.
- **Master-key principle:** NO passwordless sudo in the container. Any root/provisioning need
  is a host-side architect handoff (a ready-to-paste prompt carried by the human), never
  self-served.
- **VPS load:** 2 vCPU / ~8 GB shared with the editor; **one heavy agent at a time; wide
  multi-agent workflows run OFF this box** (notebook). Honor it even under ultracode.
- **`ws-launch` is SHA-pinned:** any change to `deploy/personal-platform/ws-launch` requires
  telling infra to re-pin `EXPECTED_WRAPPER_SHA`, or the build refuses it. This couples all
  three ws-launch flags to an infra step.
- **`coder` cannot git a ws-owned repo** (dubious-ownership; safe.directory removed as a
  CVE-2022-24765 vector) — do all git through the agent (ws-personal), not a `coder` terminal.
- **Killed-session recovery works:** a session killed mid-run resumes from the durable
  git-tracked artifacts (append-only report + activity log + sealed test). Proven this task.
- `da`/`de`/`code-reviewer`/`devils-advocate` run as spawnable subagents here.
- `secrets-manager` still needs a human-approved TODO content row.
