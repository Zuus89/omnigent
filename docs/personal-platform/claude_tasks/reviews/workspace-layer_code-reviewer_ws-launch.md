---
type: review
task: workspace-layer
title: "ws-launch — code-reviewer security gate (Step-7, pre-commit)"
status: final
author_role: code-reviewer
created: "2026-07-16"
related_decisions:
  - "reports/workspace-layer_ws-launch.md (de's Step-7 implementation report — path, deviations, self-review)"
  - "reviews/workspace-layer_infra-report.md (authoritative wrapper contract + FINAL permission model + sudoers rule)"
  - "alpha_tests/workspace-layer.md (SEALED — C2-wrap / C3 behaviors the wrapper must satisfy)"
verdict: "NOT SAFE TO COMMIT"
---

# ws-launch — code-reviewer verdict

## VERDICT: **NOT SAFE TO COMMIT**

One CRITICAL. Per Hard Rule 5, any single CRITICAL = NOT SAFE TO COMMIT.

The **resolution + fail-closed core is well-built** (see "What is sound" below) — the ownership
anchor is the right idea and is implemented correctly; the launch-path registry lock is correct.
The blocker is **post-resolution exec integrity**: the wrapper drops privilege and then runs
`claude` (and its own helpers) via an inherited, coder-controllable `PATH`, so the narrow
single-command sudo grant can be turned into arbitrary code execution as any workspace uid unless
an external, unverified sudoers setting happens to strip it. That is the exact "arbitrary command
as another workspace uid" the layer (alpha-test **C3-e**) is designed to forbid, and the wrapper
must close it itself rather than depend on config it does not own.

Scope reviewed: `deploy/personal-platform/ws-launch` (the control) and
`deploy/personal-platform/test-ws-launch.sh` (its harness), against the infra-report contract, the
FINAL permission model, and the sealed C2-wrap/C3 behaviors. Static evidence gathered:
`sh -n` clean on both files; `shellcheck` not installed on this box (deferred by `de`, so this
review is manual + targeted execution); the multiline-grep bypass below was reproduced; the harness
runs 13/13.

---

## CRITICAL

### C-1 — `exec claude` (and phase-2 helpers) run under a coder-controllable `PATH`; arbitrary code execution as any `ws-<slug>`  — `ws-launch:143`, `ws-launch:150` (root cause: no `PATH` is ever set)

**The guarantee being broken.** The sudoers grant is deliberately narrow:
`coder ALL=(ws-<slug>) NOPASSWD: /usr/local/bin/ws-launch` (infra report §2). Its whole safety
argument (alpha-test **C3-e**, and the master-key principle) is: *coder may become `ws-<slug>`, but
only to run the one trusted command `claude` — never an arbitrary command.* The wrapper is what is
supposed to keep that promise after the drop.

**The defect.** After the drop, phase 2 runs external utilities and then `exec claude` **by bare
name**, resolved through `$PATH`:
- `ws-launch:143` `exec claude "$@"` — PATH lookup.
- Phase-2 helpers before it are PATH-resolved too: `id` (`:140`), `stat` (`:83`), `grep` (`:79/:81/:82`).

The wrapper **never sets `PATH`**. Across `sudo`, with the default `env_reset`, the invoking user's
`PATH` is **preserved** unless the sudoers `secure_path` option overrides it. `coder` fully controls
its own `PATH` (shell profile, `terminal.integrated.env`, or just `PATH=… ws-launch` from the
code-server terminal).

