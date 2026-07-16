---
type: doc
title: "Context Snapshot — Personal AI Platform"
status: snapshot
created: "2026-07-13"
updated: "2026-07-15"
---

# Context Snapshot — Personal AI Platform

> Cold-resume handoff. Current state only — overwritten at every close, not a log.

## Where we are

**Phase 2 is underway.** Task `workspace-layer` is mid-lifecycle (transitory close
2026-07-15): Steps 1–4 done, Step 5 half done, Step 6 pending. All artifacts committed
and pushed through `ceeb8e10`.

- **Done:** brief approved → da state profile (`workspace-layer_step2-profile.md`; star
  finding: dormant `workspace_id` partition key on all 12 tables, never activated) →
  spec from a 3-candidate × 3-judge panel, winner **platform-registry-hybrid**
  (workspace = one `omnigent host` container holding all identity; server stripped of
  creds; `workspaces.yaml` registry; staged escalation 2a/2b/3) → 7 human rulings in the
  spec → da alpha test designed (17 binary checks, draft, seals at Step 6) →
  devils-advocate review: **2 BLOCKERs + 5 MAJORs** (headline: the architecture isolates
  the omnigent-host plane while the user's real workflow — code-server + Claude Code
  extension — spans all workspaces as one user; ruling 1 arguably narrowed locked plan
  text past Hard Rule 9's `/council` gate; ruling 6 contradicts the Stage-3 precondition).
- **Two sibling briefs captured** (own sessions later, blocked by this task):
  `kb-three-tier` (3 tiers as git repos, curator promotion, SilverBullet access layer —
  human-approved design direction) and `secrets-manager` (workspace-scoped, managed from
  the platform UI, engine-not-product).

## Resume exactly here

1. **Re-run the de Step-5 feasibility review** — two attempts died (one silent stall,
   one killed by a client disconnect). Fresh spawn, READ-ONLY mode: no server/host/runner
   processes (human consent for ephemeral probes is **still pending**); the spec's 3
   probes become code-analysis verdicts with file:line evidence. Full prompt pattern in
   this session's transcript; essentials: read CLAUDE.md → `.claude/agents/de.md` → spec
   → profile; write `claude_tasks/reviews/workspace-layer_de.md`.
2. **Step 6 package for the human:** resolve all 8 devils-advocate objections — the big
   one likely needs `/council` (re-centering Stage-1 scope on the code-server plane the
   user actually works in vs. the omnigent-host plane; also fix the ruling-6 ↔ Stage-3
   contradiction) — plus ratify 3 da items (pin BASE commit for the governance diff,
   whether `web/` is in it, agents-table lint gating). Then freeze spec + seal test.
3. **Resume the secrets deep-research** (paused mid-verify, cache intact):
   `Workflow({scriptPath: <session workflows dir>/deep-research-wf_7943ab35-6a7.js,
   resumeFromRunId: "wf_7943ab35-6a7", args: <same>})` — only AFTER lifecycle agents
   finish (VPS load rule). Its verdict feeds the `secrets-manager` spec, not this task.
4. **vps-infra architect: rulings delivered on defects #1-3, #4-5 still pending.**
   The 4-defect provisioning prompt got investigated end to end from the vps-infra
   session (2026-07-15) via direct SSH — root cause for #1 (root-owned repos), #2
   (silent resync clobbering the working tree) and #3 (root-owned `.git/objects`)
   all traced to the SAME thing: `omnigent-host.service` (systemd, runs as root,
   registers this VPS as an `omni host` runner for the Omnigent SERVER to dispatch
   sessions to) — a leftover from the original parked Omnigent pilot, never actually
   used since the code-server pivot. It was ALSO found actively crash-looping (403
   registering with the server, ~270 restarts since the last VPS reboot) — directly
   relevant to the #5 capacity question. **Ruling: disabled + stopped
   (`systemctl disable`).** This removes the write path entirely rather than patching
   around it — no cron/timer was ever the cause (checked, clean). Host-level ownership
   on all 5 repos already `coder:coder` (1000:1000), durable. Sudo-without-password in
   the container confirmed to be default upstream `codercom/code-server` image
   behavior (file mtime matches the image's own build date) — ruling: keep it,
   tailnet+password-gated is enough. **#4 (bake gh+git identity, persist
   `~/.config/gh`) and #5 (mem_limit/cpus + concurrency guidance) are designed but not
   yet implemented** — paused for a live-session check before touching
   docker-compose.yml further. Full writeup: vps-infra's own `docs/context_snapshot.md`
   (gitignored, OneDrive-synced only — read this file's summary if on a different
   device).
   **Also found + fixed along the way (unrelated to the report, discovered live):**
   the Claude Code VS Code extension auto-updated to 2.1.210, which bundles a musl
   native binary incompatible with this glibc container — fixed via
   `claudeCode.claudeProcessWrapper` pointing at `/usr/local/bin/claude` in
   `settings.json`. Right after that fix, the omnigent bind mount
   (`/opt/omnigent:/home/coder/repos/omnigent`) turned out to have never actually
   established when the container restarted post-reboot (Docker bind-mount race on
   boot) — host data was always intact, fixed with `docker compose restart
   code-server`. If `/home/coder/repos/omnigent` ever looks empty/missing again after
   a VPS reboot, this is the fix: restart the code-server container, don't panic about
   data loss first — verify from the HOST (`/opt/omnigent`) before assuming anything's
   gone.

## Access

- code-server: `https://omnigent-vps.tail05ae76.ts.net:8443` (full MagicDNS name;
  password in `/opt/code-server/.env` on the VPS).
- This fork: `/home/coder/repos/omnigent` (dev container) and `/opt/omnigent` (VPS,
  `ssh omni-vps`). Push to `origin` (`Zuus89/omnigent`) via `gh` OAuth — works.
- Linear: initiative "Personal AI Platform"; milestone comments posting again (connector
  re-connected under the user's NEW claude.ai account).
- Design mock: `https://claude.ai/code/artifact/e0c98989-9fc7-4f2a-ad85-8f3de5f15232`.

## Flags / gotchas

- **Session-start protocol applies** (CLAUDE.md §3). Also read the Claude memory dir
  (auto-loaded): environment hazards live there — provisioning clobbers (root ownership,
  stale snapshots, root-owned `.git/objects`), VPS load limits (stagger agents vs
  workflows), and the infra-consent protocol.
- **Infra protocol (human-ruled 2026-07-15):** no system-level changes without explicit
  consent; infra changes/questions go to the human AS A READY-TO-PASTE PROMPT for the
  vps-infra session. Ephemeral-server consent for de probes: PENDING.
- **Client disconnects kill the Claude Code process and all background agents/workflows**
  (three times this session: 2 internet cuts + 1 VPS hang). Transcripts and workflow
  caches survive — resume via SendMessage (agents) / resumeFromRunId (workflows). Push
  early; only pushed work provably survives.
- `.gitignore`: upstream's `reviews/` pattern swallowed `claude_tasks/reviews/` — scoped
  exception added in `ceeb8e10`.
- TODO.md needs a human-approved content update to add the `secrets-manager` item (not a
  status-sync; it's a new row).
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` note in FRAMEWORK.md Part 3 is stale in
  practice: subagent spawning works in this harness (da/de/devils-advocate all ran).
