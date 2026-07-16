#!/bin/sh
# test-ws-launch.sh — offline security test for ws-launch (returns non-zero on any failure).
#
# Scope: this box has NO ws-* users, blanket sudo is still present, and A2' is NOT active, so
# the real privilege drop (exec sudo -u ws-<slug>) and pty integration CANNOT be exercised here
# — they are validated live at Step 8 (sealed alpha test C2-wrap w-1/w-2/w-3). What IS testable
# now, non-circularly, is the security-critical logic: cwd->slug->uid resolution, FAIL-CLOSED,
# and — the point of a privilege-drop launcher — that a coder-poisoned PATH cannot redirect the
# wrapper's helpers (C-1 regression, T15), plus static proof that claude is exec'd by an absolute
# path under `sudo -n` (T17-T19). All exercised via the wrapper's no-exec `--resolve-only`.
#
# The ownership anchor is exercised faithfully without root: the runner's own uid is the
# legitimate workspace owner, and a mismatched uid simulates a coder-made look-alike directory
# (the /tmp/clientb spoof) that MUST fail closed.

set -u

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
WS_LAUNCH="$SCRIPT_DIR/ws-launch"
SH=$(command -v sh 2>/dev/null || echo /bin/sh)   # captured before any PATH poisoning (T15)

TMP_BASE=$(mktemp -d "${TMPDIR:-/tmp}/ws-launch-test.XXXXXX") || exit 2
ERRF="$TMP_BASE/stderr"
trap 'chmod -R u+rwx "$TMP_BASE" 2>/dev/null; rm -rf "$TMP_BASE"' EXIT INT TERM

MOCK_REG="$TMP_BASE/reg"
MOCK_ROOT="$TMP_BASE/work"
OUTSIDE="$TMP_BASE/outside/nowhere"
POISON_DIR="$TMP_BASE/poison"
POISON_MARKER="$TMP_BASE/poison.ran"

MY_UID=$(id -u)
MY_GID=$(id -g)
if [ "$MY_UID" -eq 0 ]; then
	# Root can chown, so exercise the ownership anchor against a non-root owner above the wrapper's
	# UID floor (1000). Keeps the harness portable to a root CI runner.
	LEGIT_UID=4243; LEGIT_GID=4243; CHOWN_LEGIT=1
else
	LEGIT_UID=$MY_UID; LEGIT_GID=$MY_GID; CHOWN_LEGIT=0
fi
SPOOF_UID=4242; SPOOF_GID=4242   # deliberately != LEGIT_UID: the look-alike's registered owner

mkdir -p "$MOCK_REG" "$MOCK_ROOT" "$OUTSIDE" "$POISON_DIR"
mkdir -p "$MOCK_ROOT/personal/proj" "$MOCK_ROOT/personal/clientb" \
         "$MOCK_ROOT/clientb" "$MOCK_ROOT/unreg" "$MOCK_ROOT/badslug" \
         "$MOCK_ROOT/nouid" "$MOCK_ROOT/rootws" "$MOCK_ROOT/baduid" \
         "$MOCK_ROOT/sysuid" "$MOCK_ROOT/unreadable"

# --- registry fixtures -------------------------------------------------------
cat > "$MOCK_REG/personal.conf"   <<EOF
SLUG=personal
UID=$LEGIT_UID
GID=$LEGIT_GID
EOF
cat > "$MOCK_REG/clientb.conf"    <<EOF
SLUG=clientb
UID=$SPOOF_UID
GID=$SPOOF_GID
EOF
cat > "$MOCK_REG/badslug.conf"    <<EOF
SLUG=not-badslug
UID=$LEGIT_UID
GID=$LEGIT_GID
EOF
cat > "$MOCK_REG/nouid.conf"      <<EOF
SLUG=nouid
GID=$LEGIT_GID
EOF
cat > "$MOCK_REG/rootws.conf"     <<EOF
SLUG=rootws
UID=0
GID=0
EOF
cat > "$MOCK_REG/baduid.conf"     <<EOF
SLUG=baduid
UID=abc
GID=$LEGIT_GID
EOF
cat > "$MOCK_REG/sysuid.conf"     <<EOF
SLUG=sysuid
UID=500
GID=500
EOF
cat > "$MOCK_REG/unreadable.conf" <<EOF
SLUG=unreadable
UID=$LEGIT_UID
GID=$LEGIT_GID
EOF
chmod 000 "$MOCK_REG/unreadable.conf"

