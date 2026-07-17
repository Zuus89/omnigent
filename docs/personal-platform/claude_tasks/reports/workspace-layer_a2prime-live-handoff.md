---
type: handoff
task: workspace-layer
title: "A2′ is LIVE — infra→agent handoff (post-recreate environment change)"
status: final
author_role: infra
captured_by: pm
created: "2026-07-16"
related_decisions:
  - "reviews/workspace-layer_infra-report.md (deliverables 1-7, authoritative permission model + sudoers rule)"
  - "reviews/workspace-layer_vps-infra-ruling-2.md"
  - "reports/workspace-layer_ws-launch.md (de Step-7 implementation report for the wrapper this handoff activates)"
  - "context_snapshot.md (refreshed from this handoff)"
  - "vps-infra PR #4 — https://github.com/Zuus89/vps-infra/pull/4"
---

# A2′ is LIVE — infra→agent handoff (2026-07-16)

> **Provenance.** Verbatim-faithful capture of the vps-infra architect's handoff delivered
> at the top of session, filed as a report per the human's instruction ("deja este handoff
> como reporte"). This is the successor to the Step-7 pause point (activity_log 2026-07-16
> T16:32/T17:26): `ws-launch` merged + gate-SAFE, architect prompt delivered, the ONE
> recreate window pending. **That window has now happened.** A2′ ("deployed" → **protected**)
> is active. pm annotations are marked _[pm]_.

## 1. What changed (environment)

1. **The agent now runs as `ws-personal` (uid 1001, gid 2001), not `coder`.** The Claude Code
   extension launches via `claudeProcessWrapper = /usr/local/bin/ws-launch`, which drops to
   the workspace uid. File ownership, git identity, and read reach are ws-personal's.
   _[pm] Confirmed live: `id` → `uid=1001(ws-personal) gid=2001(ws-personal)`._

2. **Repos moved to a nested layout.** The fork is now at
   **`/home/coder/repos/personal/omnigent`** (was `/home/coder/repos/omnigent`). All 5
   personal repos live under `personal/` (saga-voice, vps-infra, lifecycle-framework,
   zuus89.github.io, omnigent). `ws-launch` resolves the workspace by an ancestor dir named
   after a registered slug — hence the `personal/` nesting. The old path no longer exists.

3. **Auth is done and persisted** (both as ws-personal, on a host-backed volume surviving
   container recreates): **gh** authed as `Zuus89` (`/home/ws-personal/.config/gh`),
   `setup-git` done → `git push` works. **Anthropic**:
   `/home/ws-personal/.claude/.credentials.json`. No re-auth needed. If ever required: do it
   through the AGENT panel, never a plain terminal (terminals run as `coder`, ephemeral,
   agent-invisible). _[pm] This resolves continuity item (A) the pm raised pre-window._

4. **Auto-memory (4 files) was lost** in the recreate — the old `~/.claude` was on the
   ephemeral overlay, wiped before migration (an infra sequencing mistake, owned by infra).
   Reconstructable: durable state (`docs/personal-platform/` — chronicle, plan, TODO,
   context_snapshot, claude_tasks) is git-tracked and INTACT. New memory persists at
   `/home/ws-personal/.claude/projects/-home-coder-repos-personal-omnigent/memory/`.
   _[pm] This is continuity item (B) the pm raised pre-window; it did NOT land. Memory
   reconstructed this session from the durable docs._

## 2. How to work now

- **Editing, running claude, git commit/push as the agent** → all as ws-personal. The repos
  are ws-personal's (owner + ACL); push uses gh.
- **The editor file tree / `coder`'s own edits** still read/write code (via an ACL), but
  **`coder` cannot git a ws-owned repo** (dubious-ownership; `safe.directory` was removed
  deliberately — it was a CVE-2022-24765 RCE vector). Do git through the agent, not a `coder`
  terminal.
