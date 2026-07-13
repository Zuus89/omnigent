# V1 — Multi-device coding UI on the Omnigent VPS

## Context

The user wants their own personal, multi-device AI coding platform — a comfortable
multi-project editor UI (like the several VS Code windows they run today), reachable from
any device. After comparing the 2026 landscape (Cursor, Windsurf, Zed, Google Antigravity,
Cline, OpenCode, Claude Code Remote Control, code-server), the decision was: **build it as a
fork + extension of Omnigent** (open source, Apache 2.0, `github.com/omnigent-ai/omnigent`),
not from scratch — and V1's goal is a decent multi-device UI *now*, assembled from pieces
that already exist, before writing any custom Omnigent code.

**Scope decision (revised): configurable, but Claude Code is the only provider actually in
use.** The platform still needs to let the user **choose a coordinator and choose a model
per deployed agent** — that flexibility stays as a designed capability (Phase 3's agent
roster is per-role-configurable, not hardcoded to one provider). What's dropped is
*exercising* that flexibility with other providers: the user doesn't hold enough
Gemini/Codex/other-provider accounts for multi-provider orchestration to be worth anything
in practice right now. So every role defaults to, and today only ever runs as, Claude Code —
the coordinator/per-agent model picker exists in the design but has exactly one real option
until that changes. Omnigent's CLI already ships the actual multi-harness capability (see
below) — nothing to build there, it's just unused today.

**Repo strategy:** no new repo gets created. Code and product docs (this plan, specs, the
vision) live **inside the existing fork**, `Zuus89/omnigent` — already cloned on the VPS at
`/opt/omnigent`, already synced with `upstream/main`. Product docs go under their own
directory there (e.g. `docs/personal-platform/`), kept separate from upstream's own docs so
future `upstream/main` syncs don't conflict. `vps-infra` keeps its existing scope:
**deployment config only** (the code-server compose file, the Omnigent compose override,
systemd, access mirrors) — exactly the role it already plays for the Omnigent stack
currently running. One repo holds the product (code + why); the other documents how it's
hosted.

**A live audit of the VPS (this session) found the machine is much further along than any
doc in this repo records — none of this was documented anywhere:**

- `/opt/omnigent` is **already a full clone of the user's own fork**: `origin` =
  `https://github.com/Zuus89/omnigent.git` (with a live GitHub token embedded in the
  remote URL — a plaintext-credential loose end to close), `upstream` =
  `https://github.com/omnigent-ai/omnigent.git`. On `main`, clean, fully synced with
  `upstream/main` (HEAD `6e3c7785`). **The fork/clone step from the earlier plan is already
  done** — no need to redo it.
