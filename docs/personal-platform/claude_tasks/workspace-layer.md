---
type: spec
title: "Workspace layer — per-workspace identity boundary on the code-server plane (A2′)"
task: "workspace-layer"
status: frozen
created: "2026-07-14"
frozen_at: "2026-07-16"
related_decisions: ["plan.md §Phase 2 (workspace hierarchy — amendment pending)", "council/workspace-isolation-amendment.md (both decisions resolved)", "workspace-layer_vps-infra-ruling.md", "workspace-layer_vps-infra-ruling-2.md", "workspace-layer_de.md", "workspace-layer_devils-advocate.md", "workspace-layer_step2-profile.md", "collaboration-vision.md", "kb-three-tier", "secrets-manager"]
---

# Workspace layer — spec (DRAFT, rewritten post-council 2026-07-16)

> **Lifecycle state:** Steps 1–5 complete. Step 3's original design (workspace = one
> `omnigent host` container) was OVERTURNED at Step 5: both reviews + the vps-infra
> architect proved it isolates a plane the user does not use (the Omnigent host/runner
> plane, now dead/disabled). A `/council` resolved the replacement
> (`council/workspace-isolation-amendment.md`, both decisions enacted by the human
> 2026-07-16). This is the rewritten spec. Pending: the `plan.md` amendment (protected —
> human approval of exact text, drafted in `workspace-layer_planmd-amendment.md`), then
> Step 4-redo (da re-designs the alpha test from THIS spec), Step 6 (freeze + seal),
> Step 7 (implementation, split fork/infra). **Human priority: speed to a first working POC.**

## Brief (Step 1 — human-approved, 2026-07-14)

Build the **Workspace** entity as a real identity boundary: a workspace groups N projects
(repos) under one identity — git, cloud credentials (Azure/Databricks), MCP grants,
filesystem — and nothing crosses that boundary by default. Workspace = client company
(the user freelances for several); one exists today (personal); adding the second must be
trivial. Foundation for kb-three-tier, secrets-manager, and the curator.

## What changed and why (Step 5 + council)

The daily work plane is **code-server + the Claude Code extension**, NOT Omnigent's
host/runner machinery (`omnigent-host.service` was found crash-looping and is now
disabled; the Omnigent server authorizes by `owner`, not `workspace`, and all workspaces
share one owner). Isolating the Omnigent host plane protected nothing the user touches.
The council also re-declared the **threat model**: this platform runs autonomous
web-enabled agents daily, so prompt injection is a **present** threat — an injected agent
executes with the editor user's identity. A boundary must hold against *that*.

## Design decision (council-resolved 2026-07-16): A2′ default + A1 (≤1) escalation

### A2′ — per-workspace Unix users inside the single code-server container

Each workspace gets its **own Unix user** (`ws-<slug>`) inside the one code-server
container. The OS kernel — not convention — enforces that an agent running as
`ws-clientb` cannot read `ws-clienta`'s secrets, and a blocked attempt raises a **kernel
permission-denied** (the council's required *observable* trigger, emitted for free as a
side effect of blocking).

This is an **indivisible bundle** — all three parts or none (per the architect; a uid
boundary without the sudo removal is theatre):

1. **Per-workspace uids** (`ws-<slug>`), created by a custom image layer (`useradd` is
   absent from `codercom/code-server`; merges with the `gh`/git-identity bake).
2. **Delete `coder ALL=(ALL) NOPASSWD:ALL`.** Without this an injected agent just
   `sudo`s past every uid boundary. **Master-key principle (human, binding):** root on
   the box belongs ONLY to the vps-infra architect, at the HOST level. Inside the
   container nobody holds root — not `coder`, not any agent, not the lifecycle agents.
3. **The launch wrapper is a security control, tested as one.** `claudeProcessWrapper`
   becomes a script: resolve cwd → workspace → `exec sudo -u ws-<slug> claude "$@"`, so
   the agent acquires the workspace uid. It sits in the extension's pty/stdio path — the
   exact layer that broke twice in one month — so it is validated as a security control,
   never treated as a convenience.

