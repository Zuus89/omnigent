---
type: doc
title: "Context Snapshot — Personal AI Platform"
status: snapshot
created: "2026-07-13"
updated: "2026-07-13"
---

# Context Snapshot — Personal AI Platform

> Cold-resume handoff. Current state only — overwritten at every close, not a log.

## Where we are

**V1 is closed.** `code-server` is live on the Omnigent VPS, tailnet-only, real TLS,
serving all 5 repos as one multi-project workspace, with the Claude Code + Omnigent VS Code
extensions installed and working — verified from the notebook and from an Android tablet.

## Access

- `code-server`: **`https://omnigent-vps.tail05ae76.ts.net:8443`** (full MagicDNS FQDN —
  the short alias `omnigent-vps` fails certificate hostname verification, always use the
  full name). Password in `/opt/code-server/.env` on the VPS (gitignored).
- This fork: `/opt/omnigent` on `omni-vps` (tailnet `100.116.27.33`), `ssh omni-vps`.
- Full plan: `docs/personal-platform/plan.md`. Full debugging narrative for V1's close:
  `project_chronicle.md`, entry "2026-07-13 — V1 closed".
- Design reference (mockup): `https://claude.ai/code/artifact/e0c98989-9fc7-4f2a-ad85-8f3de5f15232`.
- Linear: `https://linear.app/cristobal-workspace/initiative/personal-ai-platform-01e1bba23249`.

## Next action

Pick Phase 2 (workspace hierarchy + KB curator) or Phase 3 (native project lifecycle,
sharpened by V1's live-UI findings — a Project must own a stable git binding) as the next
task. Both are custom development against `code-server`'s extension host — see `plan.md`'s
"Delivery vehicle" section: the product layer is a custom VS Code extension, not a
from-scratch app. Needs a fresh Brief to scope which one first.

## Flags / gotchas

- The embedded token that was in `origin`'s URL (fixed 2026-07-13) should still be
  **revoked on GitHub's side** — stripping the URL doesn't invalidate the token itself.
  Human action, not yet confirmed done.
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is **not yet set** for this repo (no
  `.claude/settings.json` committed yet) — full multi-agent orchestration (`pm` spawning
  teammates) won't actually work until that's wired.
- The Omnigent VS Code extension's own panel is left non-functional by decision — its
  "localhost-only" iframe restriction isn't compatible with remote `code-server` access, and
  patching it wasn't worth it since this project doesn't use Omnigent's UI day to day.
- The Command Palette doesn't respond to input on at least one tested tablet (Android, with
  keyboard/trackpad) — non-blocking (the activity-bar icon works fine as the direct path),
  not investigated further.
- Tailscale-issued TLS cert (`/opt/code-server/tls/`) is Let's Encrypt-backed, ~90-day
  lifetime — needs periodic renewal (`tailscale cert` again + `chmod 644` the new key file,
  same permission gotcha as the first time — see `vps-infra`'s `vps_ops_gotchas.md`).
