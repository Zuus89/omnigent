---
name: close-task
description: Step-10 closer for the Personal AI Platform lifecycle — append a project_chronicle.md entry, overwrite context_snapshot.md, status-sync TODO.md, and log-tracker sync at the milestone. Variants for full/ad-hoc/transitory-multi-session closes. Use at the end of any task, whether it ran the full 10-step lifecycle or the ad-hoc shortcut.
---

# Close Task

The mandatory closing step — nothing closes without this, whether the task ran the full
10-step lifecycle or the `1 → 7 → 9` ad-hoc shortcut.

## Variants

- **Full close** — a task that ran the complete lifecycle. Every sub-step below applies.
- **Ad-hoc close** — a shortcut task (`1 → 7 → 9`). Still writes a chronicle entry and
  refreshes the snapshot; skips anything that assumes a frozen spec / sealed alpha test
  (since none exists for this path).
- **Transitory close** — a task too big for one session. Persists the snapshot + a clear
  "resume exactly here" note so the next session picks up cold, without re-discovery. Does
  **not** write a chronicle entry yet (the task isn't actually done) — only the final close
  of the whole task does that.

## Steps

1. **Append to `docs/personal-platform/project_chronicle.md`** (skip only for a transitory
   close): one entry — context, summary, key findings/decisions, questions
   raised/resolved, next action. Append only, never edit a prior entry.
2. **Overwrite `docs/personal-platform/context_snapshot.md`**: current state only, not
   history — deliberately overwritten, not appended, so it stays a snapshot.
3. **Status-sync `docs/personal-platform/TODO.md`**: mark the completed item done; this is
   the *only* sanctioned write path to that file's content (it's otherwise protected).
4. **`/log-tracker`** if this close is a milestone (it almost always is, for a full or
   ad-hoc close; skip for a transitory close since the task isn't done).
5. **`/log-activity`** with `event: "closed"` (full/ad-hoc) or the appropriate transitory
   marker.

## Non-negotiable

Every task closes through this skill — no shortcuts around Step 10 itself, even when Steps
1–9 took the ad-hoc path.
