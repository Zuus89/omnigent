---
type: review
task: workspace-layer
title: "Workspace layer — devils-advocate Step-5 attack"
status: final
author_role: devils-advocate
created: "2026-07-15"
reviews_head: a9dae275
---

# Workspace layer — devils-advocate Step-5 attack

Adversarial review of the **reasoning** of `workspace-layer.md` (Step-3 spec + 7 human
rulings), per the Grounded-Dissent Protocol. This role does not approve and proposes no
solutions — it names problems, cites evidence, and raises the bar the spec must clear before
someone else approves it.

**Deliberately NOT recycled** (already raised by the 3-judge panel and ruled on by the human):
fail-open `workspace_scope()`, N-stack RAM on a 7 GB VPS, registry-vs-DB drift, and the
Stage-1 control-plane "identity by convention" gap (raw API creates a session for workspace A
on host B). Everything below is on a different axis the panel and the rulings did not visibly
reconcile.

Evidence keys: `spec` = `workspace-layer.md`; `profile` = `workspace-layer_step2-profile.md`;
`chronicle` = `project_chronicle.md`; `plan` = `plan.md`. Line numbers are at HEAD `a9dae275`.

---

## BLOCKER 1 — The entire isolation architecture protects a plane the user does not use

**Assumption attacked.** spec:64-67 — "Isolation of credentials, git identity, filesystem and
MCP env is **kernel-level from day one**"; Brief goal spec:21-26 and locked plan:198-200 —
"nothing crosses that boundary by default."

**Evidence.** The chronicle records, as an explicit V1 decision, that the Omnigent
host/session plane is **not the workflow**:
- chronicle:162-164 — "did not patch the Omnigent extension's own 'localhost-only' iframe
  restriction … not worth it, **this project doesn't plan to use Omnigent's own UI day to day,
  only its code as a base**."
- chronicle:137-141 — the daily surface is `code-server` "serving all 5 repos … as one
  multi-project workspace."
- chronicle:125-127 — code-server "solves a different need … than what Omnigent's own session
  UI provides."
- The spec's own Human-plane paragraph confirms this continues: spec:86-88 — "code-server
  keeps spanning `/opt/work/*` … The editor is a convenience plane, **NOT the security
  boundary**."
- plan:204-208 pinned the Workspace→Project→Session hierarchy to Omnigent's session sidebar;
  V1 step 3 (chronicle) then found that sidebar is not the plane the user works in.

**Failure mode.** Every Stage-1 isolation deliverable — the host container, the per-workspace
env file, the per-workspace Docker network, the per-workspace named volume — governs the
`omnigent host`/runner plane. The plane where the user actually launches Claude Code against
repos is code-server: **one process, one Unix user, one credential set, spanning every
`/opt/work/*`**. On that plane "nothing crosses the boundary" is false by construction, not by
misconfiguration. Acceptance criterion 2 (spec:132) exercises the runner plane and will pass
green while the real day-to-day risk — personal credentials and personal files reachable from
client work — is left entirely untouched. The task ships a genuine kernel-level boundary for a
workflow the chronicle says will not be used, and leaves the workflow that IS used explicitly
outside it. There is no Stage-1 deliverable that forces client work onto the isolated plane.

**Why the panel/human missed it.** The panel scored candidates against plan.md constraints as
if the omnigent-host plane were the surface; ruling 1 (spec:165-168) certified "suffices" on
that same plane. Neither reconciled with chronicle's own V1-step-3 finding that the
host/session plane is not the day-to-day surface.

---

## BLOCKER 2 — Ruling 1 narrowed a locked constraint and self-waived the /council Hard Rule 9 requires

**Assumption attacked.** Ruling 1, spec:165-168 — "Stage 1 SUFFICES. The locked text's
enumerated identity elements (git, **model credentials**, MCP grants, filesystem) are
kernel-isolated from day one … **No `/council` needed**."

**Evidence.** The locked plan is explicit and workspace-scoped:
- plan:198-200 — "its own Claude/model credentials … isolated by container … Nothing crosses
  this boundary by default."
- plan:280-281 — "The credential/identity (OAuth grant, token, account) — always
  **workspace**-scoped. Authenticated once, inherited by every project inside that workspace."