- The `omnigent` CLI already ships **11 harness launchers as first-class subcommands**:
  `claude`, `codex`, `cursor`, `antigravity`, `goose`, `hermes`, `kimi`, `kiro`, `opencode`,
  `pi`, `qwen` — plus two bundled multi-agent orchestrators, **`polly`** ("the bundled
  multi-agent coding orchestrator") and `debby`. The "coordinator dispatches to a
  different-provider sub-agent" capability the user wants is **not something to build — it
  already exists in the installed CLI** and has never been tried.
- Omnigent ships its own (currently minimal) **VS Code extension**
  (`/opt/omnigent/editors/vscode`, not yet published — builds from source into a `.vsix`).
  It opens the locally-running Omnigent server's web UI in an editor-beside iframe pane
  inside VS Code. It only auto-discovers a server on `127.0.0.1` — the deployed server is
  currently bound only to the tailnet IP (`100.116.27.33:8000`), so the extension won't find
  it as-is.
- `ufw` already has **80/443 open publicly** (comment: "https (Omnigent web UI)") but
  nothing is listening there yet — this is the unfinished "Public 443 for externals" item
  from the old context snapshot, not anything new to build for V1.
- Resources are healthy for this work: 2 vCPU, ~7 GB RAM available, 88 GB free disk.

This plan closes that documentation gap and builds V1 on top of what's actually there,
instead of re-doing work that already exists.

## What V1 delivers

Open a URL from the notebook, the tower, the tablet, or the phone — over the tailnet — and
get: a real multi-project VS Code UI (all 5 existing repo clones as one workspace), the
Claude Code extension working as it does today, and the Omnigent server's own UI reachable
inline. No custom Omnigent code gets written in V1 — that's the next phase, once this base
is proven solid.

**Explicitly out of scope for V1:** writing custom Omnigent features, exposing anything on
public 80/443, native mobile app packaging, per-client/company isolation (the user confirmed
this VPS is personal-only).

## Steps

### 1. Document the undocumented state (close the drift first)

- Update `docs/knowledge_base/vps_omnigent_inventory.md`: add a section recording the
  `/opt/omnigent` fork/clone (remotes, current HEAD, purpose — the dev base for future
  contributions), the pre-opened-but-unused 80/443 ufw rule and the existing
  `docker-compose.https.yaml` overlay (for whenever public access is decided), and the CLI's
  harness/orchestrator inventory (`polly`, `debby`, the 11 harness subcommands).
- No `vps-omnigent/` mirror changes needed yet (nothing new to version-control until the
  code-server compose file in step 3).

### 2. Strip the embedded token from the fork's git remote (small, related cleanup)

- `/opt/omnigent`'s `origin` remote has a live `gho_...` GitHub token sitting in plaintext in
  `.git/config`. `gh` is already authenticated on this VPS (confirmed this session) and can
  serve as the credential helper instead, same pattern already used for the other cloned
  repos. Repoint `origin` to the plain `https://github.com/Zuus89/omnigent.git` URL and run
  `gh auth setup-git` (or confirm the existing global gh credential helper covers it).

### 3. Confirm the coordinator/agent picker exists, Claude-only for now

Not a multi-harness smoke test (dropped — no other-provider accounts to test with).
Instead, a cheap check that the **capability to choose a coordinator and per-agent models
stays real and visible**, even with a single provider configured:

- `omnigent config` — confirm each role (coordinator + deployed agents) has its own model
  setting, currently all pointing at Claude Code, and that changing one doesn't require
  touching the others. This is the hook Phase 3's per-role model picker builds on later.
- **Also check two specific things**, since both matter for the target hierarchy
  (Workspace → Project → Session) and don't need building if Omnigent already has them:
  1. Does the existing sidebar (the desktop-app screenshot in Omnigent's own README shows
     "pinned and project-grouped sessions") actually group sessions by project the way we
     want, with more than one session open per project?
  2. Is there any view of **agents/sessions currently running in the background** — active
     elsewhere, not the one you're looking at right now — across the server? If the session
     list already surfaces this (status per session, running vs idle), nothing to build. If
     not, this becomes a named Phase 2 candidate below.

### 4. Stand up `code-server` on the VPS (the multi-project editor UI)

- New Docker Compose service, **separate file** from the existing Omnigent stack (don't
  touch `/opt/omnigent/deploy/docker/docker-compose.yaml`), bound only to the tailnet IP
  (`100.116.27.33:<port>`, matching the existing hardening pattern — never `0.0.0.0`), a free
  port (e.g. `8443`).
- Password-protected via code-server's built-in auth; password generated and stored
  following the existing `.claude/.local/secrets.env`-style pattern (never committed).
- Workspace root at `/root/repos/`, so `vps-infra`, `saga-voice`, `zuus89.github.io`,
  `lifecycle-framework`, and the `omnigent` fork are all reachable as one multi-folder
  workspace.

### 5. Wire the two VS Code extensions inside code-server

- Install the Claude Code VS Code extension (same multi-chat-tab experience already in use
  today, now reachable from any device).
- Build Omnigent's own extension from the already-cloned source: `cd
  /opt/omnigent/editors/vscode && npm ci && npm run build && npm run package` → produces a
  `.vsix`, installed via "Install from VSIX…" (it isn't published anywhere stable yet).
- Add a `docker-compose.override.yaml` next to the existing Omnigent compose stack that
  **additionally** publishes `127.0.0.1:8000:8000` (purely additive — the existing
  tailnet-only publish stays untouched). Since code-server now runs on the same VPS, this
  makes "localhost" true for the extension's auto-discovery, without exposing anything new
  off-box (a loopback bind is never reachable from outside the machine).

### 6. Test from a second device

- Open the code-server URL from the tablet or phone browser over the tailnet.
- Confirm: VS Code loads, all 5 repos are visible, both extensions load, and Omnigent's
  "Open" command successfully iframes the local server's UI inline.

### 7. Document + commit

- Mirror the new code-server compose file (and the Omnigent compose override) under
  `vps-omnigent/`, matching the existing mirror pattern for this VPS.
- Update `docs/knowledge_base/vps_omnigent_inventory.md` with the new service (port, auth
  method, purpose).
- `docs/activity_log.jsonl` entry + commit, following the pattern used all session.

## Verification

- `ssh omni-vps "docker compose -f <code-server-compose> ps"` shows the container healthy,
  port bound only to the tailnet IP (confirm with `ss -tlnp` — no `0.0.0.0` entries added).
- From the notebook browser: `http://omnigent-vps:8443` loads code-server, password prompt
  works, all 5 repo folders appear in the workspace.
- From the tablet or phone browser (tailnet-connected): same URL loads and is usable.
- Inside code-server: Claude Code extension opens a chat session normally; Omnigent
  extension's "Omnigent: Open" command successfully shows the local server's UI in an
  editor-beside pane (proves the loopback override worked).
- `omnigent config` shows a per-role model setting (coordinator + each agent), all pointing
  at Claude Code today, changeable independently — the picker is real even with one provider
  actually in use.

---

# Phase 2 — Workspace hierarchy + KB curator (defined now, built later)

Not part of V1. This section exists so the V1 infra decisions above don't paint us into a
corner — "workspace" is treated as a first-class concept from V1 onward (even though only
one exists today), so this phase slots in without rework.

## Why this is the first real "extend Omnigent" feature

Everything in V1 is assembly of existing pieces. This is the first genuinely custom feature
— the reason to fork rather than just consume Omnigent as-is.

## Workspace hierarchy

A **workspace** is a full identity context, not just a folder: its own git identity, its own
Claude/model credentials, its own MCP OAuth grants, its own filesystem — isolated by
container (or equivalent OS-level boundary). Nothing crosses this boundary by default. Today
there is exactly one workspace (personal). More get added later only when a real distinct
identity/credential need shows up (e.g. a client with their own accounts) — not speculatively.

Inside a workspace, the hierarchy goes **Workspace → Project → Session**: a workspace holds
several projects (repos), and each project holds many sessions (chats) — not one session per
project. Omnigent's own desktop app already claims exactly this ("pinned and project-grouped
sessions in the sidebar" per its README) — V1 step 3 checks this firsthand rather than
assuming it needs to be built.

**Background agent visibility** — a view of what's currently running elsewhere on the server,
not just the session in front of you — is checked the same way in V1 step 3. If Omnigent's
session list already shows running/idle status across all sessions, nothing to build here. If
it only shows the session you're actively viewing, add "background session status view" as a
Phase 2 candidate alongside the KB curator panel.

## Three-tier knowledge base

KB tiers mirror the hierarchy exactly (Global → Workspace → Project), narrowest scope wins
when both apply:

- **Project KB**: lives inside each project, private to it. This already exists in pattern —
  it's `docs/knowledge_base/` as scaffolded by the lifecycle-framework (`/lifecycle-init`)
  today, e.g. in `vps-infra`. Every project gets its own.
- **Workspace KB**: shared across every project inside one workspace, but not visible to
  other workspaces. Sits above the per-project KBs — for things true of the whole
  workspace (e.g. "how this identity's git remotes are set up") but not worth repeating in
  every project's own KB.
- **Global KB**: lives in its own space, owned by no single workspace (its own repo, mounted
  read-only into every workspace), so reading it from any workspace never crosses another
  workspace's boundary. Written to **only** via the promotion flow below — never
  auto-synced. A project can promote to its workspace tier or all the way to global,
  depending on how broadly the curator (and the user, in review) judge it applies.

## KB curator agent + review panel

- A **dedicated curator agent**, separate from the agents doing real work in each workspace.
  Its only job: notice things worth remembering during normal sessions and draft a promotion
  proposal (what, why, and which tier — workspace-local or global).
- A **review panel** in the platform UI: a queue of pending proposals, each showing its
  source workspace, the proposing agent, and the drafted content. The user can accept,
  reject, or **converse with the curator to refine it** before anything is written —
  promotion is never silent or automatic, first pass always requires explicit confirmation
  (may relax later once the curator's judgment is proven).

## Verification (when this phase is actually built)

- A curator proposal appears in the panel after a session surfaces something notable.
- Rejecting a proposal writes nothing to any KB.
- Accepting a project- or workspace-scoped proposal writes only at that tier.
- Accepting a global proposal writes to the global KB and is then readable (read-only) from
  a second workspace.

---

# Phase 3 — Native project lifecycle (reimplementing the lifecycle-framework)

Not part of V1. Defined now because it directly shapes "new project" in the UI, and because
the decision below changes what Phase 2/3 code depends on.

## Source: the user's own `lifecycle-framework` plugin

`C:\Users\celto\OneDrive\Freedom Freelancing\Portfolio\lifecycle_framework` is a real,
working Claude Code plugin (`celtonchamberlain/lifecycle-framework`, the same one that
governs `vps-infra` itself) with a `/lifecycle-init` skill that already does almost exactly
what's needed for "new project" in this platform:

- **Git connection** — detects an existing repo/remote/branch, or guides creating one.
  Today it's GitHub-first; the platform generalizes this to a provider choice (GitHub, Azure
  DevOps, other) — **every project always gets a git connection, no exceptions**, only the
  remote host is a per-project user choice.
- **MCP connection** — verifies `memory` (required, must be a **per-project isolated path** —
  the framework's own hard-learned rule: never share one memory file across projects, that
  collapses isolation), plus `github` and a tracker MCP as recommended/user-global.

### Credential vs. resource: the rule that decides workspace vs. project for every connector

Every external connection (GitHub, Azure DevOps, Atlassian/Jira, Databricks, Microsoft 365,
Tailscale, a tracker) splits into two layers that get assigned to different tiers:

1. **The credential/identity** (OAuth grant, token, account) — always **workspace**-scoped.
   Authenticated once, inherited by every project inside that workspace.
2. **The specific resource used through that connection** (which repo, which Jira project,
   which Databricks warehouse, which OneDrive folder) — always **project**-scoped, selected
   using the credential already inherited from the workspace.

Git looks like an exception but isn't: the specific repo is naturally project-scoped (a
project *is* a repo), but the account that authenticates to GitHub/DevOps is the
workspace's — same split as Databricks/Atlassian/Microsoft. `memory` is the one true
exception: there's no shared credential involved, it's pure isolation, so it's
project-scoped end to end with no workspace layer at all.
- **Optional governance scaffold** — the full Tier-B file tree (`CLAUDE.md`, `docs/`,
  `.claude/settings.json`, rules, hooks, CI) plus the Tier-A agent roster (pm/de/da/
  code-reviewer/devils-advocate + optional corpus-steward/scout/dead-code-cleanup) and the
  10-step lifecycle. Today this is all-or-nothing per repo (install the plugin, run
  `/lifecycle-init`); the platform makes it a **per-project toggle** — not every personal
  project needs the full ceremony (most of the work seen in `vps-infra` itself has actually
  been ad-hoc shortcuts, not the full 10 steps).

