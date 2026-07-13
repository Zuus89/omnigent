---
name: new-doc
description: Scaffolds a governed markdown document (spec, alpha_test, report, review, council, handoff) with valid frontmatter into the right docs/personal-platform/claude_tasks/ subfolder. Use whenever a lifecycle step needs a new artifact, instead of hand-rolling one.
---

# New Doc

Creates a new governed document from a fixed set of types, in the right place, with
consistent frontmatter — so every artifact in `docs/personal-platform/claude_tasks/` starts
in a valid, predictable shape.

## Types and destinations

| Type | Destination | Written by | When |
|------|-------------|-----------|------|
| `spec` | `claude_tasks/<slug>.md` | `pm` | Step 3 |
| `alpha_test` | `claude_tasks/alpha_tests/<slug>.md` | `da` | Step 4, sealed at Step 6 |
| `report` | `claude_tasks/reports/<slug>.md` | `de` | Step 7 |
| `review` | `claude_tasks/reviews/<slug>_<role>.md` | the reviewing role | Steps 5, 8 |
| `council` | `claude_tasks/council/<slug>.md` | `/council` | any point |
| `handoff` | `claude_tasks/<slug>_handoff.md` | `pm` | a transitory close |

## Frontmatter (every type)

```yaml
---
type: <spec|alpha_test|report|review|council|handoff>
title: "<human title>"
task: "<slug>"
status: <draft|sealed|final>
created: "<YYYY-MM-DD>"
related_decisions: []
---
```

`alpha_test` frontmatter additionally carries `sealed_at` once frozen — set once, never
edited after (a sealed test modified later is a governance violation, flagged by
`corpus-steward` if it sweeps and notices).

## Procedure

1. Confirm the type and the task slug.
2. Create the file at the right destination with the frontmatter above filled in.
3. Leave the body as a clear skeleton matching the type (a spec gets Scope / Out-of-scope /
   Approach / Acceptance criteria / Risks headers; a report gets What-was-built /
   Decisions / Deviations / Self-review-results; etc.) — the author fills it in, this skill
   only scaffolds the shape.
