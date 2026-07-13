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
| Ready | Stand up `code-server` on the VPS — tailnet-only, password-protected, workspace at `/root/repos/`. | — |
| Ready | Build and install the Omnigent VS Code extension (from this fork's `editors/vscode`) + the Claude Code extension inside `code-server`; add the loopback compose override so the Omnigent extension's auto-discovery works. | Stand up code-server |
| Ready | Test the full code-server setup from a second device (tablet/phone) over the tailnet. | Extensions installed |
| Ready | Mirror the new deployment config into `vps-infra`, update its inventory doc, log, and commit — closing V1. | Second-device test passes |

## Phase 2 — Workspace hierarchy + KB curator (not started, scope confirmed by V1 step 3)

| Status | Item | Blocked by |
|--------|------|------------|
| Blocked | Build the Workspace layer for real — Omnigent has no equivalent (its "workspace" is a filesystem path on a session, i.e. our Project, not an identity/credential boundary over multiple projects). | V1 complete |
| Blocked | Implement the three-tier knowledge base (Global / Workspace / Project) with the promotion flow. | V1 complete |
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

1. Stand up `code-server`.
2. Extensions + second-device test.
3. Close V1 (mirror config into `vps-infra`).
