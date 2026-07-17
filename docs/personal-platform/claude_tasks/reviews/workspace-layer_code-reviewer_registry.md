---
type: review
task: workspace-layer
author_role: code-reviewer
status: final
created: "2026-07-16"
---

# Code-review gate — `workspace-layer` registry + validator (Step-7 deploy gate)

**Verdict: SAFE TO COMMIT.**

No CRITICAL findings. No WARNING findings. Two SUGGESTION-level notes (non-blocking).
Every acceptance surface (sealed C7, C8 V0–V3, Hard Rule 6, scope, launch-path
decoupling) was executed against the real files, not taken from the `de`'s report.

Change set reviewed (exactly these 4 — everything else in the tree ignored per brief):
- `deploy/personal-platform/workspaces.yaml` (NEW)
- `deploy/personal-platform/workspaces.schema.md` (NEW)
- `scripts/validate_workspaces.py` (NEW — primary focus)
- `.pre-commit-config.yaml` (MODIFIED — added `validate-workspaces` local hook)

Review environment: `ws-personal` (uid 1001), A2′ live, `python3 3.13.5`, **no PyYAML**
(`ModuleNotFoundError: yaml`) — so the stdlib MiniYAML fallback is the parser actually
exercised here; the PyYAML path runs in the pre-commit venv and at Step-8 (PF-8).

---

## CRITICAL — none

Hard Rule 6 and the launch-boundary invariant both hold, verified by execution:

- **Sealed C7 inline-credential grep is EMPTY** on the registry:
  `grep -nE '^\s*[A-Z][A-Z0-9_]{2,}=[^ ]+' deploy/personal-platform/workspaces.yaml` → no
  match (exit 1). `raw_credential_errors()` on the registry → `EMPTY (clean)`.
- **`secret_store` / `git.credential_helper` are pointers, never tokens.**
  `secret_store: keychain:personal`, `credential_helper: store:/home/ws-personal/.git-credentials`
  (`workspaces.yaml:41,52`). The validator's `_is_reference` accepts `scheme:target`/`/path`
  **and** rejects any value matching a credential shape.
- **Project `repo` URLs are clean canonical form** — no `gho_`/`ghp_`/`x-access-token`/userinfo
  (`workspaces.yaml:57-77`). Positive control: injecting
  `https://x-access-token:ghp_...@github.com/...` into a `repo` line makes the validator exit 1
  and report it three ways (raw `file:line` github-token hit, raw url-userinfo hit, and
  structural `project #0 repo url embeds a credential`). Hard Rule 6 is actively enforced, not
  merely mirrored from C7.
- **Schema doc carries no credential.** Its only token-shaped substring is the literal prose
  ``​`://user:secret@` URL userinfo`` (`workspaces.schema.md:99`) documenting the regex — the
  word "secret" is literal, not a value; the validator does not scan the schema doc regardless.
- **Registry stays OUT of the security launch path** (infra ruling). The validator has zero
  coupling to `ws-launch`/`/etc/code-server-workspaces`/`sudo`/`gosu`; the only occurrences of
  those strings are the registry header comments (`workspaces.yaml:9-15`) explicitly stating
  this file is the coder/`ws-personal`-writable **product** view and must never sit in the
  privilege-drop path. Matches `workspace-layer_infra-report.md` "OPEN QUESTION" resolution.
- **Pre-commit hook uses the OFFLINE-safe layer** (`entry: python scripts/validate_workspaces.py
  --schema-only`, `.pre-commit-config.yaml:118`). It does **not** invoke the live layer, so it
  will not brick commits on a notebook where no `ws-*` user exists — a mis-wire here would have
  been CRITICAL; it is correct. `$VALIDATE_CMD` (full, incl. live) is the documented Step-8
  command (`workspaces.schema.md:118-119`).

## WARNING — none

Correctness, loud-fail contract, parser robustness, and injection safety all verified:

- **C8 loud + specific.** Appending the exact sealed ghost payload and running the FULL
  validator → exit 1, output names `ghost-<nonce>` 4× (missing git, missing projects, user does
  not resolve via getent, root does not exist). Contract met: fails non-zero AND names the entry.
- **Two-layer integrity.** A ghost with valid git+projects but nonexistent user/root:
  `--schema-only` → exit 0 (structural passes off-box), FULL → exit 1 naming the slug via the
  live layer. So the live layer is genuinely what catches a registry/live-state mismatch, and
  the structural layer is a strict subset (both pass on the real registry).
