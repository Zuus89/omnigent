---
type: review
task: workspace-layer
title: "ws-launch — code-reviewer security gate, iteration 2 (re-review of the C-1/W-1/W-2/W-3 fixes)"
status: final
author_role: code-reviewer
created: "2026-07-16"
related_decisions:
  - "reviews/workspace-layer_code-reviewer_ws-launch.md (iteration-1 review — the findings verified closed here)"
  - "reports/workspace-layer_ws-launch.md (de's Revision-2 fix report, §0)"
  - "reviews/workspace-layer_infra-report.md (authoritative wrapper contract + FINAL permission model + sudoers rule)"
  - "alpha_tests/workspace-layer.md (SEALED — C2-wrap / C3 / C4-f behaviors validated live at Step 8)"
verdict: "SAFE TO COMMIT"
---

# ws-launch — code-reviewer verdict (iteration 2)

## VERDICT: **SAFE TO COMMIT**

No CRITICAL. The single iteration-1 CRITICAL (**C-1**) is **verified closed**, and **W-1 / W-2 /
W-3 are each verified closed**. Two SUGGESTIONS carry forward (defense-in-depth, non-blocking) and
one operational deployment note is restated for the recreate window. Nothing the fixes introduced
rises to CRITICAL or WARNING.

Scope re-reviewed: `deploy/personal-platform/ws-launch` (the control) and
`deploy/personal-platform/test-ws-launch.sh` (its harness), on branch `feat/ws-launch`
(uncommitted, as expected for the re-gate), against the infra-report contract, the FINAL permission
model, and the sealed C2-wrap/C3/C4-f behaviors.

### Evidence gathered (this review, not taken on trust)

- `sh -n` clean on both files.
- Offline harness run here: **19/19 PASS**, exit 0 (T0–T19).
- `shellcheck` still not installed on this box (system change requiring consent); review is manual
  + targeted execution, as in iteration 1.
