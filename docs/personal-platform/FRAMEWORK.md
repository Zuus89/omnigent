---
type: framework
title: "Personal AI Platform — Canonical Lifecycle & Role Definitions"
status: protected
created: "2026-07-13"
---

# Personal AI Platform — Canonical Definitions

> The authoritative source behind `CLAUDE.md`'s summaries. Adapted from
> `celtonchamberlain/lifecycle-framework`'s own `FRAMEWORK.md` (read in full during this
> project's founding session) — **fixed to this one project**, not a generic scaffolder:
> there is no `/lifecycle-init` here, because there is only ever one project to govern.
> Reflects this project's defaults: models per `CLAUDE.md` §2, tracker = Linear only,
> separation-of-duties collapsed (`da` designs and runs the frozen test).

---

# Part 1 — Governed documents

## A. Persistent governance docs (outlive every task)

### `docs/personal-platform/plan.md` — **PROTECTED**
The goal and vision: the V1 / Phase 2 / Phase 3 design, the decisions already locked (fork
vs. build-from-scratch, Claude-only scope, native-vs-plugin), and the reasoning behind each.
Equivalent of `strategy.md` in the source framework. Written by the human + `pm`
(proposal-mode); edited only on new decisions of record.

### `docs/personal-platform/FRAMEWORK.md` — **PROTECTED**
This file. Re-read at every session start alongside `CLAUDE.md`.

### `docs/personal-platform/project_chronicle.md` — **APPEND-ONLY**
A running record of consequential decisions and findings. One entry per completed
non-trivial task: what was done, key findings, decisions, questions raised/resolved, next
action. Cited by `code-reviewer` and `devils-advocate` as incident history — e.g. the
embedded-token exposure is exactly the kind of thing a future `devils-advocate` pass should
be able to point back to.

## B. Recoverable state files

### `docs/personal-platform/TODO.md` — **PROTECTED**
The dependency-ordered task route, mirrored from the Linear initiative. Status-sync only,
via `/close-task`.

### `docs/personal-platform/context_snapshot.md`
The single "where we are" handoff. Current state only, overwritten at every close — not a
log.

### `docs/personal-platform/activity_log.jsonl` — **APPEND-ONLY**
The machine-readable audit trail. One JSON line per lifecycle step, plus one per commit.
Schema in `.claude/skills/log-activity/SKILL.md`.

## C. Lifecycle artifacts (`docs/personal-platform/claude_tasks/`)

- `<slug>.md` — the spec (Step 3, frozen at Step 6).
- `alpha_tests/` — the frozen acceptance tests (Step 4 design, Step 6 seal). **The `de` never
  touches this directory** — the alpha-test wall.
- `reviews/` — `review_de`, `review_devils-advocate`, `review_code-reviewer`, `review_da`.
- `reports/` — the `de`'s implementation report (Step 7).
- `council/` — one doc per convened `/council`, with explicit reopen criteria.
- `audits/` — `corpus-steward` output.

## D. Configuration

### `docs/personal-platform/CLAUDE.md`
The per-session operating contract. **Not at repo root** — the real root `CLAUDE.md` is a
symlink to upstream's own `AGENTS.md`, left untouched; a one-line pointer was added there
instead of overwriting it. Native, not plugin-resident — see `plan.md` Phase 3 for why that
distinction matters here specifically.

### `.claude/agents/*.md`
Role definitions — mandate, model, can/cannot. Committed, not plugin-installed.

### `.claude/skills/*/SKILL.md`
Native skill implementations: `close-task`, `log-activity`, `log-tracker`, `council`,
`new-doc`.

---

# Part 2 — The lifecycle

**One session runs exactly one task, Brief → Close — never a whole ticket.** A ticket can
span many tasks/sessions; a transitory close persists state so the next session resumes cold
without re-discovery.

| # | Step | Actor | Definition |
|---|------|-------|------------|
| 1 | Brief | Human | Short, intentionally rough: the goal and the motivation. |
| 2 | Data analysis | `da` | Profile the real current state before any spec is written. Read-only, exact evidence. |
| 3 | Spec expanded | `pm` | Brief + analysis → full spec: scope, out-of-scope, approach, acceptance criteria, risks. |
| 4 | Alpha test | `da` | Design the pre-committed acceptance test from the spec alone, before any implementation exists. |
| 5 | Spec reviewed | `de` + `devils-advocate` | `de` checks feasibility with executed probes; `devils-advocate` attacks the spec with ranked objections. **In parallel.** |
| 6 | Resolve | `pm` | Address every objection. Spec **FROZEN**. Alpha test **SEALED**. |
| 7 | Implementation | `de` | Build against the frozen spec; self-review; task report. `code-reviewer` gate runs here. |
| 8 | Review | `pm` + `da` | `pm` checks the report against acceptance criteria; `da` runs the frozen alpha test — binary pass/fail. |
| 9 | Validation | Human | The one human gate. Accept or send back — never skipped for a behavioral change. |
| 10 | Close | `pm` | `/close-task`. |

**Bias control (the spine):** the test is written before the code (Step 4), frozen before
implementation (Step 6), and run against a result it could not influence (Step 8) — the
verdict is binary and bias-free by construction.

**Three review layers:** ① `de` self-review (in session) → ② `pm` review vs. spec (in
session) → ③ `code-reviewer` gate (always-on, before commit).

**Shortcuts:** trivial fix or low-risk ad-hoc change = `1 → 7 → 9`, with a chronicle entry
and log line still required at close. The human decides when this applies; most of this
project's real history (see `project_chronicle.md`) has used exactly this path.

**Traceability (dual-write):** `/log-activity` after every step; `/log-tracker` at
milestones only, cross-referenced by id.

---

# Part 3 — Roles

Full can/cannot definitions live in `.claude/agents/*.md` — this is the index.

| Role | Mandate | Model |
|------|---------|-------|
| `pm` | Lead orchestrator; default session role. | session model |
| `de` | Step-5 feasibility review + Step-7 implementation. | `claude-opus-4-8` |
| `da` | Step-2 profiling, Step-4 design + Step-6 seal, Step-8 execution. | `claude-opus-4-8` |
| `code-reviewer` | The commit gate. Any CRITICAL = NOT SAFE. | `claude-opus-4-8` |
| `devils-advocate` | Adversarial reasoning review. Never approves. | `claude-opus-4-8` |
| `corpus-steward` | Read-only docs-archival proposals (default on). | `sonnet` |

**Hard prerequisite for full multi-agent orchestration:** `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
must be set (in `.claude/settings.json` once one is committed for this repo — not yet wired,
see `TODO.md`). Without it, `pm` cannot spawn teammates and the lifecycle collapses to a
single agent doing everything sequentially — workable for the ad-hoc shortcut, not for the
full 10-step process with genuine separation of duties.
