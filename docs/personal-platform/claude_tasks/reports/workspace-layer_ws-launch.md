---
type: report
task: workspace-layer
title: "ws-launch — privilege-drop launcher (Step-7 implementation report)"
status: final
author_role: de
created: "2026-07-16"
related_decisions:
  - "workspace-layer.md (FROZEN spec — permission model superseded by the infra report)"
  - "reviews/workspace-layer_infra-report.md (authoritative wrapper contract + FINAL permission model + sudoers rule)"
  - "alpha_tests/workspace-layer.md (SEALED — C2-wrap w-0..w-3, C3-c..e, C4-f validate the drop at Step 8)"
---

# ws-launch — Step-7 implementation report

Built against the FROZEN spec + the architect's infra report (the authoritative contract). This
is a **security control**; it is written and tested as one, not as a convenience wrapper.

> **Revision 2 (post code-reviewer round 1, 2026-07-16).** The `code-reviewer` gate returned
> NOT SAFE TO COMMIT — 1 CRITICAL + 3 warnings + 3 suggestions
> (`reviews/workspace-layer_code-reviewer_ws-launch.md`). All are fixed in this revision; see
> **§0**. The fixes are uncommitted on `feat/ws-launch` for the re-run gate. Test count 13 → 19
> (adds the PATH-poisoning regression test the reviewer called the single most important one).

## 0. Post-review revision — every finding addressed

**C-1 (CRITICAL) — elevated `exec` + phase-2 helpers ran under a coder-controllable `PATH`
(arbitrary code as any `ws-<slug>`).** The reviewer was right: I hardened every *input* the
wrapper reads but left `PATH` — a coder-controlled input — to govern the post-drop `exec` and its
helpers, so the narrow single-command sudo grant could become arbitrary code as a workspace uid
unless an unverifiable sudoers `secure_path` happened to strip it. Fixed **self-contained, not
depending on external config**:
- **Trusted `PATH` set as the very first executable line** (before `set -u`, before any command):
  `PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin; export PATH`. This governs
  every helper lookup (`id`/`stat`/`getent`/`sudo`) in **both** phases — the drop re-execs the
  same script, so phase 2 re-runs this line too (verified: the trusted-`PATH` line is at the top,
  so each of the two script invocations sets it before running anything).
