---
name: council
description: Multi-agent deliberation for contested, architectural, or irreversible decisions in the Personal AI Platform project. devils-advocate is a mandatory participant. Writes a council doc with explicit reopen criteria to docs/personal-platform/claude_tasks/council/. May be convened at any point in the lifecycle by anyone.
---

# Council

For decisions where a single role's judgment isn't enough: contested calls, architectural
choices, anything hard to reverse (touching the `upstream` sync boundary, a schema change, a
decision that contradicts something already locked in `plan.md`).

## Participants

- `pm` — frames the question, synthesizes the decision.
- `de` — technical feasibility perspective.
- `da` — data/state-grounding perspective.
- `devils-advocate` — **mandatory**. Attacks every position raised, evidence-cited.

## Procedure

1. Frame the question precisely — what's actually being decided, and why now.
2. Each participant states a position with reasoning.
3. `devils-advocate` attacks every position with ranked, evidence-grounded objections.
4. Resolve to a decision — or explicitly to "not yet, here's what's missing."
5. Write the council doc to `docs/personal-platform/claude_tasks/council/`: the question,
   the positions, the devils-advocate objections, the decision, and **explicit reopen
   criteria** (what would have to change for this decision to be revisited).

## Non-negotiable

`devils-advocate` is never optional on a council, and the reopen criteria are never skipped
— a decision with no stated reopen condition looks final in a way it usually isn't.
