---
type: alpha_test
title: "Workspace layer — frozen acceptance test"
task: "workspace-layer"
status: draft
created: "2026-07-15"
related_decisions: ["workspace-layer.md (spec, Step 3 + human rulings)"]
---

# Workspace layer — frozen acceptance test (Step 4, DRAFT)

> **Bias-control spine.** This test is designed at Step 4 from the **spec alone**
> (`workspace-layer.md`, Step 3 + human rulings, HEAD `a9dae275`), before any implementation
> exists. No implementation plan was read. Factual grounding about the current state comes
> from the Step-2 profile (`workspace-layer_step2-profile.md`) only. Every check below is a
> reproducible command with an exact expected observable and a **binary** (PASS/FAIL) rule —
> no judgment calls. `status` stays `draft` until Step 6, when it is **sealed** (add
> `sealed_at:`); after sealing, this file is immutable — a post-seal edge case becomes a new
> task, never an edit here.

---

## 0. What a PASS asserts (coverage of the six spec acceptance-criteria seeds)

| # | Spec acceptance seed (`workspace-layer.md` §"Acceptance criteria") | Check group in this test |
|---|---|---|
| 1 | Triviality: add workspace #2 in ≤30 min, no server/other-ws restart, no code changes | **AC1** (a–e), timed dry-run creating & tearing down `ws-test` |
| 2 | Isolation: client host can't read personal's volume; personal creds absent from client runner env; commits carry client git identity | **AC2-1** (volume), **AC2-2** (creds), **AC2-3** (git identity, container plane); **D3-1** (editor-plane identity, deliverable #3) |
| 3 | Credential strip: shared server env holds no provider creds / git tokens | **AC3-1** |
| 4 | Ecosystem hooks: kb-three-tier can clone `kb-ws-<company>` and secrets-manager can target the per-ws env/secret store, each **from the registry entry alone** | **AC4-H1** (kb), **AC4-H2** (secrets) |
| 5 | Fork governance: `git diff` of Stage 1 shows zero files under `omnigent/` | **G1** |
| 6 | Validate script **fails loudly** on a seeded registry/live-state mismatch | **AC6** (V1–V3) |

The alpha test **PASSES iff every mandatory check below passes** (§6). Any single mandatory
FAIL → the whole alpha test **FAILS**. Optional/informational checks (explicitly marked) do
not affect the verdict.

---

## 1. Out of scope (this test does NOT cover — and why)

- **Stage 2a — workspace switcher UI** (VS Code extension / later web). Successor task; human
  ruling #7 keeps it out of Stage 1. Not tested.
- **Stage 2b — server-side control-plane enforcement** that a session labeled workspace W can
  only be created on W's host. The spec states plainly that Stage-1 identity at the control
  plane is **convention until Stage 2b** ("a raw API call can create a session for workspace A
  on host B"), and human ruling #1 accepts Stage 1 as sufficient with Stage 2b behind a
  binding trigger. **This test deliberately does NOT attempt a cross-host session-create and
  does NOT assert it is blocked** — doing so would fail Stage 1 by design. The isolation this
  test proves is **kernel-level** (volumes, env, git identity, networks), which is exactly
  what Stage 1 claims.
- **Stage 3 — activating the `workspace_id` partition.** Not built in Stage 1; G1 in fact
  asserts it was **not touched**.
- **Step-5 mandatory executed probes (a/b/c).** These gate **freeze**, not **acceptance**.
  Probe (a) host-tunnel blast radius, (b) allowlist-forwarding-is-per-host verification, and
  (c) the `workspace_scope()` read-side smoke are the `de`/review responsibility at Step 5 and
  are **not part of this alpha test**. (AC2-2 below proves *credential value absence*, which is
  a weaker, acceptance-level claim than probe (b)'s mechanism verification — they do not
  overlap.)
- **Data-at-rest gate.** A binding governance gate before the *first client* workspace; no
  client is onboarded here, so nothing to test.
- **Downstream consumer behavior.** AC4 tests that the registry entry is **sufficient** for
  kb-three-tier / secrets-manager to derive their targets; it does **not** test those
  downstream tasks' full behavior (they don't exist yet). A live kb clone is offered only as
  an optional, non-gating reinforcement.
- **Agents-table env-refs lint.** The spec notes the validate script should apply the same
  env-refs-only rule to the shared `agents` table. The **AC seed #6** is specifically the
  *registry/live-state* mismatch, so that is what AC6 gates. The agents-table lint is recorded
  as a coverage note for the pm (§7), not a binary gate here.

---

## 2. Preconditions & environment (pre-flight gate)

All `docker …` commands run in a shell **on `omni-vps`** (e.g. `ssh omni-vps`, per CLAUDE.md
§13; prefix `sudo` if the operator user is not in the `docker` group). The fork clone at
`$REPO` is inspected on whichever box holds it (this dev container or the VPS checkout at
`/opt/omnigent`). The test is **BLOCKED** (not PASS/FAIL) until all of the following hold:

- **PF-1** `omni-vps` reachable; `docker ps` returns without error.
- **PF-2** The **personal** workspace host container is running and discoverable by its
  spec-guaranteed mount `/opt/work/personal` (`cid_for_ws personal` resolves — §3).
- **PF-3** The **shared Omnigent server** container is running and discoverable (`server_cid`
  resolves — §3).
- **PF-4** The fork holds the implemented Stage-1 deliverables: a single tracked
  `workspaces.yaml` (§3, `REGISTRY`), a discoverable **wired** validate entrypoint (§3,
  `VALIDATE_CMD`), the escalation-stages doc, and the second-workspace runbook.
- **PF-5** The pm has recorded, at Step-6 seal, the **`BASE`** pre-implementation baseline
  commit for G1 (§3). Absent that, G1 is ambiguous — this is a hard dependency (§7, finding 1).

If any PF fails, report **BLOCKED — precondition PF-n unmet**, not a verdict.

---

## 3. Fixtures, sentinels & discovery helpers (nothing here mutates live state)

```sh
# ---- paths / targets ----
REPO=/home/coder/repos/omnigent          # the fork clone (adjust to /opt/omnigent on the VPS)
WS_PERSONAL=personal                      # workspace #1 (confirm the exact name against the registry)
WS_TEST=ws-test                           # disposable workspace #2 created & torn down by this test
NONCE=$(date +%s)                         # one nonce per run; makes sentinels globally unique

# ---- ws-test sentinels (fixtures I define now, at Step 4; NOT real secrets) ----
WSTEST_GIT_NAME="ws-test bot"
WSTEST_GIT_EMAIL="ws-test@example.invalid"
# Each credential var gets a unique, obviously-fake sentinel value in ws-test's env file:
#   value("VAR") = "WSTEST-SENTINEL-<VAR>-$NONCE"
# Uniqueness guarantees any hash-equality with personal (AC2-2) is a genuine leak.

# ---- canonical credential/identity var list (secret-bearing only; excludes base URLs & model ids) ----
# Source: Step-2 profile, connect.py:424-441 allowlist + managed_hosts.py:44-46 + OMNIGENT_ aliases.
CRED_VARS="ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN AWS_BEARER_TOKEN_BEDROCK CLAUDE_CODE_OAUTH_TOKEN \
CODEX_ACCESS_TOKEN OPENAI_API_KEY GEMINI_API_KEY GIT_TOKEN GIT_USERNAME GITHUB_TOKEN \
OMNIGENT_ANTHROPIC_API_KEY OMNIGENT_OPENAI_API_KEY OMNIGENT_CREDENTIAL"

# ---- registry file (must be exactly one tracked file named workspaces.yaml) ----
REGISTRY="$(git -C "$REPO" ls-files | grep -E '(^|/)workspaces\.yaml$')"
# PASS precondition: exactly one line. Zero => deliverable missing; >1 => ambiguous SSOT.

# ---- wired validate entrypoint (deliverable #2: "validate script, wired, not manual") ----
# Discover the tracked validator (name pairs validate + workspace/registry):
VALIDATE_FILE="$(git -C "$REPO" ls-files | grep -iE 'validate.*(workspace|registry)|(workspace|registry).*validate' | head -1)"
# It MUST also be wired into pre-commit (the "wired, not manual" requirement):
grep -qiE 'workspace|registry|validate' "$REPO/.pre-commit-config.yaml"   # exit 0 required
# VALIDATE_CMD is the invocation of $VALIDATE_FILE (e.g. "python $REPO/$VALIDATE_FILE"
# or the pre-commit hook id); resolve concretely at Step 8 from the schema doc / hook entry.

# ---- G1 baseline commit (recorded by pm at Step-6 seal; a9dae275 as of Step 4) ----
BASE=<freeze-baseline commit recorded at Step-6 seal>     # default assumption: a9dae275

# ---- discovery helpers (run on omni-vps) ----
# Map a workspace name -> its host container id via the spec-guaranteed mount /opt/work/<ws>.
cid_for_ws() {  # $1 = ws name
  for c in $(docker ps -q); do
    hit=$(docker inspect "$c" --format \
      '{{range .Mounts}}{{if eq .Destination "/opt/work/'"$1"'"}}HIT{{end}}{{end}}')
    [ "$hit" = HIT ] && { echo "$c"; return 0; }
  done
  return 1
}
# The shared server container: runs `omnigent server`, and (unlike host containers) mounts no
# /opt/work/<ws>. Confirm the single match against the vps-infra compose service name at Step 8.
server_cid() { docker ps --format '{{.ID}} {{.Command}}' | grep -i 'server' | awk '{print $1}' | head -1; }
```

---

## 4. Checks

Execution order (dependencies): **G1 → AC3 → AC1 (creates `ws-test`) → AC2 / AC4 / D3 (with
`ws-test` live) → teardown (removes `ws-test`, restores registry) → AC6 (on the restored
registry)**.

### G1 — Fork governance: zero files under `omnigent/` (and `web/`) in the Stage-1 change set  [AC seed 5]

```sh
# (a) forbidden surface untouched
git -C "$REPO" diff --name-only "$BASE" HEAD | grep -E '^(omnigent|web)/'
# (b) anti-vacuous guard: the implementation actually delivered the product-layer artifacts
git -C "$REPO" diff --name-only "$BASE" HEAD | grep -E '(^|/)workspaces\.yaml$'
git -C "$REPO" diff --name-only "$BASE" HEAD | grep -Ei 'escalation|runbook'
```
- **Expected:** (a) prints nothing (exit 1); (b) both greps print ≥1 path.
- **PASS iff** (a) is empty **and** both (b) greps are non-empty.
- Subsumes the scope guard "no touching the dormant `workspace_id` column": any
  `db_models`/migration edit lives under `omnigent/` and would fail (a).
- *Note (finding 3):* `web/` is included because the spec's architecture section states Stage 1
  "touches zero files under `omnigent/` or `web/`". Seed #5 names only `omnigent/`; if the pm
  intends the looser reading, drop `web/` from (a) at seal.

### AC3-1 — Shared server env holds no provider credentials / git tokens  [AC seed 3]

```sh
SRV=$(server_cid)
SPID=$(docker exec "$SRV" sh -c 'pgrep -f "omnigent .*server" | head -1'); : "${SPID:=1}"
docker exec "$SRV" sh -c "tr '\0' '\n' < /proc/$SPID/environ" \
  | grep -E "^($(echo $CRED_VARS | tr ' ' '|'))=."
```
- **Expected:** the `grep` prints **nothing** (exit 1) — every credential var is absent or empty
  (`=.` requires a non-empty value) in the **effective process environment** of the running
  server.
- **PASS iff** the output is empty. Any printed line → FAIL (that credential still lives on the
  shared server).
- **Scope rationale (binary):** the forbidden set is the enumerated `CRED_VARS` (provider keys,
  tokens, git identity) only. Server-infrastructure secrets the spec does **not** target —
  `OMNIGENT_OIDC_CLIENT_SECRET`, `OMNIGENT_ACCOUNTS_COOKIE_SECRET`, `DATABASE_URL` — may legitimately
  remain and are **not** failed here ("no *provider* identity"). A broad `*_API_KEY|*_TOKEN`
  sweep is offered as an *informational, non-gating* diagnostic only:
  ```sh
  # INFORMATIONAL ONLY (not part of the verdict): surface anything credential-shaped for pm review
  docker exec "$SRV" sh -c "tr '\0' '\n' < /proc/$SPID/environ" \
    | grep -E '^[A-Z0-9_]*(API_KEY|_TOKEN|BEARER|CREDENTIAL)=.'
  ```

### AC1 — Second-workspace triviality (timed dry-run: create `ws-test`)  [AC seed 1]

```sh
SRV=$(server_cid); CID_PERSONAL=$(cid_for_ws "$WS_PERSONAL")
# --- capture invariants BEFORE ---
SRV_0=$(docker inspect "$SRV" --format '{{.State.StartedAt}} {{.State.Pid}}')
PER_0=$(docker inspect "$CID_PERSONAL" --format '{{.State.StartedAt}} {{.State.Pid}}')
T0=$(date +%s)
```
Now execute **only** the runbook (deliverable #5) steps to add `ws-test` — no code edits, no
restart of any other container. The timer brackets the mechanical procedure only (exclude
time spent reading the runbook):
1. Copy the personal compose stanza → `ws-test` stanza in **vps-infra** (edit ws name, named
   volume, `env_file`, network, `mem_limit`).
2. Create `ws-test`'s env file populated with the §3 sentinels (`WSTEST-SENTINEL-<VAR>-$NONCE`
   for each `CRED_VARS` entry; git identity = `WSTEST_GIT_NAME`/`WSTEST_GIT_EMAIL`).
3. Add a `ws-test` entry to `$REGISTRY` (host_id, owner, root `/opt/work/ws-test`, git identity
   = the ws-test sentinels, env-file **reference**, kb slug `kb-ws-ws-test`, secret-store
   pointer, ≥1 project entry with repo URL + default branch).
4. Bring up **only** `ws-test`'s container (e.g. `docker compose up -d <ws-test service>`).

```sh
# --- capture AFTER ---
T1=$(date +%s); ELAPSED=$((T1 - T0))
SRV_1=$(docker inspect "$SRV" --format '{{.State.StartedAt}} {{.State.Pid}}')
PER_1=$(docker inspect "$CID_PERSONAL" --format '{{.State.StartedAt}} {{.State.Pid}}')
CID_WSTEST=$(cid_for_ws "$WS_TEST")
```
- **AC1-a** `ELAPSED -le 1800` (≤ 30 minutes for the four mechanical steps + bring-up).
- **AC1-b** `SRV_1 == SRV_0` (shared server **not** restarted — StartedAt & Pid unchanged).
- **AC1-c** `PER_1 == PER_0` (personal workspace **not** restarted).
- **AC1-d** no code change in the fork during the procedure:
  ```sh
  git -C "$REPO" status --porcelain | grep -E ' (omnigent|web)/'   # expected: empty (exit 1)
  git -C "$REPO" status --porcelain | grep -E '(^|/)workspaces\.yaml$'  # expected: non-empty
  ```
- **AC1-e** `ws-test` host is up and registered:
  ```sh
  docker inspect "$CID_WSTEST" --format '{{.State.Running}}'          # expected: true
  docker exec "$CID_WSTEST" sh -c 'pgrep -f "omnigent .*host" >/dev/null && echo ALIVE'  # expected: ALIVE
  # registration confirmed by EITHER of (either suffices; both confirm the same fact):
  #   curl -s http://<server>/v1/hosts   | grep -q "<ws-test host_id from registry>"      # OR
  docker logs "$CID_WSTEST" 2>&1 | grep -iE 'register(ed)?'          # expected: a success line
  ```
- **PASS iff** AC1-a, -b, -c, -d, -e all hold.

### AC2-1 — `ws-test` cannot read personal's volume (both directions)  [AC seed 2, isolation]

```sh
# (i) ws-test has no mount whose destination is personal's root
docker inspect "$CID_WSTEST" --format '{{range .Mounts}}{{.Destination}}{{"\n"}}{{end}}' \
  | grep -Fx "/opt/work/$WS_PERSONAL"                              # expected: empty (exit 1)
# (ii) personal's root is unreachable from inside ws-test
docker exec "$CID_WSTEST" sh -c "[ -e /opt/work/$WS_PERSONAL ] && echo EXISTS || echo ABSENT"   # expected: ABSENT
# (iii) symmetric: personal cannot see ws-test
docker inspect "$CID_PERSONAL" --format '{{range .Mounts}}{{.Destination}}{{"\n"}}{{end}}' \
  | grep -Fx "/opt/work/$WS_TEST"                                  # expected: empty (exit 1)
docker exec "$CID_PERSONAL" sh -c "[ -e /opt/work/$WS_TEST ] && echo EXISTS || echo ABSENT"      # expected: ABSENT
# (iv) meaningfulness: personal's volume genuinely exists and is non-empty
docker exec "$CID_PERSONAL" sh -c "ls -A /opt/work/$WS_PERSONAL | head -1"                        # expected: non-empty
```
- **PASS iff** (i) & (iii) are empty **and** (ii) & (iv') both print `ABSENT` **and** (iv) is
  non-empty. (iv) makes the absence meaningful (real data exists, and `ws-test` has no route to
  it) — no canary is written into the live personal volume.

### AC2-2 — Personal credential VALUES absent from `ws-test`'s (runner-reachable) env  [AC seed 2, creds]

```sh
for VAR in $CRED_VARS; do
  PH=$(docker exec "$CID_PERSONAL" sh -c 'printf "%s" "${'"$VAR"':-}" | sha256sum | cut -d" " -f1')
  WH=$(docker exec "$CID_WSTEST"   sh -c 'printf "%s" "${'"$VAR"':-}" | sha256sum | cut -d" " -f1')
  [ "$PH" = "$WH" ] && echo "LEAK:$VAR"          # any output here => FAIL
done
# own-env sub-check: ws-test loaded ITS OWN env file (sentinels), proving the value is not inherited
docker exec "$CID_WSTEST" printenv GIT_TOKEN     # expected: WSTEST-SENTINEL-GIT_TOKEN-$NONCE
```
- **Expected:** the loop prints **nothing** (for every var, personal's hash ≠ ws-test's hash),
  and `printenv GIT_TOKEN` returns the seeded sentinel.
- **PASS iff** no `LEAK:` line is printed **and** `ws-test`'s sentinel vars equal their seeded
  values.
- **Why the host-container env proves the *runner* claim (no runner spawn needed):** the
  host→runner forwarding allowlist (`connect.py:405-441`, Step-2 profile) can only forward
  values the host container holds. A value **absent from the ws-test host container env is
  necessarily absent from any runner ws-test spawns**. Comparing hashes never reveals either
  secret. (The *forwarding mechanism* itself is Step-5 probe (b) — out of scope here.)

### AC2-3 — Commits in `ws-test` carry ws-test git identity, distinct from personal  [AC seed 2, git identity — security boundary]

```sh
docker exec "$CID_WSTEST" git config --global user.email   # expected: ws-test@example.invalid
docker exec "$CID_WSTEST" git config --global user.name    # expected: ws-test bot
# an actual commit's author, in a throwaway repo inside ws-test's OWN volume (cleaned up):
docker exec "$CID_WSTEST" sh -c \
  'd=/opt/work/ws-test/.idcheck; rm -rf "$d"; git init -q "$d" \
   && git -C "$d" commit -q --allow-empty -m t \
   && git -C "$d" log -1 --format="%an <%ae>"; rm -rf "$d"'
   # expected: ws-test bot <ws-test@example.invalid>
# distinct from personal:
docker exec "$CID_PERSONAL" git config --global user.email  # expected: some value != ws-test@example.invalid
```
- **PASS iff** the configured identity and the real commit's author both equal the ws-test
  sentinel identity **and** personal's configured email differs.

### D3-1 — Editor-plane `includeIf` resolves per-workspace identity (deliverable #3)  [AC seed 2, editor plane]

Run in the **code-server / editor user shell on `omni-vps`** (the human plane spanning
`/opt/work/*`; the *convenience* plane — the container plane above is the security boundary):
```sh
# (i) personal directory resolves to personal identity via an includeIf-INCLUDED file
git -C /opt/work/$WS_PERSONAL config --show-origin user.email
#   expected: personal's email, with origin = an included gitconfig (path under the includeIf target),
#             NOT the base ~/.gitconfig
# (ii) the editor ~/.gitconfig contains an includeIf covering ws-test after the runbook
git config --global --get-regexp 'includeif' | grep -i "/opt/work/$WS_TEST"
#   expected: a matching includeIf entry
```
- **PASS iff** (i) resolves personal's email **from an included file** (proving `includeIf` is
  wired, not the base identity) **and** (ii) a `ws-test` `includeIf` entry exists.
- *Note (finding 7):* D3 is tested via personal (guaranteed mounted) + config-presence for
  ws-test, because a brand-new ws dir's reachability in the editor plane depends on infra mount
  steps. The security-boundary identity claim is fully tested by AC2-3.

### AC4-H1 — kb-three-tier clone target derivable from the registry entry ALONE  [AC seed 4]

Read **only** `$REGISTRY` (open no other file — that is the "from the registry entry alone"
semantic). Extract the `ws-test` entry and derive the kb clone target:
```sh
# preferred parser if present: python3 -c 'import yaml,sys; ...'; else grep/awk over the ws-test block.
# Required, non-empty fields in the ws-test entry:
#   name            -> ws-test
#   root path       -> /opt/work/ws-test
#   kb slug         -> matches ^kb-ws-.+   (expected: kb-ws-ws-test)
# Derived clone destination MUST equal /opt/work/ws-test/<kb-dir>, and the repo reference is
# built from the slug alone.
```
- **Expected:** a resolver reading only `$REGISTRY` prints `kb-ws-ws-test -> /opt/work/ws-test/…`
  with **no missing field**.
- **PASS iff** both the kb slug (matching `^kb-ws-.+`) and the root path resolve from the entry
  alone and the destination lands under `/opt/work/ws-test/`.
- *(Optional, non-gating reinforcement):* create a throwaway local git repo as the
  `kb-ws-ws-test` remote, run the **derived** clone into `/opt/work/ws-test/`, assert it lands,
  then remove it. Does **not** affect the verdict.

### AC4-H2 — secrets-manager target derivable from the registry entry ALONE  [AC seed 4]

```sh
# From the ws-test entry in $REGISTRY only:
#   env-file reference  -> a PATH/reference (e.g. /…/ws-test.env or ~/…), NEVER inline values
#   secret-store pointer -> present & non-empty (e.g. keychain:ws-test / env:… / vault:…)
# env-refs-only lint over the WHOLE registry (no inline env-var assignments belong here):
grep -nE '^\s*[A-Z][A-Z0-9_]{2,}=[^ ]+' "$REGISTRY"     # expected: empty (exit 1)
```
- **Expected:** the env-file field is a path/reference, the secret-store pointer is present, and
  the `grep` for inline `NAME=VALUE` env assignments prints **nothing**.
- **PASS iff** both fields resolve as **references** from the entry alone **and** no inline
  env-var assignment exists anywhere in the registry (the spec's "env-refs-only" rule: a real
  credential like `GIT_TOKEN=ghp_…` in the registry would match and FAIL; a YAML pointer such as
  `secret_store: keychain:ws-test` does not).

### AC6 — Validate script fails loudly on a seeded registry/live-state mismatch  [AC seed 6]

Run **after teardown** (registry restored to its committed state, `ws-test` gone).
```sh
# V0: entrypoint discovered and WIRED (from §3): $VALIDATE_FILE resolves AND is referenced in
#     .pre-commit-config.yaml. If not -> deliverable #2 unmet -> AC6 FAIL.
# V1 (baseline pass): consistent registry + live state
$VALIDATE_CMD; echo "exit=$?"                    # expected: exit=0, no error lines
# V2 (seeded mismatch): append a drift entry naming a host that does not exist live
cat >> "$REGISTRY" <<EOF
  - name: ws-ghost-$NONCE
    host_id: host-absent-$NONCE
    owner: test
    root: /opt/work/ws-ghost-$NONCE
    env_file: /nonexistent/ws-ghost-$NONCE.env
EOF
$VALIDATE_CMD; echo "exit=$?"                     # expected: exit!=0 AND output names ws-ghost-$NONCE / host-absent-$NONCE
# V3 (clean restore)
git -C "$REPO" checkout -- "$REGISTRY"
$VALIDATE_CMD; echo "exit=$?"                     # expected: exit=0
git -C "$REPO" status --porcelain "$REGISTRY"     # expected: empty (registry restored)
```
- **PASS iff** V1 exits 0, **V2 exits non-zero AND its output contains the seeded offender id**
  (loud + specific, not a silent non-zero), and V3 exits 0 with a clean `git status`.
- *(The exact YAML shape of the drift entry above must match the registry schema; adjust keys
  to the schema doc at Step 8. The invariant is: an entry whose `host_id` has no live host — and
  a non-existent `env_file` — is genuine drift the validator must catch loudly.)*

---

## 5. Teardown (always run after the checks; restores live state)

```sh
# Remove ONLY ws-test's resources — never touch personal or the server:
docker rm -f "$CID_WSTEST"                                  # or: docker compose ... rm -sf <ws-test service>
docker volume rm "<ws-test named volume>"                  # only ws-test's volume
docker network rm "<ws-test network>"                      # only ws-test's network
git -C "$REPO" checkout -- "$REGISTRY"                      # drop the ws-test registry entry
# remove the ws-test compose stanza + env file from the vps-infra working copy
```
Collateral assertions (teardown must have restarted nothing and restored the registry):
```sh
docker inspect "$(server_cid)" --format '{{.State.StartedAt}} {{.State.Pid}}'      # == SRV_0
docker inspect "$(cid_for_ws "$WS_PERSONAL")" --format '{{.State.StartedAt}} {{.State.Pid}}'  # == PER_0
git -C "$REPO" status --porcelain "$REGISTRY"              # empty
cid_for_ws "$WS_TEST"; echo "rc=$?"                        # rc=1 (container gone)
```
- **PASS iff** server & personal StartedAt/Pid equal their AC1 "BEFORE" values, the registry is
  clean, and `ws-test` no longer resolves.

---

## 6. Verdict rule (binary)

**Mandatory checks** (all must PASS):

`G1`, `AC3-1`, `AC1-a`, `AC1-b`, `AC1-c`, `AC1-d`, `AC1-e`, `AC2-1`, `AC2-2`, `AC2-3`,
`D3-1`, `AC4-H1`, `AC4-H2`, `AC6-V1`, `AC6-V2`, `AC6-V3`, and the §5 teardown-collateral
assertion.

```
verdict = PASS   if every mandatory check PASSES
verdict = FAIL   if any single mandatory check FAILS
verdict = BLOCKED if any precondition PF-1..PF-5 is unmet (report which; not a PASS/FAIL)
```

No partial credit, no judgment calls. **Informational/optional** items — the AC3 broad
credential-shaped sweep, the AC4-H1 live kb clone — are reported for context but **never**
change the verdict.

---

## 7. Findings & assumptions for the pm (flag at Step 5 / resolve by Step-6 seal)

1. **`BASE` baseline must be pinned at seal.** G1 diffs `BASE..HEAD`. The pm must record the
   pre-implementation baseline commit in the Step-6 seal block (default assumption:
   `a9dae275`). Without it, G1 is ambiguous — hard dependency (PF-5).
2. **Stage-2b control-plane enforcement is deliberately NOT tested** (a raw cross-host
   session-create is a documented Stage-1 gap; testing it would fail Stage 1 by design).
   Consistent with human ruling #1 (Stage 1 suffices). Confirm the pm accepts acceptance that
   excludes it.
3. **`web/` in G1:** the spec's architecture text says "zero files under `omnigent/` or `web/`",
   but AC seed #5 names only `omnigent/`. This test treats **both** as mandatory; relax to
   `omnigent/`-only at seal if that is the intended reading.
4. **Validate-entrypoint discovery contract:** AC6 assumes the validator is discoverable (a
   tracked file pairing `validate` + `workspace`/`registry`) **and wired** in
   `.pre-commit-config.yaml` (deliverable #2 = "wired, not manual"). If the `de` names it
   opaquely or leaves it unwired, AC6 fails — correctly. Confirm this contract is acceptable, or
   have the schema doc state the canonical `VALIDATE_CMD` so Step 8 needs no discovery.
5. **Agents-table env-refs lint not gated.** The spec asks the validator to apply the
   env-refs-only rule to the shared `agents` table too; AC seed #6 is specifically the
   *registry/live-state* mismatch, so AC6 gates only that. If the pm wants the agents-table lint
   in the binary verdict, that is a distinct check needing a live DB row — heavier, and I'd add
   it as a separate seeded-inline-secret case.
6. **Runner-level cred absence is proven via host-container env absence** (absence at the
   forwarding source ⇒ absence downstream), avoiding a runner spawn (resource-frugal, matches
   the POC-speed priority). If the pm wants a literal runner-env inspection, that is a heavier
   add requiring a live session launch on `ws-test`.
7. **Editor-plane `includeIf` (D3-1)** is tested via personal + config-presence for `ws-test`,
   because a fresh ws dir's editor-plane reachability depends on infra mount steps; the
   security boundary (container plane) is fully covered by AC2-3.
8. **AC4 tests registry *sufficiency*, not downstream behavior.** kb-three-tier /
   secrets-manager don't exist yet; the binary check is "the registry entry alone yields the
   target." The live kb clone is optional and non-gating.

*End of Step-4 design. `status: draft` — to be sealed at Step 6 (add `sealed_at:`), immutable
thereafter.*
