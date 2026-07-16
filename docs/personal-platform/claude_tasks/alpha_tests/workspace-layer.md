---
type: alpha_test
title: "Workspace layer — kernel-isolation acceptance test (A2′)"
task: "workspace-layer"
status: sealed
created: "2026-07-16"
sealed_at: "2026-07-16"
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
> **Consolidated draft.** Two independent Step-4-redo designs were produced against the same
> spec HEAD on 2026-07-16 (a concurrency artifact); this file is their union — every check of
> both, the stricter observable where they differed. Deltas that pin an interpretation of the
> spec are flagged in §7 for the pm to confirm or demote at seal.
>
> **This is a Step-8 test, run against the live VPS AFTER the vps-infra deliverables ship**
> (the uid image layer, the `NOPASSWD` removal, the provisioning script). Running it *today*
> (pre-implementation) is expected to **BLOCK** on preconditions for most checks and
> **FAIL** on the few that are runnable now (C3, G9's anti-vacuous guard, SRV/INF) — that is
> correct: the test predates the code it judges (see §2 and §8).

---

## 0. What a PASS asserts — coverage of the 9 spec acceptance-criteria seeds

| Seed (`workspace-layer.md` §"Acceptance criteria") | Check |
|---|---|
| 1 — Triviality: add ws #2 = provisioning script + registry entry, ≤30 min, no code-server restart, no `omnigent/` change | **C1** (a–e) |
| 2 — Kernel isolation (core win): as `ws-test`, read of `ws-personal`'s `600` secret FAILS + observable; own secret read succeeds | **C2** (own / cross / observable / struct / code / **wrap** — the launch wrapper exercised as the security control the spec's risk section assigns to this seed) |
| 3 — No master key: `sudo -n true` as `coder` in-container FAILS (blanket NOPASSWD gone) | **C3** (a–e: coder, the rule listing, workspace uids, lateral sudo, narrow-scope) |
| 4 — State isolation: a `claude` under `ws-test`'s `CLAUDE_CONFIG_DIR` cannot see `ws-personal`'s credentials/transcripts | **C4** (a–f) |
| 5 — Editor still works: `code-server` (as `coder`, group member) browses `640`/`750` code but cannot read `600` secrets | **C5** (a–d; e informational) |
| 6 — Git identity: a commit in `ws-test`'s tree carries `ws-test`'s identity | **C6** |
| 7 — Ecosystem hooks: kb-three-tier clone path + secrets-manager target derivable from the registry entry ALONE | **C7** |
| 8 — Registry validate script fails **loudly** on a seeded registry/live-state mismatch | **C8** (V0–V3) |
| 9 — Fork governance: Stage-1 fork diff shows zero files under `omnigent/` | **G9** |

Additionally gated — not among the 9 seeds, but explicit Stage-1 deliverables in the spec's
design section and work-split table (the pm may demote any of these at seal; §7 finding 8):

| Spec deliverable (design § / work split) | Check |
|---|---|
| Omnigent server + Postgres **stopped, not removed**; `omnigent-host.service` stays disabled; the `127.0.0.1:8000` injected-agent liability is closed | **SRV-1..3** (SRV-4 reactivation smoke: optional) |
| `mem_limit: 4g`, `cpus: "1.5"` on code-server (E2 — "overdue, also a containment control") | **INF-1** |

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
  read a workspace's `600` secrets directly (C5) **or via sudo** (C3-e), which is the real
  residual guarantee.
- **Wrapper behavior from a non-workspace cwd.** The spec defines resolution only for a
  workspace cwd; behavior outside any workspace is unspecified. Recorded as a gap (finding 2),
  not tested — pinning it would invent spec.
- **Stage 3 — activating the `workspace_id` partition** on the (stopped) Omnigent server. Not
  built; G9 in fact asserts the seam was **not touched** (`workspace_id` is only *reserved* as
  a registry integer — C7 checks the reservation, not the partition).
- **A1 — dedicated code-server instance escalation.** Design-only in Stage 1; nothing to run.
- **Data-at-rest gate.** A binding governance gate before the *first client*; no client is
  onboarded here, so nothing to test.
- **Server reactivation (~10 s claim).** Stop-but-preserve is gated (SRV), but *reactivating*
  the stopped stack briefly re-opens the liability SRV-1 proves closed — offered only as the
  optional SRV-4 smoke, run solely on the human's explicit go.
- **A second live Claude login.** The spec accepts a per-workspace login as a cost; `ws-test`
  is disposable and is deliberately **never logged in** — its not-logged-in state is itself
  part of the C4 observable. No check requires an API call or a real login.
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
  referenced in `.pre-commit-config.yaml`), the escalation-stages doc, the second-workspace
  runbook, **and the launch wrapper**: its source tracked in the fork, its **deployed path**
  (`$WRAPPER`, §3) documented in the runbook/schema doc, and the code-server extension
  wired to it (C2-wrap w-0 verifies the wiring). The deployed **provisioning script**
  (vps-infra) is invocable.
