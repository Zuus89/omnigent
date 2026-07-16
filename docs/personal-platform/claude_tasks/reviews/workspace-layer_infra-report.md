---
type: review
task: workspace-layer
title: "Workspace layer — infra implementation report (deliverables 1-7, A2′)"
status: final
author_role: infra
created: "2026-07-16"
related_decisions: ["workspace-layer.md (FROZEN spec — permission model superseded by this report)", "alpha_tests/workspace-layer.md (SEALED — mechanism assertions superseded)", "workspace-layer_vps-infra-ruling-2.md"]
---

# Infra implementation report — captured by pm from the vps-infra session (2026-07-16)

Deliverables 1–7 built and tested against the live VPS; the code-server session was never
touched (`Up 25 hours`). **Still blocking: `ws-launch` (the fork's wrapper). Until it
exists, agents run as `coder` and A2′ is NOT active** — "deployed" is not "protected".

## Permission model CHANGED (measured) — this supersedes the frozen spec's model

The frozen spec / sealed alpha test specified: owner `ws-<slug>`, group `coder`, dirs 750,
code 640, secrets 600, group membership via setgid. **Live measurement disproved this**:

- **The provisioning script's first model (coder as primary group) leaked all code** —
  measured: `ws-clientb` read `ws-clienta`'s source. Only 0600 secrets were safe. Fixed:
  each workspace gets its **own primary group** (gid 2001+), never `coder`; `ws-init`
  hard-fails any entry declaring `GID=1000`.
- **Two further breaks neither side saw:** (1) `640` code stops the editor (`coder`) from
  SAVING — the human can't save from the UI. (2) With own-group + setgid-group-coder, a
  file the editor creates is born `coder:coder` and the agent (own group, not coder)
  can't read it. And supplementary groups are fixed at process exec, so adding coder to a
  new group needs a code-server restart → kills the ≤30-min/no-restart goal.
- **Resolution: POSIX ACLs** (evaluated per-access, no restart). Measured working: a new
  client added while code-server runs is readable without recreate.
- **Correction to the alpha test's mechanism reasoning:** it is the *directory mode 2770*
  (other = no bits, no traversal) that closes the hole, not setgid. setgid only keeps
  group ownership coherent on new files.

### FINAL permission model (verified end-to-end on the live VPS) — ws-launch must match

| Path | Owner | Group | Mode | Editor (coder) access |
|---|---|---|---|---|
| workspace dir | `ws-<slug>` | `ws-<slug>` (2001+) | `2770` | ACL `u:coder:rwx` + default ACL |
| code files | `ws-<slug>` | `ws-<slug>` | `660` | ACL inherited |
| `.credentials/` | `ws-<slug>` | `ws-<slug>` | `0700`, **ACL stripped** | **no access** |
| `CLAUDE_CONFIG_DIR` = `/home/ws-<slug>/.claude` | `ws-<slug>` | `ws-<slug>` | `0700` | no access |

Verified: `ws-clientb` → code/secrets/ls all Permission denied; `coder` → read code OK,
save OK, create OK, secrets denied; owner → own secrets OK (positive control).

## auditd (#6) — INSTALLED + ACTIVE on the host (accepted; the "free denial" claim was wrong)

The architect confirmed a plain DAC EACCES logs NOTHING — the pm's finding stands and
Ruling 2 §Q2 is amended. Host rules active: `-w /root/repos`, `-w .../workspaces.d`,
`-w /etc/sudoers.d`; per-workspace `-w <ws>/.credentials -p rwa -k ws-secret-access`
(appended by the provisioning script; logs denied AND successful foreign-uid reads — a
successful foreign read means the boundary FAILED). Container shares the host kernel and
cannot see/disable these. **Gotcha:** auditd refuses a watch on a not-yet-existing path
and one bad line aborts the whole ruleset (`auditctl -l` → "No rules" while service reports
active); the script now verifies with `auditctl -l`, not `augenrules` exit code.

## The wrapper (`ws-launch`) — RESOLVED: fork authors, architect bakes into image (not mounted)

**Why not bind-mounted:** `/opt/omnigent` is coder-writable, so a mounted wrapper could be
rewritten by the very injected agent it contains (`echo 'exec claude "$@"'` → no privilege
drop → bypass). `sudo` authorizes a literal path; if that path is editable the narrow rule
authorizes whatever the attacker put there. Deployment: `COPY` →
`/usr/local/bin/ws-launch`, `root:root 0755`; Dockerfile hook ready. **Cost (architect's
condition, not softened):** iterating the wrapper needs an image rebuild + recreate window.

### Contract for `ws-launch` (the fork's build spec)

1. Resolve **cwd → workspace slug** against the registry (see open question below).
2. `umask 007` (defence in depth; the dir blocks traversal anyway).
3. `exec sudo -u ws-<slug> claude "$@"`.
4. **Fail closed** — cwd maps to no known workspace → error out; **NEVER fall back to
   `coder`** (that fallback IS the bypass).
5. Handle pty/stdio transparently (driven by `claudeCode.claudeProcessWrapper`); this
   layer broke twice this month — real testing, not a smoke check.

## OPEN QUESTION for the fork (architect needs the answer before ws-launch is written)

Which registry does the wrapper resolve cwd→slug against?
- **infra's** `/opt/code-server/workspaces.d/<slug>.conf` (root-owned, mounted read-only at
  `/etc/code-server-workspaces`, tamper-audited) — the architect argues for this: a
  coder-writable `workspaces.yaml` would itself be the bypass (rewrite one line → another
  client's uid).
- **the fork's** `workspaces.yaml` (product SSOT) — if chosen, it must move somewhere
  `coder` cannot write.

## Deliverable status

| # | Deliverable | Status |
|---|---|---|
| 5 | Stop Omnigent stack | APPLIED (`stop`, volumes preserved; revive `docker compose start` ~10s; host.service disabled) |
| 1 | Image layer | BUILT + TESTED (`useradd`/`adduser`/`gosu`/`acl`, `gh`+`git` baked, base `/etc/gitconfig`) |
| 2 | Remove `NOPASSWD:ALL` | BUILT + TESTED (`sudo -n` as coder → password required; replaced by `coder ALL=(ws-<slug>) NOPASSWD: /usr/local/bin/ws-launch`) |
| 3 | Provisioning script | REWRITTEN for the corrected model (own group + ACL + auditd watch + terminal profile) |
| 4 | `mem_limit 4g` / `cpus 1.5` | WRITTEN in compose; activates on recreate |
| 6 | auditd | INSTALLED + RULES ACTIVE on host |
| 7 | group model | IMPLEMENTED + corrected per measurements |

Files in `vps-infra/vps-omnigent/opt/code-server/` (`Dockerfile`, `ws-init.sh`,
`ws-entrypoint.sh`, `provision-workspace.sh`, `gitconfig`, `docker-compose.yml`) and
`vps-omnigent/etc/audit/rules.d/workspace-secrets.rules`.

## RECREATE WINDOW needed

Deliverables 1+2+4+7 take effect only by recreating the container, which **kills the
code-server session**. Architect proposes ONE window once `ws-launch` is delivered, so
everything lands together. Needs the human's availability.

## Housekeeping (confirms the pm's earlier correction)

The 25 root-owned `.git/objects` were the architect's `scp`-as-root ruling deliveries, not
provisioning (omnigent-host.service was stopped 18h prior; the 07:16 batch matches the
ruling doc mtime). Fixed: deliveries now via `docker exec -u coder`; git there runs as
coder. If it recurs, it's an architect bug — report, don't diagnose.
