# `workspaces.yaml` — schema & validation reference

**Artifact:** `deploy/personal-platform/workspaces.yaml`
**Validator:** `scripts/validate_workspaces.py`
**Task:** `workspace-layer` (A2′) · **Status:** reference doc

---

## What this registry is (and is not)

`workspaces.yaml` is the **product SSOT** for the Personal AI Platform: one entry
per workspace, mapping a folder tree to a client/identity and carrying the
ecosystem hooks that downstream tasks (kb-three-tier, secrets-manager, the future
workspace switcher) derive their targets from.

It is **not** the security registry. The launch wrapper `ws-launch` resolves
`cwd → workspace uid` against the **root-owned, read-only**
`/etc/code-server-workspaces/<slug>.conf` (declaring `SLUG`/`UID`/`GID`), a path
hardcoded in the privilege-drop path. `workspaces.yaml` is
coder/`ws-personal`-writable and must **never** sit in that launch path — a
writable registry there would itself be the isolation bypass. The two are
deliberately separate (see `reviews/workspace-layer_infra-report.md`, "OPEN
QUESTION for the fork").

---

## Top-level shape

A single top-level `workspaces:` key holding a **list** of workspace entries:

```yaml
workspaces:
  - slug: personal
    unix_user: ws-personal
    root: /home/coder/repos/personal
    config_dir: /home/ws-personal/.claude
    kb_repo: kb-ws-personal
    secret_store: keychain:personal
    workspace_id: 1
    git:
      name: "Cristóbal Elton"
      email: celton@cristobalelton.com
      credential_helper: "store:/home/ws-personal/.git-credentials"
    projects:
      - name: omnigent
        path: /home/coder/repos/personal/omnigent
        repo: https://github.com/Zuus89/omnigent.git
        branch: main
      # … one entry per repo in the workspace
```

`yaml.safe_load(workspaces.yaml)` yields `{"workspaces": [ {entry}, … ]}`. Field
extraction follows the alpha test's `ws_field` helper: `reg.get("workspaces", reg)`
then match a row by `slug` or `unix_user`.

---

## Fields

| Field | Type | Required | Law / notes |
|---|---|---|---|
| `slug` | string | yes | Workspace id. Lowercase token `^[a-z0-9][a-z0-9._-]*$`, unique. |
| `unix_user` | string | yes | **Must equal `ws-<slug>`** (kernel-boundary law; alpha C7). Unique. |
| `root` | absolute path | yes | The workspace code tree (the folder grouping its repos). Checked to **exist** by the live layer. |
| `config_dir` | absolute path | yes | `CLAUDE_CONFIG_DIR` for this workspace's Claude Code state (own uid, `0700`). See note on nesting below. |
| `kb_repo` | string | yes | kb-three-tier clone-target slug. **Must match `^kb-ws-.+`** (e.g. `kb-ws-personal`). |
| `secret_store` | reference | yes | secrets-manager pointer — `scheme:target` (e.g. `keychain:personal`) or `/absolute/path`. **A REFERENCE, never a secret value.** |
| `workspace_id` | integer | yes | Reserved partition-seam integer (Stage 3). **Non-zero, unique.** `0` is a reserved/rejected sentinel — see below. |
| `git.name` | string | yes | Commit author name for the workspace. |
| `git.email` | string | yes | Commit author email. |
| `git.credential_helper` | reference | yes | Pointer to the credential-helper backing file/config (`scheme:target` or `/path`). **Never a token** — the actual credential lives only in the gitignored helper file, managed by the separate gitconfig-`includeIf` deliverable. |
| `projects` | list | yes (≥1) | Per-project git bindings. Each entry: `repo` (clean URL, **no embedded credentials**) + `branch` (default branch); `name`/`path` optional. Pre-builds the Phase-3 project-owns-git slot. |

**`config_dir` nesting note.** The infra model places `CLAUDE_CONFIG_DIR` at
`/home/ws-<slug>/.claude` (under the workspace user's home). The alpha's C4-a
asserts a *disposable* `ws-test` workspace's `config_dir` sits **under its
`root`**; the second-workspace runbook satisfies that for `ws-test` by choosing a
config dir under its tree. The validator does **not** enforce a nesting relation
(it would wrongly reject `personal`, whose config dir is under its home, not its
repos root); it only checks `config_dir` is a present, absolute path.

### `workspace_id = 0` is reserved

Upstream's dormant partition seam treats `0` as the pre-migration default. The
spec's Stage-3 note requires that **`0` becomes a rejected sentinel** before any
read-side filtering ships, and that `personal` never occupy `0`. This registry
reserves `personal` at `1` from day one and the validator **rejects any entry
with `workspace_id: 0`**, so no future forced migration is created.

---

## Credential safety (Hard Rule 6)

No credential, token, or connection string may appear anywhere in this file.
`secret_store` and `git.credential_helper` are pointers; project `repo` URLs are
the clean canonical form (no `user:token@` userinfo). The validator scans the raw
file text and fails the commit on: inline `UPPER_CASE=value` assignments (the
alpha's C7 grep), GitHub/GitLab/AWS/Slack/OpenAI token shapes, and any
`://user:secret@` URL userinfo.

---

## Validation — `$VALIDATE_CMD`

The validator has two layers:

- **Structural** (`--schema-only`) — shape + law + credential checks that hold
  **anywhere**, including a pre-commit run on a machine where no `ws-*` user
  exists. This is the pre-commit entrypoint, so off-box commits never break.
- **Live** (default / `--full`) — the structural layer **plus** host-state
  checks: each `unix_user` must resolve via NSS and each `root` must exist on
  disk. This is what makes a registry/live-state mismatch fail loudly.

```sh
# Structural only (pre-commit safe, runs off-box):
python3 scripts/validate_workspaces.py --schema-only

# Full — structural + live host-state. THIS IS $VALIDATE_CMD (Step-8 command):
python3 scripts/validate_workspaces.py
```

On any problem the validator prints every finding — each prefixed with the
offending workspace **slug** (or, for a raw-text credential hit, `file:line`) —
and exits non-zero. A clean run prints `workspace registry OK (<mode>)` and exits
0.

**YAML parsing.** PyYAML is used when importable (the pre-commit hook installs it
via `additional_dependencies`; a Step-8 host installs it per the alpha's PF-8).
When PyYAML is absent, the validator falls back to a strict minimal block-YAML
reader for the constrained registry subset, so it also runs on the code-server
base image (which ships neither PyYAML nor `jq`). The fallback fails loud on
anything outside the documented subset rather than guessing.

---

## Pre-commit wiring

`.pre-commit-config.yaml` runs the **structural** layer as a `repo: local` hook
(`language: python`, `additional_dependencies: [pyyaml]`), triggered only when
`deploy/personal-platform/workspaces.yaml` changes:

```yaml
      - id: validate-workspaces
        name: validate workspace registry (structural)
        language: python
        entry: python scripts/validate_workspaces.py --schema-only
        files: ^deploy/personal-platform/workspaces\.yaml$
        pass_filenames: false
        additional_dependencies: [pyyaml]
```

The full live layer is not run at commit time (a notebook has no `ws-*` users);
it is the Step-8 `$VALIDATE_CMD` above, run on the host.

---

## Ecosystem hooks (how downstream derives targets from the entry alone)

- **kb-three-tier:** clone `kb_repo` (`kb-ws-<company>`) under `root/`.
- **secrets-manager:** resolve the per-workspace store from `secret_store`.
- **workspace switcher (Stage 2a):** enumerate `workspaces[].slug` / `root`.
- **Phase-3 project-owns-git:** bind each `projects[]` entry's `repo`/`branch`.
