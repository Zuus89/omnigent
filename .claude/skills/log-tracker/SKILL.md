---
name: log-tracker
description: Dual-write milestone logger for the Personal AI Platform project — a log-activity JSONL append plus a mirrored comment on the Linear initiative, cross-referenced by id. Reserve for milestones worth surfacing (task start, blockers, decisions, Step-10 close) rather than every step. Uses the Linear MCP tools.
---

# Log to Tracker

Posts a milestone update to Linear **and** appends the matching JSONL line via
`/log-activity` in the same action — the two must always agree, cross-referenced by a shared
id.

## Where it posts

This project's tracker connection (`CLAUDE.md` §7):

- Workspace: `Cristobal_workspace`
- Initiative: **Personal AI Platform** —
  `https://linear.app/cristobal-workspace/initiative/personal-ai-platform-01e1bba23249`

No Linear *project* exists under this initiative yet — post as a comment/update on the
initiative itself (via the Linear MCP's initiative tools) until a project is created for
issue-level tracking. If a project gets created later, prefer posting there instead and
update this skill's target.

## When to run (milestones only, not every step)

- Step 1 — a new task/ticket starting.
- A blocker that changes the plan.
- A locked decision (the kind that would otherwise only live in `project_chronicle.md`).
- Step 10 — close.

Do **not** run this for every lifecycle step — that's `/log-activity`'s job, cheaply and
without touching Linear. This skill is for the human-readable trail on the tracker side.

## Procedure

1. Compose a short, human-readable update: what happened, why it matters, link to the
   relevant `docs/personal-platform/claude_tasks/` artifact if one exists.
2. Post it via the Linear MCP (comment on the initiative, or on its project once one exists).
3. Immediately run `/log-activity` with the same summary and the Linear comment/update id in
   a `tracker_comment_id` field, so the two records are cross-referenced.
