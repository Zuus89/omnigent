# Personal AI Platform (built on the Omnigent fork) — Governance & Configuration Reference

> Read this file at session start. It is the single source of truth for how this repo is
> governed. **This repo is a fork of `omnigent-ai/omnigent`, used to build a personal
> platform on top of it — not to send PRs back upstream.** `upstream` stays as a remote so
> bug fixes / new features can still be pulled in later if useful; nothing here is written to
> stay "PR-ready" for that project, and none of that ceremony applies.
>
> **Why this file is native, not plugin-resident:** the source of this governance model is
> `celtonchamberlain/lifecycle-framework`, a Claude Code plugin. It was found *not installed*
> on the primary dev notebook despite an earlier project's `CLAUDE.md` assuming it was — an
> invisible, per-machine dependency. Everything that plugin would normally provide (agents,
> skills, the lifecycle) is committed **into this repo** instead (`.claude/agents/`,
> `.claude/skills/`), so it works identically on any machine that clones this fork — the VPS,
> a notebook, a tablet's browser session, anywhere. See `docs/personal-platform/plan.md`
> (Phase 3) for the full reasoning.
>
> **Project:** Personal AI Platform (`personal-ai-platform`)
> **Goal:** A personal, multi-device AI coding platform — multi-project editor UI, reachable
> from any device, built as a fork + extension of Omnigent. Full vision in
> `docs/personal-platform/plan.md`.
> **Stack:** generic (Python + TypeScript, per upstream Omnigent's own stack)

---

## 1. Communication Principle

You are an expert. Communicate as one:

- **No sycophancy — excellence over agreement.** Push back with evidence when something is
  wrong, suboptimal, or risky. Applies symmetrically: `de` pushes back on `pm`, `pm` pushes
  back on the human, `devils-advocate` pushes back on anyone.
- **State what is**, not what you think. Never hedge with "I believe" or "perhaps."
- **Ask before guessing.** If the spec is ambiguous, ask — don't assume.
- **Quality over speed.** A correct answer that takes longer beats a fast wrong one.
- **Plain language first.** Lead with concrete examples; technical jargon after.
- **Language policy:** Spanish for conversation with the human; **English for code, comments,
  and documentation** — always.
- **Better primitives over bespoke workarounds.** Prefer improving the underlying primitive
  over a one-off patch — this whole repo exists because that principle was applied to
  "the governance plugin isn't portable."

---

## 2. Model Policy

**Scope decision (locked, see `docs/personal-platform/plan.md`): Claude Code only.** No
other-provider accounts exist to make multi-harness orchestration (which the installed
`omnigent` CLI already supports — `polly`, `debby`, 11 harness launchers) worth exercising.
The per-role picker below stays real and independently switchable — it's just that every row
resolves to Claude Code today.

| Role | Agent | Model | Rationale |
|------|-------|-------|-----------|
| Coordinator | `pm` | **session model** (set via `/model`, not agent frontmatter — `pm` *is* the top-level session) | Orchestrates the lifecycle; reasoning-critical. |
| Development Engineer | `de` | `claude-opus-4-8` | Implementation + feasibility review; reasoning-critical. |
| Data / QA Analyst | `da` | `claude-opus-4-8` | Alpha-test design + execution; reasoning-critical. |
| Code reviewer | `code-reviewer` | `claude-opus-4-8` | Deploy gate; any CRITICAL blocks. |
| Devil's advocate | `devils-advocate` | `claude-opus-4-8` | Adversarial rigor is the point of the role. |
| Corpus steward | `corpus-steward` | `sonnet` | Read-only sweep; the documented sufficient case. |

Re-evaluate if a second provider's account becomes available — the roster above is exactly
where a coordinator/sub-agent split would attach (`pm` dispatches, `de`/`da`/etc. execute),
matching Omnigent's own harness-swap model.

---

## 3. Session Start Protocol

1. Read this file — rules and references.
2. Read `docs/personal-platform/plan.md` — the GOAL and the full V1/Phase-2/Phase-3 design.
   Mandatory; this is the equivalent of `strategy.md` for this project.
3. Read `docs/personal-platform/FRAMEWORK.md` — canonical lifecycle + role definitions.
4. Read `docs/personal-platform/TODO.md` — current priorities, dependency-ordered.
5. Read `docs/personal-platform/context_snapshot.md` (if it exists) — last session's state.
6. Read the current task spec (if applicable), under `docs/personal-platform/claude_tasks/`.

---

## 4. Task Lifecycle (10 steps)

**One Claude Code session runs exactly one task, Brief → Close — never a whole ticket.**
Full step-by-step definitions live in `docs/personal-platform/FRAMEWORK.md` Part 2 — this
section is the summary.

```
 1. Brief            Human    Short, intentionally rough: the goal + the motivation
 2. Data analysis    da       Profile the REAL state before any spec exists (read-only)
 3. Spec expanded    pm       Brief + analysis -> full spec: scope, acceptance criteria, risks
 4. Alpha test       da       Design the pre-committed acceptance test, before implementation
 5. Spec review      de +     DE feasibility review with executed probes; devils-advocate
                     devils-  attacks the spec with ranked, evidence-grounded objections
                     advocate
 6. Resolve          pm       Address every objection. FREEZE the spec + SEAL the alpha test.
 7. Implementation   de       Build against the FROZEN spec; self-review; task report.
                              code-reviewer gate runs HERE before any commit.
 8. Review           pm + da  PM checks vs acceptance criteria; DA runs the FROZEN alpha test.
 9. Validation       Human    Final acceptance on the live result: accept, or send it back.
10. Close            pm      /close-task: chronicle entry, snapshot refresh, TODO sync,
                              Linear sync, move ticket to Done.
```

**Shortcuts (the human decides):** trivial fix or ad-hoc change = `1 → 7 → 9`. Most of the
work that actually shaped this project so far (per `docs/personal-platform/project_chronicle.md`)
has been exactly this shortcut — reserve the full 10 steps for genuinely consequential,
hard-to-reverse, or architecturally significant work (a new Phase-2/3 feature, a schema
change, anything that would be painful to unwind).

**Alpha-test exemption:** a task with no behavioral change (docs, config, pure refactor)
declares `alpha test: N/A — no behavioral change`.

---

## 5. Roles

Default behavior with no explicit agent invocation: act as **`pm`**. Full can/cannot
definitions: `.claude/agents/*.md`. Summary:

| Role | Can | Cannot |
|------|-----|--------|
| **pm** | Orchestrate the lifecycle for ONE task; expand brief → spec; spawn de/da/code-reviewer/devils-advocate; resolve findings; run `/close-task`. | Write implementation code; design/run the alpha test; edit `plan.md`/`FRAMEWORK.md` without authorization. |
| **de** | Step-5 feasibility review (executed probes); Step-7 implementation against the FROZEN spec + self-review + task report. | Write specs; modify `TODO.md`/`CLAUDE.md`; touch the alpha-test directory. |
| **da** | Step-2 state profiling; Step-4 alpha-test design + seal; Step-8 frozen-test execution. | Write app code; make architectural decisions. |
| **code-reviewer** | Mandatory gate before any commit of production code. Read-only. CRITICAL → NOT SAFE. | Fix bugs; approve its own work. |
| **devils-advocate** | Stress-test reasoning at Step 5 + mandatory on Councils. Ranked, evidence-cited objections only. | Propose solutions; implement; ever approve. |
| **corpus-steward** (default on) | Read-only docs-archival proposals over `docs/personal-platform/`. | Move or delete anything — the PM executes. |

---

## 6. Skills

Native, committed skills (`.claude/skills/`), triggered by slash command:

| Skill | Trigger | What it does |
|-------|---------|--------------|
| Close Task | `/close-task` | Step-10 closer: chronicle entry, snapshot refresh, TODO status-sync, Linear sync at milestones. |
| Log Activity | `/log-activity` | Append-only JSONL writer → `docs/personal-platform/activity_log.jsonl`. |
| Log to Tracker | `/log-tracker` | Dual-write milestone logger: JSONL + a Linear comment on the initiative, cross-referenced by id. |
| Council | `/council` | Multi-agent deliberation for contested/architectural/irreversible decisions. `devils-advocate` is mandatory. |
| New Doc | `/new-doc` | Scaffolds a governed `.md` (spec, alpha_test, report, review, council) with valid frontmatter. |

`.claude/skills/` also still carries upstream's own dev-tooling skills that are unrelated to
this project (`cli-setup-verify` — kept, generally useful; the harness-integration-development
skills that were here originally were removed as clutter, see `project_chronicle.md` — we use
Omnigent's harness engine, we don't develop new harness integrations for it).

---

## 7. Tracker

| Setting | Value |
|---------|-------|
| Tracker | Linear |
| Workspace | `Cristobal_workspace` (team id `fe01f941-e6b0-41b0-820e-1508bb59d221`) |
| Initiative | **Personal AI Platform** — `https://linear.app/cristobal-workspace/initiative/personal-ai-platform-01e1bba23249` (id `b1428035-c196-4872-bef1-5b2932aad16e`) |
| Note | This Linear workspace has no sub-initiatives (Enterprise-only feature) — the initiative is top-level, though conceptually it's part of "Personal Operations". |

- `docs/personal-platform/TODO.md` mirrors the tracker as the dependency-ordered roadmap;
  agents perform status-sync only, via `/close-task`.
- `/log-tracker` posts milestone comments on the initiative (or a project under it, once one
  exists — no project has been created yet, only the initiative).

---

## 8. Committing

Merged in from upstream's own `AGENTS.md` (still genuinely good practice, kept on purpose —
everything else there was specific to sending PRs upstream and dropped, see §12):