- **Parser fails LOUD, never silent.** Tab-in-indent, dangling scalar (no `key:`), trailing
  root-level junk, non-`workspaces` top-level, and empty file all raise `RegistryError` → exit 1
  with a labelled message. `validate()` wraps parsing in try/except so a parse failure is a
  labelled non-zero exit, never a crash. Silent-skip attempts (mis-indented second row; a
  second law-violating row) either raise or surface every error including the bad row — no row
  is dropped. The Hard-Rule-6 raw scan is parse-independent (scans raw text), so a credential
  cannot escape via a parser skip.
- **No MiniYAML→PyYAML false-PASS.** Every divergence I could construct is **fail-closed**:
  `workspace_id: 1  # c`, `unix_user: ws-x  # c`, flow-style `[a,b]`/`{k:v}`, and a `---` doc
  marker all make MiniYAML produce a value the validator *rejects* (loud), never one it wrongly
  accepts. The real registry uses zero trailing inline comments and pure block style, so
  MiniYAML yields byte-for-byte the structure `yaml.safe_load` would (`{workspaces:[{...}]}`,
  `workspace_id` as int, nested `git`, 5 projects) — structurally consumable by the sealed
  `ws_field`. At Step-8 the validator and `ws_field` both use PyYAML, so they cannot diverge
  there.
- **No injection/exec surface.** No `eval`/`exec`/`os.system`/`subprocess`/`shell=True`;
  liveness is `pwd.getpwnam(unix_user)` (direct NSS) and `os.path.isdir(root)` — registry values
  are never interpolated into a shell string.
- **C7 field-laws all hold** on the real entry: `unix_user == ws-personal` (== `ws-<slug>`),
  `kb_repo` matches `^kb-ws-.+`, `workspace_id` is int `1` (non-zero; `0` is validator-rejected),
  `secret_store` a non-empty reference; exactly one `workspaces.yaml` in the tree and exactly one
  `validate_workspaces.py`.
- **Pre-commit wiring valid** (C8 V0): hook block has no tabs, `- id:` at 6 spaces / keys at 8
  spaces matching every sibling local hook, `language: python` + `additional_dependencies:
  [pyyaml]` present, `pass_filenames: false`, `files: ^deploy/personal-platform/workspaces\.yaml$`.
  `grep -qiE 'workspace|registry|validate' .pre-commit-config.yaml` → wired=0. The
  `.pre-commit-config.yaml` diff is *only* the added hook block.
- **Scope clean.** Change set is exactly the 4 declared files (1 modified, 3 new). Zero content
  changes under `omnigent/` or `web/` (the `web/*` entries are pre-existing mode-only diffs,
  `0 insertions/0 deletions`). Registry not wired into the security launch path.

## SUGGESTION — non-blocking, no fix required to commit

1. **`scripts/validate_workspaces.py:96-107` (`_scalar`) — MiniYAML does not strip unquoted
   trailing `# comment`.** `workspace_id: 1  # reserved` parses to the string `"1  # reserved"`
   under the fallback (PyYAML would give int `1`). This is *fail-closed* today (the validator
   would reject such a line loudly, and the current registry has no trailing comments), so it is
   not a bug — but if a future editor adds an inline comment to a value line, the off-box
   fallback would emit a confusing false-failure that PyYAML environments would not. Optional
   hardening: strip an unquoted ` #...` suffix in `_scalar` to track PyYAML semantics.

2. **`scripts/validate_workspaces.py:51` — `_INLINE_ASSIGNMENT` uses `\S+` where the sealed C7
   grep uses `[^ ]+`.** Cosmetic only; both catch `KEY=value` and the alpha runs its own grep
   independently. No change needed.

---

## Method / evidence trail

Commands executed as `ws-personal` at `/home/coder/repos/personal/omnigent`:
- C7 sealed grep on the registry → empty; `raw_credential_errors()` → clean.
- `git ls-files | grep -E '(^|/)workspaces\.yaml$'` and the `validate*workspace*` grep return 0
  **now** only because the files are untracked pre-commit (this gate runs before the commit);
  the working-tree files are present and unique. After the Step-7 commit lands, C8 V0's
  `git ls-files` matches resolve to exactly one each — this is the intended Step-7→Step-8 order,
  not a defect.
- V1: `python3 scripts/validate_workspaces.py` and `--schema-only` → OK, exit 0.
- V2: sealed ghost payload appended to a temp copy → FULL exit 1, names `ghost-<nonce>` 4×;
  live-only ghost (valid structure) → schema-only exit 0 / full exit 1.
- Parser robustness + divergence + silent-skip probes via `_minimal_yaml_load` / `structural_errors`.
- Injection scan; scope + diff scope; schema-doc credential scan; trailing-newline check.

The real registry was never modified — all ghost/credential/malformed tests ran on `mktemp`
copies.
