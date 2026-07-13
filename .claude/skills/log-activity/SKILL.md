---
name: log-activity
description: Append-only JSONL writer — one record per lifecycle step and one per commit, to docs/personal-platform/activity_log.jsonl. The cheap, tracker-free half of the dual-write (log-tracker is the other half). Use after every consequential lifecycle step, or let the post-commit hook fire it automatically for commits.
---

# Log Activity

Appends exactly one JSON line to `docs/personal-platform/activity_log.jsonl`. Never edits or
removes an existing line — this file is append-only, full stop.

## Line schema

```json
{"ts":"<ISO-8601 UTC>","session":"<8-char session id>","event":"<event-name>","step":<1-10 or null>,"agent":"<role or null>","model":"<model id or null>","summary":"<one sentence, what happened and why it matters>","artifacts":["<files touched>"]}
```

- `event` — `brief` / `spec-drafted` / `alpha-test-sealed` / `spec-frozen` /
  `implementation-complete` / `review-verdict` / `validated` / `closed` / `committed` /
  `council-convened` for the 10-step lifecycle; `committed` also covers ad-hoc-shortcut work.
- `step` — the lifecycle step number (1–10), or `null` for ad-hoc/shortcut work.
- Get the current UTC timestamp from the actual system clock at write time, never guessed or
  reused from an earlier step.

## When to run

- After every step in the full 10-step lifecycle.
- After every commit (ideally automated via a post-commit git hook once one is wired for
  this repo — not yet set up; until then, run this skill manually right after committing).
- After an ad-hoc shortcut task completes (`event: "committed"`, `step: null`).

## Non-negotiable

A step or a commit without its log line is not done. This is the granular, queryable half of
the dual-write — `/log-tracker` is the other half, reserved for milestones worth surfacing on
the Linear initiative.