- **`claude` is exec'd by an absolute, root-owned path**, never a bare name: resolve to
  `/usr/local/bin/claude` (or `command -v claude` under the now-trusted PATH), then **require the
  binary is owned by root (uid 0)** or fail closed. So even a same-name entry earlier on `PATH`,
  or a coder-writable binary on a trusted dir, cannot be substituted. The wrapper no longer
  *depends* on `secure_path`; it is now belt-and-suspenders (handoff #3).

**W-1 — `sudo` without `-n` could hang on a pty password prompt instead of failing closed.** The
drop is now `exec sudo -n -u ws-<slug> …`: any sudoers/registry mismatch exits non-zero
immediately (the "exit non-zero" half of the fail-closed contract), never a prompt/hang.

**W-2 — the slug "safe token" gate used `grep -Eq '^…$'`, which matches per line** so
newline-bearing input passed. Replaced with a newline-proof POSIX `case` glob
(`case "$_base" in ''|[.-]*|*[!A-Za-z0-9._-]*) …no-match…`). The UID/GID numeric gates moved to
`case` globs too (no `grep` remains in `resolve()`).

**W-3 — the drop-path exec integrity had no test at any layer.** Added **T15** (dynamic): prepend
a hostile `stat`/`grep`/`id`/`getent`/`sudo`/`claude`/`ls` dir to `PATH`, run `--resolve-only`,
and assert the real helpers ran (resolution correct), **no marker file was written**, and no
`POISONED` token leaked. Plus static proofs **T16–T19** (trusted `PATH` set+exported early; no
bare `exec claude`; claude exec'd by absolute var path; drop uses `sudo -n`). Non-vacuity was
confirmed with a negative control — the pre-fix wrapper under the same poison *runs* the poison
(`marker: stat,ls,id`) and breaks resolution; T15 catches it. (The reviewer also asked to extend
**sealed C2-wrap** with a PATH-poison check at Step 8 — I cannot touch the alpha-test wall, so
that is recorded as a recommendation to da/pm in §7, not an edit.)

**S-1 (uid floor)** — `resolve()` now rejects `UID < 1000` (not only `UID<=0`), so a system/editor
uid in a conf is refused; the registry-curation invariant still owns the finer 2001+ rule.
**S-2 (HOME)** — phase 2 sets `HOME` to the workspace user's real home (via `getent passwd`)
before exec, so per-workspace Claude state is deterministic instead of inheriting coder's `HOME`.
**S-3 (portable `stat`)** — owner lookup is via a portable `owner_uid()` helper (`stat -c` with a
POSIX `ls -n` fallback), so a base-image swap cannot silently flip the anchor to fail-closed.

## 1. What was built

| File | Purpose |
|---|---|
| `deploy/personal-platform/ws-launch` | The launcher. POSIX `sh` (dash-clean), deps = coreutils + sudo only. |
| `deploy/personal-platform/test-ws-launch.sh` | Offline security harness. **19 checks**; returns non-zero on any failure. |

Absolute paths:
- `/home/coder/repos/omnigent/deploy/personal-platform/ws-launch`
- `/home/coder/repos/omnigent/deploy/personal-platform/test-ws-launch.sh`

## 2. Path choice + rationale

`deploy/personal-platform/`. `deploy/` already exists upstream as a set of per-target
deployment integrations (`boxlite/`, `cloudflare/`, `docker/`, `e2b/`, `fly/`, …); a new
`personal-platform/` subdir there is (a) semantically correct — `ws-launch` is a deployment
artifact baked into the code-server image — (b) clearly ours and (c) upstream-merge-safe (a
future `git merge upstream/main` never creates `deploy/personal-platform/`, so no conflict).
It mirrors the docs namespace (`docs/personal-platform/`). This was the task's first-suggested
option and it satisfies **G9** (zero files under `omnigent/`/`web/`) — verified: the change set
is entirely under `deploy/personal-platform/` + this report under `docs/`.

The fork holds the **source of truth**, versioned; the architect bakes it into the image
(§7). Sibling fork deliverables (the product `workspaces.yaml`, the registry-validate script,
the runbook, the escalation-stages doc) are **separate deliverables**, not part of this task —
recommend co-locating them consistently, but that is the pm's/another session's call.

## 3. Resolution + fail-closed logic (the security core)

**Resolve cwd → workspace → uid, against the ROOT-OWNED infra registry** (this answers the
infra report's OPEN QUESTION in the architect's favor, as the task conceded): the launch path
reads `/etc/code-server-workspaces/<slug>.conf` (root-owned, read-only, `SLUG`/`UID`/`GID`).
It does **not** read the fork's `workspaces.yaml` — a coder-writable registry would itself be
the bypass.

Algorithm:
1. `cwd = pwd -P` (physical; defeats symlink games).
2. Walk cwd's ancestors toward `/`. A directory is the workspace **iff** its basename is a
   registered slug (`<basename>.conf` exists) **AND** the directory is really **owned by that
   slug's registered `UID`**. Shallowest such ancestor wins (the workspace sits directly under
   the inferred root). The registry root is **not** hardcoded — it is inferred as the parent of
   the ownership-verified workspace dir, honoring "do not hardcode a home that may differ."
3. Conf must be well-formed (all checks newline-proof `case` globs): `SLUG` == filename,
   `UID`/`GID` all-digit, `UID` **at/above the 1000 floor** (non-root, non-system), `GID`
   non-root, slug a safe token. Any deviation ⇒ treated as no match.
4. `umask 007`, then drop: `exec sudo -n -u ws-<slug> /usr/local/bin/ws-launch "$@"` (re-entrant
   — see §4), which re-enters as the workspace uid, sets `HOME`, and execs `claude` **by an
   absolute root-owned path** under a **trusted `PATH`** the script sets as its first action
   (§0 C-1) — so the elevated exec cannot be redirected by a coder-controlled `PATH`.

**FAIL CLOSED everywhere.** cwd under no registered slug, cwd outside any workspace, a
look-alike directory, an unreadable/malformed conf, or an unreadable registry → a stderr error
and non-zero exit, **before any exec**. There is no default and no `coder` fallback — the error
message itself states "refusing to run as coder".

### The ownership anchor — why it is load-bearing (a security decision I made explicit)

The contract says "derive the candidate slug from the cwd path … require `<slug>.conf` exists".
Name-matching **alone** is trivially spoofable and would defeat A2′: an injected agent as
`coder` could `mkdir /tmp/clientb; cd /tmp/clientb; <launch>` and, because `clientb.conf`
exists, drop into `ws-clientb` and read clientb's secrets — the exact cross-workspace reach the
layer forbids. The wrapper therefore additionally requires
`owner(<workspace_dir>) == <registered UID>`. A coder-made look-alike is owned by `coder`, not
by `ws-clientb`, so it fails closed; `coder` holds no root (NOPASSWD:ALL removed) so it cannot
forge the ownership. This realizes the contract's rule-4 ("cwd not under the workspaces root →
fail closed") without a hardcoded root path. It aligns with the FINAL permission model (workspace
dir owner = `ws-<slug>`) — see the invariant the architect must hold in §7.