- **PF-6 (hard).** The pm recorded, at Step-6 seal, the **`BASE`** pre-implementation baseline
  commit for G9 (default assumption: `f467fc20`, this spec's HEAD). Absent that, G9 is
  ambiguous (finding 4).
- **PF-7 (conditional — grades only the auditd sub-observable in C2).** A host audit rule
  covering the workspace trees exists (`auditctl -l` shows a watch/syscall rule). If absent,
  C2's *auditd* sub-observable is **N/A** (the EACCES errno remains the graded observable) —
  see finding 1. This PF never blocks the verdict.
- **PF-8 (hard — tooling).** The registry-reading helper (`ws_field`, §3) needs
  `python3 -c 'import yaml'` to succeed **on the box where §3 runs** (the host checkout
  plane). If missing: `pip3 install --user pyyaml`, or substitute a user-space
  [mikefarah] `yq` binary (`~/.local/bin/yq`, no root needed) with equivalent extraction.
  Verified 2026-07-16: the *code-server base image* ships neither `python3` nor `jq` — do
  not assume in-container availability; run registry extraction host-side.

**Pre-implementation reality (design time, 2026-07-16):** PF-3, PF-4, PF-5 are **unmet** (no
uid layer, no provisioning script, personal not migrated, no registry). So running this test
today BLOCKs. The exceptions runnable now: **C3** and **G9(a)** (expected **FAIL** — the
blanket sudo still exists, the artifacts aren't built), **SRV-1/2** and **INF-1** (expected
**FAIL** — the stack stop and E2 limits are pending infra enactment), **SRV-3** (may already
PASS — the spec records `omnigent-host.service` as already disabled). This is the intended
state of a pre-committed acceptance test (§8).

---

## 3. Fixtures, sentinels & discovery helpers (nothing here reads or prints a secret value)

```sh
# ---- paths / targets ----
REPO=/home/coder/repos/omnigent      # the fork clone (adjust to /opt/omnigent on the VPS)
WS_PERSONAL=personal                 # workspace #1 slug (confirm against the registry)
WS_TEST_SLUG=test                    # disposable workspace #2 SLUG — per the spec's ws-<slug>
WS_TEST=ws-test                      #   law its Unix user is ws-test (finding 9)
NONCE=$(date +%s)                    # one nonce per run; makes every sentinel globally unique

# ---- ws-test git-identity sentinels (fixtures defined NOW, at Step 4; not real values) ----
WSTEST_GIT_NAME="ws-test bot"
WSTEST_GIT_EMAIL="ws-test@example.invalid"

# ---- registry: exactly one tracked file named workspaces.yaml ----
REGISTRY="$REPO/$(git -C "$REPO" ls-files | grep -E '(^|/)workspaces\.yaml$')"
# PASS precondition (PF-5): exactly one match. Zero => deliverable missing; >1 => ambiguous SSOT.

# ---- the single code-server container (confirm against the vps-infra compose service name) ----
CS=$(docker ps --format '{{.ID}} {{.Image}} {{.Names}}' | grep -iE 'code-?server' | awk '{print $1}' | head -1)
CS_0=$(docker inspect "$CS" --format '{{.State.StartedAt}} {{.State.Pid}}')   # restart canary, whole run

# ---- the launch wrapper (deployed path; PF-5). Two sources must AGREE (C2-wrap w-0): ----
#   (i) the runbook / schema doc's documented deployed path;
#   (ii) the path the extension actually references:
grep -rn 'claudeProcessWrapper' /home/coder/.local/share/code-server/ 2>/dev/null   # run in-container
WRAPPER=<the deployed wrapper path from (i), e.g. /usr/local/bin/claude-ws-wrapper>

# ---- read a field from the registry entry, reading ONLY $REGISTRY (the "from the entry alone" semantic) ----
# Registry field names per spec §"The registry": slug, unix_user, root, git.{name,email},
# config_dir, kb_repo, secret_store, workspace_id, projects[]. Top-level shape (list vs
# {workspaces:[...]}) is confirmed against the schema doc at Step 8. Needs PF-8 tooling.
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
WSTEST_ROOT=$(ws_field "$WS_TEST_SLUG" root)     # e.g. /opt/work/test   (resolved from the registry)
PERSONAL_ROOT=$(ws_field "$WS_PERSONAL" root)    # e.g. /opt/work/personal
PERSONAL_CFGDIR=$(ws_field "$WS_PERSONAL" config_dir)

# ---- C2 cross-read target: a 600 file OWNED BY ws-personal (metadata-only discovery as root) ----
# Prefer the spec-named credential; else discover any 600 ws-personal-owned file. `find`/`stat`
# read METADATA only (paths, owner, mode) — never file contents.
PERSONAL_SECRET="$PERSONAL_CFGDIR/.credentials.json"
docker exec -u root "$CS" test -f "$PERSONAL_SECRET" || \
  PERSONAL_SECRET=$(docker exec -u root "$CS" sh -c \
    "find '$PERSONAL_ROOT' -xdev -type f -user ws-personal -perm -600 ! -perm /077 2>/dev/null | head -1")
# A 640 ws-personal CODE file for the C2-code cross-read (metadata-only discovery):
PERSONAL_CODEFILE=$(docker exec -u root "$CS" sh -c \
    "find '$PERSONAL_ROOT' -xdev -type f -user ws-personal -perm 640 2>/dev/null | head -1")

# ---- ws-test fixtures (placed by root at Step 8 with the spec's CANONICAL modes; torn down in §5) ----
#   <WSTEST_ROOT>/sample.code           owner ws-test  group coder  mode 640   (a "code" file)
#   <WSTEST_ROOT>/.secrets/own.sentinel owner ws-test  group coder  mode 600   ("WSTEST-OWN-SECRET-$NONCE")
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

A third mechanism is itself **under test**: the launch wrapper (`$WRAPPER`), which must
acquire the workspace uid from inside the container with **no** docker privileges — C2-wrap.

---

## 4. Checks

**Execution order (dependencies):** `SRV/INF → G9 → C3 → C1 (creates ws-test) → C2 (wrap
last) → C4 / C5 / C6 / C7 (with ws-test live; C4-f needs C2-wrap first) → teardown (§5,
removes ws-test, restores registry) → C8 (on the restored registry)`.

---

### SRV — Omnigent server stopped-not-removed; host service disabled  [work-split deliverable]

**Runs as:** SRV-1 `coder` inside `$CS` (the exact vantage point of the spec's named
liability — an injected agent on the editor plane); SRV-2/3 host operator.
```sh
# SRV-1 — the 127.0.0.1:8000 liability is closed (spec: "an injected agent reaches the
#         server at 127.0.0.1:8000 via network_mode: host"):
docker exec -u coder "$CS" sh -c 'curl -sf -m 5 http://127.0.0.1:8000/ >/dev/null 2>&1; echo "rc=$?"'
# SRV-2 — stopped, NOT removed (compose stop leaves Exited containers; down -v would not):
docker ps    --format '{{.Names}} {{.Status}}' | grep -Ei 'omnigent|postgres'      # running
docker ps -a --format '{{.Names}} {{.Status}}' | grep -Ei 'omnigent|postgres'      # all
# SRV-3 — the crash-looping host service stays off:
systemctl is-enabled omnigent-host.service
```
- **SRV-1 PASS iff** `rc` ≠ 0 (nothing answers on the host loopback :8000).
- **SRV-2 PASS iff** the running list prints **no** `Up …` line **and** the `-a` list prints
  ≥1 `Exited …` line. If preservation took another documented form, the operator substitutes
  equivalent evidence (e.g. `docker volume ls` showing the stack's named volumes) — evidence
  of *preservation* is mandatory either way (`stop`, never `down -v`, is the spec's text).
- **SRV-3 PASS iff** output is `disabled` or `masked` (anything but `enabled`).
- **SRV-4 (OPTIONAL, non-gating, human go required):** reactivation smoke — `docker compose
  start` the stack, `curl -sf -m 10 http://127.0.0.1:8000/` succeeds, `docker compose stop`,
  re-run SRV-1/2. Validates the "~10 s reactivation / collaboration engine preserved" claim.
- **Infra dependency / pre-impl:** the stack stop is pending → SRV-1/2 **expected-FAIL
  today**; SRV-3 may already PASS (service already disabled per the spec).

### INF-1 — code-server resource limits (E2, containment control)  [work-split deliverable]

**Runs as:** host operator.
```sh
docker inspect "$CS" --format '{{.HostConfig.Memory}} {{.HostConfig.NanoCpus}}'
```
- **PASS iff** output is exactly `4294967296 1500000000` (4 GiB, 1.5 CPUs).
- **Pre-impl:** **expected-FAIL today** (E2 is "overdue" per the spec).

---

### G9 — Fork governance: zero files under `omnigent/` in the Stage-1 change set  [seed 9]

**Runs as:** host operator, on the fork checkout (no container).
```sh
# (a) forbidden surface untouched
git -C "$REPO" diff --name-only "$BASE" HEAD | grep -E '^(omnigent|web)/'
# (b) anti-vacuous guard: the product-layer artifacts were actually delivered
git -C "$REPO" diff --name-only "$BASE" HEAD | grep -E '(^|/)workspaces\.yaml$'
git -C "$REPO" diff --name-only "$BASE" HEAD | grep -Ei 'escalation|runbook'
git -C "$REPO" diff --name-only "$BASE" HEAD | grep -Ei 'wrapper|launch'      # the wrapper + its harness
# (c) the wrapper's own test harness (spec risk §: "must cover restart/reload") exists and runs:
<harness invocation exactly as documented in reports/workspace-layer.md>; echo "rc=$?"
```
- **Expected:** (a) prints nothing (exit 1); (b) all three greps print ≥1 path; (c) exit 0.
- **PASS iff** (a) is empty **and** (b) is non-empty **and** (c) exits 0 — an undocumented or
  unrunnable harness invocation is a FAIL of (c), not a shrug (finding 6). Whether the
  harness's *coverage* genuinely spans restart/reload is a pm judgment at Step 8, not a
  binary gate here.
- Subsumes the scope guard "no touching the dormant `workspace_id` column": any
  `db_models`/migration edit lives under `omnigent/` and would fail (a).
- **Infra dependency / pre-impl:** none (fork-only). **Runnable today; expected-FAIL now** —
  (b)/(c) fail because the artifacts are not yet built (finding 4 for the `web/` scope nuance).

---

### C3 — No master key inside the container  [seed 3]

**Runs as:** `coder` and `ws-test` inside `$CS` (a–b now; c–e after C1 creates `ws-test`).
```sh
# (a) coder holds no root:
docker exec -u coder "$CS" sudo -n true; echo "rc=$?"     # expected: rc != 0 (sudo denied)
# (b) and the blanket rule is gone from what coder is allowed to run:
docker exec -u coder "$CS" sudo -n -l 2>&1 | grep -E '\(ALL(\s*:\s*ALL)?\)\s+NOPASSWD:\s*ALL'
#   expected: empty (exit 1) — no "(ALL) NOPASSWD: ALL"
# (informational) the narrow per-workspace rule the wrapper relies on may appear, e.g.
#   "(ws-test) NOPASSWD: <claude path>" — recorded here, exercised by C2-wrap.
docker exec -u coder "$CS" sudo -n -l 2>&1 | grep -Ei 'ws-[a-z0-9-]+.*NOPASSWD'   # informational
# (c) workspace uids hold no root either ("inside the container nobody holds root"):
docker exec -u ws-test "$CS" sudo -n true; echo "rc=$?"                    # expected: rc != 0
# (d) no LATERAL sudo between workspace uids (an injected agent as ws-test must not become
#     ws-personal — otherwise the uid boundary is theatre, per the spec's own bundle logic):
docker exec -u ws-test "$CS" sudo -n -u ws-personal true; echo "rc=$?"     # expected: rc != 0
# (e) the narrow rule is claude-only — coder cannot run ARBITRARY commands as a workspace
#     uid (else an editor-plane compromise reads every workspace's secrets THROUGH sudo,
#     rebuilding the master key laterally). Content discarded; only rc is graded:
docker exec -u coder "$CS" sh -c 'sudo -n -u ws-personal cat "'"$PERSONAL_SECRET"'" >/dev/null 2>&1; echo "rc=$?"'
#   expected: rc != 0
```
- **PASS iff** (a) rc≠0, (b) empty, (c) rc≠0, (d) rc≠0, (e) rc≠0.
- (c)–(e) pin the interpretation that "narrow per-workspace sudoers rules" means
  *`coder` → `ws-<slug>`, `claude` binary only* — confirm or overrule at seal (finding 10).
- **Infra dependency / pre-impl:** (a)–(b) need only the `NOPASSWD` removal — **runnable
  today; expected-FAIL now** (per the Step-2 state, `coder` still holds
  `ALL=(ALL) NOPASSWD:ALL`). (c)–(e) additionally need `ws-test` (after C1).

---

### C1 — Second-workspace triviality (timed provisioning of `ws-test`)  [seed 1]

**Runs as:** host operator (invokes the provisioning script + edits the fork registry).
```sh
# --- capture invariants BEFORE ---
CS_0=$(docker inspect "$CS" --format '{{.State.StartedAt}} {{.State.Pid}}')
NCS_0=$(docker ps --format '{{.Image}}' | grep -icE 'code-?server')     # code-server container count (expect 1)
T0=$(date +%s)
```
Execute **only** the runbook (deliverable "second-workspace runbook") to add `ws-test` — any
improvised root surgery to make it work is itself a FAIL of the triviality claim. The
timer brackets the mechanical procedure only (exclude time reading the runbook):
1. Run the provisioning script for slug `test` (vps-infra; run by the host/root operator): it
   creates uid `ws-test` (`useradd`, no container restart), creates+chowns the tree
   (`ws-test:coder`, dirs `750` `g+s`, code `640`, secrets `600`), installs the **narrow**
   sudoers rule, sets `CLAUDE_CONFIG_DIR=<WSTEST_ROOT>/.claude` (owned `ws-test`, `700`),
   configures the git identity/`includeIf`, and the terminal profile.
2. Add a `ws-test` entry to `$REGISTRY` (fork, working tree — no commit during the test):
   `slug: test`, `unix_user: ws-test` (the `ws-<slug>` law — finding 9), `root`,
   `git.name/email` = the sentinels, `config_dir`, `kb_repo: kb-ws-test`, `secret_store`
   (a **reference**, never inline), reserved `workspace_id` (integer, unique), ≥1
   `projects[]` entry (repo URL + default branch — fixtures:
   `https://example.invalid/alpha.git`, `main`).
```sh
# --- capture AFTER ---
T1=$(date +%s); ELAPSED=$((T1 - T0))
CS_1=$(docker inspect "$CS" --format '{{.State.StartedAt}} {{.State.Pid}}')
NCS_1=$(docker ps --format '{{.Image}}' | grep -icE 'code-?server')
WSTEST_ROOT=$(ws_field "$WS_TEST_SLUG" root)   # re-resolve now that the entry exists
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
- **PASS iff** C1-a…-e all hold. *Informational (not gated):* terminal-profile presence —
  `docker exec -u coder "$CS" grep -rn 'ws-test' /home/coder/.local/share/code-server/User/ 2>/dev/null`
  (the profile's mechanism is underdetermined by the spec; the human-terminal path is
  Stage 2b anyway).
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

The centerpiece. **No secret value is ever printed** — every read discards content to
`/dev/null` and only the exit code / errno string is inspected.

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

**C2-code — as `ws-test`, reading `ws-personal`'s 640 CODE also FAILS.**
**Runs as:** `ws-test`. The Brief draws the boundary around the **filesystem** ("nothing
crosses that boundary by default") and a workspace is a *client company* — their code is
confidential, not just their secrets. Denial comes from dir traversal (`750`, `other=0`)
for a non-member of group `coder` (finding 5 — this gate is what forces the setgid design).
```sh
docker exec -u root "$CS" stat -c '%U:%G %a' "$PERSONAL_CODEFILE"   # metadata: ws-personal:coder 640
docker exec -u ws-test "$CS" sh -c 'cat "'"$PERSONAL_CODEFILE"'" >/dev/null 2>&1; echo "rc=$?"'
#   expected: rc != 0
docker exec -u ws-personal "$CS" sh -c 'cat "'"$WSTEST_ROOT"'/sample.code" >/dev/null 2>&1; echo "rc=$?"'
#   expected: rc != 0   (symmetric: the boundary is mutual)
```

**C2-struct — the file-layout backing the boundary is actually applied.**
**Runs as:** host operator (metadata only).
```sh
docker exec -u root "$CS" stat -c '%U:%G %a' "$WSTEST_ROOT/.secrets/own.sentinel"   # expected: ws-test:coder 600
docker exec -u root "$CS" stat -c '%U:%G %a' "$WSTEST_ROOT/sample.code"             # expected: ws-test:coder 640
docker exec -u root "$CS" stat -c '%U:%G %a' "$WSTEST_ROOT"                         # expected: ws-test:coder 750
```

**C2-wrap — the launch wrapper is the security control, exercised as one.** The spec's risk
section is explicit: "tested as a security control (acceptance criterion 2 exercises it); its
failure surfaces as a permission-denied not firing." None of these needs a login or an API
call — `claude --version` and an idle launch work logged-out; what is graded is the **uid**.
```sh
# (w-0) the extension is actually WIRED to the deployed wrapper (an existing-but-unwired
#       wrapper is a FAIL):   runs as: coder
docker exec -u coder "$CS" grep -rn 'claudeProcessWrapper' /home/coder/.local/share/code-server/ 2>/dev/null
#   expected: ≥1 hit, and the referenced path == $WRAPPER (the documented deployed path)
# (w-1) cwd→workspace resolution + the narrow sudoers drop path work end-to-end, no login:
docker exec -u coder -w "$WSTEST_ROOT" "$CS" "$WRAPPER" --version; echo "rc=$?"
#   expected: rc=0 and a version string (the wrapper resolved ws-test and sudo permitted claude)
# (w-2) the privilege drop is REAL: a wrapper-launched claude RUNS as ws-test. Preferred
#       route: start a Claude Code extension session in code-server with $WSTEST_ROOT open
#       (human clicks; binary observable below). Scriptable route (pty via script(1),
#       present in the image; claude idles at its login screen — uid is what we grade):
docker exec -u coder "$CS" touch "/tmp/alpha-wrap-t0-$NONCE"           # C4-f marker, BEFORE launch
docker exec -u coder -w "$WSTEST_ROOT" "$CS" sh -c \
  'setsid script -qec "'"$WRAPPER"'" /dev/null >/dev/null 2>&1 & sleep 8; \
   ps -eo user:12,args | grep "^ws-test" | grep -i claude'
#   expected: ≥1 process line, USER column ws-test, args containing claude.
#   (If the wrapper had hardcoded personal's uid, this reads ws-personal → FAIL.)
docker exec -u root "$CS" sh -c 'pkill -u ws-test -f claude; true'     # cleanup the idle session
```
- **PASS iff** C2-own `rc=0`; C2-cross `rc!=0` + `OBSERVABLE=EACCES`; C2-code both `rc!=0`;
  C2-struct owner `ws-test`, group `coder`, modes `600`/`640`/`750`; C2-wrap w-0 wired to
  `$WRAPPER`, w-1 `rc=0`, w-2 ≥1 `ws-test`-owned claude process (either launch route).
- *Corroboration (informational):* if the Step-8 da session itself was wrapper-launched in
  personal's tree, its own `id -un` printing `ws-personal` is live evidence of the drop.
- **Infra dependency / pre-impl:** the uid layer + provisioning + PF-3 (personal migrated) +
  PF-5 (wrapper deployed). **BLOCKED pre-implementation.**

---

### C4 — State isolation: `ws-test`'s `CLAUDE_CONFIG_DIR` cannot see `ws-personal`'s state  [seed 4]

Non-destructive; no API call. The kernel already forbids `ws-test` from reading
`ws-personal`'s config dir; C4 additionally proves the **config-dir relocation** put ws-test on
its own isolated base — including on the REAL launch path (f).
```sh
WSTEST_CFGDIR=$(ws_field "$WS_TEST_SLUG" config_dir)     # runs as: host operator (registry read)
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
# (d′) the pre-migration GLOBAL credential is invisible too (spec: "the global credential is
#      invisible"); /home/coder is 700 coder — denial at traversal:   runs as: ws-test
docker exec -u ws-test "$CS" sh -c 'cat /home/coder/.claude/.credentials.json >/dev/null 2>&1; echo "rc=$?"'
#   expected: rc != 0
# (e) INFORMATIONAL — the spec's own observable ("a scratch dir reports Not logged in"), no API:
docker exec -u ws-test -e CLAUDE_CONFIG_DIR="$WSTEST_CFGDIR" "$CS" sh -lc \
  'claude --version >/dev/null 2>&1 && (claude auth status 2>/dev/null || claude whoami 2>/dev/null) || true'
#   informational: expected to report ws-test / "Not logged in", never ws-personal. Exact
#   read-only status subcommand resolved at Step 8; not gated (no local status cmd => rely on a–d).
# (f) the RELOCATION TOOK EFFECT on the real launch path: C2-wrap's launch left state under
#     ws-test's config dir (newer than the pre-launch marker):   runs as: ws-test
docker exec -u ws-test "$CS" sh -c \
  'find "'"$WSTEST_CFGDIR"'" -newer "/tmp/alpha-wrap-t0-'"$NONCE"'" 2>/dev/null | head -3'
#   expected: ≥1 path (the launched claude wrote its state base inside $WSTEST_CFGDIR —
#   per the spec's verified relocation, CLAUDE_CONFIG_DIR is the CLI's whole state base)
```
- **PASS iff** (a) `UNDER_ROOT`, (b) `ws-test 700`, (c) `ABSENT_OR_OWN`, (d) `rc!=0`,
  (d′) `rc!=0`, (f) ≥1 path.
- **Infra dependency / pre-impl:** provisioning (config-dir relocation) + PF-3 + C2-wrap
  (for f). **BLOCKED pre-implementation.**

---

### C5 — Editor still works: `coder` browses `640`/`750` code, cannot read `600` secrets  [seed 5]

A group-permission check. **Runs as:** `coder` (the code-server user).
```sh
# (a) coder can traverse the workspace dir (group r-x via 750):
docker exec -u coder "$CS" sh -c 'ls "'"$WSTEST_ROOT"'" >/dev/null 2>&1; echo "rc=$?"'          # expected: rc=0
# (b) coder can read a 640 code file (group r) — in BOTH workspaces (personal proves the
#     migration kept the editor working on the daily tree):
docker exec -u coder "$CS" sh -c 'cat "'"$WSTEST_ROOT"'/sample.code" >/dev/null 2>&1; echo "rc=$?"'   # expected: rc=0
docker exec -u coder "$CS" sh -c 'cat "'"$PERSONAL_CODEFILE"'" >/dev/null 2>&1; echo "rc=$?"'         # expected: rc=0
# (c) coder CANNOT read a 600 secret (group has no bits):
docker exec -u coder "$CS" sh -c 'cat "'"$WSTEST_ROOT"'/.secrets/own.sentinel" >/dev/null 2>/tmp/c5.$$; echo "rc=$?"; grep -qi "permission denied" /tmp/c5.$$ && echo DENIED; rm -f /tmp/c5.$$'
#   expected: rc != 0  AND  DENIED
# (d) editor keeps working on AGENT-CREATED files: a file ws-test creates in its setgid tree
#     must inherit group coder so code-server can read it (else the editor breaks on new files):
docker exec -u ws-test "$CS" sh -c 'umask 027; printf x > "'"$WSTEST_ROOT"'/created_by_ws.code"'   # runs as: ws-test
docker exec -u root  "$CS" stat -c '%G %a' "$WSTEST_ROOT/created_by_ws.code"                        # expected: coder 640
docker exec -u coder "$CS" sh -c 'cat "'"$WSTEST_ROOT"'/created_by_ws.code" >/dev/null 2>&1; echo "rc=$?"'  # expected: rc=0
# (e) INFORMATIONAL — the human opens $WSTEST_ROOT/sample.code in the BROWSER editor and it
#     renders. The uid-level mechanism is (a)-(d); the experiential gate is Step 9's
#     (human validation), so this is recorded, not gated.
```
- **PASS iff** (a) `rc=0`, (b) both `rc=0`, (c) `rc!=0` + `DENIED`, (d) new file is group
  `coder` and `coder` reads it (`rc=0`).
- **Infra dependency / pre-impl:** the file-layout (owner/group/mode + setgid) from
  provisioning. **BLOCKED pre-implementation.** (d) additionally proves setgid, not
  primary-group, is how group `coder` is achieved — with C2-code gating the other side, a
  primary-group design cannot pass both (finding 5).

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
KB=$(ws_field "$WS_TEST_SLUG" kb_repo)                  # expected: matches ^kb-ws-.+  (kb-ws-test)
ROOT=$(ws_field "$WS_TEST_SLUG" root)                   # expected: non-empty (clone lands under here)
echo "$KB" | grep -qE '^kb-ws-.+' && [ -n "$ROOT" ] && echo "KB_DERIVED=$KB -> $ROOT/"
# secrets-manager target, from the ws-test entry alone — a REFERENCE, never an inline value:
SS=$(ws_field "$WS_TEST_SLUG" secret_store)             # expected: non-empty pointer (keychain:… / vault:… / a path)
[ -n "$SS" ] && echo "SECRET_STORE=$SS"
# the ws-<slug> law + the reserved partition seam, over EVERY entry (both workspaces today):
for S in "$WS_PERSONAL" "$WS_TEST_SLUG"; do
  U=$(ws_field "$S" unix_user); [ "$U" = "ws-$S" ] || echo "LAW_VIOLATION:$S=$U"
  ws_field "$S" workspace_id | grep -qE '^[0-9]+$' || echo "BAD_ID:$S"
done                                                    # expected: no LAW_VIOLATION / BAD_ID lines
ws_field "$WS_PERSONAL" workspace_id; ws_field "$WS_TEST_SLUG" workspace_id   # expected: two DIFFERENT integers
# env-refs-only lint over the WHOLE registry (no inline NAME=VALUE credential belongs here):
grep -nE '^\s*[A-Z][A-Z0-9_]{2,}=[^ ]+' "$REGISTRY"     # expected: empty (exit 1)
```
- **PASS iff** `kb_repo` matches `^kb-ws-.+` and `root` is non-empty (kb target derivable);
  `secret_store` is a non-empty **reference**; every entry satisfies `unix_user == ws-<slug>`
  with an integer `workspace_id`, and the two ids differ (the reserved seam stays coherent —
  `0` is NOT rejected here, that is Stage 3 by spec); **and** the inline-assignment grep is
  empty (a real credential like `GIT_TOKEN=ghp_…` in the registry would match and FAIL; a
  pointer like `secret_store: keychain:test` does not).
- **Infra dependency / pre-impl:** the registry file + the ws-test entry (from C1). **BLOCKED
  pre-implementation** (no registry).

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
#      (if wiring is the spec's alternative "scheduled" route instead, the runbook must name
#       the unit; `systemctl list-timers | grep -i <unit>` is the equivalent evidence)
# V1 — baseline pass: consistent registry + live state
$VALIDATE_CMD; echo "exit=$?"                            # expected: exit=0, no error lines
# V2 — seeded mismatch: a registry entry naming a Unix user / root that do not exist live
#      (keys per the ws-<slug> law; adjust spellings to the schema doc at Step 8)
cat >> "$REGISTRY" <<EOF
  - slug: ghost-$NONCE
    unix_user: ws-ghost-$NONCE
    root: /opt/work/ghost-$NONCE
    config_dir: /opt/work/ghost-$NONCE/.claude
    kb_repo: kb-ws-ghost-$NONCE
    secret_store: keychain:ghost-$NONCE
    workspace_id: 9999
EOF
$VALIDATE_CMD; echo "exit=$?"                            # expected: exit != 0 AND output names ghost-$NONCE
# V3 — clean restore
git -C "$REPO" checkout -- "$REGISTRY"
$VALIDATE_CMD; echo "exit=$?"                            # expected: exit=0
git -C "$REPO" status --porcelain "$REGISTRY"            # expected: empty (registry restored)
```
- **PASS iff** V0 finds a wired validator, V1 exits 0, **V2 exits non-zero AND its output
  contains the seeded offender `ghost-$NONCE`** (loud + specific, not a silent non-zero),
  and V3 exits 0 with a clean `git status`.
- **Infra dependency / pre-impl:** the validate script + wiring (fork). **BLOCKED
  pre-implementation.** *The invariant is: an entry whose `unix_user`/`root` has no live
  counterpart is genuine drift the validator must catch loudly.* (finding 6: agents-table
  env-refs lint is a distinct check, not gated here.)

---

## 5. Teardown (always run after the checks — restores live state, zero collateral)

**Runs as:** host operator (the master key; deprovisioning is a root, host-side action).
```sh
WSTEST_ROOT=$(ws_field "$WS_TEST_SLUG" root)
# Remove ONLY ws-test's resources — never touch ws-personal, coder, or the container itself:
docker exec -u root "$CS" sh -c 'pkill -u ws-test 2>/dev/null; sleep 1; userdel ws-test 2>/dev/null || true'   # remove the uid
docker exec -u root "$CS" sh -c 'rm -rf "'"$WSTEST_ROOT"'"'                                            # remove ws-test's tree (+ fixtures)
docker exec -u root "$CS" sh -c 'rm -f /etc/sudoers.d/*ws-test* "/tmp/alpha-wrap-t0-'"$NONCE"'" 2>/dev/null; true'
# remove the ws-test narrow sudoers rule + terminal profile (the provisioning script's reverse step)
git -C "$REPO" checkout -- "$REGISTRY"                                                                 # drop the ws-test registry entry
```
Collateral assertions (teardown must have restarted nothing and restored everything):
```sh
docker inspect "$CS" --format '{{.State.StartedAt}} {{.State.Pid}}'          # == CS_0 (never restarted, whole run)
docker exec -u root "$CS" id ws-personal                                     # still resolves (personal intact)
docker exec -u root "$CS" stat -c '%U:%G %a' "$PERSONAL_ROOT"                # unchanged (ws-personal:coder 750)
docker exec -u ws-personal "$CS" sh -c 'cat "'"$PERSONAL_SECRET"'" >/dev/null 2>&1; echo "rc=$?"'   # rc=0 (personal still reads its own secret)
docker exec -u root "$CS" id ws-test 2>&1 | grep -q 'no such user' && echo "WSTEST_GONE"   # expected: WSTEST_GONE
git -C "$REPO" status --porcelain "$REGISTRY"                                # empty (registry restored)
```
- **PASS iff** `$CS` StartedAt/Pid equal their C1 "BEFORE" values, `ws-personal` still resolves
  with its tree intact and its own secret readable by it, `ws-test` no longer resolves, and
  the registry is clean.

---

## 6. Verdict rule (binary)

**Mandatory checks** (every one must PASS):

`SRV-1`, `SRV-2`, `SRV-3`, `INF-1`, `G9` (a–c), `C3` (a–e), `C1-a…-e`, `C2-own`, `C2-cross`,
`C2-code`, `C2-struct`, `C2-wrap` (w-0, w-1, w-2), `C4` (a, b, c, d, d′, f), `C5` (a–d),
`C6`, `C7`, `C8` (V0–V3), and the **§5 teardown-collateral** assertion.

```
verdict = PASS    if every mandatory check PASSES
verdict = FAIL    if any single mandatory check FAILS
verdict = BLOCKED if any hard precondition PF-1..PF-6, PF-8 is unmet (report which; not a PASS/FAIL)
```

No partial credit, no judgment calls. **Informational** items — C2's auditd sub-observable
(PF-7-conditional), C3's narrow-rule listing, C4(e)'s `claude` status, C5(e)'s browser
render, C1's terminal-profile presence, the wrapper corroboration via the da session's own
uid, SRV-4 — are reported for context and **never** change the verdict.

---

## 7. Findings & assumptions for the pm (resolve by Step-6 seal)

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

2. **The wrapper IS gated (C2-wrap), without any login or API call.** The spec's risk section
   assigns the wrapper to acceptance criterion 2 ("tested as a security control … criterion 2
   exercises it"), so an alpha test that leaves it informational contradicts the spec: an
   existing-but-unwired wrapper, or one that never drops uid, would otherwise pass the suite.
   w-0 (wiring), w-1 (`--version` through the wrapper: cwd resolution + sudoers path), and
   w-2 (a pty launch whose `claude` process demonstrably runs as `ws-test`; claude idles at
   its login screen — the uid is what is graded) need no credentials. **Recommendation kept:**
   the wrapper should also ship a `--resolve-only` dry-run mode printing the resolved
   `ws-<slug>`, making future checks even cheaper. **Untested gap (spec-silent):** wrapper
   behavior from a NON-workspace cwd — pinning it would invent spec; flagged for Stage 2b.

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

5. **Cross-workspace CODE opacity is gated (C2-code), which forces the setgid design.** Seed 2
   names secrets only, but the Brief's boundary is the *filesystem* ("nothing crosses that
   boundary by default") and a workspace is a client company — code is confidential too.
   C5(d) requires agent-created files to inherit group `coder`; C2-code requires `ws-*` users
   NOT to be members of group `coder`. The only design satisfying **both** is a setgid
   (`g+s`) tree group-owned by `coder` with no `ws-*` membership in that group. A
   primary-group design would pass C5(d) alone but FAIL C2-code — by construction, not by
   luck. If the pm rules secrets-only isolation acceptable, demote C2-code at seal (and note
   every client's code becomes container-readable cross-workspace).

6. **Report-documented invocations are part of the deliverable.** G9(c) (the wrapper's test
   harness) and C8 (`$VALIDATE_CMD`) run exactly as the de's report / schema doc documents
   them; undocumented or unrunnable = FAIL of that check. Whether the harness's *coverage*
   truly spans restart/reload (the spec's fragility concern) is a pm judgment at Step 8 —
   only its existence and green run are binary here. The agents-table env-refs lint stays
   un-gated (seed 8 is specifically the registry/live-state mismatch); a seeded-inline-secret
   case can be added as a separate check on request.

7. **Container-plane discovery names must be confirmed at Step 8.** `$CS` (single code-server
   container), `$VALIDATE_CMD`, `$WRAPPER` (deployed path), the registry top-level shape, and
   `PERSONAL_SECRET`/`PERSONAL_CODEFILE` canonical paths are resolved against the vps-infra
   compose service name + the fork's schema doc at run time. None changes the logic; each is
   a name-binding step noted inline.

8. **SRV-1..3 and INF-1 gate work-split deliverables that are not among the 9 seeds** (server
   stop-but-preserve + the closed `127.0.0.1:8000` liability, `omnigent-host.service`
   disabled, E2 resource limits). Rationale: the spec's design section makes them Stage-1
   deliverables of THIS task, and acceptance that ignores them can PASS with the
   injected-agent liability still live. The pm may demote any of them to informational at
   seal — explicitly, not by omission.

9. **The `ws-<slug>` law is enforced in the fixtures and C7.** The disposable workspace is
   slug `test`, unix user `ws-test`, `kb_repo: kb-ws-test` (an earlier draft used
   `slug: ws-test` → `kb-ws-ws-test`, which breaks the spec's naming law). C7 now checks
   `unix_user == ws-<slug>` and integer, mutually-distinct `workspace_id` for every entry.

10. **"Narrow sudoers" is pinned by C3(c–e):** `coder` may become a workspace uid ONLY through
    the `claude` launch path (w-1 proves that path works); workspace uids hold no root and
    cannot sudo laterally into each other; `coder` cannot run arbitrary commands (e.g. `cat`)
    as a workspace uid. If the architect needs a broader grant, that is a seal-time decision
    with the lateral-master-key cost stated, not a silent widening.

11. **C4(f) assumes a first launch writes state under `CLAUDE_CONFIG_DIR`.** Grounded in the
    spec's own verified relocation ("relocates the entire `~/.claude` base"); if a logged-out
    idle launch ever proves write-free, the FAIL surfaces at Step 8 with the raw `find`
    output and the pm adjudicates — the check stays binary.

12. **No commits during the run.** The ws-test registry entry stays a working-tree change,
    reverted at teardown; the ≤30-min timer covers the provisioning script + the entry edit
    (seed 1's own wording), not commit ceremony.

*End of Step-4 (redo) design.*

---

## Step-6 SEAL block (pm, 2026-07-16) — immutable after this point

**Sealed.** `status: sealed`, `sealed_at: 2026-07-16`. No edits after this line — a
post-seal change is a governance violation (`da` never touches it either).

**BASE pin (for G9):** the seal commit — the git commit that carries this seal block.
Step-8 runs `git diff <seal-commit>..HEAD -- omnigent/ web/` and expects it EMPTY. The
exact hash is recorded in this seal's commit message and the activity-log line.

**Authorship note:** this test was designed at Step 4 by two `da` agents that ran
concurrently (a session race); the surviving `da` consolidated both into the union sealed
here (its report, 2026-07-16). Bias-control intact: both designed from the spec alone,
before any implementation. The pm performs the seal per CLAUDE.md §4 (Step 6 = pm resolves
+ freezes + seals); no check was rewritten — the 12 findings are resolved below and govern.

**Resolution of §7's 12 findings (each is now binding):**

1. **auditd — RESOLVED option (a).** A host **auditd rule is a vps-infra deliverable**
   (watch each workspace secret tree, log denied + successful cross-uid reads with
   pid/exe/cwd). Therefore **PF-7 is a HARD precondition** (not conditional-N/A) and C2's
   auditd sub-observable is **MANDATORY**, alongside the `EACCES` errno. The plan's
   "logs the denial" is kept — auditd makes it true. This was the load-bearing finding.
2. **Wrapper gates (C2-wrap w-0/w-1/w-2) stay mandatory.** w-1 already proves cwd→uid
   resolution non-circularly without login; the `--resolve-only` dry-run stays a `de`
   deliverable recommendation (cheaper future checks), not a rework of this test.
3. **Personal migration confirmed** as a hard Step-7 precondition (PF-3). Not deferred.
4. **G9 gates BOTH `omnigent/` AND `web/`** — NOT relaxed to omnigent-only (the spec's
   out-of-scope forbids both). BASE pinned as above.
5. **C2-code stays MANDATORY** — code opacity is kept; the Brief's boundary is the
   filesystem and a workspace is a client company. The setgid design is forced by
   construction (C2-code + C5-d). Not demoted to secrets-only.
6. Documented-invocation gating stays as designed; agents-table env-refs lint stays
   un-gated (the Omnigent server is stopped, so that runtime vector is closed for Stage 1).
7. Discovery-name binding at Step 8 — accepted (logic-neutral).
8. **SRV-1..3 + INF-1 stay MANDATORY** — NOT demoted. They gate real Stage-1 deliverables
   (server stop-but-preserve, the `127.0.0.1:8000` liability closed, `omnigent-host`
   disabled, E2 `4g/1.5` limits); acceptance that ignored them could pass with the
   injected-agent liability live.
9. `ws-<slug>` law / C7 — accepted as designed.
10. **Narrow-sudoers interpretation (C3 c–e) is the pinned one** — workspace uids hold no
    root, no lateral sudo between workspaces, `coder` becomes a workspace uid ONLY via the
    `claude` launch path. Any broader architect grant is a stated seal-time decision with
    its lateral-master-key cost, never a silent widening (master-key principle).
11. C4(f) accepted (binary; edge case adjudicated at Step 8).
12. No commits during the run — accepted.

**Corresponding vps-infra deliverable added by finding 1:** the auditd rule (delivered to
the architect as prompt addendum #6, 2026-07-16), plus setgid provisioning (#7).
