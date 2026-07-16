---
type: handoff
title: "Proposed plan.md amendment — workspace isolation model (for human approval)"
task: "workspace-layer"
status: draft
created: "2026-07-16"
related_decisions: ["council/workspace-isolation-amendment.md", "plan.md §Phase 2 (protected — this is the proposed edit)"]
---

# Proposed `plan.md` amendment — for human word-by-word approval

`plan.md` is a **protected file** (CLAUDE.md §11). This document proposes the exact edit;
nothing is written to `plan.md` until the human approves. Scope: the "Workspace hierarchy"
subsection of §Phase 2. No other section changes (the §Phase 3 credential-vs-resource rule
already says credential = workspace-scoped, which A2′ implements — no edit needed there).

## Current locked text (plan.md, "Workspace hierarchy", 1st paragraph)

> A **workspace** is a full identity context, not just a folder: its own git identity, its
> own Claude/model credentials, its own MCP OAuth grants, its own filesystem — isolated by
> container (or equivalent OS-level boundary). Nothing crosses this boundary by default.
> Today there is exactly one workspace (personal). More get added later only when a real
> distinct identity/credential need shows up (e.g. a client with their own accounts) — not
> speculatively.

## Proposed replacement text

> A **workspace** is a full identity context, not just a folder: its own git identity, its
> own Claude/model credentials, its own MCP OAuth grants, its own filesystem. Today there
> is exactly one workspace (personal); more get added only when a real distinct
> identity/credential need shows up (e.g. a client with their own accounts) — not
> speculatively.
>
> **Isolation model (resolved by council 2026-07-16, see
> `claude_tasks/council/workspace-isolation-amendment.md`).** The boundary is enforced by
> the **operating system**, not by convention, and not by a full container per workspace
> (rejected — a 2 vCPU / 8 GB VPS cannot hold N editor stacks). Each workspace is a
> distinct **Unix user** (`ws-<slug>`) inside the shared code-server container:
>
> - **Agent path — kernel-enforced.** Agents run as their workspace's user; the kernel
>   blocks a cross-workspace read of another workspace's `600` secrets and *logs the
>   denial* (the observable trigger). This requires that **no one inside the container
>   holds root** — the blanket passwordless `sudo` is removed; the **only master key
>   belongs to the vps-infra architect, operating from the host.**
> - **Human-terminal path — convention-enforced** until a later hardening stage (a user
>   can still open a `coder` shell by choosing a non-default terminal profile). This is a
>   known, documented gap, not a hidden one.
> - **"Nothing crosses by default" holds for the agent path once this model ships.** Until
>   it ships, the honest statement is: *the default plane has no boundary against the
>   platform's own daily activity — an agent that ingests hostile web content executes as
>   the editor user and can read every workspace's credentials.* That exposure is the
>   reason this model is being built.
>
> A workspace that earns stronger isolation (a client contract, a data-at-rest
> requirement) **escalates to its own dedicated code-server instance** — a real kernel
> boundary including data at rest. This escalation is bounded at **≤1** on current
> hardware and buys *isolation, not capacity*: both instances share the same 2 vCPUs, so
> the concurrency ceiling is global. The **Omnigent server is not part of this boundary**
> (it authorizes by owner, not workspace); it is stopped-but-preserved as the future
> collaboration engine, with each workspace reserving a partition id for that day.

## What the change does (rationale, for the approval decision)

1. **Drops "isolated by container"** as the mechanism — container-per-workspace was
   scored and rejected on this hardware. Keeps "OS-level boundary" (now per-uid).
2. **Replaces the bare "nothing crosses by default"** — a universal negative that is
   false-by-construction for the human-terminal path under A2′ — with an honest split:
   kernel-enforced agent path + convention human path + the verbatim interim-exposure
   statement (the council's condition, so the plan never carries a promise the default
   topology can't keep).
3. **Adds the master-key principle** (your ruling) into the protected plan.
4. **Adds the A1 ≤1 escalation** and the isolation-not-capacity / 2-vCPU reality.
5. **Records the Omnigent-decoupled-but-preserved** stance and the reserved partition id.

## Approve / adjust

Reply with approval of the replacement text as written, or edits. On approval the pm
makes exactly this edit to `plan.md` (nothing more), then the da re-designs the alpha test
and the spec freezes.