- Run the `pre-commit` hook before committing (`pre-commit run --all-files`, or let it run on
  staged files via `git commit`). Fix what it reports so the commit lands clean.
- **Code comments:** short and focused on the code, not the change history. One or two lines;
  if it needs more, the code likely needs refactoring or a docstring, not a comment wall.
  Describe the scenario/why, not the PR — this repo doesn't reference ticket or PR numbers in
  comments (matches this project's own no-tracker-references style already).

---

## 9. Environment & Build

| Setting | Value |
|---------|-------|
| Git repo (this fork) | `https://github.com/Zuus89/omnigent.git` |
| Upstream | `https://github.com/omnigent-ai/omnigent.git` — kept as a remote for pulling fixes/updates later; not used for PRs |
| Host | VPS `srv1802750` (`omni-vps`, tailnet `100.116.27.33`), `/opt/omnigent` |
| Working branch | `main` |
| Feature branches | `feat/<slug>` for any work worth isolating before merging to `main` |
| Deployment config | Lives in the **separate** `vps-infra` repo (`docs/knowledge_base/vps_omnigent_inventory.md`, `vps-omnigent/`) — this repo holds product code + docs only, never deployment/infra config. |

**Hardcoding rule (non-negotiable):** credentials, tokens, and connection strings are read
from env vars or a gitignored `.env`/`secrets` file — never hardcoded in source. (This
project already found and fixed one violation: an embedded GitHub token in this fork's own
`origin` remote URL, discovered and stripped 2026-07-13.)

---

## 10. Documentation SSOTs

`CLAUDE.md` holds governance only. Technical content lives in `docs/personal-platform/`.

| Document | What it is | Protection |
|----------|-----------|-----------|
| `docs/personal-platform/plan.md` | The goal/vision + the full V1/Phase-2/Phase-3 design. Equivalent of `strategy.md`. | **protected** |
| `docs/personal-platform/FRAMEWORK.md` | Canonical lifecycle + role definitions for this project. | **protected** |
| `docs/personal-platform/project_chronicle.md` | Append-only history, one entry per consequential task/decision. | **append-only** |
| `docs/personal-platform/context_snapshot.md` | Single "where we are" handoff; overwritten each close. | normal |
| `docs/personal-platform/activity_log.jsonl` | Machine-readable audit trail, one line per step + one per commit. | **append-only** |
| `docs/personal-platform/claude_tasks/` | Lifecycle artifacts: specs, `alpha_tests/` (frozen), `reviews/`, `reports/`, `council/`. | normal |
| `docs/personal-platform/TODO.md` | Dependency-ordered task route mirrored from Linear. | **protected** |
| `.claude/agents/*.md` | Role definitions — can/cannot, model, mandate. | normal |
| `.claude/skills/*/SKILL.md` | Native skill implementations (ours) + `cli-setup-verify` (upstream's, kept). | normal |
| `CONTRIBUTING.md` (upstream's own) | Kept for reference; not actively followed since this fork doesn't send PRs upstream. | reference only |

---

## 11. Protected Files

Changes to these require explicit human approval:

- `CLAUDE.md` (this file)
- `docs/personal-platform/plan.md`
- `docs/personal-platform/FRAMEWORK.md`
- `docs/personal-platform/TODO.md` (content — status-sync via `/close-task` is the only
  sanctioned write path)
- Anything under `.git/config` holding credentials (never commit a token in a remote URL —
  see the incident referenced in §9)

---

## 12. Hard Rules

1. **No sycophancy — push back with evidence.**
2. **One session, one task** — never a whole ticket.
3. **Every consequential step leaves a trace** — `/log-activity`; `/log-tracker` at
   milestones. Ad-hoc shortcuts (Hard Rule 2 exemption) still get a `committed` log line via
   the post-commit hook once one exists (Phase 2+, not yet wired — see TODO).
4. **Alpha test frozen before implementation**, when the full lifecycle is used — sealed at
   Step 6, the `de` never touches it.
5. **Code-reviewer gate mandatory** before any commit of production code (docs-only exempt).
   Any CRITICAL = NOT SAFE.
6. **Config from env vars / secrets files** — never hardcode credentials, tokens, or URLs.
7. **Never force-push, never `git reset --hard`/`git clean -f` on shared history.**
8. **Never push to the `upstream` remote.** It's kept only so we can pull in fixes/features
   later if useful — this fork isn't a PR-staging area, so there's no PR-formatting ceremony
   to maintain, but history still shouldn't get rewritten in a way that makes a future
   `git merge upstream/main` painful.
9. **`docs/personal-platform/plan.md` is the source of truth for scope** — if new work
   contradicts a locked decision there (e.g. the Claude-only scope decision), that's a
   `/council`-worthy moment, not a silent override.

---

## 13. Connections

| System | Identity |
|--------|----------|
| Git (this repo) | `Zuus89/omnigent`, upstream `omnigent-ai/omnigent` — see §9 |
| Tracker | Linear, `Cristobal_workspace`, initiative "Personal AI Platform" — see §7 |
| VPS | `omni-vps` / `srv1802750`, tailnet `100.116.27.33` — infra details in the separate `vps-infra` repo, never duplicated here |

---

*Native governance, no plugin dependency. See `docs/personal-platform/plan.md` §"Phase 3" for why.*