**File layout** — **⚠ POST-FREEZE CORRECTION (2026-07-16): the illustrative mechanism
below was DISPROVEN by live measurement during Step-7 infra build and is SUPERSEDED. The
authoritative permission model is the measured table in
`reviews/workspace-layer_infra-report.md`** (own per-workspace group `ws-<slug>` — never
`coder`; dirs `2770`; code `660`; secrets `0700` ACL-stripped; editor access via POSIX
ACL `u:coder:rwx`, not group membership; audit trail via host `auditd`). The behaviors
this spec requires (editor works, cross-workspace reads denied and recorded, secrets
invisible to the editor) are UNCHANGED; only the how changed. The `de` builds `ws-launch`
against the infra report's model, and the sealed alpha test asserts these behaviors
mechanism-agnostically. Original (disproven) text, kept for history: *each workspace tree
is owner `ws-<slug>`, group `coder`, dirs `750`, code `640`, secrets `600` owner-only.*

**Full Claude Code state isolation:** each workspace launches with
`CLAUDE_CONFIG_DIR=<workspace>/.claude` (owned by its uid). Verified: this relocates the
entire `~/.claude` base including `.credentials.json` and `projects/` transcripts — a
scratch dir reports "Not logged in", the global credential is invisible. Cost: a
per-workspace Claude login (isolation-positive).

**Honest scope:** A2′ hardens the **agent** path. The **human-terminal** path stays
convention-enforced (a user can pick a non-default terminal profile and get a `coder`
shell) — documented, not hidden.

### A1 — dedicated code-server instance, escalation only, ceiling ≤1

A workspace that earns it (contract / data-at-rest / higher trust) escalates to its **own
code-server instance** (own port/volume). Bounded at **≤1** on current hardware: one
instance measures 807 MiB idle. **A1 buys isolation, not capacity** — the binding
constraint is the **2 vCPUs**, not RAM (the 2026-07-15 hard-lock was ~13 Node processes
on 2 cores); the ~3–4 concurrent-Claude ceiling is global across both containers.

### Omnigent server: decoupled but preserved (stop-but-preserve)

