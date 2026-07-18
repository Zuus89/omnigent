---
type: alpha_test
title: "Workspace layer — kernel-isolation acceptance test (A2′), mechanism-agnostic"
task: "workspace-layer"
status: sealed
created: "2026-07-16"
sealed_at: "2026-07-16"
resealed_at: "2026-07-17"
reseal: "post-seal correction — mechanism assertions DELETED, observable behaviors UNCHANGED. See the RE-SEAL block at the top. /audit-corpus: a post-seal modification is expected HIGH severity; this file explains itself below. // 2026-07-17 SECOND scoped re-seal (human ruling, Cristobal): C4-a ONLY — the topology clause 'config_dir under root' is superseded by the mechanism-agnostic config-isolation PROPERTY; every other sealed criterion byte-identical; precedent 220f2db8. See the C4-a RE-SEAL note in the C4 section."
related_decisions:
  - "workspace-layer.md (FROZEN spec — its acceptance criteria are behavior-level and unchanged; its illustrative permission-mechanism table is superseded by the infra report)"
  - "reviews/workspace-layer_infra-report.md (independent live VPS measurement that disproved the sealed mechanism)"
  - "council/workspace-isolation-amendment.md"
  - "plan.md §Phase 2 (workspace hierarchy — kernel-enforced isolation)"
---

# ⚠ RE-SEAL (post-seal correction) — read this first  (da, 2026-07-16)

