---
type: doc
title: "Personal AI Platform — Project Chronicle"
status: living
protection: append-only
owner: human
created: "2026-07-13"
---

# Personal AI Platform — Project Chronicle

> The book of strategic decisions and findings — APPEND-ONLY. One entry per completed
> consequential task or decision. Cited as incident history by `code-reviewer` and
> `devils-advocate`. Newest entries at the bottom.

---

## 2026-07-13 — Project founded: fork Omnigent, don't build from scratch

**Context:** wanted a personal, multi-device AI coding platform — a comfortable
multi-project editor UI reachable from any device, ideally with the ability to choose a
coordinator and per-agent models. Compared the 2026 landscape (Cursor, Windsurf, Zed, Google
Antigravity, Cline, OpenCode, Claude Code Remote Control, code-server) before deciding how to
build it.

**Decisions:**

1. **Fork + extend Omnigent** (open source, Apache 2.0), not build from scratch. It already
   solves the hardest parts: multi-harness orchestration, multi-device continuity,
   project-grouped sessions.
2. **A live VPS audit found the fork already existed** — `/opt/omnigent`, cloned as
   `Zuus89/omnigent`, synced with `upstream/main` — done in an earlier, undocumented session.
   V1 closed that documentation gap instead of redoing the work.
3. **Scope narrowed to Claude Code only.** Multi-provider orchestration (a coordinator
   dispatching to Gemini/Codex sub-agents) is real and already in the installed `omnigent`
   CLI (`polly`, `debby`, 11 harness launchers) — but there aren't enough other-provider
   accounts to make it worth exercising. The coordinator/per-agent model picker stays a real,
   designed capability; every role just resolves to Claude Code today.
4. **Governance is native, not plugin-resident.** The source pattern
   (`celtonchamberlain/lifecycle-framework`) is a Claude Code plugin — found *not installed*
   on the primary dev notebook despite an earlier project's `CLAUDE.md` assuming it was. This
   project commits its own `CLAUDE.md` / `.claude/agents/` / `.claude/skills/` directly into
   the repo instead, so governance works identically on any machine that clones the fork.
5. **Repo split:** this fork holds product code + docs (`docs/personal-platform/`);
   deployment/infra config lives in the separate `vps-infra` repo, exactly as it already does
   for the running Omnigent server.
6. **Security incident, found and fixed same day:** this fork's `origin` remote had a
   GitHub OAuth token (`gho_...`) embedded in plaintext in the URL. Stripped, `gh` set up as
   credential helper instead. The token should still be revoked on GitHub's side (human
   action, not something an agent can safely automate) — flag this in any future security
   review of this repo until confirmed done.
7. **Tracker: Linear**, initiative "Personal AI Platform" under the `Cristobal_workspace`
   team — conceptually a child of the existing "Personal Operations" initiative, though this
   Linear workspace's plan doesn't support sub-initiatives, so it's top-level.

