---
type: handoff
title: "Collaboration vision — human brief for the post-Phase-2 direction"
task: "collaboration-vision"
status: draft
created: "2026-07-16"
related_decisions: ["council/workspace-isolation-amendment.md (changes Decision-1 framing)", "plan.md (future amendment candidate — human approval required)", "workspace-layer_step2-profile.md (evidence the engine exists)"]
---

# Collaboration vision (Step-1-grade brief, human, 2026-07-16)

> Captured verbatim-in-substance from the human, mid-workspace-layer task. Not a task
> yet — a direction that reframes pending decisions and belongs in plan.md once the
> human approves the wording.

**The vision:** the platform must scale to be collaborative. Someone else running the
same software can join a shared project (a repo), both people see live what the other
is doing, and — crucially — the other user works with **their own credentials for
whatever harness they use** (Claude Code, GitHub Copilot, Antigravity, …), connecting
to the shared project.

## How it maps onto the architecture (pm analysis, evidence-linked)

Two distinct axes, composable, not to be conflated:

1. **Client isolation (the current workspace-layer task):** whose credentials — a
   boundary inside the operator's own multi-client practice.
2. **Collaboration (this vision):** each person brings their own identity/credentials;
   the shared project is the meeting point. The locked credential-vs-resource rule
   generalizes: credential = per-person identity; resource (the repo/project) = shared.

**The engine already exists** (Step-2 profile evidence): Omnigent's server is built for
exactly this — multi-user (`users`, `account_tokens` invites), per-session permissions
(read/edit/manage + share), live session status (`WS /v1/sessions/updates`,
SubagentsPanel — verified live in V1), 11 harness launchers with per-session
`harness_override`, and credentials that travel with each user's registered HOST (each
collaborator's machine holds their own harness credentials; `hosts.owner` binds it to
their user). A collaborator needs no credentials from the operator, and vice versa.

## Immediate consequences (recorded 2026-07-16)

- **Council Decision 1 reframed:** "decouple the Workspace entity from the Omnigent
  server" ≠ "discard the server." The Workspace (client-isolation) layer is built
  without it; the server is PRESERVED as the future collaboration engine. The de's
  council conditions (keep the stack; reserve per-workspace `workspace_id` integers)
  are upgraded from caution to strategy.
- **The zombie-stack question routed to vps-infra changed:** decommissioning is no
  longer a neutral RAM reclaim — it forfeits the collaboration engine. The follow-up
  handoff prompt was revised accordingly before delivery.
- **Threat-model note for the isolation decision:** "multi-user is parked" is now
  time-bounded, not permanent. External collaborators arrive via their OWN hosts and
  the server's auth (session_permissions) — not via shells in the operator's
  code-server — so the A2/A2′ question for the local box stands, but the amendment
  text must not assume single-operator-forever.

## Not decided here

Everything else: when this becomes a task, what V-next scope it takes (Omnigent web UI
vs our extension as the collaboration surface, hosting model for the second user,
project-level ACLs vs session-level). Needs its own brief → lifecycle when its turn
comes; blocked at minimum by the workspace-layer task and plan.md amendment approval.