> **A sealed alpha test was re-opened and re-sealed. This is a governance-flagged event.**
> `/audit-corpus` marks any post-seal modification HIGH severity — so this block states, on the
> record, exactly why the modification is legitimate.
>
> **What changed:** every **implementation-mechanism** assertion was **DELETED**; every
> **observable behavior** was **KEPT**, rephrased to be implementation-independent. The set of
> behaviors this test grades is **unchanged** — only the *how* was removed.
>
> **Why the re-open is legitimate (four conditions, all met):**
> 1. **The sealed test encoded a mechanism, and that exact mechanism was measured wrong.** The
>    sealed version made specific file modes/groups/setgid PASS/FAIL criteria (`C2-struct`
>    asserting `stat` = owner `ws-<slug>`, group `coder`, dirs `750`, code `640`, secrets `600`,
>    group membership via setgid; `chmod`-based fixtures; C1/C4/C5 mode `stat`s). During Step-7
>    infra build the vps-infra architect **independently measured on the live VPS** that this
>    precise mechanism **leaks code cross-workspace** (`ws-clientb` read `ws-clienta`'s source)
>    **and breaks the editor** (`640` stops `coder` saving; an editor-created file is invisible to
>    the agent). Evidence: `reviews/workspace-layer_infra-report.md` (committed). The mechanism was
>    replaced (own per-workspace group + dirs `2770` + POSIX ACLs + secrets `0700`).
> 2. **A mechanism-coupled test is a defective test.** Run against the corrected, measured-secure
>    implementation, the sealed `C2-struct` would **FAIL a correct implementation** — because the
>    correct implementation deliberately does not use those modes. That is a false-negative built
>    into the acceptance gate. Removing the coupling is a **correction of a test defect**, not a
>    tuning-to-pass. My original framing ("correct the test to the new modes") was itself the bug;
>    the correct fix is to **delete** the mechanism assertions, not rewrite them to `2770`/ACL —
>    so the test survives the *next* mechanism change too (there will be one).
> 3. **Human governance ruling (2026-07-16):** an alpha test must assert **OBSERVABLE BEHAVIOR,
>    not mechanism** — which uid can read what, and whether the denial is recorded — with **no
>    mention of modes, ACLs, group names, or setgid**. This re-seal enacts that ruling.
> 4. **Bias control is intact.** This correction was made and re-sealed **BEFORE Step 8 ever
>    ran** — the test has never been executed against any implementation. It is driven by
>    *independent infra measurement of the mechanism*, not by observing this test pass or fail.
>    No behavioral pass/fail line was weakened to accommodate code; the behaviors are exactly the
>    ones the architect reported measuring **passing** under the corrected mechanism.
>
> **Governance caveat (stated, not hidden):** the `da` card says "cannot modify a sealed alpha
> test for any reason." This modification proceeds **only** under the cited human ruling above,
> as a one-time governed correction. If that ruling is not in force, this re-seal is void and the
> prior sealed version (preserved verbatim in the "PRESERVED — prior Step-6 seal" block at the
> foot of this file) is authoritative. The mechanism-coupled resolutions of that prior seal
> (old finding 5 "setgid forced", old finding 1's mode-framing, the whole `C2-struct` check) are
> **superseded for PASS/FAIL** by this re-seal and retained only as history.
>
> **Separation of duties:** the `da` authors and re-seals the *content*; the pm commits this
> re-seal and records the commit hash in the commit message + activity log (that commit is the
> new `BASE` for G9). No `de` touches this file.

---

# Workspace layer — kernel-isolation acceptance test (A2′)

> **Bias-control spine.** This test is designed from the **spec alone**
> (`workspace-layer.md`, FROZEN; its behavior-level acceptance criteria) before any
> implementation is judged by it. Every check is a reproducible command with an exact
> **observable** and a **binary** PASS/FAIL rule. **What it grades is behavior**: which uid can
> read what, whether a save works, whether a denial is recorded, whether the launch wrapper drops
> privilege and fails closed. It grades **no mechanism** — no file mode, group name, ACL, or
> setgid appears as a criterion anywhere (that is the whole point of the re-seal; the mechanism is
> the implementer's to choose and re-choose).
>
> **This is a Step-8 test, run against the live VPS AFTER A2′ is active.** "Active" means: the
> A2′ image is deployed, the container has been **recreated**, `ws-personal` is migrated, and the
> fork's launch wrapper (`ws-launch`) is baked in and wired. Per the infra report, until
> `ws-launch` exists agents still run as `coder` and **A2′ is not active** — "deployed" is not
> "protected". Running this test before that window is expected to **BLOCK** on preconditions for
> most checks and **FAIL** the few runnable now — that is correct (the test predates the code it
> judges; see §2 and §6).

---

## 0. What a PASS asserts — behavioral coverage of the 9 spec acceptance-criteria seeds

| Seed (`workspace-layer.md` §"Acceptance criteria") | Behavioral check |
|---|---|
| 1 — Triviality: add ws #2 via the provisioning script + a registry entry, ≤30 min, no code-server restart, no `omnigent/`/`web/` change | **C1** (a–e) |
| 2 — Kernel isolation (core win): as `ws-test`, reading `ws-personal`'s **private** file FAILS + is **recorded**; own private file read SUCCEEDS; `ws-personal`'s **code** is confidential too | **C2** (own / cross / audit / code / wrap) |
| 3 — No master key: `coder` cannot become root or run arbitrary commands as a workspace uid; only the sanctioned launch path crosses uids | **C3** (a–e) |
| 4 — State isolation: a `claude` for `ws-test` cannot see `ws-personal`'s credentials/transcripts | **C4** (a–f) |
| 5 — Editor still works: `coder` can **read and save** a workspace's code but **cannot read** its private secrets; editor and agent can each read files the OTHER created | **C5** (a–e) |
| 6 — Git identity: a commit in `ws-test`'s tree carries `ws-test`'s identity | **C6** |
| 7 — Ecosystem hooks: kb-three-tier clone path + secrets-manager target derivable from the registry entry ALONE | **C7** |
| 8 — Registry validate script fails **loudly** on a seeded registry/live-state mismatch | **C8** (V0–V3) |
| 9 — Fork governance: `BASE..HEAD` fork diff shows zero files under `omnigent/` and `web/` | **G9** |

Additionally gated (Stage-1 work-split deliverables, not among the 9 seeds; behavioral, contain
no file-permission mechanism):

| Spec deliverable | Behavioral check |
|---|---|
| Omnigent server + Postgres **stopped, not removed**; `omnigent-host.service` stays disabled; the `127.0.0.1:8000` injected-agent liability is closed | **SRV-1..3** (SRV-4 reactivation smoke: optional) |
| code-server resource limits (E2 — containment control) | **INF-1** |

The alpha test **PASSES iff every mandatory check (§6) passes**. Any single mandatory FAIL → the
whole test **FAILS**. Any unmet hard precondition → **BLOCKED** (not a verdict). Items marked
*informational* are reported for the pm but never change the verdict.

---

## 1. Out of scope (this test does NOT cover — and why)

- **Stage 2a — workspace switcher UI.** Successor task, human-ruled out of Stage 1. Not tested.
- **Stage 2b — human-terminal-path hardening.** The spec is explicit: A2′ hardens the *agent*
  path; the *human-terminal* path stays convention-enforced (a user may pick a non-default
  profile and get a `coder` shell in a workspace folder). This test **does not** attempt to prove
  the human-terminal path is bounded. What it *does* prove is that even a `coder` shell cannot
  read a workspace's private secrets directly (**C5-c**) or via sudo (**C3-e**) — the real residual
  guarantee.
- **Stage 3 — activating the `workspace_id` partition** on the (stopped) Omnigent server. Not
  built; G9 asserts the seam was **not touched** (`workspace_id` is only *reserved* as a registry
  integer — C7 checks the reservation, not the partition).
- **A1 — dedicated code-server instance.** Design-only in Stage 1; nothing to run.
- **Data-at-rest gate.** A governance gate before the *first client*; no client is onboarded here.
- **Server reactivation smoke.** Reactivating the stopped stack re-opens the liability SRV-1
  proves closed — offered only as the optional SRV-4, on the human's explicit go.
- **A second live Claude login.** `ws-test` is disposable and deliberately **never logged in** —
  its not-logged-in state is itself part of the C4 observable. No check requires an API call.
- **Downstream consumer behavior.** C7 tests that the registry entry is *sufficient* for
  kb-three-tier / secrets-manager to derive their targets; it does not test those unbuilt tasks.

---

## 2. Preconditions & pre-flight gate

All `docker …`, `id`, `ausearch` commands run in a shell **on `omni-vps`** (CLAUDE.md §13; the
operator is the host/root plane — the vps-infra "master key"; prefix `sudo` if not in the `docker`
group). The fork checkout at `$REPO` is inspected on whichever box holds it. Report **BLOCKED —
precondition PF-n unmet** (not PASS/FAIL) if any hard PF fails.

- **PF-1** `omni-vps` reachable; `docker ps` returns without error.
- **PF-2** The **single code-server container** is running and discoverable (`$CS` resolves, §3).
- **PF-3 (hard — A2′ active).** The container has been **recreated onto the A2′ image**, and
  `ws-personal` has been **migrated**: the Unix user `ws-personal` resolves inside `$CS`
  (`docker exec -u root "$CS" id ws-personal`), a workspace tree exists for it, and **at least one
  file exists under `ws-personal`'s private/credential area that `ws-personal` can read and `coder`
  cannot** (the behavioral definition of a private secret — the C2 cross-read target; discovered in
  §3, never by mode). If personal is not migrated, C2/C4/C5 have no counterpart → BLOCKED.
- **PF-4 (hard).** `$CS` can create/manage per-workspace Unix users **without a container
  restart** (`docker exec -u root "$CS" command -v useradd` resolves) — this is what makes C1's
  "no restart" achievable.
- **PF-5 (hard).** The fork holds the Stage-1 product-layer deliverables: exactly one tracked
  `workspaces.yaml` (`$REGISTRY`, §3); a **wired** validate entrypoint (`$VALIDATE_CMD`, referenced
  in `.pre-commit-config.yaml`); the escalation-stages doc; the second-workspace runbook; **and the
  launch wrapper `ws-launch`**: source tracked in the fork, **baked into the image** at a documented
  deployed path (`$WS_LAUNCH`, §3), and the code-server process-wrapper setting wired to it
  (C2-wrap w-0 verifies the wiring). The deployed **provisioning script** (vps-infra) is invocable.
- **PF-6 (hard).** The pm recorded, in the **RE-SEAL commit**, the **`BASE`** baseline for G9 (the
  commit that carries this re-seal block). Absent that, G9 is ambiguous.
- **PF-7 (hard — audit trail active).** The host audit facility is running and the workspace
  credential trees are watched, such that a foreign-uid access attempt is recorded and retrievable
  via `ausearch`. This is a **hard** precondition (the infra report confirms auditd installed +
  active). It is confirmed **behaviorally** by C2-audit (an entry appears), never by asserting the
  rule syntax. If no entry can ever be produced for a covered attempt, C2-audit FAILS (the plan's
  required observability is not delivered).
- **PF-8 (hard — tooling).** The registry-reading helper (`ws_field`, §3) needs
  `python3 -c 'import yaml'` on the box where §3 runs (host checkout plane). If missing:
  `pip3 install --user pyyaml`, or a user-space `yq` with equivalent extraction. (Verified
  2026-07-16: the code-server base image ships neither `python3` nor `jq` — run registry
  extraction host-side.)

**Pre-implementation reality (2026-07-16, from `reviews/workspace-layer_infra-report.md`).** A2′
is **not yet active**: infra deliverables 1–4 + 7 are BUILT/TESTED but activate **only on
container recreate** (still the old container, `Up`), and the fork's `ws-launch` is **not built**
(blocking — until it exists agents run as `coder`). Therefore running this test today yields:

| Now-status | Checks | Why |
|---|---|---|
| **Runnable now, expected-PASS** | SRV-1, SRV-2, SRV-3 | Deliverable #5 (stack stop) is **APPLIED**; `omnigent-host.service` disabled. |
| **Runnable now, expected-FAIL** | G9, C3-a/b, INF-1 | Fork artifacts + `ws-launch` not built (G9 anti-vacuous); `NOPASSWD:ALL` removal (#2) and mem/cpu limits (#4) activate only on recreate, so the **running** container still has blanket sudo and old limits. |
| **BLOCKED until the recreate window + `ws-launch`** | C1, C2 (all), C3-c/d/e, C4, C5, C6, C7, C8, teardown | All require the recreated A2′ container (workspace uids, provisioning script) and/or the baked `ws-launch`. auditd is active on the host now, but no workspace uids exist yet to exercise it → C2-audit blocks with them. |

This is the intended state of a pre-committed acceptance test (§6). A2′ becomes fully testable
only in the single recreate window the architect proposes once `ws-launch` is delivered.

---

## 3. Fixtures, sentinels & behavioral discovery (nothing here reads or prints a secret value)

Fixtures are established through the **real provisioning path** and by the **actual principals**
(the owner uid, the editor uid) — never hand-placed with root `chmod`. A "private" file and a
"code" file are defined **behaviorally** (by who can read them), never by a permission bit.

```sh
# ---- paths / targets ----
REPO=/home/coder/repos/omnigent      # the fork clone (adjust to /opt/omnigent on the VPS)
WS_PERSONAL=personal                 # workspace #1 slug (confirm against the registry)
WS_TEST_SLUG=test                    # disposable workspace #2 SLUG — per the spec's ws-<slug> law
WS_TEST=ws-test                      #   its Unix user is ws-test
NONCE=$(date +%s)                    # one nonce per run; every sentinel is globally unique
AUDIT_START=$(date '+%x %T')         # run-start timestamp for ausearch -ts (host clock)

# ---- ws-test git-identity sentinels (fixtures, not real values) ----
WSTEST_GIT_NAME="ws-test bot"
WSTEST_GIT_EMAIL="ws-test@example.invalid"

# ---- registry: exactly one tracked file named workspaces.yaml ----
REGISTRY="$REPO/$(git -C "$REPO" ls-files | grep -E '(^|/)workspaces\.yaml$')"
# PF-5: exactly one match. Zero => deliverable missing; >1 => ambiguous SSOT.

# ---- the single code-server container ----
CS=$(docker ps --format '{{.ID}} {{.Image}} {{.Names}}' | grep -iE 'code-?server' | awk '{print $1}' | head -1)
CS_0=$(docker inspect "$CS" --format '{{.State.StartedAt}} {{.State.Pid}}')   # restart canary, whole run

# ---- the launch wrapper under test (deployed, baked path; PF-5). Resolved at Step 8 from the
#      runbook / schema doc, and confirmed to match the wired process-wrapper setting (C2-wrap w-0): ----
WS_LAUNCH=<the deployed ws-launch path documented in the runbook, e.g. /usr/local/bin/ws-launch>

# ---- read a field from the registry entry, reading ONLY $REGISTRY ("from the entry alone") ----
# Registry fields per spec §"The registry": slug, unix_user, root, git.{name,email}, config_dir,
# kb_repo, secret_store, workspace_id, projects[]. Top-level shape confirmed against the schema doc
# at Step 8. Needs PF-8 tooling.
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
PERSONAL_ROOT=$(ws_field "$WS_PERSONAL" root)
PERSONAL_CFGDIR=$(ws_field "$WS_PERSONAL" config_dir)
# WSTEST_ROOT / WSTEST_CFGDIR resolve AFTER C1 creates the ws-test entry.

# ---- BEHAVIORAL discovery of the cross-read targets (no mode is ever inspected) ----
# PERSONAL_SECRET := a file in ws-personal's private/credential area that ws-personal CAN read and
#   coder CANNOT — the behavioral definition of a secret. Chosen from the credential area so the
#   required audit observability (PF-7) applies. `find` lists PATHS only (metadata, no content);
#   readability is judged by exit code, content discarded to /dev/null.
PERSONAL_SECRET=
for f in $(docker exec -u root "$CS" sh -c 'find "'"$PERSONAL_CFGDIR"'" -xdev -type f 2>/dev/null'); do
  docker exec -u ws-personal "$CS" sh -c 'cat "'"$f"'" >/dev/null 2>&1' || continue   # owner must read it
  docker exec -u coder       "$CS" sh -c 'cat "'"$f"'" >/dev/null 2>&1' && continue    # coder must NOT
  PERSONAL_SECRET="$f"; break
done
# fallback: if the config dir yielded nothing, widen the search to the whole personal tree.
[ -n "$PERSONAL_SECRET" ] || for f in $(docker exec -u root "$CS" sh -c 'find "'"$PERSONAL_ROOT"'" -xdev -type f 2>/dev/null'); do
  docker exec -u ws-personal "$CS" sh -c 'cat "'"$f"'" >/dev/null 2>&1' || continue
  docker exec -u coder       "$CS" sh -c 'cat "'"$f"'" >/dev/null 2>&1' && continue
  PERSONAL_SECRET="$f"; break
done

# PERSONAL_CODEFILE := a file in ws-personal's tree that coder (the editor) CAN read — i.e. code the
#   editor is meant to work on. Behavioral: first coder-readable regular file under the tree.
PERSONAL_CODEFILE=
for f in $(docker exec -u root "$CS" sh -c 'find "'"$PERSONAL_ROOT"'" -xdev -type f 2>/dev/null | head -100'); do
  docker exec -u coder "$CS" sh -c 'cat "'"$f"'" >/dev/null 2>&1' || continue
  PERSONAL_CODEFILE="$f"; break
done
```

Two mechanisms establish "run **as** a given Unix user", both uid-faithful:
- `docker exec -u <user> "$CS" <cmd>` — the daemon sets the process uid directly; used for the
  graded kernel-boundary observations (the kernel judges by uid, not by how it was acquired).
- `docker exec -u root "$CS" …` — the **host/root operator** (the vps-infra master key), used
  **only** for orchestration and *path* discovery (`find` prints paths, never content). This never
  reads a secret's contents and never contradicts C3 (which concerns `coder`'s in-container sudo,
  not the host operator).

A third mechanism is itself **under test**: the launch wrapper `ws-launch`, which must acquire the
workspace uid from inside the container with **no** docker privileges — C2-wrap.

---

## 4. Checks

**Execution order (dependencies):** `SRV/INF → G9 → C3(a,b) → C1 (creates ws-test) → C3(c–e) →
C2 (wrap last) → C4 / C5 / C6 / C7 (ws-test live; C4-f needs C2-wrap first) → teardown (§5, removes
ws-test, restores registry) → C8 (on the restored registry)`.

---

### SRV — Omnigent server stopped-not-removed; host service disabled  [work-split deliverable]

**Runs as:** SRV-1 `coder` inside `$CS` (the exact vantage of the spec's named liability — an
injected agent on the editor plane); SRV-2/3 host operator.
```sh
# SRV-1 — the 127.0.0.1:8000 liability is closed:
docker exec -u coder "$CS" sh -c 'curl -sf -m 5 http://127.0.0.1:8000/ >/dev/null 2>&1; echo "rc=$?"'
# SRV-2 — stopped, NOT removed:
docker ps    --format '{{.Names}} {{.Status}}' | grep -Ei 'omnigent|postgres'      # running
docker ps -a --format '{{.Names}} {{.Status}}' | grep -Ei 'omnigent|postgres'      # all
# SRV-3 — the crash-looping host service stays off:
systemctl is-enabled omnigent-host.service
```
- **SRV-1 PASS iff** `rc` ≠ 0 (nothing answers on host loopback :8000).
- **SRV-2 PASS iff** the running list prints **no** `Up …` line **and** the `-a` list prints ≥1
  `Exited …` line (or equivalent documented preservation evidence, e.g. `docker volume ls` showing
  the stack's named volumes — *preservation* evidence is mandatory either way; `stop`, never
  `down -v`).
- **SRV-3 PASS iff** output is `disabled` or `masked`.
- **SRV-4 (OPTIONAL, non-gating, human go required):** reactivation smoke — `docker compose start`,
  `curl -sf -m 10 http://127.0.0.1:8000/` succeeds, `docker compose stop`, re-run SRV-1/2.
- **Now-status:** deliverable #5 APPLIED → **expected-PASS today**.

### INF-1 — code-server resource limits (E2, containment control)  [work-split deliverable]

**Runs as:** host operator.
```sh
docker inspect "$CS" --format '{{.HostConfig.Memory}} {{.HostConfig.NanoCpus}}'
```
- **PASS iff** output is exactly `4294967296 1500000000` (the E2 deliverable's mem/cpu limits).
  This grades the *containment deliverable value*, not any file-permission mechanism.
- **Now-status:** limits are WRITTEN in compose, activate on recreate → **expected-FAIL today**.

---

### G9 — Fork governance: no `omnigent/`/`web/` files in the Stage-1 change set  [seed 9]

**Runs as:** host operator, on the fork checkout (no container). `BASE` = the **RE-SEAL commit**
(PF-6).
```sh
# (a) forbidden surface untouched in the post-reseal implementation diff:
git -C "$REPO" diff --name-only "$BASE" HEAD | grep -E '^(omnigent|web)/'
# (b) anti-vacuous guard: the product-layer artifacts are actually present in the tree:
git -C "$REPO" ls-files | grep -E '(^|/)workspaces\.yaml$'
git -C "$REPO" ls-files | grep -Ei 'escalation|runbook'
git -C "$REPO" ls-files | grep -Ei 'ws-launch|wrapper|launch'      # ws-launch + its harness
# (c) the wrapper's own test harness (spec risk §: "must cover restart/reload") exists and runs:
<harness invocation exactly as documented in reports/workspace-layer.md>; echo "rc=$?"
```
- **PASS iff** (a) is empty (exit 1) **and** (b) all three greps print ≥1 path **and** (c) exits 0.
  An undocumented or unrunnable harness invocation is a FAIL of (c), not a shrug. Whether the
  harness's *coverage* truly spans restart/reload is a pm judgment at Step 8, not a binary gate.
- Subsumes the scope guard "no touching the dormant `workspace_id` column": any `db_models`/
  migration edit lives under `omnigent/` and would fail (a).
- **Now-status:** fork-only; **runnable today, expected-FAIL** — (b)/(c) fail because `ws-launch`
  and the fork artifacts are not yet built.

---

### C3 — No master key inside the container  [seed 3]

**Runs as:** `coder` and `ws-test` inside `$CS` (a–b now; c–e after C1 creates `ws-test`). Grades
**behavior**: who can become root / another uid, and by what path — no sudoers file syntax asserted.
```sh
# (a) coder holds no root:
docker exec -u coder "$CS" sudo -n true; echo "rc=$?"                       # expected: rc != 0
# (b) coder cannot run ARBITRARY commands as root (the blanket master key is gone):
docker exec -u coder "$CS" sudo -n whoami 2>/dev/null; echo "rc=$?"         # expected: rc != 0
# (c) workspace uids hold no root either:
docker exec -u ws-test "$CS" sudo -n true; echo "rc=$?"                     # expected: rc != 0
# (d) no LATERAL crossing between workspace uids (ws-test must not become ws-personal):
docker exec -u ws-test "$CS" sudo -n -u ws-personal true; echo "rc=$?"      # expected: rc != 0
# (e) coder cannot run an ARBITRARY command as a workspace uid (else an editor-plane compromise
#     reads every workspace's secrets by proxy, rebuilding the master key laterally). Content
#     discarded; only rc graded:
docker exec -u coder "$CS" sh -c 'sudo -n -u ws-personal cat "'"$PERSONAL_SECRET"'" >/dev/null 2>&1; echo "rc=$?"'
#     expected: rc != 0
# (informational) coder → workspace uid is permitted ONLY along the sanctioned launch path; that
#   path is exercised positively by C2-wrap (w-1). Any narrow grant that appears is recorded here,
#   not graded by syntax.
```
- **PASS iff** (a) rc≠0, (b) rc≠0, (c) rc≠0, (d) rc≠0, (e) rc≠0.  [maps behavioral item: no lateral
  sudo, no arbitrary cat as another uid, cross-uid only via the sanctioned launch path]
- **Now-status:** (a)–(b) need only the `NOPASSWD` removal, which activates on recreate — the
  running container still grants blanket sudo → **runnable today, expected-FAIL**. (c)–(e) need
  `ws-test` (after C1) → BLOCKED until then.

---

### C1 — Second-workspace triviality (timed provisioning of `ws-test`)  [seed 1]

**Runs as:** host operator (invokes the **real provisioning script** + edits the fork registry).
No hand-rolled `chmod` — provisioning creates the tree so C1 tests reality.
```sh
# --- invariants BEFORE ---
CS_0=$(docker inspect "$CS" --format '{{.State.StartedAt}} {{.State.Pid}}')
NCS_0=$(docker ps --format '{{.Image}}' | grep -icE 'code-?server')     # code-server container count (expect 1)
T0=$(date +%s)
```
Execute **only** the runbook (deliverable "second-workspace runbook") to add `ws-test` — any
improvised root surgery to make it work is itself a FAIL of the triviality claim. The timer brackets
the mechanical procedure only (exclude time spent reading the runbook):
1. Run the deployed **provisioning script** for slug `test` (vps-infra): it creates uid `ws-test`
   with no container restart, provisions its tree and private state area, installs the sanctioned
   launch grant, sets `CLAUDE_CONFIG_DIR`, configures the git identity, and the terminal profile.
   (This test asserts the *behavioral outcomes* below — it does not assert how the script lays the
   tree out.)
2. Add a `ws-test` entry to `$REGISTRY` (fork working tree — no commit during the test): `slug: test`,
   `unix_user: ws-test`, `root`, `git.name/email` = the sentinels, `config_dir`, `kb_repo: kb-ws-test`,
   `secret_store` (a **reference**, never inline), reserved unique integer `workspace_id`, ≥1
   `projects[]` entry (fixtures: `https://example.invalid/alpha.git`, `main`).
```sh
# --- AFTER ---
T1=$(date +%s); ELAPSED=$((T1 - T0))
CS_1=$(docker inspect "$CS" --format '{{.State.StartedAt}} {{.State.Pid}}')
NCS_1=$(docker ps --format '{{.Image}}' | grep -icE 'code-?server')
WSTEST_ROOT=$(ws_field "$WS_TEST_SLUG" root)       # resolve now that the entry exists
WSTEST_CFGDIR=$(ws_field "$WS_TEST_SLUG" config_dir)
```
- **C1-a** `[ "$ELAPSED" -le 1800 ]` — the mechanical procedure ≤ 30 minutes.
- **C1-b** `[ "$CS_1" = "$CS_0" ]` — code-server **not** restarted (StartedAt & Pid unchanged).
- **C1-c** `[ "$NCS_1" = "$NCS_0" ]` — no new code-server container; `ws-personal` undisturbed
  (`docker exec -u root "$CS" id ws-personal` still resolves).
- **C1-d** no code change under `omnigent/`/`web/` during the procedure; the registry did change:
  ```sh
  git -C "$REPO" status --porcelain | grep -E ' (omnigent|web)/'        # expected: empty (exit 1)
  git -C "$REPO" status --porcelain | grep -E '(^|/)workspaces\.yaml$'  # expected: non-empty
  ```
- **C1-e** `ws-test` exists as a live Unix user and **controls its own tree** (behavioral, no mode):
  ```sh
  docker exec -u root  "$CS" id ws-test                                             # expected: resolves
  docker exec -u ws-test "$CS" sh -c 'touch "'"$WSTEST_ROOT"'/.c1probe" && rm -f "'"$WSTEST_ROOT"'/.c1probe"; echo "rc=$?"'
  #   expected: rc=0  (the owner can create/remove in its own root)
  ```
- **PASS iff** C1-a…-e all hold. *Informational:* terminal-profile presence (Stage 2b anyway).
- **Now-status:** the provisioning script + recreated container are required → **BLOCKED today**.

---

### C2 — Kernel isolation: the core win  [seed 2]

The centerpiece. **No secret value is ever printed** — every read discards content to `/dev/null`;
only the exit code / error class / audit record is inspected. Targets are **discovered behaviorally**
(§3): a "private" file is one the owner reads and `coder` cannot; a "code" file is one `coder` can
read.

**C2-own — as `ws-test`, reading `ws-test`'s OWN private file SUCCEEDS.**  **Runs as:** `ws-test`.
```sh
# the owner creates a private sentinel in its own state base (behavioral fixture; never a real
# secret, never printed), then reads it back:
docker exec -u ws-test "$CS" sh -c 'printf "WSTEST-OWN-%s" "'"$NONCE"'" > "'"$WSTEST_CFGDIR"'/own.sentinel"'
docker exec -u ws-test "$CS" sh -c 'cat "'"$WSTEST_CFGDIR"'/own.sentinel" >/dev/null 2>&1; echo "rc=$?"'
#   expected: rc=0  (the owner reads its own private file — proves the uid was genuinely acquired)
```

**C2-cross — as `ws-test`, reading `ws-personal`'s private file FAILS (permission-denied class).**
**Runs as:** `ws-test`.
```sh
docker exec -u ws-test "$CS" sh -c '
  cat "'"$PERSONAL_SECRET"'" >/dev/null 2>/tmp/c2.$$ ; rc=$?
  echo "rc=$rc"
  grep -qi "permission denied" /tmp/c2.$$ && echo "OBSERVABLE=EACCES"
  rm -f /tmp/c2.$$'
#   expected: rc != 0  AND  a line "OBSERVABLE=EACCES"
```
- **PASS iff** rc ≠ 0 **and** `OBSERVABLE=EACCES` (a non-zero exit + a permission-denied-class error
  returned to the caller). The observable graded is the **denial itself**, not any mode.

**C2-audit — the cross-workspace denial IS recorded in the audit trail.**  **Runs as:** host
operator (auditd is host-level).
```sh
# after the C2-cross attempt above, an audit entry for that access attempt exists:
ausearch -f "$PERSONAL_SECRET" -ts $AUDIT_START 2>/dev/null | grep -Eiq 'ws-test|auid|uid=' && echo "AUDITED"
```
- **PASS iff** `AUDITED` prints — an entry for the attempt appears via `ausearch` (the plan's
  required observability). This asserts *an entry appears*, never the rule syntax. If nothing is
  ever recorded for a covered attempt, the required observability is undelivered → FAIL.

**C2-code — as `ws-test`, reading `ws-personal`'s CODE also FAILS (code is confidential too).**
**Runs as:** `ws-test` / `ws-personal`.
```sh
docker exec -u ws-test    "$CS" sh -c 'cat "'"$PERSONAL_CODEFILE"'" >/dev/null 2>&1; echo "rc=$?"'
#   expected: rc != 0   (a workspace is a client company; its source is confidential cross-workspace)
# symmetric — ws-personal cannot read ws-test's agent-created code (created in C5-d):
docker exec -u ws-personal "$CS" sh -c 'cat "'"$WSTEST_ROOT"'/by_agent.code" >/dev/null 2>&1; echo "rc=$?"'
#   expected: rc != 0   (the boundary is mutual)
```
- **PASS iff** both reads fail (rc ≠ 0). [behavioral item: client code confidential, not just secrets]

**C2-wrap — the launch wrapper `ws-launch` is exercised as the security control.** None of these
needs a login or an API call — `--version` and an idle launch work logged-out; the graded observable
is the **uid** the launched process runs as, and that the wrapper **fails closed**.
```sh
# (w-0) the process-wrapper setting is WIRED to the deployed ws-launch (an unwired wrapper is a FAIL):
docker exec -u coder "$CS" grep -rn 'claudeProcessWrapper' /home/coder/.local/share/code-server/ 2>/dev/null
#   expected: ≥1 hit, and the referenced path == $WS_LAUNCH
# (w-1) driving ws-launch from a WORKSPACE path resolves + runs end-to-end (no login):
docker exec -u coder -w "$WSTEST_ROOT" "$CS" "$WS_LAUNCH" --version; echo "rc=$?"
#   expected: rc=0 and a version string (cwd→workspace resolved, launch permitted)
# (w-2) the privilege drop is REAL — a ws-launch-launched claude RUNS as ws-test:
docker exec -u coder "$CS" touch "/tmp/alpha-wrap-t0-$NONCE"           # C4-f marker, BEFORE launch
docker exec -u coder -w "$WSTEST_ROOT" "$CS" sh -c \
  'setsid script -qec "'"$WS_LAUNCH"'" /dev/null >/dev/null 2>&1 & sleep 8; \
   ps -eo user:16,args | grep -i claude'
#   expected: ≥1 process line whose USER is ws-test and args contain claude.
#   (If ws-launch resolved the wrong workspace or dropped to coder, USER differs → FAIL.)
docker exec -u root "$CS" sh -c 'pkill -u ws-test -f claude; true'     # cleanup the idle session
# (w-3) ws-launch FAILS CLOSED from an UNKNOWN path — never falls back to coder:
docker exec -u coder -w /tmp "$CS" "$WS_LAUNCH" --version; echo "rc=$?"
#   expected: rc != 0  (cwd maps to no workspace → error out)
docker exec -u coder -w /tmp "$CS" sh -c \
  'setsid script -qec "'"$WS_LAUNCH"'" /dev/null >/dev/null 2>&1 & sleep 5; \
   ps -eo user:16,args | grep -i claude | grep "^coder" && echo "BYPASS" || echo "NO_CODER_FALLBACK"'
docker exec -u root "$CS" sh -c 'pkill -f "'"$WS_LAUNCH"'"; true'      # cleanup any spawned process
#   expected: NO_CODER_FALLBACK  (never a claude running as coder from an unknown path)
```
- **PASS iff** w-0 wired to `$WS_LAUNCH`; w-1 rc=0; w-2 ≥1 `ws-test`-owned claude process; w-3 the
  unknown-path launch **exits non-zero AND yields `NO_CODER_FALLBACK`** (fails closed).
  [behavioral item 9: workspace path → workspace uid; unknown path → fail closed, never coder]
- *Corroboration (informational):* if the Step-8 da session was itself wrapper-launched in
  personal's tree, its own `id -un` printing `ws-personal` is live evidence of the drop.
- **Now-status:** needs A2′ active + `ws-launch` baked + PF-3 → **BLOCKED today**.

---

### C4 — State isolation: `ws-test`'s Claude state cannot see `ws-personal`'s state  [seed 4]

Non-destructive; no API call. Grades **behavior** (who can read whose state; where the launch wrote
its state), never a directory mode.
```sh
# (a) [C4-a RE-SEALED 2026-07-17 — human ruling (Cristobal), scoped to C4-a; see the C4-a RE-SEAL
#      note directly beneath this code block. Precedent 220f2db8.]
#   SUPERSEDED (topology — NOT graded): the old (a) required config_dir to be a filesystem descendant
#   of root, which the shipped `personal` workspace itself does not satisfy (config_dir
#   /home/ws-personal/.claude is OUTSIDE root /home/coder/repos/personal). Original criterion, kept
#   verbatim for the freeze trail:
#       case "$WSTEST_CFGDIR" in "$WSTEST_ROOT"/*) echo "UNDER_ROOT" ;; *) echo "OUTSIDE_ROOT" ;; esac  # expected: UNDER_ROOT
#   NEW (a) = the config-isolation PROPERTY, wherever config lives (location NOT graded); three legs:
#     (i)   owner reads its OWN config              — observed by C2-own / the owner sentinel   (rc=0)
#     (ii)  coder/editor DENIED the config          — observed by (b) below                     (rc!=0)
#     (iii) cross-workspace read of config DENIED    — observed by (d)/(d′) below + C2-cross      (rc!=0)
# (b) ws-test's state base is PRIVATE — coder cannot read the sentinel ws-test placed there (C2-own):
docker exec -u coder "$CS" sh -c 'cat "'"$WSTEST_CFGDIR"'/own.sentinel" >/dev/null 2>&1; echo "rc=$?"'
#   expected: rc != 0   (behavioral privacy of the state base — no mode asserted)
# (c) ws-personal's credential is NOT present inside ws-test's config dir:
docker exec -u ws-test "$CS" sh -c '[ -e "'"$WSTEST_CFGDIR"'/.credentials.json" ] && echo PRESENT || echo ABSENT_OR_OWN'
#   expected: ABSENT_OR_OWN
# (d) ws-personal's credentials are unreadable from ws-test (kernel):
docker exec -u ws-test "$CS" sh -c 'cat "'"$PERSONAL_CFGDIR"'/.credentials.json" >/dev/null 2>&1; echo "rc=$?"'
#   expected: rc != 0
# (d′) the pre-migration GLOBAL credential is invisible too:
docker exec -u ws-test "$CS" sh -c 'cat /home/coder/.claude/.credentials.json >/dev/null 2>&1; echo "rc=$?"'
#   expected: rc != 0
# (e) INFORMATIONAL — the spec's own observable ("a scratch dir reports Not logged in"), no API:
docker exec -u ws-test -e CLAUDE_CONFIG_DIR="$WSTEST_CFGDIR" "$CS" sh -lc \
  'claude --version >/dev/null 2>&1 && (claude auth status 2>/dev/null || claude whoami 2>/dev/null) || true'
#   informational: expected to report ws-test / "Not logged in", never ws-personal.
# (f) the RELOCATION TOOK EFFECT on the real launch path: C2-wrap's launch left state under ws-test's
#     config dir (newer than the pre-launch marker):
docker exec -u ws-test "$CS" sh -c \
  'find "'"$WSTEST_CFGDIR"'" -newer "/tmp/alpha-wrap-t0-'"$NONCE"'" 2>/dev/null | head -3'
#   expected: ≥1 path (the launched claude wrote its state base inside $WSTEST_CFGDIR)
```

> **⚠ C4-a RE-SEAL — scoped, human-ruled (Cristobal, 2026-07-17). Precedent: 220f2db8.**
> The ONE sanctioned post-seal edit authorized after Step 8 began; it touches **C4-a only** — every
> other sealed criterion is byte-identical (not renumbered, not reworded). `/audit-corpus`: a post-seal
> modification is expected HIGH severity; this note is the on-the-record justification.
>
> **SUPERSEDED — the old (a) graded topology, not a security property, and is wrong for this
> architecture.** Old (a): `case "$WSTEST_CFGDIR" in "$WSTEST_ROOT"/*) echo "UNDER_ROOT"` — it required
> `config_dir` to be a filesystem descendant of `root`. The shipped, accepted `personal` workspace
> declares `config_dir: /home/ws-personal/.claude` **outside** `root: /home/coder/repos/personal` (the
> delivered architecture keeps agent config in the workspace Unix HOME). Grading the topology literally
> FAILS correct, shipped code — the same mechanism-coupling class the 220f2db8 re-seal deleted for
> `C2-struct`.
>
> **NEW C4-a criterion — the config-isolation PROPERTY, wherever config lives (location NOT graded):**
>   - **(i)**  the owning workspace uid reads its OWN config (rc=0);
>   - **(ii)** the `coder`/editor plane is DENIED the config (rc≠0, permission-denied class);
>   - **(iii)** a cross-workspace read of another workspace's config is DENIED (rc≠0).
>   **C4-a PASS iff all three legs hold.** No mode, group, ACL, or path-topology is asserted. Legs are
>   observed by checks already in this test: (i) C2-own / the owner sentinel; (ii) C4-a leg (b); (iii)
>   C4-a legs (d)/(d′) + C2-cross.
>
> **NOT goalpost-moving (mid-Step-8 re-seal integrity):** this DELETES a non-security topology check and
> SUBSTITUTES the actual security assertions — a strengthening/clarification, never a loosening. The old
> (a) could pass on a string-match while proving nothing about confidentiality; the new (a) requires
> demonstrated privacy of the config against BOTH the editor plane AND peer workspaces. No isolation
> guarantee is weakened; only the location requirement — never a security property — is removed. C4 legs
> (b)–(f) are unchanged. Authority: human governance ruling logged to `activity_log.jsonl`
> (2026-07-17T14:45:58Z); Hard Rule 9 satisfied (explicit authorization, not silent override). Absent
> that ruling this scoped re-seal is void and the superseded topology (a) above is authoritative.

- **PASS iff** (a) the C4-a config-isolation property holds — owner reads own config; `coder` denied; cross-ws read denied (see the C4-a RE-SEAL note above; **topology NOT graded**) — (b) rc≠0, (c) `ABSENT_OR_OWN`, (d) rc≠0, (d′) rc≠0, (f) ≥1 path.
  [behavioral item 7: one workspace's logged-in state / transcripts are not visible to the other]
- **Now-status:** needs provisioning (config-dir relocation) + PF-3 + C2-wrap (for f) → **BLOCKED**.

---

### C5 — Editor still works: `coder` reads AND saves code, cannot read secrets; editor↔agent files mutually readable  [seed 5]

Grades **behavior** only. **Runs as:** `coder`, `ws-test`, `ws-personal` as noted.
```sh
# (a) coder can browse the workspace and read code — in BOTH workspaces (personal proves the
#     migration kept the editor working on the daily tree):
docker exec -u coder "$CS" sh -c 'ls "'"$WSTEST_ROOT"'" >/dev/null 2>&1; echo "rc=$?"'                 # expected: rc=0
docker exec -u coder "$CS" sh -c 'cat "'"$PERSONAL_CODEFILE"'" >/dev/null 2>&1; echo "rc=$?"'          # expected: rc=0
# (b) coder can SAVE and CREATE code (the break the infra report measured: the old model stopped
#     coder writing — the editor could not save from the UI):
docker exec -u coder "$CS" sh -c 'printf "edited-%s" "'"$NONCE"'" >> "'"$PERSONAL_CODEFILE"'" 2>/dev/null; echo "save_rc=$?"'   # expected: save_rc=0
docker exec -u coder "$CS" sh -c 'printf "new" > "'"$WSTEST_ROOT"'/by_editor.code" 2>/dev/null; echo "create_rc=$?"'           # expected: create_rc=0
# (c) coder CANNOT read a workspace's private secret (behavioral — the ws-test own sentinel from C2-own):
docker exec -u coder "$CS" sh -c 'cat "'"$WSTEST_CFGDIR"'/own.sentinel" >/dev/null 2>/tmp/c5.$$; echo "rc=$?"; grep -qi "permission denied" /tmp/c5.$$ && echo DENIED; rm -f /tmp/c5.$$'
#   expected: rc != 0  AND  DENIED
# (d) editor↔agent files are MUTUALLY readable in the same workspace (both directions — the
#     "editor-created file invisible to the agent" break must not recur):
docker exec -u ws-test "$CS" sh -c 'printf "x" > "'"$WSTEST_ROOT"'/by_agent.code"'                     # agent creates
docker exec -u coder   "$CS" sh -c 'cat "'"$WSTEST_ROOT"'/by_agent.code"  >/dev/null 2>&1; echo "editor_reads_agent_rc=$?"'   # expected: rc=0
docker exec -u ws-test "$CS" sh -c 'cat "'"$WSTEST_ROOT"'/by_editor.code" >/dev/null 2>&1; echo "agent_reads_editor_rc=$?"'   # expected: rc=0
# (e) INFORMATIONAL — the human opens $WSTEST_ROOT/by_agent.code in the BROWSER editor and it
#     renders / saves. The experiential gate is Step 9; recorded, not gated.
```
- **PASS iff** (a) both rc=0, (b) `save_rc=0` and `create_rc=0`, (c) rc≠0 + `DENIED`, (d) BOTH
  `editor_reads_agent_rc=0` and `agent_reads_editor_rc=0`.
  [behavioral items 4 & 5: editor reads+saves code but not secrets; editor and agent read each
   other's files in both directions]
- **Now-status:** needs A2′ active + PF-3 → **BLOCKED today**.

---

### C6 — Git identity: a commit in `ws-test`'s tree carries `ws-test`'s identity  [seed 6]

**Runs as:** `ws-test` (the agent's uid), inside `$CS`.
```sh
docker exec -u ws-test "$CS" git -C "$WSTEST_ROOT" config user.email   # expected: ws-test@example.invalid
docker exec -u ws-test "$CS" git -C "$WSTEST_ROOT" config user.name    # expected: ws-test bot
docker exec -u ws-test "$CS" sh -c '
  d="'"$WSTEST_ROOT"'/.idcheck"; rm -rf "$d"; git init -q "$d" \
  && git -C "$d" commit -q --allow-empty -m t \
  && git -C "$d" log -1 --format="%an <%ae>"; rm -rf "$d"'
#   expected: ws-test bot <ws-test@example.invalid>
docker exec -u ws-personal "$CS" git -C "$PERSONAL_ROOT" config user.email   # expected: != ws-test@example.invalid
```
- **PASS iff** the configured identity **and** the real commit author both equal the ws-test
  sentinel identity **and** personal's resolved email differs.
- **Now-status:** needs the per-workspace git identity + provisioning → **BLOCKED today**.

---

### C7 — Ecosystem hooks: targets derivable from the registry entry ALONE  [seed 7]

**Runs as:** host operator. Read **only** `$REGISTRY`.
```sh
KB=$(ws_field "$WS_TEST_SLUG" kb_repo)                  # expected: matches ^kb-ws-.+  (kb-ws-test)
ROOT=$(ws_field "$WS_TEST_SLUG" root)                   # expected: non-empty (clone lands under here)
echo "$KB" | grep -qE '^kb-ws-.+' && [ -n "$ROOT" ] && echo "KB_DERIVED=$KB -> $ROOT/"
SS=$(ws_field "$WS_TEST_SLUG" secret_store)             # expected: non-empty REFERENCE (keychain:/vault:/path)
[ -n "$SS" ] && echo "SECRET_STORE=$SS"
for S in "$WS_PERSONAL" "$WS_TEST_SLUG"; do
  U=$(ws_field "$S" unix_user); [ "$U" = "ws-$S" ] || echo "LAW_VIOLATION:$S=$U"     # ws-<slug> law
  ws_field "$S" workspace_id | grep -qE '^[0-9]+$' || echo "BAD_ID:$S"
done
ws_field "$WS_PERSONAL" workspace_id; ws_field "$WS_TEST_SLUG" workspace_id          # expected: two DIFFERENT integers
grep -nE '^\s*[A-Z][A-Z0-9_]{2,}=[^ ]+' "$REGISTRY"    # expected: empty — no inline credential
```
- **PASS iff** `kb_repo` matches `^kb-ws-.+` and `root` non-empty; `secret_store` a non-empty
  reference; every entry satisfies `unix_user == ws-<slug>` with an integer `workspace_id`, and the
  two ids differ; and the inline-assignment grep is empty (a real `GIT_TOKEN=ghp_…` would match and
  FAIL; a pointer `secret_store: keychain:test` does not).
- **Now-status:** needs the registry + the ws-test entry (from C1) → **BLOCKED today**.

---

### C8 — Registry validate script fails loudly on a seeded mismatch  [seed 8]

**Runs as:** host operator, on the fork checkout. Run **after teardown** (registry restored, ws-test
gone). `$VALIDATE_CMD` = the tracked validator's invocation (resolved at Step 8).
```sh
# V0 — entrypoint discovered AND wired (PF-5):
git -C "$REPO" ls-files | grep -iE 'validate.*(workspace|registry)|(workspace|registry).*validate'   # expected: ≥1
grep -qiE 'workspace|registry|validate' "$REPO/.pre-commit-config.yaml"; echo "wired=$?"              # expected: wired=0
# V1 — baseline pass:
$VALIDATE_CMD; echo "exit=$?"                            # expected: exit=0
# V2 — seeded mismatch: an entry naming a Unix user / root that do not exist live:
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
# V3 — clean restore:
git -C "$REPO" checkout -- "$REGISTRY"
$VALIDATE_CMD; echo "exit=$?"                            # expected: exit=0
git -C "$REPO" status --porcelain "$REGISTRY"            # expected: empty
```
- **PASS iff** V0 finds a wired validator, V1 exits 0, **V2 exits non-zero AND its output contains
  `ghost-$NONCE`** (loud + specific), and V3 exits 0 with a clean `git status`.
- **Now-status:** needs the validate script + wiring (fork) → **BLOCKED today**.

---

## 5. Teardown (always run after the checks — restores live state, zero collateral)

**Runs as:** host operator (deprovisioning is a root, host-side action).
```sh
WSTEST_ROOT=$(ws_field "$WS_TEST_SLUG" root)
docker exec -u root "$CS" sh -c 'pkill -u ws-test 2>/dev/null; sleep 1; userdel ws-test 2>/dev/null || true'
docker exec -u root "$CS" sh -c 'rm -rf "'"$WSTEST_ROOT"'"'
docker exec -u root "$CS" sh -c 'rm -f /etc/sudoers.d/*ws-test* "/tmp/alpha-wrap-t0-'"$NONCE"'" 2>/dev/null; true'
git -C "$REPO" checkout -- "$REGISTRY"
```
Collateral assertions (teardown must have restarted nothing and restored everything — behavioral):
```sh
docker inspect "$CS" --format '{{.State.StartedAt}} {{.State.Pid}}'          # == CS_0 (never restarted, whole run)
docker exec -u root "$CS" id ws-personal                                     # still resolves (personal intact)
docker exec -u ws-personal "$CS" sh -c 'cat "'"$PERSONAL_SECRET"'" >/dev/null 2>&1; echo "rc=$?"'   # rc=0 (personal still reads its own secret)
docker exec -u root "$CS" id ws-test 2>&1 | grep -q 'no such user' && echo "WSTEST_GONE"            # expected: WSTEST_GONE
git -C "$REPO" status --porcelain "$REGISTRY"                                # empty (registry restored)
```
- **PASS iff** `$CS` StartedAt/Pid equal their C1 "BEFORE" values, `ws-personal` still resolves and
  still reads its own secret, `ws-test` no longer resolves, and the registry is clean. (No mode is
  asserted — restoration is judged by behavior: personal still works, ws-test is gone.)

---

## 6. Verdict rule (binary)

**Mandatory checks** (every one must PASS):

`SRV-1`, `SRV-2`, `SRV-3`, `INF-1`, `G9` (a–c), `C3` (a–e), `C1-a…-e`, `C2-own`, `C2-cross`,
`C2-audit`, `C2-code`, `C2-wrap` (w-0, w-1, w-2, w-3), `C4` (a, b, c, d, d′, f), `C5` (a–d),
`C6`, `C7`, `C8` (V0–V3), and the **§5 teardown-collateral** assertion.

```
verdict = PASS    if every mandatory check PASSES
verdict = FAIL    if any single mandatory check FAILS
verdict = BLOCKED if any hard precondition PF-1..PF-8 is unmet (report which; not a PASS/FAIL)
```

No partial credit, no judgment calls. **Informational** items — C2-wrap's da-session corroboration,
C3's narrow-grant listing, C4(e)'s `claude` status, C5(e)'s browser render, C1's terminal-profile
presence, SRV-4 — are reported for context and **never** change the verdict.

**Pre-implementation expectation (2026-07-16):** most checks **BLOCK** (A2′ not yet active — the
recreate window is pending and `ws-launch` is unbuilt). The exceptions, and why, are the table in
§2: `SRV-1/2/3` expected-**PASS** now (stack already stopped); `G9`, `C3-a/b`, `INF-1` expected-**FAIL**
now (fork artifacts + wrapper unbuilt; `NOPASSWD` removal + resource limits activate only on
recreate). This is correct — the test predates the code it judges.

---

## 7. Findings & interpretation notes

**Behavioral interpretation choices (still live, resolved at re-seal):**

1. **The denial's observability is a real requirement, and it is not free.** A plain DAC `EACCES` is
   returned only to the caller; the kernel does not log it. The plan's "the denial is observable /
   logged" therefore depends on a host audit deliverable. The infra report confirms auditd is
   INSTALLED + ACTIVE and the "free denial" claim was wrong (the pm's finding stood). So **PF-7 is
   hard** and **C2-audit is mandatory** — asserted behaviorally ("an entry appears via `ausearch`
   for the attempt"), never by rule syntax.
2. **The wrapper is a security control, gated as one, with no login required** — C2-wrap w-0
   (wiring), w-1 (workspace-path resolve+run), w-2 (real uid drop), and **w-3 (fail-closed from an
   unknown path — never a fallback to `coder`)**. w-3 is now a defined, mandatory behavior: the
   infra report's `ws-launch` contract makes "cwd maps to no known workspace → error out; NEVER fall
   back to coder" the specified behavior, closing the prior "wrapper-from-non-workspace-cwd" gap.
3. **Personal must be migrated before Step 8 (PF-3).** C2/C4/C5 need a second real workspace as the
   cross-read counterpart. Confirmed as a hard Step-7 precondition.
4. **G9 gates BOTH `omnigent/` AND `web/`**, with `BASE` = the RE-SEAL commit (PF-6).
5. **Cross-workspace CODE opacity is a graded behavior (C2-code)** — a workspace is a client
   company; its source is confidential, not just its secrets. The infra report's first mechanism
   *leaked code* (`ws-clientb` read `ws-clienta`'s source) — exactly the failure C2-code catches, at
   the behavioral level, independent of whichever mechanism is used to close it.
6. **Editor read-AND-save + bidirectional readability are graded behaviors (C5).** The infra report
   measured two mechanism-specific breaks (`640` blocked `coder` saving; an editor-created file was
   invisible to the agent). Both are now behavioral pass/fail lines (C5-b save/create; C5-d both
   directions) — so any future mechanism must satisfy the behavior, not a mode.
7. **Container-plane names bind at Step 8** — `$CS`, `$VALIDATE_CMD`, `$WS_LAUNCH`, the registry
   top-level shape, and the discovered `PERSONAL_SECRET`/`PERSONAL_CODEFILE` — logic-neutral.
8. **SRV-1..3 + INF-1 stay mandatory** — they gate real Stage-1 deliverables (server stop-but-
   preserve, the `127.0.0.1:8000` liability closed, `omnigent-host` disabled, E2 limits); acceptance
   that ignored them could pass with the injected-agent liability live. Neither asserts a
   file-permission mechanism.

**VOIDED by the mechanism-agnostic ruling (retained only as history in the prior seal block):**

- **`C2-struct` — DELETED.** It asserted `stat` = owner/group + modes `600`/`640`/`750`. Modes,
  groups, ACLs, and setgid are the implementer's choice; the infra report proved the specific modes
  it named were wrong. Its intent (the boundary is really applied) is fully covered by the
  behavioral C2-cross / C2-code / C5.
- **Old finding 5 ("setgid design forced by C2-code + C5-d") — VOID.** The re-seal does not force
  any mechanism. C2-code and C5 assert the *behaviors*; how the implementer achieves them (setgid,
  ACLs, `2770`, or a future scheme) is out of scope for the test. The infra measurement in fact
  replaced setgid-group-`coder` with own-group + ACLs.
- **Old finding 1's mode/rule-coupled framing — SUPERSEDED.** The observability requirement is kept
  (C2-audit, mandatory); the specific rule syntax it named is not graded.
- **Hand-rolled `chmod 640/600/750` fixtures — DELETED.** Fixtures now come from the real
  provisioning script (C1 tests reality) and from owner/editor-created sentinels; cross-read targets
  are discovered behaviorally (§3), never by `-perm`.
- **C1-e / C4-b / teardown mode `stat`s — DELETED**, replaced by behavioral equivalents (owner
  controls its tree; state base is private because `coder` is denied; personal still works).

---

## RE-SEAL block (da, 2026-07-16) — immutable after this point

**Re-sealed.** `status: sealed`, `sealed_at: 2026-07-16`, `resealed_at: 2026-07-16`. No edits after
this line — a further post-seal change is a governance violation (the `de` never touches it; the
`da` does not touch it again absent a fresh human ruling).

**Scope of this re-seal (bounded, one-time):** DELETE every implementation-mechanism PASS/FAIL
criterion (file modes, group names, ACLs, setgid — including the whole `C2-struct` check and the
`chmod` fixtures); KEEP every observable behavior, rephrased to be implementation-independent. The
graded behaviors are **unchanged** from the prior seal — they are exactly those the vps-infra
architect reported measuring **passing** under the corrected mechanism
(`reviews/workspace-layer_infra-report.md`).

**Bias control:** designed/re-designed from the spec's behavior-level acceptance criteria; re-sealed
**before Step 8 ever ran** (this test has never been executed against any implementation); driven by
**independent** infra measurement of the mechanism, not by observing this test pass or fail. No
behavioral pass/fail line was weakened to fit code.

**BASE pin (for G9):** the **RE-SEAL commit** — the git commit that carries this block. Step-8 runs
`git diff <reseal-commit>..HEAD -- omnigent/ web/` and expects it EMPTY; anti-vacuousness is checked
against the tree (`git ls-files`). The exact hash is recorded in this re-seal's commit message and
the activity-log line (pm action; separation of duties).

**Authority:** performed under the human governance ruling of 2026-07-16 (an alpha test must assert
observable behavior, not mechanism). Absent that ruling this re-seal is void and the prior sealed
version below is authoritative.

---

## PRESERVED — prior Step-6 seal block (da/pm, 2026-07-16) — HISTORY, superseded above

> Retained verbatim as this file's own audit trail. The mechanism-coupled resolutions here (the
> `C2-struct` check; finding 5's "setgid forced"; finding 1's rule-coupled framing; the
> `640/750/600` file-layout as PASS/FAIL) are **SUPERSEDED for PASS/FAIL** by the RE-SEAL above,
> which deletes them per the 2026-07-16 mechanism-agnostic ruling after the vps-infra architect
> measured the named mechanism to leak code and break the editor
> (`reviews/workspace-layer_infra-report.md`). Preserved, not erased.

### Prior Step-6 SEAL block — verbatim (pm, 2026-07-16)

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

### Why the above is now history, not law

During Step-7 the architect built provisioning + the group model (#3/#7) and **measured**
the setgid-group-`coder` model leaking code cross-workspace and breaking editor
save/agent-read; it was replaced (own per-workspace group + dirs `2770` + POSIX ACLs +
secrets `0700`). The prior seal's mechanism assertions (finding 5's forced setgid, the
`C2-struct` modes, finding 1's rule-coupled framing) would thus **FAIL a correct
implementation** — the defect the RE-SEAL above corrects by grading behavior instead. The
behavioral resolutions (auditd observability mandatory, C2-code opacity, SRV/INF, narrow
cross-uid path, personal migration, G9 over both trees) all **carry forward unchanged**.
