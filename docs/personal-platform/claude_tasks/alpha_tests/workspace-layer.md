---
type: alpha_test
title: "Workspace layer — kernel-isolation acceptance test (A2′)"
task: "workspace-layer"
status: draft
created: "2026-07-16"
related_decisions: ["workspace-layer.md (spec, rewritten post-council, HEAD f467fc20)", "council/workspace-isolation-amendment.md", "plan.md §Phase 2 (workspace hierarchy — kernel-enforced isolation)"]
---

# Workspace layer — kernel-isolation acceptance test (Step 4 REDO, DRAFT)

> **Bias-control spine.** This test is (re)designed at Step 4 from the **rewritten spec
> alone** (`workspace-layer.md`, HEAD `f467fc20`), before any implementation exists. No
> implementation plan was read. The previous alpha test targeted the abandoned
> "workspace = one `omnigent host` container" design (Docker volumes / container env) and is
> **obsolete** — this file replaces it wholesale. A2′ moves the boundary from *volume mounts*
> to the *OS kernel*: per-workspace Unix users (`ws-<slug>`) inside the single code-server
> container, `600`-owner-only secrets, no in-container root. Every check below is a
> reproducible command with an exact observable and a **binary** (PASS/FAIL) rule — no
> judgment. `status` stays `draft` until Step 6, when the pm **seals** it (adds `sealed_at:`);
> after sealing this file is immutable — a post-seal edge case becomes a new task, never an
> edit here.
>
> **This is a Step-8 test, run against the live VPS AFTER the vps-infra deliverables ship**
> (the uid image layer, the `NOPASSWD` removal, the provisioning script). Running it *today*
> (pre-implementation) is expected to **BLOCK** on preconditions for most checks and
> **FAIL** on the two that are runnable now (C3, and G9's anti-vacuous guard) — that is
> correct: the test predates the code it judges (see §2 and §8).

---

## 0. What a PASS asserts — coverage of the 9 spec acceptance-criteria seeds

| Seed (`workspace-layer.md` §"Acceptance criteria") | Check |
|---|---|
| 1 — Triviality: add ws #2 = provisioning script + registry entry, ≤30 min, no code-server restart, no `omnigent/` change | **C1** (a–e) |
| 2 — Kernel isolation (core win): as `ws-test`, read of `ws-personal`'s `600` secret FAILS + observable; own secret read succeeds | **C2** (own / cross / observable / structural) |
| 3 — No master key: `sudo -n true` as `coder` in-container FAILS (blanket NOPASSWD gone) | **C3** |
| 4 — State isolation: a `claude` under `ws-test`'s `CLAUDE_CONFIG_DIR` cannot see `ws-personal`'s credentials/transcripts | **C4** |
| 5 — Editor still works: `code-server` (as `coder`, group member) browses `640`/`750` code but cannot read `600` secrets | **C5** |
| 6 — Git identity: a commit in `ws-test`'s tree carries `ws-test`'s identity | **C6** |
| 7 — Ecosystem hooks: kb-three-tier clone path + secrets-manager target derivable from the registry entry ALONE | **C7** |
| 8 — Registry validate script fails **loudly** on a seeded registry/live-state mismatch | **C8** (V0–V3) |
| 9 — Fork governance: Stage-1 fork diff shows zero files under `omnigent/` | **G9** |

The alpha test **PASSES iff every mandatory check (§6) passes**. Any single mandatory FAIL →
the whole test **FAILS**. Any unmet hard precondition → **BLOCKED** (not a verdict).
Items explicitly marked *informational* are reported for the pm but never change the verdict.

---

## 1. Out of scope (this test does NOT cover — and why)

- **Stage 2a — workspace switcher UI** (VS Code extension, then web). Successor task, kept out
  of Stage 1 by human ruling. Not tested.
- **Stage 2b — human-terminal-path hardening.** The spec is explicit ("**Honest scope:** A2′
  hardens the *agent* path. The *human-terminal* path stays convention-enforced"). A user may
  select a non-default terminal profile and get a `coder` shell in a workspace folder. This
  test **deliberately does not attempt to prove the human-terminal path is bounded** — doing
  so would fail Stage 1 by design. What it *does* prove is that even that `coder` shell cannot
  read a workspace's `600` secrets (C5), which is the real residual guarantee.
- **Stage 3 — activating the `workspace_id` partition** on the (stopped) Omnigent server. Not
  built; G9 in fact asserts the seam was **not touched** (`workspace_id` is only *reserved* as
  a registry integer).
- **A1 — dedicated code-server instance escalation.** Design-only in Stage 1; nothing to run.
- **Data-at-rest gate.** A binding governance gate before the *first client*; no client is
  onboarded here, so nothing to test.
- **The Omnigent server "stop-but-preserve".** A vps-infra deliverable but **not one of the 9
  seeds**; not gated here (an informational note is offered in §7, finding 8).
- **The `claudeProcessWrapper` end-to-end drive** (pty/extension path). C2 proves the *kernel
  boundary at the uid level* the wrapper must land an agent inside; driving the wrapper itself
  needs a live `claude` login/API and the extension pty, against the POC-frugal + "no API
  calls" guidance. Covered as *informational* + finding 2. The wrapper's unit correctness is
  the `de`'s own fork test harness (a separate deliverable).
- **Downstream consumer behavior.** C7 tests that the registry entry is *sufficient* for
  kb-three-tier / secrets-manager to derive their targets; it does not test those (unbuilt)
  tasks' behavior.

---

## 2. Preconditions & pre-flight gate

All `docker …`, `id`, `stat`, `auditctl`, `ausearch` commands run in a shell **on `omni-vps`**
(CLAUDE.md §13; the operator is the host/root plane — the vps-infra "master key"; prefix
`sudo` if not in the `docker` group). The fork checkout at `$REPO` is inspected on whichever
box holds it (this dev container, or `/opt/omnigent` on the VPS). Report **BLOCKED —
precondition PF-n unmet** (not PASS/FAIL) if any hard PF fails.

- **PF-1** `omni-vps` reachable; `docker ps` returns without error.
- **PF-2** The **single code-server container** is running and discoverable (`$CS` resolves, §3).
- **PF-3 (hard — new architecture).** `ws-personal` has been **migrated to A2′**: the Unix
  user `ws-personal` resolves inside `$CS` (`docker exec -u root "$CS" id ws-personal`), its
  tree is owned `ws-personal:coder` with the `750`/`640`/`600` layout, and **at least one
  `600` file owned by `ws-personal` exists** (the C2 cross-read target — guaranteed by the
  spec's required per-workspace login, else nominated per §3). If personal is not yet
  migrated, C2/C4/C5 have no counterpart workspace → **BLOCKED** (finding 3).
- **PF-4 (hard).** The **uid image layer is deployed** — `$CS` provides the user-creation
  capability the provisioning script needs (`docker exec -u root "$CS" command -v useradd`
  resolves) so adding `ws-test` needs **no image rebuild / container restart** (this is what
  makes C1's "no restart" achievable).
- **PF-5 (hard).** The fork holds the Stage-1 product-layer deliverables: exactly one tracked
  `workspaces.yaml` (`$REGISTRY`, §3), a **wired** validate entrypoint (`$VALIDATE_CMD`,
  referenced in `.pre-commit-config.yaml`), the escalation-stages doc, and the
  second-workspace runbook. The deployed **provisioning script** (vps-infra) is invocable.
- **PF-6 (hard).** The pm recorded, at Step-6 seal, the **`BASE`** pre-implementation baseline
  commit for G9 (default assumption: `f467fc20`, this spec's HEAD). Absent that, G9 is
  ambiguous (finding 4).
- **PF-7 (conditional — grades only the auditd sub-observable in C2).** A host audit rule
  covering the workspace trees exists (`auditctl -l` shows a watch/syscall rule). If absent,
  C2's *auditd* sub-observable is **N/A** (the EACCES errno remains the graded observable) —
  see finding 1. This PF never blocks the verdict.

**Pre-implementation reality (design time, 2026-07-16):** PF-3, PF-4, PF-5 are **unmet** (no
uid layer, no provisioning script, personal not migrated, no registry). So running this test
today BLOCKs. The two exceptions — C3 and G9(a) — are runnable now and **expected to FAIL**
(§8). This is the intended state of a pre-committed acceptance test.

---

## 3. Fixtures, sentinels & discovery helpers (nothing here reads or prints a secret value)

```sh
# ---- paths / targets ----
REPO=/home/coder/repos/omnigent      # the fork clone (adjust to /opt/omnigent on the VPS)
WS_PERSONAL=personal                 # workspace #1 slug (confirm against the registry)
WS_TEST=ws-test                      # disposable workspace #2, created & torn down by this test
NONCE=$(date +%s)                    # one nonce per run; makes every sentinel globally unique

# ---- ws-test git-identity sentinels (fixtures defined NOW, at Step 4; not real values) ----
WSTEST_GIT_NAME="ws-test bot"
WSTEST_GIT_EMAIL="ws-test@example.invalid"

# ---- registry: exactly one tracked file named workspaces.yaml ----
REGISTRY="$REPO/$(git -C "$REPO" ls-files | grep -E '(^|/)workspaces\.yaml$')"
# PASS precondition (PF-5): exactly one match. Zero => deliverable missing; >1 => ambiguous SSOT.

# ---- the single code-server container (confirm against the vps-infra compose service name) ----
CS=$(docker ps --format '{{.ID}} {{.Image}} {{.Names}}' | grep -iE 'code-?server' | awk '{print $1}' | head -1)

# ---- read a field from the registry entry, reading ONLY $REGISTRY (the "from the entry alone" semantic) ----
# Registry field names per spec §"The registry": slug, unix_user, root, git.{name,email},
# config_dir, kb_repo, secret_store, workspace_id, projects[]. Top-level shape (list vs
# {workspaces:[...]}) is confirmed against the schema doc at Step 8.
ws_field() { REG="$REGISTRY" SLUG="$1" FIELD="$2" python3 - <<'PY'
import os, sys, yaml
reg = yaml.safe_load(open(os.environ["REG"]))
rows = reg.get("workspaces", reg) if isinstance(reg, dict) else reg
hit = [w for w in rows if w.get("slug")==os.environ["SLUG"] or w.get("unix_user") in (os.environ["SLUG"], "ws-"+os.environ["SLUG"])]
if not hit: sys.exit(3)
cur = hit[0]
for k in os.environ["FIELD"].split("."):
    cur = cur.get(k) if isinstance(cur, dict) else None
print(cur if cur is not None else "")
PY
}
WSTEST_ROOT=$(ws_field "$WS_TEST" root)          # e.g. /opt/work/ws-test  (resolved from the registry)
PERSONAL_ROOT=$(ws_field "$WS_PERSONAL" root)    # e.g. /opt/work/personal
PERSONAL_CFGDIR=$(ws_field "$WS_PERSONAL" config_dir)

# ---- C2 cross-read target: a 600 file OWNED BY ws-personal (metadata-only discovery as root) ----
# Prefer the spec-named credential; else discover any 600 ws-personal-owned file. `find`/`stat`
# read METADATA only (paths, owner, mode) — never file contents.
PERSONAL_SECRET="$PERSONAL_CFGDIR/.credentials.json"
docker exec -u root "$CS" test -f "$PERSONAL_SECRET" || \
  PERSONAL_SECRET=$(docker exec -u root "$CS" sh -c \
    "find '$PERSONAL_ROOT' -xdev -type f -user ws-personal -perm -600 ! -perm /077 2>/dev/null | head -1")

# ---- ws-test fixtures (placed by root at Step 8 with the spec's CANONICAL modes; torn down in §5) ----
#   <WSTEST_ROOT>/sample.code          owner ws-test  group coder  mode 640   (a "code" file)
#   <WSTEST_ROOT>/.secrets/own.sentinel owner ws-test group coder  mode 600   ("WSTEST-OWN-SECRET-$NONCE")
# These exercise the 640/600 permission model deterministically; the value is a chosen sentinel,
# never a real secret, and is never printed (every read below discards content to /dev/null).
```

Two mechanisms establish "run **as** a given Unix user", both uid-faithful:
- `docker exec -u <user> "$CS" <cmd>` — the daemon sets the process's uid directly. Used for
  the kernel-boundary observations (the kernel judges by uid, not by how it was acquired).
- `docker exec -u root "$CS" …` — the **host/root operator** (the vps-infra master key), used
  **only** for test orchestration and *metadata* inspection (discovering a target path,
  `stat`, placing fixtures). This never reads a secret's contents and never contradicts C3
  (C3 concerns `coder`'s in-container sudo, not the host operator).

---

## 4. Checks

**Execution order (dependencies):** `G9 → C3 → C1 (creates ws-test) → C2 / C4 / C5 / C6 / C7
(with ws-test live) → teardown (§5, removes ws-test, restores registry) → C8 (on the restored
registry)`.

---

### G9 — Fork governance: zero files under `omnigent/` in the Stage-1 change set  [seed 9]

**Runs as:** host operator, on the fork checkout (no container).
```sh
# (a) forbidden surface untouched
git -C "$REPO" diff --name-only "$BASE" HEAD | grep -E '^(omnigent|web)/'
# (b) anti-vacuous guard: the product-layer artifacts were actually delivered
git -C "$REPO" diff --name-only "$BASE" HEAD | grep -E '(^|/)workspaces\.yaml$'
git -C "$REPO" diff --name-only "$BASE" HEAD | grep -Ei 'escalation|runbook'
```
- **Expected:** (a) prints nothing (exit 1); (b) both greps print ≥1 path.
- **PASS iff** (a) is empty **and** both (b) greps are non-empty.
- Subsumes the scope guard "no touching the dormant `workspace_id` column": any
  `db_models`/migration edit lives under `omnigent/` and would fail (a).
- **Infra dependency / pre-impl:** none (fork-only). **Runnable today; expected-FAIL now** —
  (b) fails because the artifacts are not yet built (finding 4 for the `web/` scope nuance).

---

### C3 — No master key: `coder` has no blanket root inside the container  [seed 3]

**Runs as:** `coder` (the code-server user), inside `$CS`.
```sh
docker exec -u coder "$CS" sudo -n true; echo "rc=$?"     # expected: rc != 0 (sudo denied)
# and the blanket rule is gone from what coder is allowed to run:
docker exec -u coder "$CS" sudo -n -l 2>&1 | grep -E '\(ALL(\s*:\s*ALL)?\)\s+NOPASSWD:\s*ALL'
#   expected: empty (exit 1) — no "(ALL) NOPASSWD: ALL"
# (informational) the narrow per-workspace rule the wrapper relies on may appear, e.g.
#   "(ws-test) NOPASSWD: <claude path>" — recorded, not gated here.
docker exec -u coder "$CS" sudo -n -l 2>&1 | grep -Ei 'ws-[a-z0-9-]+.*NOPASSWD'   # informational
```
- **PASS iff** `sudo -n true` exits non-zero **and** no `(ALL) NOPASSWD: ALL` line is present.
- **Infra dependency / pre-impl:** needs the vps-infra **`NOPASSWD` removal**. **Runnable
  today; expected-FAIL now** — per the Step-2 state, `coder` still holds
  `ALL=(ALL) NOPASSWD:ALL`, so `sudo -n true` succeeds today → this check FAILs
  pre-implementation and PASSes only once A2′ ships. This is correct for an alpha test.

---

### C1 — Second-workspace triviality (timed provisioning of `ws-test`)  [seed 1]

**Runs as:** host operator (invokes the provisioning script + edits the fork registry).
```sh
# --- capture invariants BEFORE ---
CS_0=$(docker inspect "$CS" --format '{{.State.StartedAt}} {{.State.Pid}}')
NCS_0=$(docker ps --format '{{.Image}}' | grep -icE 'code-?server')     # code-server container count (expect 1)
T0=$(date +%s)
```
Execute **only** the runbook (deliverable "second-workspace runbook") to add `ws-test`. The
timer brackets the mechanical procedure only (exclude time reading the runbook):
1. Run the provisioning script for `ws-test` (vps-infra; run by the host/root operator): it
   creates uid `ws-test` (`useradd`, no container restart), creates+chowns the tree
   (`ws-test:coder`, dirs `750` `g+s`, code `640`, secrets `600`), installs the **narrow**
   sudoers rule, sets `CLAUDE_CONFIG_DIR=<WSTEST_ROOT>/.claude` (owned `ws-test`, `700`),
   configures the git identity/`includeIf`, and the terminal profile.
2. Add a `ws-test` entry to `$REGISTRY` (fork): `slug: ws-test`, `unix_user: ws-test`, `root`,
   `git.name/email` = the sentinels, `config_dir`, `kb_repo: kb-ws-ws-test`, `secret_store`
   (a **reference**, never inline), reserved `workspace_id`, ≥1 `projects[]` entry (repo URL +
   default branch).
```sh
# --- capture AFTER ---
T1=$(date +%s); ELAPSED=$((T1 - T0))
CS_1=$(docker inspect "$CS" --format '{{.State.StartedAt}} {{.State.Pid}}')
NCS_1=$(docker ps --format '{{.Image}}' | grep -icE 'code-?server')
WSTEST_ROOT=$(ws_field "$WS_TEST" root)   # re-resolve now that the entry exists
```
- **C1-a** `[ "$ELAPSED" -le 1800 ]` — the mechanical procedure ≤ 30 minutes.
- **C1-b** `[ "$CS_1" = "$CS_0" ]` — code-server **not** restarted (StartedAt & Pid unchanged).
- **C1-c** `[ "$NCS_1" = "$NCS_0" ]` — no **new** code-server container spawned (still one);
  and `ws-personal` undisturbed: `docker exec -u root "$CS" id ws-personal` still resolves.
- **C1-d** no code change under `omnigent/` during the procedure, and the registry did change:
  ```sh
  git -C "$REPO" status --porcelain | grep -E ' (omnigent|web)/'        # expected: empty (exit 1)
  git -C "$REPO" status --porcelain | grep -E '(^|/)workspaces\.yaml$'  # expected: non-empty
  ```
- **C1-e** `ws-test` exists and is registered as a live Unix user with the correct tree owner:
  ```sh
  docker exec -u root "$CS" id ws-test                                  # expected: uid=… ws-test resolves
  docker exec -u root "$CS" stat -c '%U:%G %a' "$WSTEST_ROOT"           # expected: ws-test:coder 750
  ```
- **PASS iff** C1-a…-e all hold.
- **Infra dependency / pre-impl:** the provisioning script (PF-4/PF-5) + uid layer. **BLOCKED
  pre-implementation** (no provisioning script exists yet).

**Fixture placement (excluded from the C1 timer; root, canonical modes):** place the two
ws-test fixtures for C2/C5, then confirm modes.
```sh
docker exec -u root "$CS" sh -c '
  set -e
  mkdir -p "'"$WSTEST_ROOT"'/.secrets" && chmod 750 "'"$WSTEST_ROOT"'/.secrets"
  printf "code sample"                      > "'"$WSTEST_ROOT"'/sample.code"
  printf "WSTEST-OWN-SECRET-'"$NONCE"'"      > "'"$WSTEST_ROOT"'/.secrets/own.sentinel"
  chown ws-test:coder "'"$WSTEST_ROOT"'/sample.code" "'"$WSTEST_ROOT"'/.secrets" "'"$WSTEST_ROOT"'/.secrets/own.sentinel"
  chmod 640 "'"$WSTEST_ROOT"'/sample.code"
  chmod 600 "'"$WSTEST_ROOT"'/.secrets/own.sentinel"
'
```

---

### C2 — Kernel isolation: the core win  [seed 2]

The centerpiece. Three parts; **no secret value is ever printed** — every read discards
content to `/dev/null` and only the exit code / errno string is inspected.

**C2-own — as `ws-test`, reading `ws-test`'s OWN `600` secret SUCCEEDS.**
**Runs as:** `ws-test`.
```sh
docker exec -u ws-test "$CS" sh -c 'cat "'"$WSTEST_ROOT"'/.secrets/own.sentinel" >/dev/null 2>&1; echo "rc=$?"'
#   expected: rc=0  (the owner can read its own secret — proves the uid was genuinely acquired,
#             i.e. the process is ws-test and not coder/nobody)
```

**C2-cross — as `ws-test`, reading `ws-personal`'s `600` secret FAILS with permission-denied.**
**Runs as:** `ws-test`.
```sh
# metadata-only confirmation the target is a real ws-personal-owned owner-only file (root; no content):
docker exec -u root "$CS" stat -c '%U %a' "$PERSONAL_SECRET"        # expected: ws-personal 600
# the denied read, as ws-test:
docker exec -u ws-test "$CS" sh -c '
  cat "'"$PERSONAL_SECRET"'" >/dev/null 2>/tmp/c2.$$ ; rc=$?
  echo "rc=$rc"
  grep -qi "permission denied" /tmp/c2.$$ && echo "OBSERVABLE=EACCES"
  rm -f /tmp/c2.$$'
#   expected: rc != 0  AND  a line "OBSERVABLE=EACCES"
```

**C2-observable — where the denial is read.** The **kernel permission-denied itself is the
errno `EACCES` (13)** returned to the caller, surfaced above as (i) the non-zero exit and (ii)
the `"… Permission denied"` string on the reader's stderr. That is the guaranteed, graded
observable. **Note (finding 1):** a routine *DAC* denial is **not** written to `dmesg`/the
kernel ring buffer, and is **not** logged by auditd **unless** a host audit rule exists.
Where you would read the *logged* denial, if PF-7's rule is present:
```sh
# host-side, only meaningful if `auditctl -l` shows a watch/syscall rule covering the tree:
ausearch -f "$PERSONAL_SECRET" -ts recent 2>/dev/null | grep -E 'exit=-13|res=(no|0)'   # informational
```
This auditd line is **informational** (PF-7-conditional): the council's "denied+logged …
emitted for free" is inaccurate for DAC (finding 1); the errno is the observable this test
grades.

**C2-struct — the file-layout backing the boundary is actually applied.**
**Runs as:** host operator (metadata only).
```sh
docker exec -u root "$CS" stat -c '%U:%G %a' "$WSTEST_ROOT/.secrets/own.sentinel"   # expected: ws-test:coder 600
docker exec -u root "$CS" stat -c '%U:%G %a' "$WSTEST_ROOT/sample.code"             # expected: ws-test:coder 640
docker exec -u root "$CS" stat -c '%U:%G %a' "$WSTEST_ROOT"                         # expected: ws-test:coder 750
```

- **PASS iff** C2-own `rc=0` **and** C2-cross `rc!=0` with `OBSERVABLE=EACCES` **and** C2-struct
  shows owner `ws-test`, group `coder`, modes `600`/`640`/`750` as listed.
- **Informational (not gated):** cross-workspace *code* readability — `docker exec -u ws-test
  "$CS" sh -c 'cat "$PERSONAL_ROOT"/<any 640 file> >/dev/null 2>&1; echo $?'`. If this reads
  `0`, `ws-test` is a member of group `coder` and isolation is secrets-only (not code); if it
  denies, code is isolated too. A valuable signal for the pm; the seed only requires the
  **secret** boundary, which C2-cross gates.
- **Infra dependency / pre-impl:** the uid layer + provisioning + PF-3 (personal migrated).
  **BLOCKED pre-implementation.**

---

### C4 — State isolation: `ws-test`'s `CLAUDE_CONFIG_DIR` cannot see `ws-personal`'s state  [seed 4]

Non-destructive; no API call. The kernel already forbids `ws-test` from reading
`ws-personal`'s config dir; C4 additionally proves the **config-dir relocation** put ws-test on
its own isolated base.
```sh
WSTEST_CFGDIR=$(ws_field "$WS_TEST" config_dir)      # runs as: host operator (registry read)
# (a) the registry places ws-test's config dir UNDER ws-test's own root (not a shared ~/.claude):
case "$WSTEST_CFGDIR" in "$WSTEST_ROOT"/*) echo "UNDER_ROOT" ;; *) echo "OUTSIDE_ROOT" ;; esac   # expected: UNDER_ROOT
# (b) that dir exists, owned by ws-test, private (700):   runs as: host operator (metadata)
docker exec -u root "$CS" stat -c '%U %a' "$WSTEST_CFGDIR"          # expected: ws-test 700
# (c) ws-personal's credential is NOT present inside ws-test's config dir:   runs as: ws-test
docker exec -u ws-test "$CS" sh -c '[ -e "'"$WSTEST_CFGDIR"'/.credentials.json" ] && echo PRESENT || echo ABSENT_OR_OWN'
#   expected: ABSENT_OR_OWN  (a scratch/own dir has no inherited global credential)
# (d) ws-personal's credential is unreadable from ws-test (kernel):   runs as: ws-test
docker exec -u ws-test "$CS" sh -c 'cat "'"$PERSONAL_CFGDIR"'/.credentials.json" >/dev/null 2>&1; echo "rc=$?"'
#   expected: rc != 0
# (e) INFORMATIONAL — the spec's own observable ("a scratch dir reports Not logged in"), no API:
docker exec -u ws-test -e CLAUDE_CONFIG_DIR="$WSTEST_CFGDIR" "$CS" sh -lc \
  'claude --version >/dev/null 2>&1 && (claude auth status 2>/dev/null || claude whoami 2>/dev/null) || true'
#   informational: expected to report ws-test / "Not logged in", never ws-personal. Exact
#   read-only status subcommand resolved at Step 8; not gated (no local status cmd => rely on a–d).
```
- **PASS iff** (a) `UNDER_ROOT`, (b) `ws-test 700`, (c) `ABSENT_OR_OWN`, (d) `rc!=0`.
- **Infra dependency / pre-impl:** provisioning (config-dir relocation) + PF-3. **BLOCKED
  pre-implementation.**

---

### C5 — Editor still works: `coder` browses `640`/`750` code, cannot read `600` secrets  [seed 5]

A group-permission check. **Runs as:** `coder` (the code-server user).
```sh
# (a) coder can traverse the workspace dir (group r-x via 750):
docker exec -u coder "$CS" sh -c 'ls "'"$WSTEST_ROOT"'" >/dev/null 2>&1; echo "rc=$?"'          # expected: rc=0
# (b) coder can read a 640 code file (group r):
docker exec -u coder "$CS" sh -c 'cat "'"$WSTEST_ROOT"'/sample.code" >/dev/null 2>&1; echo "rc=$?"'  # expected: rc=0
# (c) coder CANNOT read a 600 secret (group has no bits):
docker exec -u coder "$CS" sh -c 'cat "'"$WSTEST_ROOT"'/.secrets/own.sentinel" >/dev/null 2>/tmp/c5.$$; echo "rc=$?"; grep -qi "permission denied" /tmp/c5.$$ && echo DENIED; rm -f /tmp/c5.$$'
#   expected: rc != 0  AND  DENIED
# (d) editor keeps working on AGENT-CREATED files: a file ws-test creates in its setgid tree
#     must inherit group coder so code-server can read it (else the editor breaks on new files):
docker exec -u ws-test "$CS" sh -c 'umask 027; printf x > "'"$WSTEST_ROOT"'/created_by_ws.code"'   # runs as: ws-test
docker exec -u root  "$CS" stat -c '%G %a' "$WSTEST_ROOT/created_by_ws.code"                        # expected: coder 640
docker exec -u coder "$CS" sh -c 'cat "'"$WSTEST_ROOT"'/created_by_ws.code" >/dev/null 2>&1; echo "rc=$?"'  # expected: rc=0
```
- **PASS iff** (a) `rc=0`, (b) `rc=0`, (c) `rc!=0` + `DENIED`, (d) new file is group `coder`
  and `coder` reads it (`rc=0`).
- **Infra dependency / pre-impl:** the file-layout (owner/group/mode + setgid) from
  provisioning. **BLOCKED pre-implementation.** (d) additionally proves setgid, not just
  primary-group, is how group `coder` is achieved — the design must not make `ws-test`'s
  *primary* group `coder`, which would break C2's cross-workspace code isolation (finding 5).

---

### C6 — Git identity: a commit in `ws-test`'s tree carries `ws-test`'s identity  [seed 6]

**Runs as:** `ws-test` (the agent's uid), inside `$CS`.
```sh
# effective identity as resolved in ws-test's tree (covers per-uid [user] OR includeIf):
docker exec -u ws-test "$CS" git -C "$WSTEST_ROOT" config user.email   # expected: ws-test@example.invalid
docker exec -u ws-test "$CS" git -C "$WSTEST_ROOT" config user.name    # expected: ws-test bot
# a real commit's author, in a throwaway repo inside ws-test's OWN tree (cleaned up):
docker exec -u ws-test "$CS" sh -c '
  d="'"$WSTEST_ROOT"'/.idcheck"; rm -rf "$d"; git init -q "$d" \
  && git -C "$d" commit -q --allow-empty -m t \
  && git -C "$d" log -1 --format="%an <%ae>"; rm -rf "$d"'
#   expected: ws-test bot <ws-test@example.invalid>
# distinct from personal:
docker exec -u ws-personal "$CS" git -C "$PERSONAL_ROOT" config user.email   # expected: a value != ws-test@example.invalid
```
- **PASS iff** the configured identity **and** the real commit author both equal the ws-test
  sentinel identity **and** personal's resolved email differs.
- **Infra dependency / pre-impl:** the per-workspace git identity / `includeIf` (fork,
  applied host-side) + provisioning. **BLOCKED pre-implementation.**

---

### C7 — Ecosystem hooks: targets derivable from the registry entry ALONE  [seed 7]

**Runs as:** host operator. Read **only** `$REGISTRY` (open no other file — that is the "from
the registry entry alone" semantic).
```sh
# kb-three-tier clone target, from the ws-test entry alone:
KB=$(ws_field "$WS_TEST" kb_repo)                       # expected: matches ^kb-ws-.+  (e.g. kb-ws-ws-test)
ROOT=$(ws_field "$WS_TEST" root)                        # expected: non-empty (clone lands under here)
echo "$KB" | grep -qE '^kb-ws-.+' && [ -n "$ROOT" ] && echo "KB_DERIVED=$KB -> $ROOT/"
# secrets-manager target, from the ws-test entry alone — a REFERENCE, never an inline value:
SS=$(ws_field "$WS_TEST" secret_store)                  # expected: non-empty pointer (keychain:… / vault:… / a path)
[ -n "$SS" ] && echo "SECRET_STORE=$SS"
# env-refs-only lint over the WHOLE registry (no inline NAME=VALUE credential belongs here):
grep -nE '^\s*[A-Z][A-Z0-9_]{2,}=[^ ]+' "$REGISTRY"     # expected: empty (exit 1)
```
- **PASS iff** `kb_repo` matches `^kb-ws-.+` and `root` is non-empty (kb target derivable);
  `secret_store` is a non-empty **reference**; **and** the inline-assignment grep is empty
  (a real credential like `GIT_TOKEN=ghp_…` in the registry would match and FAIL; a pointer
  like `secret_store: keychain:ws-test` does not).
- **Infra dependency / pre-impl:** the registry file + the ws-test entry (from C1). **BLOCKED
  pre-implementation** (no registry). *Note:* C7 also runs against the permanent `ws-personal`
  entry once the registry exists — the ws-test entry is used here for a single consistent flow.

---

### C8 — Registry validate script fails loudly on a seeded mismatch  [seed 8]

**Runs as:** host operator, on the fork checkout. Run **after teardown** (registry restored,
`ws-test` gone). `$VALIDATE_CMD` = the invocation of the tracked validator (resolved at Step 8
from the schema doc / the pre-commit hook entry).
```sh
# V0 — entrypoint discovered AND wired (PF-5): a tracked validator pairing validate+registry/workspace,
#      referenced in .pre-commit-config.yaml. If not => deliverable unmet => C8 FAIL.
git -C "$REPO" ls-files | grep -iE 'validate.*(workspace|registry)|(workspace|registry).*validate'   # expected: ≥1
grep -qiE 'workspace|registry|validate' "$REPO/.pre-commit-config.yaml"; echo "wired=$?"              # expected: wired=0
# V1 — baseline pass: consistent registry + live state
$VALIDATE_CMD; echo "exit=$?"                            # expected: exit=0, no error lines
# V2 — seeded mismatch: a registry entry naming a Unix user / root that do not exist live
cat >> "$REGISTRY" <<EOF
  - slug: ws-ghost-$NONCE
    unix_user: ws-ghost-$NONCE
    root: /opt/work/ws-ghost-$NONCE
    config_dir: /opt/work/ws-ghost-$NONCE/.claude
    secret_store: keychain:ws-ghost-$NONCE
EOF
$VALIDATE_CMD; echo "exit=$?"                            # expected: exit != 0 AND output names ws-ghost-$NONCE
# V3 — clean restore
git -C "$REPO" checkout -- "$REGISTRY"
$VALIDATE_CMD; echo "exit=$?"                            # expected: exit=0
git -C "$REPO" status --porcelain "$REGISTRY"            # expected: empty (registry restored)
```
- **PASS iff** V0 finds a wired validator, V1 exits 0, **V2 exits non-zero AND its output
  contains the seeded offender `ws-ghost-$NONCE`** (loud + specific, not a silent non-zero),
  and V3 exits 0 with a clean `git status`.
- **Infra dependency / pre-impl:** the validate script + wiring (fork). **BLOCKED
  pre-implementation.** *The seeded YAML keys are adjusted to the schema doc at Step 8; the
  invariant is: an entry whose `unix_user`/`root` has no live counterpart is genuine drift the
  validator must catch loudly.* (finding 6: agents-table env-refs lint is a distinct check, not
  gated here.)

---

## 5. Teardown (always run after the checks — restores live state, zero collateral)

**Runs as:** host operator (the master key; deprovisioning is a root, host-side action).
```sh
WSTEST_ROOT=$(ws_field "$WS_TEST" root)
# Remove ONLY ws-test's resources — never touch ws-personal, coder, or the container itself:
docker exec -u root "$CS" sh -c 'pkill -u ws-test 2>/dev/null; userdel ws-test 2>/dev/null || true'   # remove the uid
docker exec -u root "$CS" sh -c 'rm -rf "'"$WSTEST_ROOT"'"'                                            # remove ws-test's tree (+ fixtures)
# remove the ws-test narrow sudoers rule + terminal profile (the provisioning script's reverse step)
git -C "$REPO" checkout -- "$REGISTRY"                                                                 # drop the ws-test registry entry
```
Collateral assertions (teardown must have restarted nothing and restored everything):
```sh
docker inspect "$CS" --format '{{.State.StartedAt}} {{.State.Pid}}'          # == CS_0 (never restarted)
docker exec -u root "$CS" id ws-personal                                     # still resolves (personal intact)
docker exec -u root "$CS" stat -c '%U:%G %a' "$PERSONAL_ROOT"                # unchanged (ws-personal:coder 750)
docker exec -u root "$CS" id ws-test 2>&1 | grep -q 'no such user' && echo "WSTEST_GONE"   # expected: WSTEST_GONE
git -C "$REPO" status --porcelain "$REGISTRY"                                # empty (registry restored)
```
- **PASS iff** `$CS` StartedAt/Pid equal their C1 "BEFORE" values, `ws-personal` still resolves
  with its tree intact, `ws-test` no longer resolves, and the registry is clean.

---

## 6. Verdict rule (binary)

**Mandatory checks** (every one must PASS):

`G9`, `C3`, `C1-a`, `C1-b`, `C1-c`, `C1-d`, `C1-e`, `C2-own`, `C2-cross`, `C2-struct`, `C4`,
`C5` (a–d), `C6`, `C7`, `C8` (V0–V3), and the **§5 teardown-collateral** assertion.

```
verdict = PASS    if every mandatory check PASSES
verdict = FAIL    if any single mandatory check FAILS
verdict = BLOCKED if any hard precondition PF-1..PF-6 is unmet (report which; not a PASS/FAIL)
```

No partial credit, no judgment calls. **Informational** items — C2's auditd sub-observable
(PF-7-conditional), the C2 cross-workspace *code* probe, C3's narrow-rule listing, C4(e)'s
`claude` status, the `claudeProcessWrapper` end-to-end drive — are reported for context and
**never** change the verdict.

---

## 7. Findings & assumptions for the pm (flag at Step 5 / resolve by Step-6 seal)

1. **The "logged/observable denial" sub-claim of seed 2 is not free — and, as written, partly
   untestable.** The council says a blocked read "raises a kernel permission-denied … emitted
   for free as a side effect of blocking" and the spec says "denied+**logged**". For pure
   **DAC** (Unix file permissions, which A2′ uses), a denied `open()` returns `EACCES` **to the
   caller only** — it is **not** written to `dmesg`/the kernel ring buffer and **not** recorded
   by auditd **unless a host audit rule exists** (none is in the vps-infra deliverables list).
   This test therefore grades the observable as the **`EACCES` errno** (guaranteed, uid-faithful)
   and flags the *logged*-denial claim as untestable without an added deliverable. **Decision
   needed:** either (a) add a host **auditd rule** (`auditctl -w <tree> -p r -k ws_denied`, or a
   syscall rule filtering `exit=-EACCES`) to the vps-infra deliverables so the denial is
   genuinely logged and readable via `ausearch` (then PF-7 becomes a hard precondition and the
   auditd sub-check is promoted to mandatory), or (b) accept the errno as the observable and
   correct the spec/council wording from "logged" to "returns a kernel permission-denied
   (EACCES) to the caller". This is the single genuinely-untestable seed sub-claim.

2. **The `claudeProcessWrapper` is not driven end-to-end here.** C2 proves the *kernel boundary
   at the uid level* (`docker exec -u ws-test`) — the property the wrapper must land an agent
   inside. Driving the actual wrapper needs a live `claude` login/API + the extension pty
   (against the POC-frugal + "no API calls" guidance) and would judge the `de`'s own code with
   the `de`'s own harness (circular). **Recommendation:** have the wrapper ship with an
   observable **`--resolve-only`/dry-run** mode that prints the resolved `ws-<slug>` (or effective
   uid) without launching a session; a future check can then assert the drop non-circularly.
   Meanwhile the wrapper's unit correctness is the `de`'s fork test harness, and C2 guarantees
   the boundary any correct drop inherits. Confirm the pm accepts acceptance that gates the
   boundary (C2) but not the wrapper drive.

3. **`ws-personal` must be migrated to A2′ before Step 8 (PF-3).** C2/C4/C5 need a *second*
   real workspace under the kernel model to be the cross-read counterpart. The spec's Scope
   says "Personal becomes workspace #1 under A2′", so this is in Stage-1 scope — but if the pm
   intends to defer personal's migration, C2/C4/C5 are BLOCKED and the "core win" is unproven.
   Confirm personal migration is part of the Step-7 build.

4. **`BASE` baseline must be pinned at seal (PF-6), and the `web/` scope confirmed.** G9 diffs
   `BASE..HEAD`; the pm records the pre-implementation commit in the Step-6 seal block (default
   `f467fc20`). Seed 9 names only `omnigent/`, but the spec's out-of-scope section says "no
   `omnigent/` or `web/` changes" — this test gates **both**. Relax G9(a) to `omnigent/`-only
   at seal if that is the intended reading.

5. **Group `coder` must come from setgid dirs, not from `ws-*`'s primary group.** C5(d) checks
   that a file *created by* `ws-test` inherits group `coder` (so the editor keeps working on
   agent-created files). The only design that satisfies this **without** breaking C2's
   cross-workspace isolation is a setgid (`g+s`) tree group-owned by `coder`, with `ws-*` users
   **not** members of group `coder`. If provisioning instead makes `coder` a `ws-*` user's
   *primary* group, C5(d) passes but `ws-test` gains group-read of `ws-personal`'s `640` code
   (surfaced by C2's informational cross-code probe). Flagging so the `de` picks setgid.

6. **Agents-table env-refs lint is not gated.** Seed 8 is specifically the *registry/live-state*
   mismatch, so C8 gates that. If the pm also wants the env-refs-only rule enforced on a shared
   `agents` table, that is a distinct seeded-inline-secret case needing a live row — heavier;
   I would add it as a separate check on request.

7. **Container-plane discovery names must be confirmed at Step 8.** `$CS` (single code-server
   container), `$VALIDATE_CMD`, the registry top-level shape, and `PERSONAL_SECRET`'s canonical
   path are resolved against the vps-infra compose service name + the fork's schema doc at run
   time. None changes the logic; each is a name-binding step noted inline.

8. **Omnigent server "stop-but-preserve" is not gated** (not among the 9 seeds). If the pm wants
   assurance the injected-agent liability at `127.0.0.1:8000` is closed, an informational check
   `docker compose … ps` showing the omnigent+postgres services `Exited`/stopped can be added —
   reported, not gated.

*End of Step-4 (redo) design. `status: draft` — to be sealed at Step 6 (add `sealed_at:`),
immutable thereafter.*
