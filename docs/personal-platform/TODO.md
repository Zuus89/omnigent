---
type: doc
title: "Personal AI Platform — Roadmap"
status: living
protection: protected
owner: human
created: "2026-07-13"
---

# Personal AI Platform — Roadmap

> The dependency-ordered task route, mirrored from the Linear initiative
> ("Personal AI Platform" — `https://linear.app/cristobal-workspace/initiative/personal-ai-platform-01e1bba23249`).
> **Protected:** agents perform status-sync only, via `/close-task`.

Status markers: `Ready` · `In Progress` · `Blocked` · `Done`

---

## V1 — Multi-device coding UI (assembly, no custom code)

| Status | Item | Blocked by |
|--------|------|------------|
| Done | Document the undocumented VPS state (fork, ufw rules, CLI harness inventory) in `vps-infra`'s `vps_omnigent_inventory.md`. | — |
| Done | Strip the embedded GitHub token from this fork's `origin` remote; `gh` set up as credential helper. | — |
| Done | Create the Linear initiative ("Personal AI Platform") and connect it as this project's tracker. | — |
| Done | Author native governance (`CLAUDE.md`, `.claude/agents/`, `.claude/skills/`, `FRAMEWORK.md`) for this repo; consolidated to a single root `CLAUDE.md` and dropped 7 unrelated upstream dev skills. | — |
| Done | Confirm the coordinator/per-agent model picker exists in `omnigent config` (Claude-only today); checked project grouping + background visibility — see `project_chronicle.md` 2026-07-13 for the live-UI findings (Omnigent's own "workspace" ≠ our Workspace; no mobile project creation; git is bound per-chat not per-project). | — |
| Done | Stand up `code-server` on the VPS — tailnet-only (`network_mode: host` + `--bind-addr`), password-protected, real TLS via `tailscale cert`, workspace at `/root/repos/` + this fork. | — |
| Done | Build and install the Omnigent VS Code extension (from this fork's `editors/vscode`) + the Claude Code extension inside `code-server`; added the loopback compose override + mounted the `claude` CLI binary onto PATH (extension needs it, wasn't bundled). | Stand up code-server |
| Done | Tested from a second device — Android tablet with keyboard/trackpad: Claude Code session opens via the activity-bar icon. Command Palette input doesn't respond on that device (non-blocking quirk, parked). Omnigent's own panel left unfixed by decision (see chronicle 2026-07-13) — not used day to day, only its code as a base. | Extensions installed |
| Done | Mirrored the new deployment config into `vps-infra` (`vps-omnigent/opt/code-server/`, `vps-omnigent/opt/omnigent/deploy/docker/`), updated its inventory doc + `vps_ops_gotchas.md` with 3 reusable findings, logged, committed. | Second-device test passes |

**V1 closed 2026-07-13.** Full debugging narrative in `project_chronicle.md`.

## Phase 2 — Workspace hierarchy + KB curator (not started, scope confirmed by V1 step 3)

| Status | Item | Blocked by |
|--------|------|------------|
| Done | Build the Workspace layer for real — Omnigent has no equivalent (its "workspace" is a filesystem path on a session, i.e. our Project, not an identity/credential boundary over multiple projects). **CLOSED 2026-07-17 (A2′): full 10-step lifecycle, Step-8 alpha test PASS 42/42, kernel-enforced per-client isolation live via `ws-launch`. See chronicle 2026-07-17.** | V1 complete |
| Ready (unblocked) | Implement the three-tier knowledge base (Global / Workspace / Project) with the promotion flow. Brief captured under `claude_tasks/`. | ~~Workspace layer~~ done |
| Blocked | Build the KB curator agent + review panel. | Three-tier KB |
| Done (already native to Omnigent) | ~~Background-agent status view~~ — confirmed live: `SubagentsPanel.tsx` + `RunningDot` + session `idle`/`running` states already exist. Nothing to build here. | — |

## Phase 3 — Native project lifecycle (not started, scope confirmed by V1 step 3)

| Status | Item | Blocked by |
|--------|------|------------|
| Blocked | Build the native "new project" wizard (identity → git connection → MCP connection → governance toggle) — **mobile/tablet-friendly**, confirmed live that Omnigent's own project creation is effectively desktop-only today. | Phase 2 workspace concept |
| Blocked | **Sharpened by live testing:** a Project must own a stable git binding, and every Session under it inherits it — Omnigent currently lets sessions under the same project point at different repos. This is the concrete bug/gap our Project entity has to fix, not just "add a git step to a wizard." | New-project wizard |
| Blocked | Wire the credential-vs-resource split for GitHub/Azure DevOps/Atlassian/Databricks/Microsoft 365 connectors. | New-project wizard |

---

## Next up

Phase 2's foundation — the **Workspace-layer task — CLOSED 2026-07-17** (full 10-step
lifecycle, alpha PASS; see chronicle). It no longer blocks anything. Next natural pick:
**`kb-three-tier`** (three-tier KB, now Ready above). Also queued: the three `ws-launch`
flags (`--shell` [highest], scalable persistence, `.claude` audit gap — each needs a spec +
code-reviewer gate + an infra SHA re-pin) and `secrets-manager` (brief captured, still needs
a human-approved row in this roadmap). ~~Deferred cross-repo item: 3 sibling repos carried
embedded tokens in their remote URLs~~ — **resolved 2026-07-19** (all 5 repos verified
tokenless + OAuth-only; token deleted on GitHub — see `context_snapshot.md`). Sequencing
is a Cristóbal decision.