## Decision: reimplement natively, don't depend on the Claude Code plugin

Today Tier A (the agents/skills) is a Claude Code plugin — installed per machine, outside
the repo, invisible unless that exact plugin happens to be installed (this was the whole
`vps-infra` audit finding earlier this session: the plugin wasn't installed on this notebook
despite `CLAUDE.md` assuming it was). For the platform, **the roles, the 10-step lifecycle,
and `/lifecycle-init`'s interview get rebuilt as native features of the platform itself** —
not dependent on any Claude Code plugin being present. This costs more upfront than just
depending on the existing plugin, but means:

- The lifecycle works the same for every project regardless of which machine/session opens
  it — no more "governance doc assumes a plugin that isn't there."
- The roles (pm/de/da/code-reviewer/devils-advocate) get their own per-role model setting by
  construction, not tied to one harness — the coordinator/agent picker from V1 step 3 is
  really this. Every role runs on Claude Code today (see the scope decision at the top of
  this plan — no other-provider accounts to make multi-provider worth anything right now),
  but the picker stays real: `pm` as the coordinator, `de`/`da`/`code-reviewer`/
  `devils-advocate` as its agents, each independently switchable later if that changes.

## New-project flow (native reimplementation of `/lifecycle-init`)

1. Project identity (name, goal, stack) — same as today's interview.
2. **Git connection (mandatory)**: detect existing remote, or create one — provider choice
   (GitHub / Azure DevOps / other), not assumed.