The Workspace entity has **no dependency** on the Omnigent server. The server + Postgres
are **stopped, not removed** (`docker compose stop`, never `down -v`; ~10 s
reactivation), because they are the **existing engine for the collaboration vision**
(`collaboration-vision.md`: multi-user auth, per-session permissions, live status, 11
harnesses, credentials that travel with each collaborator's own host). Stopping also
removes a live liability: while running, an injected agent reaches the server at
`127.0.0.1:8000` via `network_mode: host` (the `PUT mcp-servers → agents` secret-
persistence path). `omnigent-host.service` stays disabled. Each registry entry reserves a
stable `workspace_id` integer from day one, so the dormant partition seam stays reachable
if collaboration later wants it.

## Work split (fork vs vps-infra) — most of Stage 1 is infra

| Deliverable | Repo / owner |
|-------------|--------------|
| Custom image layer: `useradd`, bake `gh` + git identity | **vps-infra** (architect) |
| Delete `NOPASSWD:ALL`; narrow per-workspace sudoers rules | **vps-infra** (architect) |
| Per-workspace provisioning script (create uid → chown tree → sudoers → `CLAUDE_CONFIG_DIR` → terminal profile) | **vps-infra** (architect) |
| `mem_limit: 4g`, `cpus: "1.5"` on code-server (E2 — overdue, also a containment control) | **vps-infra** (architect) |
| `docker compose stop` the Omnigent/Postgres stack | **vps-infra** (architect) |
| The launch wrapper script (security control) + its test harness | **this fork** (de) — deployed via vps-infra |
| `workspaces.yaml` registry + schema doc | **this fork** (de) |
| Registry validate script (loud-fail, wired into pre-commit/scheduled) | **this fork** (de) |
| `gitconfig includeIf` config (per-workspace `[user]` + `[credential]`) | **this fork** (de) — applied host-side |
| Governance updates (CLAUDE.md refs, this task's docs) | **this fork** (pm/de) |

The fork footprint is small and touches **zero files under `omnigent/`** — this task does
not modify upstream code. Infra deliverables go to the architect as prompts (per the
infra-consent protocol); this spec is their source of truth.

## The registry (`workspaces.yaml`, in this fork)

One entry per workspace: `slug`, `unix_user` (`ws-<slug>`), root path, git identity
(name/email + credential-helper file ref), `config_dir` (`CLAUDE_CONFIG_DIR` path),
`kb_repo` slug (`kb-ws-<company>`, for kb-three-tier), `secret_store` pointer (for
secrets-manager), reserved `workspace_id` integer (for the future partition seam), and
per-project entries carrying repo URL + default branch (pre-building the Phase-3
project-owns-git-binding slot). Values that are *runnable config* (env files, compose,
sudoers) live in vps-infra and are referenced by path/name, never duplicated (SSOT rule).

## Scope (Stage 1)

Personal becomes workspace #1 under A2′ (its own uid `ws-personal`, config dir, gitconfig
scope), proving the pattern before any client. Deliverables per the work-split table.
"Add workspace #2" is a runbook proven by the alpha test.

## Out of scope

No `/v1/workspaces` API; no DB schema changes; no `omnigent/` or `web/` changes; no
touching the dormant `workspace_id` column (only *reserving* integers in the registry);
no workspace switcher UI (Stage 2a, successor task); no A1 build now (escalation design
only); the human-terminal-path hardening (documented gap, not closed here).

## Escalation stages (triggers BINDING — human-ruled)

- **Stage 2a** — workspace switcher in the VS Code extension (then web UI), reading the
  registry. Trigger: second real client onboarded.
- **Stage 2b** — harden the human-terminal path (force per-workspace profile; no `coder`
  shell fallback in a client folder). Trigger: any cross-workspace access event, or the
  terminal gap proving real in use.
- **Stage 3** — activate the `workspace_id` partition on upstream's seam (collaboration
  driver). Hard precondition: personal migrates off id 0 and 0 becomes a rejected
  sentinel before any read-side filtering ships; this is *sequenced with*, not
  contradicted by, ruling 6 (history stays UNTIL Stage 3, whose precondition then
  migrates it). Trigger: collaboration phase starts, or a client audit / data-at-rest
  requirement.
- **Data-at-rest gate (binding):** before the FIRST client workspace is added, resolve
  the posture explicitly (A2′ commingled-DB-is-moot since the server is stopped; if a
  client needs physical separation → A1 escalation for that client). Onboarding without
  this ruling is a governance violation.

## Acceptance criteria (seeds — da re-designs the alpha test from this spec alone)

1. **Triviality:** adding workspace #2 = run the provisioning script + add a registry
   entry, ≤30 min, no restart of code-server or any other workspace, no `omnigent/`
   changes. The alpha test performs this with a disposable `ws-test`.
2. **Kernel isolation (the core win):** as `ws-test`, reading `ws-personal`'s secret file
   FAILS with permission denied (and the denial is observable); reading its own succeeds.
3. **No master key:** `sudo -n true` as `coder` inside the container FAILS (blanket
   NOPASSWD removed); root operations are only possible host-side (architect).
4. **State isolation:** a `claude` launched under `ws-test`'s `CLAUDE_CONFIG_DIR` does not
   see `ws-personal`'s credentials or transcripts.
5. **Editor still works:** code-server (as `coder`) can open/browse a workspace's code
   (`640`/`750`) but cannot read its `600` secrets.
6. **Git identity:** a commit made in `ws-test`'s tree carries `ws-test`'s configured
   identity, not `coder`'s or another workspace's.
