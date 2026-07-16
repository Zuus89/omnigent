---
type: council
title: "Council — amend the locked Phase-2 workspace-isolation model?"
task: "workspace-layer"
status: final
created: "2026-07-16"
related_decisions: ["plan.md §Phase 2 (locked text under deliberation)", "workspace-layer_vps-infra-ruling.md", "workspace-layer_de.md", "workspace-layer_devils-advocate.md", "workspace-layer_step2-profile.md"]
---

# Council — workspace-isolation amendment

## The question

Should the LOCKED `plan.md` §Phase 2 text — "a workspace is a full identity context …
**isolated by container (or equivalent OS-level boundary). Nothing crosses this boundary
by default**" — be formally amended to the vps-infra architect's A2 model (single
code-server, convention-based boundary: filesystem convention + git `includeIf` incl.
per-workspace `credential.helper`/PAT files + path-scoped credential files, never
container-wide env vars + product registry as SSOT), with a designed A1 per-workspace
dedicated-container escalation, and the Workspace entity fully decoupled from the
Omnigent server? Triggered by: Step-5 reviews (devils-advocate BLOCKER 1/2, de CRITICAL
owner≠workspace) + the vps-infra ruling of 2026-07-16. Convened mid-Step-6 of the
`workspace-layer` task; Hard Rule 9 applies (the amendment contradicts locked text).

## Positions

**pm — AMEND.** The locked text was written with multi-user collaboration in view (now
parked); a kernel boundary on a dead plane protects less than a convention boundary on
the live plane; A1 escalation preserves the original intent for cases that earn it.
Proposed reopen criteria: multi-user revived; second workspace escalates; VPS upgrade;
any real cross-contamination incident.

**de — AMEND-WITH-CONDITIONS.** All A2 mechanisms are real, zero fork code. But file
permissions are NOT a control against same-user agents (every process runs as `coder`;
600 is owner-readable): real enforcement is tool-default-resolution + discipline — stops
accidents, not confused/injected processes, and that failure mode is the A1 trigger.
Conditions: (1) boundary-honesty language; (2) reserve a stable `workspace_id` integer
per registry entry from day one (Stage 3 becomes a lookup); (3) the amendment must not
authorize decommissioning the Omnigent/Postgres stack (separate call); (4) bound A1
honestly (~one escalated workspace on this box; commit+push before any move; transcript
scoping resolved first).

**da — AMEND-WITH-CONDITIONS.** Evidence for the plane pivot is strong and cross-source
(chronicle: code-server is the daily plane, Omnigent UI out of the daily path by locked
V1 decision; infra: `omnigent-host.service` dead/disabled, server authorizes by owner;
profile: no live server state). The locked text traces to the parked multi-tenant
direction — amending unwinds nothing implemented. CRITICAL CONDITION: "nothing crosses
by default" is a universal negative — provable under A1, **false by construction** under
A2 (one uid, one namespace) — the amended text must replace it on the A2 plane with
enumerated positive controls, reserving the universal negative for A1; otherwise the
plan carries an acceptance criterion the default topology can never pass. Verified:
`CLAUDE_CONFIG_DIR` exists (claude 2.1.207, 43 references; relocates the `~/.claude`
base incl. `projects/` transcripts) — per-workspace transcript scoping is feasible,
convention-enforced.

## Devils-advocate attack (mandatory; ranked; none recycles Step 5)

- **BLOCKER 1 (hits all):** the "self-contamination only" threat model is FALSE — the
  platform runs autonomous web-enabled agents daily; a prompt-injected agent is a
  hostile actor **with `coder`'s uid**; under A2-default a cross-workspace credential
  read succeeds silently. The §9 embedded-token incident shows creds-in-reach is not
  hypothetical.
- **BLOCKER 2 (pm):** the load-bearing reopen trigger ("any real incident") is
  unobservable by construction — a boundary with no enforcement emits no violation
  events; the rollback clause cannot fire. Remaining criteria are circular, loosening,
  or directional. A protected security downgrade mislabeled reversible.
