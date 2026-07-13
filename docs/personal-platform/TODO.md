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
| In Progress | Author native governance (`CLAUDE.md`, `.claude/agents/`, `.claude/skills/`, `FRAMEWORK.md`) for this repo. | — |
| Ready | Confirm the coordinator/per-agent model picker exists in `omnigent config` (Claude-only today); check whether the sidebar already groups sessions by project and shows background-agent status. | — |
| Ready | Stand up `code-server` on the VPS — tailnet-only, password-protected, workspace at `/root/repos/`. | — |
| Ready | Build and install the Omnigent VS Code extension (from this fork's `editors/vscode`) + the Claude Code extension inside `code-server`; add the loopback compose override so the Omnigent extension's auto-discovery works. | Stand up code-server |
| Ready | Test the full code-server setup from a second device (tablet/phone) over the tailnet. | Extensions installed |
| Ready | Mirror the new deployment config into `vps-infra`, update its inventory doc, log, and commit — closing V1. | Second-device test passes |

## Phase 2 — Workspace hierarchy + KB curator (not started)

| Status | Item | Blocked by |
|--------|------|------------|
| Blocked | Implement the Workspace → Project → Session hierarchy as a real feature (if V1's check found Omnigent doesn't already provide it). | V1 complete |
| Blocked | Implement the three-tier knowledge base (Global / Workspace / Project) with the promotion flow. | V1 complete |
| Blocked | Build the KB curator agent + review panel. | Three-tier KB |
| Blocked | Build a background-agent status view (if V1's check found Omnigent doesn't already provide one). | V1 complete |

## Phase 3 — Native project lifecycle (not started)

| Status | Item | Blocked by |
|--------|------|------------|
| Blocked | Build the native "new project" wizard (identity → git connection → MCP connection → governance toggle). | Phase 2 workspace concept |
| Blocked | Wire the credential-vs-resource split for GitHub/Azure DevOps/Atlassian/Databricks/Microsoft 365 connectors. | New-project wizard |

---

## Next up

1. Confirm the coordinator/agent picker + check sidebar grouping + background visibility (V1 step 3).
2. Stand up `code-server`.
3. Extensions + second-device test.
