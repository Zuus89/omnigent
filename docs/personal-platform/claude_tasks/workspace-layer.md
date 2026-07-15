---
type: spec
title: "Workspace layer — identity/credential boundary over N projects"
task: "workspace-layer"
status: draft
created: "2026-07-14"
related_decisions: ["plan.md §Phase 2 (workspace hierarchy)", "kb-three-tier (kb-ws addressing)", "secrets-manager (per-workspace vault scope)", "workspace-layer_step2-profile.md", "step-3 design panel 2026-07-15 (3 candidates × 3 judges)"]
---

# Workspace layer — spec (DRAFT, Step 3 expanded)

> **Lifecycle state:** Step 1 (Brief) approved 2026-07-14. Step 2 (da state profile)
> complete — `workspace-layer_step2-profile.md`. Step 3 (this spec) expanded 2026-07-15
> from a 3-candidate × 3-judge design panel; the 7 open decisions were ruled by the human
> the same day (see "Human rulings"). Pending: Step 4 (alpha test), Step 5 (de +
> devils-advocate reviews, with mandatory executed probes), Step 6 (freeze). NOT frozen
> yet. **Human priority note: optimize for speed to a first working POC.**

## Brief (Step 1 — human-approved, 2026-07-14)

**Goal:** Build the **Workspace** entity as a real identity boundary in our platform: a
workspace groups N projects (repos) under one identity — git, cloud credentials
(Azure/Databricks), MCP OAuth grants, filesystem — and **nothing crosses that boundary by
default**. Workspace = company (the user freelances for several clients); exactly one
exists today (personal), and the entity must make adding the second one trivial when a
real client lands.

**Motivation:** Foundation for kb-three-tier (`kb-ws-<company>` addressing), the
secrets-manager (per-workspace scoping), and the curator (the boundary it must not
cross). Omnigent brings none of this — verified: its "workspace" is a per-session
filesystem path.

## Current state (Step 2 — see the full profile)

No entity above session; "project" is only an `omni_project` label (different repos per
session is definitional); credentials are process-global env (fixed allowlist forwarded
host→runner, `connect.py:405-441`) plus a per-user secret store; backend never sets git
identity; MCP grants are per-session-agent YAML, no persistent store; a **dormant**
`workspace_id` tenant partition key exists on all 12 tables (never activated in this
fork; its ContextVar defaults to `0`); server config is entirely server-global.

## Design decision (Step 3 panel, 2026-07-15)

Three candidates, judged by architect/operator/risk lenses against the locked plan.md
constraints:

| Candidate | Score | Verdict |
|-----------|-------|---------|
| **platform-registry-hybrid** (winner) | 121/150 | Container boundary exactly where agents execute; 3–5 days to first value; zero `omnigent/` changes; staged path TOWARD the partition seam, not away from it |
| container-per-workspace | 107/150 | Most literal isolation, but N full stacks (0.4–0.8 GB idle each) fail a 7 GB VPS; entities never built. Survives as the single-client **escape valve** |
| activate-partition | 103/150 | Only candidate mechanizing Workspace→Project→Session server-side, but `workspace_scope()` **fails open** (default 0 = personal; unbound paths leak silently) and is slowest to value. Its best ideas survive as grafts and as the Stage-3 destination |

**The chosen architecture (Stage 1):** a Workspace is **one Docker container running
`omnigent host`**, registered against the single shared Omnigent server, owning:

- a named volume mounted at `/opt/work/<ws>` (the workspace filesystem),
- its own env file (provider creds, `GIT_TOKEN`/`GIT_USERNAME`, client cloud vars via
  `OMNIGENT_RUNNER_ENV_PASSTHROUGH`) — the container is the **only** holder of that
  workspace's identity,