**The attack (coder is prompt-injected and wants another workspace's secrets).**
```
coder$ mkdir -p /tmp/evil && cp ~/mysteal /tmp/evil/claude   # or shadow id/stat/grep
coder$ PATH=/tmp/evil:$PATH  ;  cd /workspaces/clientb        # coder has ACL x on every ws dir
coder$ /usr/local/bin/ws-launch                              # the only sanctioned crossing
# phase 1 (coder): resolve -> uid=ws-clientb ; exec sudo -u ws-clientb ws-launch
# phase 2 (ws-clientb): PATH still /tmp/evil:... (no secure_path) -> exec claude
#   -> runs /tmp/evil/claude AS ws-clientb -> reads clientb's .credentials, exfiltrates
```
The single-command grant has become an arbitrary-command grant as `ws-clientb` — the lateral
master key **C3-e** forbids. It does not even need to reach `exec claude`: the first PATH-resolved
helper in phase 2 (`id`/`stat`/`grep`) already runs attacker code as the workspace uid.

**Reachability is real, not theoretical.** `coder`'s only route to another workspace uid *is*
`sudo … ws-launch` (all other sudo was removed, infra #2), so this is the one primitive that is
supposed to be safe, and it is the one being subverted. Confirmed cross-workspace ACL traversal is
by design (FINAL model gives `coder` `u:coder:rwx` on every workspace dir), so `cd /workspaces/<any>`
succeeds.

**Why "delegated to `secure_path`" is not enough to clear this.**
- The `de` correctly *identified* this exact attack and delegated the fix to sudoers `secure_path`
  (report §7, handoff #3). But `secure_path` lives in the **vps-infra** repo, is **not present or
  verifiable in this change set**, and the handoff records it as a *request to confirm*, not a
  confirmed invariant. I cannot verify it from here, so I cannot clear the CRITICAL.
- The consequence if it is absent (plausible on a minimized container image) is **total**: arbitrary
  code as any workspace uid = full defeat of A2′.
- The wrapper otherwise goes to great lengths to trust nothing coder controls (hardcoded registry,
  hardcoded `SELF`, env-override refused on the launch path). Leaving `PATH` — a coder-controlled
  input — to govern the elevated `exec` is an internal inconsistency in the control's own threat model.
- **Neither test layer catches it** (see W-3): the offline harness cannot run phase 2, and sealed
  **C2-wrap w-1/w-2** drive the real drop but never poison `PATH`, so both pass with the hole open.
  The reviewer is the only gate that sees this.

**What a correct version needs (describe, not patch).**
1. Set a fixed, trusted `PATH` at the top of the script (e.g. `PATH=/usr/local/bin:/usr/bin:/bin;
   export PATH`). This hardens phase-1 helper lookups **and** flows through `sudo`'s `env_reset` into
   phase 2 when `secure_path` is absent (and is harmlessly overridden when it is present) — so the
   control no longer depends on external config for its core guarantee.
2. `exec` claude by an **absolute, root-owned path** (the documented trusted install path from
   handoff #3 — "install claude at a path coder cannot write"), not a bare-name PATH lookup, so even
   a same-name entry earlier on `PATH` cannot substitute it.
3. Treat sudoers `secure_path` as a **documented hard deployment invariant** (belt-and-suspenders),
   and extend **C2-wrap** to prove a poisoned `claude`/`id` on `PATH` does **not** run as the
   workspace uid — otherwise the regression is invisible.

---

## WARNING

### W-1 — `sudo` invoked without `-n`: a sudoers mismatch hangs on a password prompt instead of failing closed  — `ws-launch:150`

`exec sudo -u "ws-$slug" "$SELF" "$@"` omits `-n`. The fail-closed contract is "any doubt ⇒ exit
non-zero, before any exec" (`ws-launch:9`, `:32`). A password prompt is neither: on any rule
mismatch (a provisioning drift, a `ws-<slug>` uid that disagrees with the registry `UID` so phase 2
re-enters the drop as a non-`coder` uid, or a Cmnd/path mismatch) `sudo` will **prompt on the pty**
and block — a hang, not a clean refusal. `sudo -n` converts every such case into an immediate
non-zero exit (which, being `exec`-ed, becomes the wrapper's own non-zero exit → the extension sees a
failed launch → genuinely fail-closed). Not a wrong-uid bypass; a violation of the "exit non-zero"
half of the fail-closed contract in the corner cases.

### W-2 — the slug charset validator accepts multiline input — `ws-launch:79`

`printf '%s' "$_base" | grep -Eq '^[a-zA-Z0-9][a-zA-Z0-9._-]*$'` is presented (comment `:77-78`) as
the "safe token" gate. `grep -q` matches **per line**, so any input containing a newline passes as
long as *one* line matches. Reproduced:
```
$ printf 'evil\npersonal' | grep -Eq '^[a-zA-Z0-9][a-zA-Z0-9._-]*$'; echo $?
0        # a newline-bearing basename PASSES the "safe token" check
```
**Not currently exploitable**: `_base` can only carry a newline if a cwd ancestor directory is named
with one, and the match is then blocked downstream by `[ "$_cslug" = "$_base" ]` (`:80`, `_cslug`
comes from `read -r`, single-line, so it can never equal a multiline `_base`) and by the ownership
check (`:84`). So the value is doubly contained. But a validator in a security control that does not
enforce what it claims is a latent footgun one refactor away from mattering. A correct gate uses a
`case` glob (`case "$_base" in *[!A-Za-z0-9._-]* | "" ) …no-match… ; esac`) which is not fooled by
newlines, or anchors the whole input (`grep -Ezq`).

### W-3 — the security-critical exec path (the C-1 attack) is exercised by no test — `test-ws-launch.sh` (whole file) + sealed C2-wrap

The offline harness is honest and non-vacuous for what it covers — the closed-tests pass alongside
exact-output open-tests (T1/T2/T12 assert `slug=…uid=…gid=…`), and **T5** genuinely exercises the
ownership anchor (registered owner ≠ real owner → fail closed). Confirmed: 13/13. **But** it can only
test `--resolve-only` (no privilege drop, no `exec`), so phase 2 — where C-1 lives — is untested here
(acknowledged, `test-ws-launch.sh:4-8`). The gap is that **sealed C2-wrap does not close it either**:
w-1/w-2 drive the real drop but never prepend a hostile `claude`/`id` to `PATH`, so a PATH-substituted
exec would pass w-1/w-2 unnoticed. Result: the single most dangerous property of a privilege-drop
launcher (that the elevated `exec` cannot be redirected) has **no** coverage at any layer. Add a
Step-8 check that a poisoned `PATH` entry does not run as the workspace uid (this also becomes the
regression test for C-1's fix).

---

## SUGGESTION

- **S-1 (`ws-launch:81`) — only `UID<=0` is rejected; no workspace-uid floor.** A registry conf
  declaring `UID=1000` (the editor) or a system uid would be honored. Risk is low — `coder` can only
  *forge* directory ownership equal to its **own** uid (no `CAP_CHOWN`), and that path yields at most
  a `claude` running as `coder` (the pre-A2′ status quo, no escalation) — so this rests safely on the
  registry-curation invariant (handoff #5). Still, a documented minimum workspace-uid floor would make
  the anchor self-defending rather than curation-dependent.
- **S-2 (`ws-launch:150`) — `HOME` across the drop is left to sudo's default.** `sudo` without `-H`
  may leave `HOME=/home/coder` in phase 2, so `claude`'s state location is nondeterministic (ties to
  the `de`'s deviation #2 and sealed **C4-f**). Setting `HOME`/`CLAUDE_CONFIG_DIR` explicitly, or
  `sudo -H`, makes per-workspace state deterministic instead of relying on a Step-8 discovery.
- **S-3 (`ws-launch:83`) — `stat -c '%u'` is GNU-specific.** Fine on a Debian/Ubuntu code-server base
  (BusyBox differs). Worth a one-line note pinning the assumption, since a base-image swap would flip
  the anchor to fail-closed silently.

---

## Architectural observation (not a wrapper defect — for the pm/architect)

The wrapper faithfully implements "resolve cwd → drop → fail closed," and the effective boundary it
enforces is **workspace-to-workspace** (a `ws-personal` agent cannot reach `ws-clientb`). It is worth
recording that A2′'s guarantee against an **editor-plane** compromise is narrower than it may read:
`coder` holds `u:coder:rwx` ACL on **every** workspace tree (FINAL model, required by C5) **and** may
launch a `claude` as **any** single workspace via the sanctioned path. So even with C-1 fixed, an
injected `coder` can drive a `claude`-as-`ws-clientb` to copy `ws-clientb`'s secret into
`ws-clientb`'s code tree, then read it back over its own ACL — cross-workspace exfiltration *by
proxy*, without arbitrary command execution. **C3-e**'s "reads every workspace's secrets by proxy"
concern is only partly closed by restricting the crossing to `claude`, because `claude` is itself a
general read/write agent. This is a property of the shared-editor design (sudoers + ACL), not of
`ws-launch`, and may already be accepted as the semi-trusted-editor / Stage-2b residual — but it
should be an explicit, recorded decision, not an implicit one.

---

## What is sound (verified, worth stating in a security review)

- **Ownership anchor (`:83-86`) is correct and is the right design.** `coder` cannot `chown` to a
  foreign uid, so a look-alike dir it creates (owned by `coder`) fails `owner == registered UID`.
  Because `pwd -P` (`:107`) canonicalizes first, every walked ancestor (`:70-92`) is symlink-free, so
  `stat` reads the real owner — no symlink/`..` confusion. T5 exercises this for real.
- **Launch-path registry lock (`:117-121`) is correct.** `WS_LAUNCH_REGISTRY` is honored *only* under
  `--resolve-only` (which never `exec`s); the launch path forces the hardcoded root-owned registry, so
  no env can move the authority that picks the drop target. This is the key anti-bypass and it holds.
- **No `eval`/`source` of registry data (`:39-56`);** confs parsed as inert `KEY=VALUE` with `IFS= read
  -r`, immune to `IFS`. `CDPATH` is irrelevant (no `cd`). `LD_*`/`ENV`/`IFS` are stripped by sudo's
  `env_reset` (only `PATH` survives — hence C-1).
- **No shell-injection in the exec.** `"$@"` is passed as a quoted argv array to `sudo`→`ws-launch`→
  `claude` (`:150`, `:143`); positional args cannot inject sudo options (they follow the command).
  `printf` uses literal `%s` formats with data as arguments (`:35`, `:50`, `:94`, `:133`) — no
  format-string exposure. Arithmetic `-gt` (`:81-82`) is reached only after a `^[0-9]+$` gate, so no
  arithmetic injection. Quoted paths mean glob/space basenames just fail to match a conf.
- **Re-exec is not trickable and cannot loop.** Phase 2 re-resolves from scratch and gates `exec
  claude` on `[ "$(id -u)" = "$uid" ]` (`:140`) — a freshly resolved value, not a forgeable flag. A
  non-`coder` re-entry cannot re-drop (sudoers authorizes only `coder` as the runas source), so a
  mismatch fails/So it terminates rather than looping. `UID=0` rejected (T8); `umask 007` applied on
  every exec branch (`:138`).

---

## Contract coverage (infra report §"Contract for ws-launch")

| # | Contract point | Status |
|---|---|---|
| 1 | Resolve cwd → slug against the **root-owned** registry | Met (`:117-135`, root-owned lock correct) |
| 2 | `umask 007` before exec | Met (`:138`) |
| 3 | Drop to the workspace uid, run `claude` | Mechanism met (re-exec, documented deviation) — **but the "run *claude*, not arbitrary code" intent is broken by C-1** |
| 4 | Fail closed, **never** `coder` | Structurally met; **W-1** is a hang (not exit-non-zero) corner case |
| 5 | pty/stdio transparent (clean `exec`) | Plausibly met; only verifiable live at Step 8 (C2-wrap) |

---

## To clear to SAFE

1. **C-1 (blocking):** make the elevated `exec` PATH-independent — set a trusted `PATH` in the script
   **and** `exec` claude by an absolute root-owned path; do not rely on unverified external
   `secure_path`. Add the PATH-substitution regression test to C2-wrap.
2. **W-1, W-2, W-3:** `sudo -n`; a newline-proof charset gate; a test that actually exercises the
   drop-path exec integrity.
3. SUGGESTIONS S-1..S-3 at the team's discretion.

Re-review the revised wrapper before commit.