## 4. Two design decisions that deviate from the literal spec text — flagged, not silent

Per my card I do not silently deviate. Two points reconcile the contract's illustrative text
with the architect's **authoritative** infra report; both need the architect's confirmation
(§7), and both are consistent with the observable the sealed test grades (a `claude` running as
`ws-<slug>`):

1. **Re-entrant drop, not `sudo … claude`.** The contract's step 3 reads
   `exec sudo -u ws-<slug> claude`, but the infra report's deployed sudoers rule authorizes the
   command **`/usr/local/bin/ws-launch`** (`coder ALL=(ws-<slug>) NOPASSWD: /usr/local/bin/ws-launch`),
   not `claude`. `sudo -u ws-<slug> claude` would not match that rule → password prompt → the
   launch would never work. So the wrapper drops by re-execing **its own authorized literal
   path** and, on re-entry as the workspace uid, execs `claude`. This is also the *secure*
   reading: sudo authorizes a command by path, so the path must be root-owned/immutable (which
   `claude`'s install path may not be). The phase discriminator is the **euid check**
   (`id -u == resolved uid`), never a forgeable flag — a forged re-entry as `coder` can never
   reach `exec claude` because coder's uid never equals a resolved workspace uid.
2. **The wrapper sets `HOME` (post-review, S-2) but not `CLAUDE_CONFIG_DIR`.** Setting
   `CLAUDE_CONFIG_DIR` remains the provisioning script's deliverable in the work-split table, not
   the wrapper's 6-point contract. But to make per-workspace state deterministic rather than
   inherited-from-coder across the drop, phase 2 now sets `HOME` to the workspace user's real home
   (read from `getent passwd`, no hardcoded path) — so claude defaults to `<home>/.claude`, the
   FINAL model's per-workspace config dir. Sealed test **C4-f** validates this at Step 8; if it
   needs the wrapper to also own `CLAUDE_CONFIG_DIR` explicitly, that is a small follow-up.

## 5. Self-review checklist

- **Contract coverage (infra report §"Contract for ws-launch"):** (1) resolve cwd→slug against
  the root-owned registry ✓; (2) `umask 007` before exec ✓ (applies to both branches + phase-2);
  (3) drop to the workspace uid **and run *claude*, not arbitrary code** ✓ (re-entrant §4.1;
  exec integrity closed by the C-1 fix — trusted `PATH` + absolute root-owned claude, §0); (4)
  fail closed, never coder ✓ (verified §6; W-1 `sudo -n` closes the hang corner case); (5)
  pty/stdio transparent via clean `exec`, no lingering wrapper ✓ (validated live at Step 8). Plus
  the two extra deliverables: `--resolve-only` dry-run ✓; test harness ✓.
- **Exec integrity (post-review):** trusted `PATH` set before any command in both phases; `claude`
  and all helpers resolved from trusted dirs; `claude` additionally required root-owned; verified
  by T15–T19 and a negative control (§0/§6).
- **No hardcoded config/credentials/URLs (CLAUDE.md §6/§9):** none. The one hardcoded path
  (`/etc/code-server-workspaces`) is a security *constant*, not config — it is deliberately
  non-overridable in the launch path (an env-movable registry would let a coder-set env choose
  the drop target). `WS_LAUNCH_REGISTRY` is honored **only** under `--resolve-only` (a no-exec
  diagnostic), commented as such.
- **Fail-closed by construction:** no code path reaches an `exec` without an ownership-verified
  slug/uid; every doubt routes through `fail()` (stderr + non-zero). No `set -e` reliance —
  failure is structural, not incidental.
- **No `eval`/`source` of registry data** (a security control never executes its data files);
  safe `KEY=VALUE` parse; slug charset-validated before use in `sudo -u ws-$slug` (quoted).
- **Error handling / conventions:** POSIX `sh` for the guaranteed base-image shell (`/bin/sh`
  is dash); `set -u`; comments short and scenario-focused on the WHY (CLAUDE.md §8).
- **Static gates:** `sh -n` clean on both files (revised); no trailing whitespace, no CRLF, final
  newline present; repo pre-commit hooks are scoped to Python/`^web/`/Android and do **not** touch
  these shell files, so a later commit lands clean. `shellcheck` is **not installed** on this box
  (installing it is a system change requiring consent); the round-1 code-reviewer confirmed the
  same and reviewed manually + by targeted execution.
- **Language:** English throughout (code/comments/report), per CLAUDE.md §1.

## 6. Tests — exact commands + output

Run here (this box: no `ws-*` users, blanket sudo still present, A2′ NOT active — so the real
privilege drop cannot be exercised; that is Step 8). The harness exercises the security-critical
half — resolution + fail-closed — non-circularly via `--resolve-only` against a mock registry,
using the runner's own uid as the legitimate owner and a mismatched uid to simulate the
look-alike-directory spoof.

```
$ deploy/personal-platform/test-ws-launch.sh
PASS T0-artifact-executable-shebang
PASS T1-under-registered-slug
PASS T2-at-workspace-dir
PASS T12-nested-lookalike-bypassed
PASS T3-unregistered-slug
PASS T4-outside-workspaces-root
PASS T5-ownership-spoof
PASS T6-slug-filename-mismatch
PASS T7-missing-uid
PASS T8-uid-zero-root
PASS T9-uid-non-numeric
PASS T14-uid-below-floor
PASS T10-registry-absent
PASS T11-conf-unreadable
PASS T15-poisoned-PATH-does-not-run-helpers
PASS T16-trusted-PATH-set-and-exported-early
PASS T17-no-bare-exec-claude
PASS T18-claude-exec-by-absolute-var-path
PASS T19-drop-uses-sudo-n
-----------------------------------------
ws-launch security tests: 19 passed, 0 failed   (exit 0)
```

Mapping to the task's required coverage: correct cwd under a registered slug → right uid
(T1/T2/T12); unregistered slug → fail closed (T3); cwd outside the workspaces root → fail closed
(T4); unreadable/malformed/out-of-range entry → fail closed (T6–T11, T14); **the critical
negative — no input path yields a `coder` fallback** (every fail-closed check asserts non-zero
exit **and** no resolved slug on stdout, so the launch path — which execs only after a successful
resolve — can never fall through to a coder launch). T5 is the anti-bypass ownership anchor;
**T15 is the C-1 regression** (poisoned `PATH` does not run poison helpers); T16–T19 statically
prove the exec-integrity fixes.

**C-1 non-vacuity — negative control (not part of the committed harness).** Same poison scenario
against a copy of the wrapper with the trusted-`PATH` lines stripped (the pre-fix state):
```
# UNFIXED wrapper, poisoned PATH → the poison helpers RUN and resolution breaks:
rc=1  out='ws-launch: … refusing to run as POISONED'   poison-ran marker: YES (stat,ls,id)
# FIXED wrapper, identical poison → real helpers run, clean resolve, nothing poisoned:
rc=0  out='slug=personal uid=1000 gid=1000'            poison-ran marker: NO
```

Direct output separation (stdout = resolution, stderr = refusal):
```
# success: owner == registered uid
$ (cd <root>/demo/src && WS_LAUNCH_REGISTRY=<mock> ws-launch --resolve-only)
slug=demo uid=1000 gid=1000              # stdout, rc=0

# fail-closed: cwd outside any workspace
$ (cd /tmp && WS_LAUNCH_REGISTRY=<mock> ws-launch --resolve-only)
ws-launch: no registered workspace owns /tmp (fail-closed; refusing to run as coder)   # stderr, rc=1
```

## 7. Handoff — for the architect (bake) and for Step 8 (live validation)

**Deployment snippet (the `COPY` line is yours; here for reference):**
```dockerfile
COPY deploy/personal-platform/ws-launch /usr/local/bin/ws-launch
RUN chown root:root /usr/local/bin/ws-launch && chmod 0755 /usr/local/bin/ws-launch
```

**Assumptions the wrapper makes — please confirm they match your build:**
1. **Registry mount path.** The launch path reads `/etc/code-server-workspaces/<slug>.conf`.
   Your infra report proposed mounting `/opt/code-server/workspaces.d/<slug>.conf` read-only at
   exactly `/etc/code-server-workspaces` — **match**; please confirm the mount point and that
   confs are `KEY=VALUE` with `SLUG`/`UID`/`GID` (one per line).
2. **Sudoers reconciliation (CRITICAL — see §4.1).** The wrapper drops via
   `sudo -u ws-<slug> /usr/local/bin/ws-launch …`. Confirm the rule authorizes
   `coder ALL=(ws-<slug>) NOPASSWD: /usr/local/bin/ws-launch` as a **path-only** Cmnd (any args
   allowed). If you instead authorized a `claude` path, the wrapper and rule disagree and
   C2-wrap w-1/w-2 will fail.
3. **cwd across the drop.** The re-entrant design relies on `sudo` **preserving cwd** (so phase-2
   re-resolves the same slug). Confirm no sudoers `cwd`/chdir override.
3b. **`claude` MUST be installed root-owned on a trusted PATH dir (HARD — the wrapper now enforces
   it).** Post-review (C-1), phase 2 execs `claude` by an absolute path resolved from a trusted
   `PATH` the script sets itself, and **refuses to run a `claude` not owned by root (uid 0)** —
   fail-closed. `/usr/local/bin/claude` (root:root) is the expected location. If the image installs
   `claude` coder-owned or on a non-trusted dir (e.g. an npm global under `~coder`), **every
   workspace launch fails closed** until it is moved. This is the correct posture (a coder-writable
   claude is itself the vulnerability), but it means you must confirm/relocate the install. sudo
   `secure_path` is now **belt-and-suspenders**, not required (the wrapper no longer depends on it).
4. **Ownership invariant (load-bearing, §3).** The wrapper anchors on
   `owner(<workspace_dir>) == <registered UID>` — the dir whose basename equals the slug must be
   chowned to `ws-<slug>`. The FINAL permission model already states this; confirm provisioning
   holds it, else legitimate launches fail closed.
5. **Registry-curation invariant.** Confs must only ever declare **real per-workspace uids** —
   the wrapper rejects `UID=0`, but trusts the root-owned registry not to declare `coder`'s uid
   or a system uid as a workspace.
6. **Process-wrapper wiring (Step-8 precondition PF-5 / w-0).** Set
   `claudeCode.claudeProcessWrapper = /usr/local/bin/ws-launch` in the code-server/VS Code
   settings scope so the extension actually invokes the wrapper.

**Validated live at Step 8 (cannot be exercised pre-A2′), covered by the SEALED test:** the
real privilege drop and pty integration — **C2-wrap w-1** (workspace path → resolve + run),
**w-2** (a `claude` process actually runs as `ws-test`), **w-3** (unknown path → fail closed,
never a `coder` claude); **C3-c/d/e** (no lateral sudo between workspace uids); **C4-f** (the
launch wrote Claude state under the workspace's config dir). These require the recreated A2′
container + `ws-*` users + the baked, wired wrapper — the single recreate window the architect
proposed once `ws-launch` is delivered. It is delivered.

**Recommendation to da/pm (I cannot touch the sealed alpha test).** The code-reviewer noted that
sealed **C2-wrap w-1/w-2 drive the real drop but never poison `PATH`**, so a PATH-substituted exec
would pass them unnoticed — the C-1 regression is invisible at the live layer. Consider, under the
governed re-seal process, adding a Step-8 C2-wrap sub-check that a hostile `claude`/`id` prepended
to `PATH` does **not** run as the workspace uid (the live counterpart of harness T15). Offline
T15–T19 + the negative control cover it as far as this box can; the live gap is the da/pm's call.
