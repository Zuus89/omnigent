---
type: doc
title: "Context Snapshot — Personal AI Platform"
status: snapshot
created: "2026-07-13"
updated: "2026-07-16"
---

# Context Snapshot — Personal AI Platform

> Cold-resume handoff. Current state only — overwritten at every close, not a log.

## Where we are

**Phase 2, task `workspace-layer` — A2′ is now LIVE; Step 7 (implementation) complete,
Step 8 (frozen alpha test) is the critical path to close.** The container-recreate window
that the previous snapshot warned would kill the session **has happened**. The agent now
runs as **`ws-personal` (uid 1001, gid 2001)** via `ws-launch` — kernel-enforced isolation
on the agent path is active ("deployed" → **protected**). Full environment-change handoff:
`claude_tasks/reports/workspace-layer_a2prime-live-handoff.md` (captured from the vps-infra
architect this session).

**The task in one paragraph:** build the Workspace entity — a per-client identity boundary.
A `/council` overturned the original design; resolution (human-approved): **A2′** — each
workspace is its own **Unix user** (`ws-<slug>`, own group gid 2001+) inside the single
code-server container; kernel-enforced isolation on the agent path; **no root inside the
container** (master-key principle — root belongs only to the vps-infra architect, host-side);
editor access via **POSIX ACLs**; per-workspace `CLAUDE_CONFIG_DIR`; secrets `0700`; audit
via host `auditd`. A1 (a dedicated code-server instance) is the ≤1 escalation a client can
earn. The Omnigent server is stopped-but-preserved as the future collaboration engine.

**Done and on main:**
- `plan.md` §Phase 2 amended (protected, human-approved) to A2′.
- Spec FROZEN (`claude_tasks/workspace-layer.md`) + post-freeze correction banner pointing to
  the infra report as the authoritative permission model.
- Alpha test SEALED, then RE-SEALED **mechanism-agnostic** (`alpha_tests/workspace-layer.md`,
  BASE for G9 = commit `220f2db8`) — asserts observable BEHAVIOR (which uid reads what, is the
  denial recorded), never modes/ACLs/groups.
- Infra deliverables 1–7 built + live-tested (`reviews/workspace-layer_infra-report.md`
  + two rulings): image layer, blanket sudo removed, provisioning script, mem_limit 4g /
  cpus 1.5, Omnigent stack stopped, auditd rules, own-group+ACL permission model.
- **`ws-launch`** (the fork's privilege-drop wrapper — a security control) built, gate-SAFE
  (iter 1 NOT SAFE PATH-hijack C-1 → fixed → iter 2 SAFE), merged to main at
  `deploy/personal-platform/ws-launch` (+19-check harness). Now **baked, SHA-256 pinned**
  (`build.sh` `EXPECTED_WRAPPER_SHA`), wired as `claudeProcessWrapper`, E2E-verified live by
  infra (drop, kernel denial, PATH-poison defeat, ownership anchor all green).
- **Continuity (A):** ws-personal has its own git push (gh authed as `Zuus89`, persisted).
- **Continuity (B):** the auto-memory migration FAILED — 4 memory files lost in the recreate;
  reconstructed this session from the durable git-tracked docs into the new memory dir.

## Resume exactly here

1. **Two fork pieces still to build** (gate workspace-layer Step 8; each needs the
   code-reviewer gate): the product registry **`workspaces.yaml` + schema** (first entry:
   `personal` = all 5 repos, human-confirmed — activity_log 2026-07-16T17:26), and its
   **validate script** (loud-fail on registry/live-state mismatch). These back alpha checks
   C7 (registry derivability) and C8 (validator). Buildable solo on the fork; no infra
   dependency to BUILD them (only Step-8 execution needs infra).
2. **Step 8 — DA runs the sealed alpha test** against the live VPS. Bias-free split: infra
   (root) stands up a throwaway 2nd workspace + planted secrets; the **DA** performs the
   cross-workspace read as ws-personal and observes the denial. **Needs a Cristóbal→infra
   ping** to stand up the scaffold (host-side, master-key principle — never self-served).
   Infra runbook: `vps-infra/docs/a2prime_alpha_verification.md`; scaffold in vps-infra PR #4.
3. **Then Step 9 (human validation) → Step 10 (close).**
4. **Three open ws-launch flags** (NEW Phase-2 tasks, from the infra handoff — each needs a
   spec + code-reviewer gate + an infra SHA re-pin): (1) `ws-launch --shell` mode [highest —
   the only UX gap: no human workspace shell exists today]; (2) scalable per-workspace
   persistence via `CLAUDE_CONFIG_DIR`/`GH_CONFIG_DIR` under one mounted parent (kills the
   per-client recreate); (3) `.claude` audit-boundary gap. Do NOT preempt closing
   workspace-layer (Hard Rule 2). Sequencing is a Cristóbal decision.

## Access

- code-server: `https://omnigent-vps.tail05ae76.ts.net:8443` (full MagicDNS; pw in
  `/opt/code-server/.env` on the VPS).
- Fork: **`/home/coder/repos/personal/omnigent`** (nested layout — all 5 repos under
  `personal/`). Push to `origin` (`Zuus89/omnigent`) via `gh` OAuth as ws-personal.
- Auth (persisted, ws-personal): gh `/home/ws-personal/.config/gh`; Anthropic
  `/home/ws-personal/.claude/.credentials.json`. Re-auth (if ever) via the AGENT panel only,
  never a `coder` terminal.
- Memory dir (persisted): `/home/ws-personal/.claude/projects/-home-coder-repos-personal-omnigent/memory/`.
- Linear initiative "Personal AI Platform"; design mock
  `https://claude.ai/code/artifact/e0c98989-9fc7-4f2a-ad85-8f3de5f15232`.

## Flags / gotchas

- **Session-start protocol** (CLAUDE.md §3) + read the memory dir (reconstructed this session).
- **Master-key principle:** NO passwordless sudo in the container. Any root-owned-file or
  provisioning need is a host-side architect handoff (a ready-to-paste prompt carried by the
  human), never self-served.
- **VPS load:** 2 vCPU / ~8 GB shared with the editor; **one heavy agent at a time; wide
  multi-agent workflows run OFF this box** (notebook). This constrains fan-out even under
  ultracode — honor it.
- **`ws-launch` is SHA-pinned:** any change to `deploy/personal-platform/ws-launch` requires
  telling infra to re-pin `EXPECTED_WRAPPER_SHA`, or the build refuses it (the anti-poisoning
  control). This couples all three ws-launch flags to an infra step.
- **`coder` cannot git a ws-owned repo** (dubious-ownership; safe.directory removed as a
  CVE-2022-24765 vector) — do all git through the agent (ws-personal), not a `coder` terminal.
- The `da`/`de`/`code-reviewer`/`devils-advocate` roles run as spawnable subagents here.
- `TODO.md` still needs a human-approved content row for the `secrets-manager` task.
- Sibling briefs blocked by this task: `kb-three-tier` (SilverBullet access layer) and
  `secrets-manager`. The secrets deep-research workflow is paused/resumable
  (`resumeFromRunId wf_7943ab35-6a7`) — run it OFF this box.