- **Independent C-1 non-vacuity control (mine, not the de's).** I ran the exact T15 PATH-poison
  scenario against (a) the real wrapper and (b) a copy with *only* the two trusted-`PATH` lines
  stripped:
  - real wrapper → `rc=0`, `out=[slug=personal uid=1000 gid=1000]`, poison marker **empty**;
  - stripped wrapper → `rc=1`, `out=[]`, poison marker **`stat,ls,id`** (the hostile helpers ran).
  This confirms the trusted-`PATH` reset is load-bearing and that **T15 is a genuine regression
  test** — it fails on pre-fix code rather than passing by construction.

---

## C-1 — CLOSED (verified)

**Iteration-1 defect:** after the privilege drop, `exec claude` and the phase-2 helpers
(`id`/`stat`/`grep`) ran by bare name under a coder-controllable `PATH`, turning the narrow
single-command sudo grant into arbitrary code execution as any `ws-<slug>` unless an unverifiable
sudoers `secure_path` happened to strip it.

**Fix verified on every sub-point the re-review demanded:**

1. **Trusted `PATH` is the first executable line, before any external command** — `ws-launch:26-27`
   (`PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin; export PATH`), ahead of
   `set -u` (`:29`) and every helper. Lines 1–25 are comments; nothing runs before it. (T16 + read.)
2. **Re-established in phase 2** — the drop is a re-exec of **this same script**
   (`exec sudo -n -u "ws-$slug" "$SELF" …`, `ws-launch:206`, `SELF=/usr/local/bin/ws-launch` `:39`),
   so the phase-2 invocation re-runs `:26` at the top before any helper. Belt-and-suspenders: phase 1
   also sanitizes `PATH` *before* it exec's `sudo`, so the value flowing through `sudo`'s
   `env_reset` into phase 2 is already the trusted one even when `secure_path` is absent — the
   control no longer depends on external config for its core guarantee. Confirmed empirically above.
3. **`claude` exec'd by a trusted absolute, root-owned path** — `ws-launch:186-197`:
   `claude_bin=/usr/local/bin/claude` (absolute literal), fallback `command -v claude` resolved
   under the now-trusted `PATH` (`:187`), then hard gates: must be absolute (`:188-191`), must be
   executable (`:192`), and **must be owned by uid 0 or fail closed** (`:193-195`). A bare
   `exec claude` PATH-lookup is gone (T17). If the owner can't be determined, `claude_owner` is
   empty and `[ "$claude_owner" = "0" ]` is false → fail closed (`:193-195`).
4. **Root-owned check is not race-/TOCTOU-able, and coder cannot influence the resolved path.** The
   checked file lives on a root-owned trusted-`PATH` directory (`/usr/local/bin`, or another element
   of the hardcoded trusted list — every element is a root-owned system dir). coder holds no write
   on any of them, so it can neither swap the file between the `owner_uid` check (`:193`) and the
   `exec` (`:197`) nor plant a same-name binary/symlink earlier on the path. The absolute default
   and the trusted-`PATH`-only fallback mean the resolved path is entirely root-controlled.
5. **All helpers safe from PATH hijack in BOTH phases** — `id` (`:158`, `:173`), `stat`/`ls`
   (`owner_uid`, `:78`/`:81`), `getent` (`:178`), `sudo` (`:206`) all resolve after `:26` in each
   phase. The independent control confirms the real helpers run (clean resolve, empty marker) while
   the stripped copy runs the poison (`stat,ls,id`).

**Note on offline coverage (honest, not a blocker):** the real privilege drop and pty cannot be
exercised on this box (no `ws-*` users, A2′ not active). T15 exercises the trusted-`PATH` mechanism
via `--resolve-only` (phase 1); T16–T19 statically prove the phase-2-specific exec shape (absolute
`claude`, root-owned check, `sudo -n`). Because phase 2 re-runs the identical top-of-script `PATH`
reset, the mechanism that T15 proves for phase-1 helpers is the same one protecting the phase-2
`exec`. The live phase-2 PATH-poison check remains a Step-8 recommendation to da/pm (the de correctly
did **not** touch the sealed alpha test); it is not a commit blocker, since the wrapper-side
guarantee is structurally closed and offline-proven here.

---

## W-1 — CLOSED (verified)

`exec sudo -n -u "ws-$slug" "$SELF" "$@"` — `ws-launch:206`. `-n` present (T19). Any
sudoers/registry mismatch now exits non-zero immediately (the exec makes it the wrapper's own
non-zero exit) instead of hanging on a pty password prompt — the "exit non-zero" half of the
fail-closed contract. A non-`coder` re-entry (e.g. a conf `UID` disagreeing with the real `ws-<slug>`
uid) is refused by sudo under `-n` rather than looping.

## W-2 — CLOSED (verified)

The slug/UID/GID gates in `resolve()` are newline-proof `case` globs — `ws-launch:111-114`:
`case "$_base" in ''|[.-]*|*[!A-Za-z0-9._-]*) _ok=0` plus `[ "$_cslug" = "$_base" ]` and
`case "$_cuid"/"$_cgid" in ''|*[!0-9]*)`. A shell `case` glob matches the **whole** word and `*`
matches a newline, so a newline-bearing basename is rejected by `*[!A-Za-z0-9._-]*` (newline is a
disallowed char) — the exact bypass W-2 flagged is gone. **No `grep` remains anywhere in the
resolution path** — `resolve()`, `conf_get()` (`:60-69`, `case`-based trim), and `owner_uid()`
(`:74-86`) are all `case`/parameter-expansion only. Verified by read; the only `grep` in the change
set is inside the *test harness*, not the control.

## W-3 — CLOSED (verified)

T15 (dynamic PATH-poison regression) added and **independently confirmed non-vacuous** (fails on
pre-fix code — my control above, and the de's negative control in report §6 agree: stripped code
runs the poison and breaks resolution). T16–T19 add static proofs of the exec-integrity shape. The
harness grew 13→19 and asserts real properties (exact resolution output on the open tests; `rc≠0`
+ no `slug=` on stdout on the closed tests; no marker + no `POISONED` leak on T15). Coverage is real,
not green-by-construction. `$SH` is captured absolute *before* poisoning (`test:20`), so the harness
itself isn't hijacked. The live-layer gap (sealed C2-wrap never poisons PATH) is disclosed and routed
to da/pm under the governed re-seal process — the correct handling, since `de`/`code-reviewer` must
not edit the sealed test.

---

## New issues introduced by the fixes

**None at CRITICAL or WARNING.** The five fix surfaces were each re-checked:

- **Trusted-`PATH` hardcode (`:26`)** — every element is a standard root-owned system dir; no
  coder-writable dir; contains `sudo`/`id`/`stat`/`ls`/`getent`. Sound.
- **Absolute-`claude` resolution + root-owned check (`:186-197`)** — analyzed above; fail-closed on
  missing/non-absolute/non-executable/non-root-owned/undeterminable-owner. No new fail-open path.
- **`HOME` from `getent` (`:178-179`)** — `getent passwd "$uid"` reads root-controlled NSS; the
  6th field is taken and accepted only if it starts with `/`. It affects only claude's state
  location, not the (already-dropped) uid boundary, so it cannot escalate. If `getent` yields no
  home, `HOME` is left inherited — identical to pre-fix behavior, no regression, and any resulting
  cross-read is still DAC-denied. Sound.
- **Portable `owner_uid` (`:74-86`)** — `stat -c '%u'` with a POSIX `ls -dn` field-3 fallback; both
  forms exist on the Debian/Ubuntu code-server base and on BusyBox. A non-numeric/empty result at
  either step returns 1 → fail closed. No portability break, no fail-open.
- **`sudo -n` (`:206`)** — argv passthrough unchanged; `"$@"` follows the command so it cannot inject
  sudo options; the drop target is a quoted single token. Sound.

The full iteration-1 **fail-closed enumeration still holds** (re-verified line-by-line and by
T3–T14): no-slug, outside-root, ownership spoof, unreadable/malformed conf, `UID=0`, `UID` below
floor, `GID=0`, unreadable registry — every one routes through `fail()` before any `exec`, and no
`exec` is reachable without an ownership-verified slug/uid.

---

## SUGGESTIONS (non-blocking, carry-forward)

- **S-1 residual — UID floor still admits the editor uid.** `UID_FLOOR=1000` (`:44`, `:115`) rejects
  system uids but not `1000` itself (coder). Because the phase discriminator is `[ "$(id -u)" = "$uid" ]`
  (`:173`), a *mis-curated* `UID=1000` conf over a coder-owned dir would let phase 1 skip the drop and
  run `claude` as coder — no privilege gain (pre-A2′ status quo), and blocked by the root-owned
  registry-curation invariant, but it rests on curation rather than the wrapper. Raising the floor
  above the editor uid (the deployed model is 2001+) would make the wrapper self-defending here.
- **S-4 (new) — reset `IFS` at the top for defense-in-depth.** The new `owner_uid` `ls` fallback uses
  a default-`IFS` `read` (`:81`). Not exploitable (on the coreutils/BusyBox base `stat -c` succeeds so
  the fallback is unused; a poisoned `IFS` yields a non-matching/empty owner → fail closed, never
  escalation; and phase 2 has `IFS` stripped by sudo's `env_reset`), but an explicit `IFS=' \t\n'`
  (or unset) beside the `PATH` reset would remove the last coder-controlled input that touches a
  parsing path. Optional.

(Iteration-1 S-2/S-3 are addressed: `HOME` set from `getent`; portable `owner_uid`.)

## Operational note for the recreate window (not a wrapper defect)

The root-owned-`claude` gate (`:193-195`) is the correct posture, but it is a **hard deployment
dependency**: if the image installs `claude` non-root-owned or off the trusted `PATH` (e.g. an npm
global under `~coder`), **every** workspace launch fails closed. Confirm/relocate `claude` to
`/usr/local/bin/claude` (`root:root`, `0755`) before or during the recreate window (de handoff #3b).
This is fail-closed, not fail-open — the risk is availability, and the mitigation must be to fix the
install, never to relax the check.

---

## To commit

The change set is entirely under `deploy/personal-platform/` (the control + its harness) plus the
`docs/` report — no files under `omnigent/`/`web/`, and the repo pre-commit hooks don't scope these
shell files. **C-1 closed; W-1, W-2, W-3 closed. SAFE TO COMMIT.** Route the two Step-8 items — a
live phase-2 PATH-poison sub-check in the sealed C2-wrap, and confirmation that `claude` is installed
root-owned — to da/pm/architect; neither blocks this commit.
