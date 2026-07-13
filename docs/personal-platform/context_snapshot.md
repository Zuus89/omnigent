---
type: doc
title: "Context Snapshot — Personal AI Platform"
status: snapshot
created: "2026-07-13"
updated: "2026-07-13"
---

# Context Snapshot — Personal AI Platform

> Cold-resume handoff. Current state only — overwritten at every close, not a log.

## Where we are

Project just founded. Governance scaffolded natively this session (`CLAUDE.md`,
`.claude/agents/`, `.claude/skills/`, `FRAMEWORK.md`, `TODO.md`, `project_chronicle.md`,
this file). V1 execution is **in progress**:

- **Done:** VPS state documented in `vps-infra`; embedded GitHub token stripped from this
  fork's `origin` remote; Linear initiative created and connected.
- **Next:** V1 step 3 — confirm the coordinator/per-agent model picker in `omnigent config`,
  and check whether Omnigent's own UI already groups sessions by project and shows
  background-agent status (both would mean less to build in Phase 2).
- **After that:** stand up `code-server`, install the two VS Code extensions, test from a
  second device, then mirror the deployment config into `vps-infra` to close V1.

## Access

- This fork: `/opt/omnigent` on `omni-vps` (tailnet `100.116.27.33`), `ssh omni-vps`.
- Full plan: `docs/personal-platform/plan.md`.
- Design reference (mockup): `https://claude.ai/code/artifact/e0c98989-9fc7-4f2a-ad85-8f3de5f15232`.
- Linear: `https://linear.app/cristobal-workspace/initiative/personal-ai-platform-01e1bba23249`.

## Flags / gotchas

- The embedded token that was in `origin`'s URL should still be **revoked on GitHub's side**
  — stripping the URL doesn't invalidate the token itself. Human action, not yet confirmed
  done.
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is **not yet set** for this repo (no
  `.claude/settings.json` committed yet) — full multi-agent orchestration (`pm` spawning
  teammates) won't actually work until that's wired. Fine for now since work has been
  ad-hoc/single-agent; flag before attempting a full 10-step lifecycle task.
- Headless (`claude -p`) invocations against this repo hit permission friction this session —
  Bash commands got blocked even in `acceptEdits` mode, and `--allowedTools` needs the
  colon syntax (`Bash(git:*)`), not the space syntax shown in `claude --help`'s own example.
  Prefer an interactive session for anything needing more than pure file writes.
