---
type: report
title: "Workspace layer — registry + validator (fork product-layer deliverables)"
task: "workspace-layer"
author_role: de
status: final
created: "2026-07-16"
related_decisions:
  - "workspace-layer.md (FROZEN spec — §'The registry', Work-split table, Out of scope)"
  - "alpha_tests/workspace-layer.md (SEALED — acceptance: C7, C8 V0-V3, ws_field + $REGISTRY discovery)"
  - "reviews/workspace-layer_infra-report.md (registry-format ruling: product SSOT vs security registry)"
---

# Step-7 implementation report — `workspaces.yaml` registry + validator

Built the last two fork product-layer deliverables of `workspace-layer` against
the FROZEN spec: the product-SSOT registry (`workspaces.yaml` + schema doc) and a
loud-failing registry validator wired into pre-commit. These back the two
still-BLOCKED alpha checks **C7** (ecosystem hooks derivable from the entry alone)
and **C8** (validator fails loudly on a registry/live-state mismatch).

Nothing committed (per instruction; the code-reviewer gate + human-authorized
commit follow). The alpha-test directory was not touched.

## What I built, where, and why

| File | Status | Purpose |
|---|---|---|
| `deploy/personal-platform/workspaces.yaml` | new | Product SSOT — one entry per workspace (folder↔identity map + ecosystem hooks). Co-located with `ws-launch`. |
| `deploy/personal-platform/workspaces.schema.md` | new | Documents the top-level shape + every field + `$VALIDATE_CMD` + the credential-safety rules. |
| `scripts/validate_workspaces.py` | new | Two-layer validator (structural / live). Loud-fail, slug-named. |
| `.pre-commit-config.yaml` | modified | Adds the `validate-workspaces` local hook running the structural layer. |

**Registry home.** `deploy/personal-platform/` groups the personal-platform deploy
artifacts and sits next to `ws-launch`. Critically, this file is **not** in the
security launch path: `ws-launch` resolves `cwd→uid` against the root-owned,
read-only `/etc/code-server-workspaces/<slug>.conf` (hardcoded in the wrapper,
lines 34–35 of `ws-launch`). `workspaces.yaml` is the coder/`ws-personal`-writable
**product** view only — the two are kept separate exactly as the infra report's
"OPEN QUESTION" requires (a writable registry in the drop path would be the bypass).

**`personal` entry (the only current entry).** Real values, probed from the live
box, not guessed:
- `unix_user: ws-personal` (getent-confirmed: `ws-personal:x:1001:2001`).
- `root: /home/coder/repos/personal` (exists; owns all 5 repos).
- `config_dir: /home/ws-personal/.claude` (exists, `0700`, owner ws-personal).
- `kb_repo: kb-ws-personal`; `secret_store: keychain:personal`; `workspace_id: 1`.
- `git`: `Cristóbal Elton <celton@cristobalelton.com>` + a credential-helper
  **pointer** (`store:/home/ws-personal/.git-credentials`), never a token.
- `projects[]`: all 5 personal repos (human-confirmed), with **clean** canonical
  URLs and default branch `main`. Real remotes/branches read from the clones under
  `/home/coder/repos/personal/*`.

**`workspace_id = 0` reserved.** Personal is pinned at `1`; the validator rejects
any entry with id `0`, honoring the spec's Stage-3 note ("0 becomes a rejected
sentinel") so no forced migration is ever created.

## The validator — design

Two layers, matching the alpha's split:
1. **Structural (`--schema-only`)** — runs ANYWHERE, incl. pre-commit on a
   notebook with no `ws-*` users: required fields; `unix_user == ws-<slug>`;
   `kb_repo` ~ `^kb-ws-.+`; integer + unique + non-zero `workspace_id`;
   `secret_store`/`credential_helper` are references not credentials; `git` and
   `projects[]` shape; and a **raw-text credential scan** (Hard Rule 6) catching
   inline `KEY=VALUE`, GitHub/GitLab/AWS/Slack/OpenAI token shapes, and
   `://user:secret@` URL userinfo.
2. **Live (default / `--full` = `$VALIDATE_CMD`)** — adds host-state: each
   `unix_user` resolves via NSS (`pwd.getpwnam`) and each `root` exists on disk.
   This is what makes C8's ghost entry (nonexistent user/root) exit non-zero.