3. **MCP connection**: attach the workspace's shared MCP credentials (github, tracker) +
   provision this project's own isolated `memory` path (never shared across projects, per
   the framework's own corrected rule — §9 of its `INVENTORY.md`).
4. **Governance toggle**: full lifecycle scaffold (docs tree, roles, 10-step process) on, or
   stay lightweight (just the git + MCP connections, no ceremony) — per project, not global.
5. If governance is on: seed the project KB (this plan's Phase 2 tiering) instead of a bare
   `docs/knowledge_base/`, so it's promotion-aware from day one.

## Verification (when this phase is actually built)

- Creating a project without a git remote is not possible — the flow blocks until one exists
  or is created.
- A project created against Azure DevOps (not GitHub) works identically to a GitHub one.
- Two projects in the same workspace never share a `memory` path.
- Toggling governance off produces a project with no `docs/` ceremony, still git + MCP
  connected.

---

# Design reference: the interactive mockup

Built and iterated during this planning conversation:
`https://claude.ai/code/artifact/e0c98989-9fc7-4f2a-ad85-8f3de5f15232`. This is the visual
target for Phase 2/3's actual UI work — not built in V1, but every structural decision below
is locked in and should be matched, not reinvented, when the real implementation starts.

## Information architecture — a VS-Code-style activity bar, not floating panels

An early version of the mock used popovers/slide-overs for background agents and the KB;
that was wrong (learned from studying Google Antigravity's actual layout: an activity bar on
the left swaps the *same* sidebar region, it doesn't stack floating surfaces). The corrected,
locked-in IA — a narrow activity bar with five sections, each swapping the sidebar's content:

1. **Sesiones** — the Project → Session tree (this plan's core hierarchy).
2. **Filesystem** — the active project's file tree, decorated with live git status (see
   below), file rows open in the right rail as a read-only preview.
3. **Background** — every agent/session currently running elsewhere in *this workspace only*
   (never another workspace — the isolation boundary holds even here).
4. **Knowledge base** — the three tiers (Global / Workspace / Project) as tabs, plus the
   curator's proposal queue with Accept / Reject / Discuss.
5. **Agentes & config** — four tabs: **Agentes** (the pm/de/da/code-reviewer/devils-advocate
   roster, each showing which model it's mapped to — the concrete surface for the
   coordinator/per-agent model picker; every row shows Claude Code today, per the scope
   decision at the top of this plan), **Skills** (`/lifecycle-init`, `/close-task`, etc.),
   **Hooks** (destructive-guard, post-commit-log, index-rebuild — each with its trigger
   event), **MCP** (the connectors, each tagged with its scope per the credential-vs-resource
   rule above).

   **Known stale bit in the current mock:** the top bar's harness chips and a couple of
   agent rows still show Gemini/Codex as if actively in use — a leftover from before the
   scope decision above. Cosmetic only; fix whenever the mock gets touched again, not urgent
   enough to interrupt V1 execution for.

## Git status is always visible, not something you go looking for

The Filesystem section's icon carries a badge with the uncommitted-file count. Inside: a
branch/sync summary at the top (branch name, ahead/behind, dirty count) and every changed
file decorated inline with its status letter (`M` modified, `U` untracked) in a semantic
color — never the rationed accent color, per the design system's own rule.

## The right rail defaults to session progress, not a dead space

A persistent right-hand panel shows the active session's step-by-step TODO (mirrors the
TodoWrite tool's own state: done / in-progress / pending, with a completion bar) by default.
Clicking a file in the Filesystem section temporarily swaps this same rail to a read-only
file preview, with a back arrow to return to progress — the rail is never idle chrome.

## Design system discipline (why it doesn't look like a generic "AI tool")

Modeled after the `impeccable` design methodology (the user's own design-system generator,
referenced via its output for `zuus89.github.io`, since the plugin itself is vendored as a
broken junction in this environment and isn't directly runnable here). Rules actually
followed in the mock, to keep following in the real build:

- **One rationed accent** (a muted sage), used only for: the active activity-bar item,
  primary buttons, focus rings, and "promoted" KB tags. Never decorative, never more than a
  small fraction of any screen.
- **Semantic colors are never the accent** — running/done/error/git-modified/git-new each
  get their own hue, distinct from the accent and from each other.
- **A dedicated "provenance" color** (muted violet), used *only* to mark curator/agent-
  authored content (KB proposals) — analogous to `impeccable`'s "AI purple is never a style
  choice" rule. Never used decoratively elsewhere.
- **Flat by default** — 1px borders carry structure; shadow is reserved for the one surface
  that truly floats (the new-project modal). No glow, no pulse-on-loop animations (an earlier
  draft had a pulsing "background agents" badge — removed for reading as generic "AI is
  thinking" chrome).
- **Mono for data, sans for anything spoken** — paths, timestamps, counts, and labels in
  monospace; chat messages and descriptions in a humanist sans. Never swapped.