- **MAJOR 3 (amendment):** false trichotomy — per-workspace **Unix uids in the one
  container** (kernel-enforced 600, observable denies, ~A2 cost) was never scored.
  Locking "convention, zero enforcement" as default before pricing an enforcement option
  is the silent narrowing §11 exists to stop.
- **MAJOR 4 (pm):** "discipline" degrades under the operator's declared speed priority;
  weakest exactly when used most.
- **MAJOR 5 (pm):** the A1 valve holds ~one workspace on this box; pm's phrasing is
  plural; two contract-bound clients cannot both be served without a bigger box.
- **MAJOR 6 (da):** the "positive controls" list mixes enforced identity resolution
  (includeIf — real) with unenforced confidentiality (600/path-scoping/CONFIG_DIR — none
  stop a same-uid injected agent); shipping them as one set launders convention as
  control.
- **MAJOR 7 (da):** CLAUDE_CONFIG_DIR relocation of ALL state (vs transcripts-only,
  leaving cached credentials behind) is unproven in this corpus.
- **MAJOR 8 (de):** keeping the zombie Omnigent/Postgres stack preserves the runtime
  secret-persistence vector (de review MAJOR-2) on a plane declared "no role", while
  consuming the RAM the A1 valve needs.
- **MINOR A:** the council may recommend; only the human enacts a protected-file edit.
- **MINOR B:** the ruling-6 ↔ Stage-3 id-0 contradiction is still unresolved downstream.

## Resolution (pm synthesis)

**The decision SPLITS — the devils-advocate's bar item 4 is accepted: the uncontested
part must not launder the contested part.**

**Decision 1 — Workspace entity decoupled from the Omnigent server: RECOMMEND ENACT.**
Near-unopposed, cross-evidenced (dead host plane, owner-scoped control plane, no live
server state, V1 locked decision). Spec-level re-centering; no plan.md text names the
Omnigent server as the workspace substrate, so no locked-text edit is required for this
half. Conditions absorbed: de-(2) reserved `workspace_id` per registry entry; de-(3)
zombie-stack decommission stays a SEPARATE infra decision (flagged to vps-infra with
MAJOR 8 attached); MINOR B's contradiction gets fixed in the same spec rewrite (human
ruling 6 is superseded by the Stage-3 precondition: history stays UNTIL Stage 3, whose
precondition then migrates it — the two are sequenced, not contradictory, and the spec
must say so).

**Decision 2 — A2-as-default amendment of the locked isolation text: NOT YET.**
Missing, explicitly:
1. Score the unpriced option **A2′ (per-workspace Unix uids in one container)** against
   A2 and A1 — routed to the vps-infra architect with the attack attached (BLOCKER 1,
   MAJORs 3/4/8). The threat model must be restated to include the resident
   prompt-injection vector, or the amendment must state plainly that the default plane
   has no boundary against the platform's own daily activity.
2. One **observable** reopen/escalation trigger (BLOCKER 2) — e.g., kernel
   permission-denied events under A2′, or an equivalent detectable signal under plain A2.
3. Product-side verification: does `CLAUDE_CONFIG_DIR` relocate ALL state including
   credential caches (MAJOR 7)?
4. A1 capacity stated as ≤1 escalated workspace on current hardware (MAJOR 5).

**Enactment:** per MINOR A, nothing in this document edits `plan.md`. Decision 1 goes to
the human for validation now; Decision 2 returns to council-resolution (no second full
council needed — this doc's missing-list is the gate) once items 1–4 land.

## Reopen criteria

- **For Decision 1 (decoupling):** reopen if Omnigent's multi-user collaboration model
  is revived for this deployment, or if upstream ships a workspace-native control plane
  (true workspace-scoped auth) that outclasses the registry — the reserved
  `workspace_id` integers keep that door open.
- **For Decision 2 (isolation model):** this decision is not closed; the missing-list
  above IS the reopen state. Once resolved and enacted, reopen on: any observed
  cross-workspace access event; onboarding of a client whose contract requires physical
  separation beyond the A1 capacity bound; VPS hardware change; or multi-user revival.