**Key findings:** the interactive mockup built during planning
(`https://claude.ai/code/artifact/e0c98989-9fc7-4f2a-ad85-8f3de5f15232`) is the locked-in
visual/IA reference for Phase 2/3 — a VS-Code-style activity bar (Sessions / Filesystem /
Background / Knowledge base / Agentes & config), not floating panels; a persistent
right-rail progress panel; a flat, rationed-accent design system (see `plan.md`'s "Design
reference" section for the full rationale).

**Questions raised / resolved:** resolved — where does product vs. infra documentation live
(this fork vs. `vps-infra`); how does the workspace/project credential model work for
external connectors (see `plan.md`'s "Credential vs. resource" rule).
Open — whether Omnigent's existing UI already provides project-grouped sessions and
background-agent visibility (V1 step 3, not yet run).

**Alpha test:** N/A — founding/infrastructure work, no behavioral change to test yet.

**Next action:** V1 step 3 — confirm the coordinator/agent picker in `omnigent config`, and
check session grouping + background visibility before deciding what Phase 2 actually needs
to build.

## 2026-07-13 — V1 step 3: live UI testing corrects the source-reading over-read

**Context:** V1 step 3 asked to confirm the coordinator/agent picker and check whether
Omnigent already provides project-grouped sessions and background-agent visibility, before
deciding what Phase 2 actually needs to build. A source-code read (web/src/shell/, the
server API docs) found WorkspacePicker.tsx, WorkspacePanel.tsx, SubagentsPanel.tsx with a
RunningDot, and a workspace field on the session object — read as strong evidence that most
of Phase 2 might already exist. The human then opened the live UI and corrected this.

**Findings (live UI, ground truth over source-reading):**

1. **Omnigent's workspace is our Project, not our Workspace.** It's a filesystem path
   on a session, not an identity/credential boundary spanning multiple projects. Project →
   Session grouping does exist in the live UI. Our Workspace layer (multiple projects under
   one identity — git/model/MCP credentials) does not exist anywhere in Omnigent — **Phase 2
   is still fully needed**, not redundant as the source read suggested.
2. **Creating a new project from a tablet or phone is effectively not possible today** in
   the live UI. Directly validates the Phase 3 native-project wizard's mobile-friendliness
   requirement.
3. **Git/repo binding lives on the chat/session, not on a persistent project entity.**
   Today two sessions under the same Omnigent workspace (= our project) can point at
   different repos. This contradicts Phase 3's core rule (every project always has a git

## 2026-07-13 — V1 step 3: live UI testing corrects the source-reading over-read

**Context:** V1 step 3 asked to confirm the coordinator/agent picker and check whether
Omnigent already provides project-grouped sessions and background-agent visibility, before
deciding what Phase 2 actually needs to build. A source-code read (web/src/shell/, the
server API docs) found WorkspacePicker.tsx, WorkspacePanel.tsx, SubagentsPanel.tsx with a
RunningDot, and a workspace field on the session object — read as strong evidence that most
of Phase 2 might already exist. The human then opened the live UI and corrected this.

**Findings (live UI, ground truth over source-reading):**

1. **Omnigent's "workspace" is our "Project", not our "Workspace".** It's a filesystem path
   on a session, not an identity/credential boundary spanning multiple projects. Project →
   Session grouping does exist in the live UI. Our Workspace layer (multiple projects under
   one identity — git/model/MCP credentials) does not exist anywhere in Omnigent — **Phase 2
   is still fully needed**, not redundant as the source read suggested.
2. **Creating a new project from a tablet or phone is effectively not possible today** in
   the live UI. Directly validates the Phase 3 native-project wizard's mobile-friendliness
   requirement.
3. **Git/repo binding lives on the chat/session, not on a persistent project entity.**
   Today two sessions under the "same" Omnigent workspace (= our project) can point at
   different repos. This contradicts Phase 3's core rule ("every project always has a git
   connection, no exceptions") — Omnigent does not enforce project-repo as a stable 1:1
   binding. This is now the sharpest concrete requirement for Phase 3's project entity: a
   Project must own its git binding, and every Session under it inherits that binding rather
   than choosing its own.

**Decision:** proceed with V1 (code-server) as planned — it solves a different need (a real
multi-project code editor) than what Omnigent's own session UI provides. Phase 2/3 scope is
confirmed, not shrunk; finding 3 sharpens Phase 3's project-entity design specifically.

**Lesson for future sessions:** reading source code is evidence of capability, not of actual
UX — the two diverged here. Verify live before treating a source-code find as settled,
especially for anything UI/UX-shaped.

**Alpha test:** N/A — investigation, no behavioral change.

**Next action:** continue V1 — stand up code-server.

## 2026-07-13 — V1 closed: code-server deployed, verified from two devices

**Context:** V1's remaining steps (4-7) — stand up `code-server`, install both VS Code
extensions, verify from a second device, document + commit — executed end to end this
session.

**Summary:**

- `code-server` deployed at `/opt/code-server` (VPS), tailnet-only, password-protected,
  serving all 5 repos (the 4 personal clones + this fork) as one multi-project workspace.
- Node.js 22 installed (was missing); the Omnigent VS Code extension built from this fork's
  own source and installed alongside the Claude Code extension.
- Three real infra bugs found and fixed, each general enough to be written to `vps-infra`'s
  `vps_ops_gotchas.md` rather than just here:
  1. Container network namespace isolation blocked the Omnigent extension's localhost
     server discovery — fixed with `network_mode: host`.
  2. `/root` isn't traversable by the container's non-root user, so mounting the `claude`
     CLI under `/root/.local/bin` silently failed — fixed by mounting the binary directly
     onto a normal PATH location.
  3. The big one: VS Code webviews (any extension's visual panel) render silently blank
     without a real secure context (HTTPS or literal `localhost`) — browsers withhold
     `crypto.subtle`, which webview rendering depends on, over plain HTTP on a tailnet
     IP/hostname. Fixed by enabling Tailscale HTTPS certs and serving `code-server` with a
     real `tailscale cert`-issued certificate. Learned the cert only covers the full
     MagicDNS FQDN, not the short alias — the short alias fails hostname verification.
- **Decision:** did not patch the Omnigent extension's own "localhost-only" iframe
  restriction (a real, separate limitation, understood and documented) — not worth it, this
  project doesn't plan to use Omnigent's own UI day to day, only its code as a base.
- Verified from two devices: the notebook (full pass) and an Android tablet with a physical
  keyboard/trackpad (Claude Code session opens correctly via the activity-bar icon; the
  Command Palette search doesn't respond to that device's input for unclear reasons — a
  known, non-blocking quirk, not investigated further since the direct-icon path works).

**Key findings:** captured above; the ops-level ones live in `vps-infra`'s
`vps_ops_gotchas.md` for reuse beyond this project.

**Questions raised / resolved:** resolved — code-server's viability as the multi-project
editor engine, now proven end to end on two devices.
Open — the Command Palette input quirk on the tablet; not blocking, parked.

**Alpha test:** N/A — infra deployment, no user-facing app behavior yet to test against a
frozen spec.

**Next action:** V1 is closed. Next up is Phase 2 (the workspace hierarchy + KB curator) or
Phase 3 (native project lifecycle) — the custom VS Code extension work, per `plan.md`'s
"Delivery vehicle" section. Not started.

## 2026-07-13 — Git push to origin was silently broken; fixed via OAuth re-auth

**Context:** Confirming this fork's remote setup (`origin` = the user's own
`Zuus89/omnigent`, `upstream` = the read-only `omnigent-ai/omnigent`) surfaced 6
same-day commits that had never actually been pushed. `git push origin main` failed with:

```
remote: Permission to Zuus89/omnigent.git denied to Zuus89.
fatal: unable to access 'https://github.com/Zuus89/omnigent.git/': The requested URL returned error: 403
```

**Root cause:** the `gh` credential helper was correctly wired
(`credential.https://github.com.helper=!/usr/bin/gh auth git-credential`) and using a
fine-grained PAT (`github_pat_...`) that could read the repo fine — `gh api
repos/Zuus89/omnigent` returned `permissions.push: true`. But that field reflects the
**user's** role on the repo, not the **token's** granted scope. Direct curl testing against
the actual push endpoint (`.../info/refs?service=git-receive-pack`) confirmed: read (`GET`
the repo) → 200, push endpoint → 403, same token. The fine-grained PAT's `Contents`
repository-permission was not set to read-write for this repo (it predates this fork;
originally scoped only to `saga-voice`/`vps-infra`/`zuus89.github.io`). An in-place edit
to the token's permissions did not resolve it on the first attempt (identical 403 after the
user reported updating it) — the reliable fix was deleting the PAT entirely and
re-authenticating `gh` via OAuth device flow, which carries a durable `repo`-scope grant
not tied to a per-repo allowlist.

**Secondary finding while diagnosing:** `branch.main.remote` was `upstream`, not `origin`
— a bare `git push`/`git pull` on `main` would have targeted the read-only upstream repo
by default, which this repo's own `CLAUDE.md` (Hard Rule 8) explicitly forbids pushing to.
Fixed with `git branch --set-upstream-to=origin/main main`.

**Outcome:** the 6 pending commits pushed cleanly; git operations on this fork now use OAuth
end to end (no PAT); the original embedded-token loose end from V1 (flagged in
`context_snapshot.md` since V1's close) is now confirmed revoked by the user — closing that
flag.

**Key findings:** the GitHub REST API's `permissions` field on a repo describes the
*authenticated user's* access, not the *token's* granted scope — a fine-grained PAT can read
a repo it can't push to, with no error until the actual write-capable endpoint is hit. Worth
remembering for any future fine-grained-PAT setup on this project.

**Alpha test:** N/A — credential/config troubleshooting, no behavioral change to the product.

**Next action:** unchanged — Phase 2 or Phase 3, per `plan.md`'s "Delivery vehicle" section.