- **Terminals run as `coder`.** There is intentionally no `sudo -u ws-personal` terminal
  profile (a shell sudo grant would be a cross-workspace escalation). Until `ws-launch
  --shell` exists (flag #1 below), a human shell-as-workspace is unavailable — work the repo
  via the agent.

## 3. Alpha test (Step 8) — ready for the DA

Infra-side verification runbook:
**`/home/coder/repos/personal/vps-infra/docs/a2prime_alpha_verification.md`** — every
acceptance criterion mapped to a live command + expected output, captured 2026-07-16 with two
real workspaces. Verified live by infra: cross-workspace secret read denied both directions,
denial logged in auditd with the offending uid, narrow-sudoers escalation denied, editor
reads/writes code but not secrets, launcher fails closed, PATH/claude poison defeated,
continuity persists across recreate.

**Split (bias-free):** infra (root) stands up a throwaway 2nd workspace + planted secrets;
the **DA** performs the cross-workspace read attempt as ws-personal and observes the denial
itself. When the DA is ready → ping infra (via Cristóbal); infra stands up the scaffold on
the spot. Everything is in **vps-infra PR #4**.

_[pm] This is the critical path to CLOSE workspace-layer (Step 8 → 9 → 10). It has a host-side
dependency: infra must stand up the scaffold, so it is NOT self-served — it needs a Cristóbal
→ infra ping. Two fork pieces still gate the DA run: `workspaces.yaml` (+schema) and its
validator, backing alpha checks C7 (registry derivability) and C8 (validator loud-fail)._

## 4. Flags that need the fork agent (they touch `ws-launch` — the agent's file)

Ranked by impact by infra:

1. **`ws-launch --shell` mode (highest — the only real UX gap).** A fail-closed, path-pinned
   shell: resolve cwd→workspace, `exec sudo -u ws-<slug> bash`. One control for both the agent
   (claude) and the human (terminal + git as the workspace uid). Without it the human has no
   workspace shell. The sudoers rule + build pin already fit a single wrapper — adding
   `--shell` needs no infra change beyond a rebuild.

2. **Scalable per-workspace persistence.** Today each workspace home is a per-workspace host
   bind-mount → a new client needs a compose edit + recreate (breaks the ≤30-min / no-restart
   goal). Proper form: `ws-launch` exports `CLAUDE_CONFIG_DIR` and `GH_CONFIG_DIR` into a
   single already-mounted parent (`/opt/code-server/ws-homes/<slug>/…`), so a new client is
   just `mkdir` — no recreate. A ws-launch change, hence the agent's.

3. **`.claude` audit gap.** The workspace `.claude` (OAuth + transcripts) sits outside the
   `/root/repos` audit boundary. DAC (0700) still protects it; only observability is missing.
   To make it auditable, decide where `CLAUDE_CONFIG_DIR` lives (a host-visible path) — a
   ws-launch / topology call.

_[pm] These are each a NEW Phase-2 task on a SHA-pinned security control — each needs its own
spec, code-reviewer gate, and an infra re-pin (see §5). They are enhancements to a wrapper
that already passed its gate; per Hard Rule 2 (one session, one task) they do not preempt
closing workspace-layer. Logged for sequencing — see this session's triage._

## 5. Housekeeping (from infra)

- **`ws-launch` passed** its own code-reviewer gate AND infra's adversarial pre-commit review.
  The 1 CRITICAL + several HIGH the review found were all in **infra's** scripts (symlink-follow
  in the secrets chown, the safe.directory RCE, build-time wrapper poisoning, a mislevelled
  audit watch, a GID-collision fail-open) — all fixed and verified. The wrapper's ownership
  anchor + PATH-hardening held up.
- **`ws-launch` is baked with a SHA-256 integrity pin** (`build.sh` `EXPECTED_WRAPPER_SHA`).
  **If the agent ships a new `ws-launch`, tell infra** — the pin must be re-verified and
  updated, or the build refuses it (the anti-poisoning control working). _[pm] This is the
  hard coupling on every one of the three flags above._
- **Adding a client workspace later:** update `workspaces.yaml` (the product registry, the
  folder↔client map) → tell infra → infra runs `provision-workspace.sh <slug>` (root); the
  client's repos go under `/home/coder/repos/<slug>/`. `ws-launch` keeps resolving against the
  root-owned `/etc/code-server-workspaces` registry (coder cannot rewrite it).

## 6. pm status summary

| Item | State |
|------|-------|
| A2′ isolation model | **LIVE** — agent runs as ws-personal, kernel-enforced |
| `ws-launch` wrapper | Merged, gate-SAFE, baked + SHA-pinned, E2E-verified live by infra |
| Continuity (A) git push as ws-personal | ✅ resolved (gh as Zuus89) |
| Continuity (B) memory migration | ❌ failed → reconstructed this session from durable docs |
| workspace-layer Step 8 (DA alpha test) | **Ready**, blocked on: 2 fork pieces + a Cristóbal→infra scaffold ping |
| Fork piece: `workspaces.yaml` + schema | Not built (backs alpha C7) |
| Fork piece: registry validator | Not built (backs alpha C8) |
| Flag #1 `ws-launch --shell` | Open — new task, needs spec + gate + infra re-pin |
| Flag #2 scalable persistence | Open — new task, needs spec + gate + infra re-pin |
| Flag #3 `.claude` audit gap | Open — new task, topology decision + infra |