if [ "$CHOWN_LEGIT" -eq 1 ]; then
	chown -R "$LEGIT_UID:$LEGIT_GID" "$MOCK_ROOT"/* 2>/dev/null
fi

# --- runner + assertions -----------------------------------------------------
pass=0; fail=0
rec() { if [ "$2" -eq 0 ]; then echo "PASS $1"; pass=$((pass + 1)); else echo "FAIL $1 ${3:-}"; fail=$((fail + 1)); fi; }

run_resolve() {   # $1=cwd  [$2=registry override, default $MOCK_REG]
	_reg=${2:-$MOCK_REG}
	OUT=$(cd "$1" 2>/dev/null && WS_LAUNCH_REGISTRY="$_reg" "$SH" "$WS_LAUNCH" --resolve-only 2>"$ERRF")
	RC=$?
	ERR=$(cat "$ERRF" 2>/dev/null)
}

check_ok() {      # $1=name $2=cwd $3=slug $4=uid $5=gid
	run_resolve "$2"
	if [ "$RC" -eq 0 ] && [ "$OUT" = "slug=$3 uid=$4 gid=$5" ]; then
		rec "$1" 0
	else
		rec "$1" 1 ": rc=$RC out='$OUT' err='$ERR'"
	fi
}

check_closed() {  # $1=name $2=cwd [$3=registry override]
	run_resolve "$2" "${3:-}"
	# Fail-closed contract: non-zero AND no resolved slug on stdout (no actionable resolution the
	# launch path could act on => it can never fall through to a coder launch).
	if [ "$RC" -ne 0 ] && ! printf '%s' "$OUT" | grep -q 'slug='; then
		rec "$1" 0
	else
		rec "$1" 1 ": rc=$RC out='$OUT' err='$ERR'"
	fi
}

# T0 — the wrapper is present, executable, and a /bin/sh script.
{ [ -f "$WS_LAUNCH" ] && [ -x "$WS_LAUNCH" ] && head -1 "$WS_LAUNCH" | grep -q '^#!/bin/sh'; }
rec T0-artifact-executable-shebang $?

# T1/T2/T12 — legitimate resolution (owner matches the registered uid, at/above the UID floor).
check_ok     T1-under-registered-slug        "$MOCK_ROOT/personal/proj"    personal "$LEGIT_UID" "$LEGIT_GID"
check_ok     T2-at-workspace-dir             "$MOCK_ROOT/personal"         personal "$LEGIT_UID" "$LEGIT_GID"
check_ok     T12-nested-lookalike-bypassed   "$MOCK_ROOT/personal/clientb" personal "$LEGIT_UID" "$LEGIT_GID"

# T3/T4 — no registered workspace owns cwd.
check_closed T3-unregistered-slug            "$MOCK_ROOT/unreg"
check_closed T4-outside-workspaces-root      "$OUTSIDE"

# T5 — CRITICAL: look-alike dir whose registered owner differs (the /tmp/clientb spoof).
check_closed T5-ownership-spoof              "$MOCK_ROOT/clientb"

# T6..T9,T14 — malformed / out-of-range registry entries all fail closed.
check_closed T6-slug-filename-mismatch       "$MOCK_ROOT/badslug"
check_closed T7-missing-uid                  "$MOCK_ROOT/nouid"
check_closed T8-uid-zero-root                "$MOCK_ROOT/rootws"
check_closed T9-uid-non-numeric              "$MOCK_ROOT/baduid"
check_closed T14-uid-below-floor             "$MOCK_ROOT/sysuid"

# T10 — registry directory unreadable/absent.
check_closed T10-registry-absent             "$MOCK_ROOT/personal" "/no/such/registry"

# T11 — registered conf exists but is unreadable (skip when running as root: root reads anything).
if [ "$MY_UID" -ne 0 ]; then
	check_closed T11-conf-unreadable         "$MOCK_ROOT/unreadable"
else
	echo "SKIP T11-conf-unreadable (running as root)"
fi

# T15 — C-1 REGRESSION: a coder-poisoned PATH does NOT redirect the wrapper's helpers. Prepend a
# dir of hostile stat/grep/id/getent/sudo/claude/ls that record they ran + print POISONED. Because
# the wrapper resets PATH to a trusted list as its first action, the REAL helpers run: resolution
# is correct, no marker file is written, and no POISONED token leaks. (Unfixed, the poison stat
# would run — resolution would break AND the marker would appear.)
for h in stat grep id getent sudo claude ls pwd; do
	printf '#!/bin/sh\necho %s >> "%s"\necho POISONED\nexit 0\n' "$h" "$POISON_MARKER" > "$POISON_DIR/$h"
	chmod 0755 "$POISON_DIR/$h"
done
rm -f "$POISON_MARKER"
OUT=$(cd "$MOCK_ROOT/personal/proj" 2>/dev/null \
	&& PATH="$POISON_DIR:$PATH" WS_LAUNCH_REGISTRY="$MOCK_REG" "$SH" "$WS_LAUNCH" --resolve-only 2>"$ERRF")
RC=$?
if [ "$RC" -eq 0 ] && [ "$OUT" = "slug=personal uid=$LEGIT_UID gid=$LEGIT_GID" ] \
	&& [ ! -e "$POISON_MARKER" ] && ! printf '%s' "$OUT" | grep -q 'POISONED'; then
	rec T15-poisoned-PATH-does-not-run-helpers 0
else
	rec T15-poisoned-PATH-does-not-run-helpers 1 ": rc=$RC out='$OUT' ran='$(cat "$POISON_MARKER" 2>/dev/null | tr '\n' ',')'"
fi

# T16-T19 — static proof of the C-1 / W-1 fixes in the wrapper source.
{ head -30 "$WS_LAUNCH" | grep -q '^PATH=/usr/local/sbin:/usr/local/bin:' && grep -q '^export PATH' "$WS_LAUNCH"; }
rec T16-trusted-PATH-set-and-exported-early $?

if grep -nE '^[[:space:]]*exec[[:space:]]+claude([[:space:]]|$)' "$WS_LAUNCH" >/dev/null 2>&1; then
	rec T17-no-bare-exec-claude 1 ": found a bare 'exec claude' PATH-lookup"
else
	rec T17-no-bare-exec-claude 0
fi

grep -qF 'exec "$claude_bin" "$@"' "$WS_LAUNCH"; rec T18-claude-exec-by-absolute-var-path $?
grep -q 'exec sudo -n -u ' "$WS_LAUNCH";          rec T19-drop-uses-sudo-n $?

# --- verdict -----------------------------------------------------------------
echo "-----------------------------------------"
echo "ws-launch security tests: $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
exit 0