7. **Ecosystem hooks:** kb-three-tier can derive `kb-ws-<company>`'s clone path, and
   secrets-manager its per-workspace secret-store target, from the registry entry alone.
8. **Registry validate script fails loudly** on a seeded registry/live-state mismatch.
9. **Fork governance:** Stage-1 fork diff shows zero files under `omnigent/`.

## Step-5 reviews — COMPLETE (probes already executed)

The original spec's "mandatory probes" targeted the now-abandoned Omnigent host plane and
are moot. What was executed: de code-analysis (`workspace-layer_de.md` — owner≠workspace
CRITICAL, runtime-MCP secret vector), devils-advocate attack (`workspace-layer_devils-
advocate.md`), and the architect's live-measured rulings (`…ruling.md`, `…ruling-2.md`).
No live ephemeral-server probe is outstanding — the architect declined it as moot (the
Omnigent server has no role).

## Risks (residual, post-council)

- **The wrapper is the boundary.** If `claudeProcessWrapper` privilege-drop is wrong or
  bypassed, A2′'s agent-path isolation fails. Mitigation: tested as a security control
  (acceptance criterion 2 exercises it); its failure surfaces as a permission-denied not
  firing.
- **Human-terminal path stays soft** until Stage 2b (documented gap).
- **Day-2 erosion:** shared-repo-across-workspaces needs a hand-punched shared group;
  `apt install` from the container terminal is gone (routes to the architect) — accepted
  cost of the master-key principle.
- **Wrapper layer fragility:** it lives in the pty/stdio path that broke twice this month;
  the test harness must cover restart/reload.

## Seal-prep resolutions (pm, 2026-07-16 — da's 5 alpha-test findings)

1. **"Denied + logged" needs an auditd rule — it is NOT free (load-bearing).** The da is
   correct: a plain DAC `EACCES` is returned only to the caller; the kernel does not log
   it. This matters beyond wording — the council's decisive advantage of A2′ over plain
   A2, and its answer to devils-advocate BLOCKER 2, was an **observable** trigger. Without
   a log there is no observable trigger and the council's resolution is undermined.
   **Resolution: add an `auditd` rule as a vps-infra deliverable** (watch each workspace's
   `.credentials`/secret paths, log denied *and* successful cross-uid reads with
   pid/exe/cwd). This keeps the amended `plan.md` "logs the denial" accurate — its
   observability now *depends on* the auditd deliverable. The alpha test's auditd
   sub-check (C2) becomes **mandatory**, not informational.
2. **Wrapper testability:** the launch wrapper ships with a `--resolve-only` dry-run mode
   (prints the resolved `cwd → workspace → uid` decision without exec), so a check can
   assert the privilege-drop logic non-circularly. Added as a fork deliverable requirement.
3. **Personal migration confirmed in Step-7 scope:** `ws-personal` is migrated to A2′
   before Step 8, else C2/C4/C5 have no counterpart. Already in Scope ("Personal migrates
   first"); reaffirmed as a hard Step-7 precondition.
4. **Governance diff gates `omnigent/` AND `web/`** (both — Out of scope says neither
   changes; seed 9 said only `omnigent/`, now widened to match). `BASE` pins at
   **`f467fc20`** at seal (the amendment commit) unless a later pre-seal commit supersedes.
5. **Group membership via setgid dirs**, not `ws-*`'s primary group (a primary-group
   shortcut would silently break C2's cross-workspace *code* isolation). Added to the
   architect provisioning-script requirements.

## Human rulings carried forward (2026-07-15/16)

Escalation triggers BINDING; registry SSOT rule adopted; data-at-rest gate before first
client; personal migration = new sessions only (sequenced with Stage 3, not contradictory);
interim mobile = extension switcher (Stage 2a), speed-to-POC priority; **A2′ chosen** as
default isolation; **master-key principle** (root only with the architect, host-side).