**Loud-fail contract:** all findings are aggregated and printed, each prefixed
with the offending **slug** (or `file:line` for a raw credential hit), then exit 1.

**YAML parsing (PF-8 hardening):** the box ships **no PyYAML, no pip, no jq**
(measured — see below). The validator therefore prefers PyYAML when importable
(the pre-commit hook installs it via `additional_dependencies: [pyyaml]`; a Step-8
host installs it per PF-8) and otherwise falls back to a strict, minimal
block-YAML reader for the constrained registry subset. The fallback fails loud on
anything it does not understand — it never silently mis-parses. This makes the
validator runnable on the bare base image, which is the whole PF-8 problem.

**Pre-commit wiring:** a `repo: local` hook (`language: python`,
`additional_dependencies: [pyyaml]`, `pass_filenames: false`, triggered only on
`^deploy/personal-platform/workspaces\.yaml$`) runs `--schema-only`, so off-box
commits never break on absent `ws-*` users.

## Self-verification (A2′ is live — all commands run as `ws-personal`, real output)

Environment probe (drives the parser design):
```
$ id
uid=1001(ws-personal) gid=2001(ws-personal) groups=2001(ws-personal)
$ getent passwd ws-personal
ws-personal:x:1001:2001::/home/ws-personal:/bin/bash
$ python3 -c 'import yaml'        -> ModuleNotFoundError: No module named 'yaml'
$ command -v pip3 / pre-commit    -> not found ;  ensurepip -> absent
```
→ The fallback parser path is the one exercised in every run below.

**C7 (offline) — the exact sealed grep + ws_field logic (MiniYAML swapped for the
absent pyyaml):**
```
$ grep -nE '^\s*[A-Z][A-Z0-9_]{2,}=[^ ]+' workspaces.yaml   -> EMPTY (PASS)
  personal.unix_user == ws-personal   : True
  personal.kb_repo ~ ^kb-ws-.+        : True (kb-ws-personal)
  personal.workspace_id is int        : True (1)   ; != 0 : True
  personal.secret_store non-empty ref : True (keychain:personal)
  personal.root non-empty             : True (/home/coder/repos/personal)
  personal.git.name / git.email       : nested extraction OK
```

**C8 — validator, full sequence (V1 baseline / V2 ghost / V3 restore):**
```
V0  ls-files match: scripts/validate_workspaces.py ; pre-commit wired=0
V1  python3 scripts/validate_workspaces.py           -> OK (full)        exit=0
    python3 scripts/validate_workspaces.py --schema-only -> OK           exit=0
V2  (append ghost: ws-ghost-<nonce> / /opt/work/ghost-<nonce>, no user/root)
    python3 scripts/validate_workspaces.py           -> FAILED           exit=1
      - [ghost-<nonce>] missing required field 'git' ...
      - [ghost-<nonce>] missing required field 'projects' ...
      - [ghost-<nonce>] unix_user 'ws-ghost-<nonce>' does not exist (getent passwd)
      - [ghost-<nonce>] root '/opt/work/ghost-<nonce>' does not exist on this host
    NAMES-GHOST=yes
V3  (restore) python3 scripts/validate_workspaces.py -> OK               exit=0 ; RESTORED-CLEAN
```
(V3 restore was `cp` from a backup because the file is untracked pre-commit; at
Step 8 the file is committed and `git checkout -- $REGISTRY` restores it identically.)

**Isolation proofs (extra rigor):**
- Live layer in isolation — a ghost WITH valid git+projects but nonexistent
  user/root: `--schema-only` exit 0, full exit 1 naming the slug. Confirms the
  live layer is genuinely what catches a live-state mismatch (the C8 intent).
- Credential scanner — temporarily pointing a project `repo` at the tokenised URL
  actually found on the box (`gho_...@github.com`): validator exit 1, naming both
  the raw `file:line` token hit and the structural `project #0 repo url embeds a
  credential` — proves Hard Rule 6 is enforced, not just mirrored from C7.
- Fallback parser fails loud on a tab in indentation (never silent mis-parse).
- Uniqueness: exactly one `workspaces.yaml`, exactly one `validate*workspace*`.

