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
