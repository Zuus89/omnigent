---
type: doc
title: "Context Snapshot — Personal AI Platform"
status: snapshot
created: "2026-07-13"
updated: "2026-07-16"
---

# Context Snapshot — Personal AI Platform

> Cold-resume handoff. Current state only — overwritten at every close, not a log.

## Where we are

**Phase 2, task `workspace-layer` — deep in Step 7 (implementation), nearly ready for
Step 8.** Everything committed and pushed to `main` (HEAD `b5dc1fd4`). This session is
expected to be **killed by the architect's container-recreate window** (see resume point);
the next session starts fresh.

**The task in one paragraph:** build the Workspace entity — a per-client identity boundary.
After Steps 1–5, a `/council` overturned the original design (it isolated Omnigent's dead
host plane, not the code-server plane the user actually works in). Resolution, all
human-approved: **A2′** — each workspace is its own **Unix user** (`ws-<slug>`, own group
gid 2001+) inside the single code-server container; kernel-enforced isolation on the agent
path; **no root inside the container** (blanket sudo removed — the "master-key principle":
root belongs only to the vps-infra architect, host-side); editor access via **POSIX ACLs**;
per-workspace `CLAUDE_CONFIG_DIR`; secrets `0700`; audit trail via host `auditd`. A1
(a dedicated code-server instance) is the ≤1 escalation for a client that earns it. The
Omnigent server is **stopped-but-preserved** as the future collaboration engine.

**Done and on main:**
- `plan.md` §Phase 2 amended (protected file, human-approved) to the A2′ isolation model.
- Spec FROZEN (`claude_tasks/workspace-layer.md`), with a post-freeze correction banner
  pointing to the infra report as the authoritative permission model.
- Alpha test SEALED, then RE-SEALED **mechanism-agnostic** (`alpha_tests/workspace-layer.md`,
  BASE for G9 = commit `220f2db8`) — it asserts observable BEHAVIOR (which uid reads what,
  is the denial recorded), never modes/ACLs/groups. Human ruling: tests assert behavior,
  not mechanism.
- Architect built + live-tested infra deliverables 1–7 (`reviews/workspace-layer_infra-report.md`
  + `…_vps-infra-ruling.md` + `…_vps-infra-ruling-2.md`): image layer (uids/gh/git/acl),
  blanket sudo removed, provisioning script, mem_limit 4g / cpus 1.5, Omnigent stack
  stopped, auditd rules active, own-group+ACL permission model (which corrected the sealed
  test's original setgid/group-coder model — measured to leak code).
- **`ws-launch`** (the fork's privilege-drop wrapper — a security control) built, passed the
  code-reviewer gate (iter 1 NOT SAFE: PATH-hijack C-1 → fixed → iter 2 SAFE), merged to
  main at `deploy/personal-platform/ws-launch` (+ 19-check security harness). Resolves
  cwd→slug against the architect's **root-owned** registry with an ownership anchor;
  fail-closed, never falls back to `coder`.

## Resume exactly here

1. **Architect handoff for `ws-launch`** (prompt delivered to the human 2026-07-16): bake
   `COPY → /usr/local/bin/ws-launch root:root 0755`; **confirm `claude` is installed
   root-owned at `/usr/local/bin/claude`** (the wrapper fail-closes otherwise — hard
   requirement); confirm the registry mount `/etc/code-server-workspaces` + SLUG/UID/GID
   format; path-only sudoers Cmnd; sudo preserves cwd; wire
   `claudeCode.claudeProcessWrapper = /usr/local/bin/ws-launch`.
2. **The ONE recreate window** (architect + human): deliverables 1+2+4+7 + baking ws-launch
   take effect only on container recreate, which **kills the session**; also migrate
   `personal` → `ws-personal` (A2′) in that window (precondition for Step 8). Until
   ws-launch is baked, A2′ is NOT active — agents still run as `coder` ("deployed" ≠
   "protected").
3. **Two fork pieces still to build** (needed for Step 8, NOT for the recreate window;
   each needs the code-reviewer gate): the product registry `workspaces.yaml` + schema,
   and its validate script (loud-fail on registry/live-state mismatch). These back alpha
   checks C7 (registry derivability) and C8 (validator). The pm offered to build them
   before the recreate window; the human chose to pass the architect prompt first.
4. **Step 8:** `da` runs the sealed alpha test against the live VPS after A2′ is active —
   needs a host-side operator window (architect) for provisioning + `docker exec --user`
   probes (master-key principle). Then **Step 9: human validation**, **Step 10: close**.

## Access

- code-server: `https://omnigent-vps.tail05ae76.ts.net:8443` (full MagicDNS; pw in
  `/opt/code-server/.env` on the VPS). **After the recreate the container is new** — the
  bind mount `/opt/omnigent → /home/coder/repos/omnigent` must re-establish (a known boot
  race; if the repo looks empty, `docker compose restart code-server`, verify from the
  host `/opt/omnigent` before assuming data loss).
- Fork: `/home/coder/repos/omnigent`; push to `origin` (`Zuus89/omnigent`) via `gh` OAuth.
- Linear initiative "Personal AI Platform"; design mock
  `https://claude.ai/code/artifact/e0c98989-9fc7-4f2a-ad85-8f3de5f15232`.

## Flags / gotchas

- **Session-start protocol** (CLAUDE.md §3) + read the Claude memory dir (env hazards,
  infra-consent + master-key principle, VPS load limits).
- **Master-key principle:** after A2′ ships, there is NO passwordless sudo in the
  container — the `sudo chown` workaround for root-owned files is GONE by design; any such
  issue is a host-side architect handoff, never self-served.
- **Infra work = a ready-to-paste prompt for the vps-infra architect session**, carried by
  the human; never self-serve system-level changes.
- **VPS load:** 2 vCPU / ~8 GB shared with the editor; one heavy agent/workflow at a time;
  wide multi-agent workflows run OFF this box (notebook).
- Client disconnects / VPS hangs kill the session + background agents; transcripts and
  workflow caches survive (resume via SendMessage / resumeFromRunId). Push early.
- Root-owned files inside the fork are the **architect's** host-side deliveries (now fixed:
  they go via `docker exec -u coder`), not provisioning — report, don't self-diagnose.
- The `da`/`de`/`code-reviewer` roles run as spawnable subagents here (the
  `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` note in FRAMEWORK.md is stale — spawning works).
- `TODO.md` still needs a human-approved content row for the `secrets-manager` task
  (a new row, not a status-sync).
- Sibling briefs blocked by this task: `kb-three-tier` (SilverBullet access layer) and
  `secrets-manager`. The secrets deep-research workflow is paused/resumable
  (`resumeFromRunId wf_7943ab35-6a7`) — run it OFF this box.
