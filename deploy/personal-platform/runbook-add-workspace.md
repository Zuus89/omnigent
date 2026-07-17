# Runbook — add a workspace (the "second workspace" procedure)

> The Stage-1 second-workspace runbook required by the `workspace-layer` task (alpha PF-5);
> the alpha test's C1 proves this procedure live (≤30 min, no container restart, zero
> `omnigent/`/`web/` changes). Sources: the FROZEN spec (`docs/personal-platform/claude_tasks/
> workspace-layer.md`), the infra implementation report
> (`docs/personal-platform/claude_tasks/reviews/workspace-layer_infra-report.md`), and the
> A2′-live handoff (`docs/personal-platform/claude_tasks/reports/
> workspace-layer_a2prime-live-handoff.md`).

## Model in one line

A workspace = a per-client identity boundary: its own Unix user `ws-<slug>` (own group),
its own repo tree `/home/coder/repos/<slug>/`, its own Claude state (`CLAUDE_CONFIG_DIR`),
kernel-enforced isolation via the `ws-launch` privilege drop, audit via host `auditd`.

## Preconditions

- **Data-at-rest gate (binding):** before the FIRST client workspace, the data-at-rest
  posture must be ruled explicitly (see `docs/personal-platform/escalation-stages.md`).
  Onboarding without that ruling is a governance violation.
- The slug is a safe token (`[A-Za-z0-9._-]+`, not starting with `.` or `-`) — `ws-launch`
  validates this shape; the Unix user will be `ws-<slug>` (the ws-<slug> law).

## Procedure

### 1. Fork side (agent, runs as its workspace user)

1. Add the workspace entry to the product registry
   `deploy/personal-platform/workspaces.yaml`, per the schema
   (`deploy/personal-platform/workspaces.schema.md`): `slug`, `unix_user: ws-<slug>`,
   `root: /home/coder/repos/<slug>`, `git` identity (references only — never tokens),
   `config_dir`, `kb_repo: kb-ws-<...>`, `secret_store` (a reference, e.g.
   `keychain:<slug>`), a unique integer `workspace_id` (0 is reserved/rejected), and
   `projects[]` (repo URL + default branch each).
2. Structural validation: `python3 scripts/validate_workspaces.py --schema-only` → exit 0
   (also enforced by pre-commit on any registry change).
3. Commit the registry change.

### 2. Infra side (host-side, root — via the vps-infra architect, master-key principle)

Hand the architect a prompt naming the slug. The architect runs, on the host:

```
provision-workspace.sh <slug>
```

which creates the Unix user `ws-<slug>` (uid/gid 2001+), the workspace tree
`/home/coder/repos/<slug>/` (owner `ws-<slug>`, editor access via POSIX ACL `u:coder:rwx`,
secrets `0700` ACL-stripped), the per-workspace git identity, the `CLAUDE_CONFIG_DIR`, the
auditd coverage, and the **security registry** entry
`/etc/code-server-workspaces/<slug>.conf` (`SLUG`/`UID`/`GID`, root-owned — this, not
`workspaces.yaml`, is what `ws-launch` resolves against at launch). **No container
restart is required** — that is the C1 triviality guarantee.

### 3. Verify (either side)

- `cd` into the new tree and run `/usr/local/bin/ws-launch --resolve-only` → prints
  `slug=<slug> uid=<uid> gid=<gid>` (fail-closed otherwise).
- Full registry validation (structural + live):
  `python3 scripts/validate_workspaces.py` → exit 0.
- Open a Claude Code session in a folder under the new tree → the agent runs as
  `ws-<slug>` (the extension launches through `claudeProcessWrapper =
  /usr/local/bin/ws-launch`). First launch needs a per-workspace Claude login
  (isolation-positive: credentials never shared across workspaces).

## Invariants (do not violate)

- **Two registries, deliberately separate:** `workspaces.yaml` is the product SSOT
  (folder↔client map + ecosystem hooks); the root-owned `/etc/code-server-workspaces/` is
  the security-authoritative launch registry. Never wire the product file into the launch
  path.
- **`ws-launch` is SHA-256-pinned** by infra's image build (`EXPECTED_WRAPPER_SHA`). Any
  change to `deploy/personal-platform/ws-launch` must be announced to infra for a re-pin,
  or the build refuses it.
- No credentials in the registry, ever (Hard Rule 6) — `secret_store`/git fields are
  references; the validator scans for inline tokens.
- The A1 escalation (a dedicated code-server instance) is bounded at ≤1 — see
  `docs/personal-platform/escalation-stages.md`.