- its own `~/.gitconfig` (user.name/email + credential helper) and secret store,
- its own Docker network (a client runner has no route to another workspace's host) and a
  `mem_limit`.

Every session for that workspace is created with that `host_id`. Isolation of
credentials, git identity, filesystem and MCP env is **kernel-level from day one**,
riding verified upstream mechanisms — Stage 1 touches **zero files under `omnigent/` or
`web/`**.

**Server credential strip (acceptance criterion):** as part of Stage 1, all provider
credentials and git tokens are removed from the shared server process env. After this
task, the server holds no provider identity at all.

**Product-layer registry:** `workspaces.yaml` in this fork — one entry per workspace:
name, `host_id`, owner, root path, git identity, env-file **reference** (path, never
values), `kb-ws-<company>` repo slug (for kb-three-tier), secret-store pointer (for
secrets-manager), and per-project entries carrying repo URL + default branch
(pre-building the Phase-3 project-owns-git-binding slot). Compose stanzas and env-file
contents live in `vps-infra` (CLAUDE.md §9); the registry references them by name.

**Registry-drift guard (mechanism, not convention):** a validate script cross-checks
registry entries against live hosts/sessions and **fails loudly**, wired into pre-commit
or a scheduled run. Same mechanism for the env-refs-only rule on the shared `agents`
table (one inline secret in a bundle would persist a client credential in the commingled
DB — lint it).

**Human plane:** code-server keeps spanning `/opt/work/*`; correct git identity per
directory via `gitconfig includeIf` (graft from container-per-workspace). The editor is a
convenience plane, NOT the security boundary — the host container is.

**Personal migrates first:** the existing personal usage becomes workspace #1 with its
own host container, proving the pattern before any client exists.

## Scope (Stage 1 deliverables)

1. Personal workspace host container (compose in `vps-infra`, referenced from the
   registry) + server credential strip.
2. `workspaces.yaml` registry + schema doc + validate script (wired, not manual).
3. `gitconfig includeIf` setup for the editor plane.
4. Escalation-stages document with written triggers (see below) — a deliverable, not a
   vibe.
5. Second-workspace runbook proven by the alpha test (the triviality criterion).

## Out of scope

No `/v1/workspaces` API; no DB schema changes or migrations; no `Sidebar.tsx`/web-UI
changes; no per-workspace full Omnigent stacks (rejected on resource fit; documented
escape valve only); no MCP OAuth grant store; **no touching the dormant `workspace_id`
column in any way**. Workspace switcher UI = Stage 2a (successor task).

## Escalation stages (pre-planned, with triggers — pending human sign-off as binding)

- **Stage 2a** — workspace switcher in the VS Code extension (later web UI), reading the
  registry. Proposed trigger: second real client onboarded.
- **Stage 2b** — server-side enforcement that a session labeled workspace W can only be
  created on W's host (closes the "identity by convention" gap at the control plane).
  Proposed trigger: any mislabel/cross-host incident, OR Step-5 probe (a) failure.
- **Stage 3** — activate the `workspace_id` partition on upstream's own seam, with the
  fail-open fix as a **hard precondition**: personal migrates off id 0 and 0 becomes a
  rejected sentinel before any read-side filtering ships. Nothing in Stage 1/2 may assume
  "id 0 = personal". Proposed trigger: client audit / data-at-rest requirement (or the
  stack-per-client escape valve for that one client).
- **Data-at-rest gate (human-added, binding):** before the FIRST client workspace is
  added, the data-at-rest posture must be resolved explicitly — commingled DB accepted
  for that client, escape-valve stack, or accelerated Stage 3. Onboarding a client
  workspace without this ruling is a governance violation.

## Acceptance criteria (seeds — da designs the alpha test from this spec alone)

1. **Triviality test:** adding workspace #2 = copy compose stanza + create env file + add
   registry entry, ≤30 min, no restart of the shared server or any other workspace, no
   code changes. The alpha test literally performs this.
2. **Isolation:** client host cannot read personal's volume; personal creds absent from
   client runner env; git commits in the client workspace carry the client identity.
3. **Credential strip:** shared server env contains no provider credentials or git tokens.
4. **Ecosystem hooks:** kb-three-tier can clone `kb-ws-<company>` into `/opt/work/<ws>/`
   from the registry entry alone; secrets-manager can target the per-workspace env
   file/secret store from the registry pointer alone.
5. **Fork governance:** `git diff` of Stage 1 shows zero files under `omnigent/` — any
   such file in the diff is a spec violation.
6. Validate script fails loudly on a seeded registry/live-state mismatch.

## Step-5 mandatory executed probes (blocking freeze)

(a) **Host-tunnel blast radius:** can a registered host's tunnel token enumerate or act
on other hosts' sessions through the shared server? (Risk judge's key objection; profile
open-unknown 7.) **Contingency if it fails:** see open decision 3.
(b) Allowlist env forwarding is per-host-container as documented (`connect.py:405-441`);
verify no server-global leak via `managed_hosts.py` env injection.
(c) Smoke probe that upstream's `workspace_scope()` read-side filtering actually works
(informs Stage-3 feasibility; it has never executed in this fork).

## Risks

- Stage-1 identity isolation at the **control plane** is convention until Stage 2b
  (architect's objection): a raw API call can create a session for workspace A on host B.
  Mitigated by the validate script + Stage 2b trigger; ruled on in open decision 1.
- Single-operator deferral hazard: Stage 2b/3 never funded once Stage 1 "works" (both
  C-preferring judges). Mitigation: binding triggers (open decision 2).
- Registry beside DB = second source of truth; drift guarded by mechanism (validate
  script), SSOT rule in open decision 4.
- All clients' transcripts/metadata commingle in one DB until Stage 3 (open decision 5).

## Human rulings (2026-07-15 — all 7 decisions resolved, question by question)

1. **Locked-constraint interpretation:** Stage 1 SUFFICES. The locked text's enumerated
   identity elements (git, model credentials, MCP grants, filesystem) are kernel-isolated
   from day one; the control-plane misuse gap is closed by Stage 2b under a binding
   trigger. No `/council` needed.
2. **Escalation triggers are BINDING** — written into TODO.md at close; a fired trigger
   creates a mandatory task.
3. **If Step-5 probe (a) fails:** Stage 2b is pulled into the immediate successor task.
4. **Registry SSOT rule adopted as stated:** registry owns product semantics; `vps-infra`
   owns runnable config; the validate script arbitrates loudly.
5. **Data-at-rest:** no client requiring physical separation is anticipated, BUT the
   posture must be explicitly resolved BEFORE the first client workspace is added — added
   above as a binding gate. Escape valve stays documented.
6. **Personal migration:** new sessions only; existing history stays where it is.
7. **Interim mobile surface:** the VS Code extension switcher suffices (Stage 2a);
   priority is speed to a first working POC — no web-UI scope now.