- On the plane of use, this is inverted: code-server holds one Claude credential and one
  `GIT_TOKEN` for all repos (spec:86; chronicle:137-141). A client project opened in
  code-server inherits **code-server's** credential, not the client workspace's env file —
  the per-workspace env file is loaded into the `omnigent host` container (spec:57-59), a
  different container that the code-server terminal and its Claude Code never touch. That is
  the exact inverse of plan:280-281.
- CLAUDE.md Hard Rule 9 — "`plan.md` is the source of truth for scope — if new work
  contradicts a locked decision there … that's a `/council`-worthy moment, not a silent
  override."

**Failure mode.** "Kernel-isolated from day one" holds only if "container" in plan:199 is
silently redefined from "the workspace boundary" to "the omnigent-host container," excluding
the plane of use. That redefinition is a scope narrowing of a locked constraint. Ruling 1
resolved it by unilateral interpretation and, in the same sentence, declared the council gate
unnecessary — the one governance step Hard Rule 9 exists to force. This is a process objection
distinct from BLOCKER 1: even if the technical gap were acceptable, the decision to accept it
was taken through the wrong door.

---

## MAJOR 3 — "Speed to a first working POC" yields no artifact the user can experience

**Assumption attacked.** Human priority, spec:17 and spec:179 — "priority is speed to a first
working POC"; Stage-1 scope, spec:93-101.

**Evidence.** The five deliverables are: (1) host container + credential strip; (2) registry +
schema + validate script; (3) `gitconfig includeIf`; (4) escalation-stages doc; (5)
second-workspace runbook. Of these, only (3) changes anything in the user's real
code-server / Claude Code surface (the git author line per directory), and (3) is a graft from
the **losing** container-per-workspace candidate (spec:86-88), achievable with a few lines of
gitconfig, independent of the host-container/registry architecture. (1) is invisible unless the
user adopts Omnigent host sessions, which chronicle:162-164 says they will not; (2) and (4) are
infra/document artifacts; (5) is inert until a second client exists, and "exactly one exists
today" (spec:24-25).

**Failure mode.** There is no user-experienceable POC in Stage 1 — the deliverable is
invisible plumbing for an unused plane plus a runbook for a client that does not exist. Step-9
human validation "on the live result" (FRAMEWORK) has essentially nothing user-facing to judge
against the very priority the human set, and the single visible change does not require the
architecture being built.

---

## MAJOR 4 — The volume-isolation acceptance criterion is void on the plane of use, by the spec's own design

**Assumption attacked.** AC2, spec:132 — "client host cannot read personal's volume."

**Evidence.** spec:56 — each workspace is "a named volume mounted at `/opt/work/<ws>`."
spec:86 — "code-server keeps spanning `/opt/work/*`." For one code-server process to span
`/opt/work/*`, it must mount the shared `/opt/work` tree (or each volume) — so one Unix user
reads every workspace's files. profile:139-140 already documents the milder version of this
collapse: two sessions at one directory share the same `FilesystemRegistry` and see each
other's working-tree edits; one code-server user over all volumes is that failure a fortiori.

**Failure mode.** AC2's first clause is satisfiable only container-to-container, while the
spec simultaneously guarantees a single process that violates it. A Claude Code agent running
in code-server can `cat /opt/work/<any-other-client>/...` directly. The alpha test greens the
boundary that is not used; the boundary that is used is broken by construction.

---

## MAJOR 5 — The env-refs-only guard lints the wrong layer relative to the vector it names

**Assumption attacked.** spec:80-84 — "Registry-drift guard (**mechanism, not convention**) …
Same mechanism for the env-refs-only rule on the shared `agents` table (one inline secret in a
bundle would persist a client credential in the commingled DB — lint it)."

**Evidence.** profile:71 and profile:155 — the session-scoped MCP route
`POST|PUT /v1/sessions/{id}/agent/mcp-servers` **edits the agent bundle spec at runtime**.
profile:67-69 — bundle `headers`/`env` can carry secrets (`env = strip_runner_auth_secrets(
os.environ) | self.config.env`). The `agents` table lives in the one commingled DB
(profile:161; spec:161). A pre-commit or scheduled **file** lint (spec:81-82) inspects
filesystem bundles at git time; the secret-persistence vector is a runtime API write straight
into the DB.

**Failure mode.** Presented as "mechanism, not convention," but against runtime bundle writes
it is after-the-fact detection at best — and only if the validate script scans the `agents`
table's bundle blobs, which the spec does not state (it "cross-checks registry entries against
live hosts/sessions"). The single commingled-DB leak the spec explicitly fears has an unguarded
live path through the API.