**Pre-commit:** `pre-commit` is not installed for `ws-personal` (and no `.venv`),
so I could not run `pre-commit run --all-files`. Verified instead: the config has
no tabs, my hook block matches sibling `- id:` indentation exactly (6/8 spaces),
and the V0 wiring greps pass. `ruff` is likewise not runnable here (no `.venv`);
the validator is written to the repo's ruff config (line-length 99 — 0 lines over;
selected rules E/F/I/UP/ARG/BLE/B/SIM/RET/C4/PIE/RUF respected: single justified
`# noqa: BLE001`, no unused noqa, 2-blank-line spacing, py310 target) and
`py_compile` is clean. `ruff format`/`check` will run at commit as fixers.

## Self-review checklist

- **Correctness:** C7 offline + C8 V0–V3 pass with real output above; nested
  `git.*` extraction works; ghost is named in the failure. ✔
- **Security / Hard Rule 6:** no inline credentials in the registry (exact C7 grep
  empty); `secret_store`/`credential_helper`/`repo` are pointers/clean URLs; the
  validator actively scans for and rejects token shapes and URL-embedded
  credentials. ✔
- **Scope:** my change set is exactly 4 files — `.pre-commit-config.yaml`,
  `deploy/personal-platform/workspaces.yaml`, `deploy/personal-platform/workspaces.schema.md`,
  `scripts/validate_workspaces.py`. **Zero** under `omnigent/` or `web/`. No
  `TODO.md`/`CLAUDE.md` edits; alpha-test dir untouched. ✔
- **Meets C7/C8:** yes (evidence above). The registry shape satisfies the sealed
  `ws_field` (`reg.get("workspaces", reg)` → list of rows). ✔

## Residual risk / decisions for pm + code-reviewer to scrutinize

1. **HANDOFF HAZARD (commit hygiene — read before staging).** The working tree
   had **31 pre-existing modified files** at session start (all `web/`, `.github/`,
   `deploy/*.sh`, `scripts/*.sh` — mode-only diffs, `0 insertions/0 deletions`),
   NOT produced by this task. Plus `docs/personal-platform/activity_log.jsonl`,
   `context_snapshot.md`, and an untracked `..._a2prime-live-handoff.md` from a
   concurrent session. **The commit must stage ONLY the 4 workspace-layer files —
   never `git add -A`.** A blanket add would pull `web/` files into the commit and
   **fail G9**.
2. **Two-layer split is load-bearing.** The structural layer must stay a strict
   subset of the full run so the pre-commit hook (off-box) and `$VALIDATE_CMD`
   (on-host) never disagree on structure. Confirmed: full = structural + live; the
   only delta is the two host-state checks.
3. **PyYAML vs fallback parser.** In THIS environment only the fallback path is
   exercised (no PyYAML obtainable). The PyYAML path (`yaml.safe_load`) is the same
   one the sealed `ws_field` uses, and the registry is deliberately bog-standard
   block YAML, so the two parsers produce identical structure. The PyYAML path is
   NOT directly executed here — it will run first in the pre-commit venv and at
   Step 8 (PF-8). If the reviewer wants belt-and-suspenders, install pyyaml and
   diff the two loaders on the registry; I could not (no pip/ensurepip).
4. **`workspace_id = 0` rejection** is enforced now, before any second entry
   exists — intentional, per the Stage-3 sequencing note. Flagging in case the
   reviewer expected 0 to be merely reserved-in-doc rather than validator-rejected.
5. **SECURITY FINDING (out of my scope to fix, must be surfaced).** Three of the
   live clones carry **plaintext GitHub tokens embedded in their `origin` remote
   URLs**: `saga-voice`, `vps-infra` (`gho_7na1qt…`) and `zuus89.github.io`
   (`gho_9gwyDl…`) — in each repo's `.git/config`, i.e. the *same class* of
   Hard-Rule-6 leak stripped from this fork's origin on 2026-07-13, now recurring
   in sibling repos. My registry uses the clean URLs and never carries these; but
   the live remotes remain exposed. Recommend the pm route a token rotation +
   `git remote set-url` cleanup (and migrating to the credential-helper the
   registry already points at). Not fixed here — it lives in other repos'
   `.git/config`, outside this task's surface.