---

## MAJOR 6 — Ruling 6 and the binding Stage-3 precondition are mutually contradictory

**Assumption attacked.** Ruling 6, spec:177 — "Personal migration: new sessions only; existing
history stays where it is" — against Stage 3, spec:117-120 — "personal migrates off id 0 and 0
becomes a rejected sentinel … **Nothing in Stage 1/2 may assume 'id 0 = personal'**." Ruling 2
(spec:169) makes both binding.

**Evidence.** profile:167-170 — every existing row is stamped `workspace_id = 0`
(`DEFAULT_WORKSPACE_ID = 0`). Ruling 6 freezes personal's history at 0 permanently. Stage 3
requires 0 to become a rejected sentinel with personal migrated off it.

**Failure mode.** You cannot both leave personal history at 0 (ruling 6) and reject 0 / migrate
personal off 0 (Stage 3). At Stage 3 — triggered by a client audit, i.e. the worst possible
moment — personal's entire pre-Stage-3 history is either orphaned beneath a read-side filter
that rejects id 0, or the sentinel rejection is unenforceable because legitimate id-0 rows
exist. Ruling 6 perpetuates exactly the "id 0 = personal" assumption Stage 3 forbids. A binding
self-contradiction is being frozen into the artifact.

---

## MAJOR 7 — The triviality criterion is circular and unprovable where the review sits

**Assumption attacked.** AC1, spec:129-131 — "adding workspace #2 = copy compose stanza +
create env file + add registry entry, ≤30 min … The alpha test **literally performs this**."

**Evidence.** "Copy compose stanza" presupposes the personal stanza (deliverable #1, spec:95)
was authored as a parameterized, copyable template — but templating appears nowhere as a
construction requirement of #1; it exists only as an acceptance property tested afterward by a
test `da` designs "from the spec alone" (spec:127). If #1 ships a personal-specific stanza,
"copy + adapt" is precisely the non-trivial work whose triviality is being asserted.
Separately, profile:220 and profile:222 (open-unknowns 1 & 3) — this box is "the dev container
holding the clone, not the running VPS," there is no live `chat.db`, and vps-infra / live-server
state is out of reach — so "the alpha test literally performs this" (add ws #2 with "no
restart of the shared server") requires the production VPS, which the coordinator reports just
hung under load.

**Failure mode.** The 30-minute number measures a deliverable's quality with a test that can
pass only if that deliverable was built a specific, unstated way, and can be executed only on a
box the reviewer/`da` may not be able to drive. The criterion validates itself into existence
rather than being independently measurable.

---

## MINOR 8 — Probe (b) may be a no-op against the actual topology

**Assumption attacked.** Probe (b), spec:147-148 — "verify no server-global leak via
`managed_hosts.py` env injection."

**Evidence.** profile:62 — `managed_hosts.py:44-46` injects server env var names into every
**server-managed sandbox**. The chosen architecture is externally-run host containers with
their own env files, "registered against the single shared Omnigent server" (spec:53-57) — not
server-managed sandboxes.

**Failure mode.** If the personal/client hosts are not spawned through the managed-host path,
probe (b) inspects a code path outside the deployment topology and passes vacuously — false
assurance that no server-global credential reaches a workspace runner, while the credential
strip's real correctness (spec:69-71) turns on how the externally-registered containers receive
env, which probe (b) as scoped does not test.

---

## Bar this raises (no approval — by mandate)

Before anyone else approves, the spec must answer, in order:
1. **BLOCKER 1** — name the deliverable that makes the isolated plane the plane the user
   actually works in, or restate the goal to match the code-server reality the chronicle and
   spec:86-88 both describe. Until then, "nothing crosses the boundary by default" is unmet for
   real use.
2. **BLOCKER 2** — either the model-credential isolation of plan:198-200/280-281 is met on the
   plane of use, or ruling 1's "no `/council` needed" stands in conflict with Hard Rule 9.
3. **MAJORs 3-7** — a POC with a user-visible surface; an AC2 that is not falsified by spec:86;
   a secret guard that covers the runtime MCP-write vector; a resolution of the ruling-6 /
   Stage-3 contradiction; and a triviality criterion that is both a construction requirement and
   executable where it will be tested.
