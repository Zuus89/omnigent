#!/bin/sh
# test-ws-launch.sh — offline security test for ws-launch (returns non-zero on any failure).
#
# Scope: this box has NO ws-* users, blanket sudo is still present, and A2' is NOT active, so
# the real privilege drop (exec sudo -u ws-<slug>) and pty integration CANNOT be exercised here
# — they are validated live at Step 8 (sealed alpha test C2-wrap w-1/w-2/w-3). What IS testable
# now, non-circularly, is the security-critical half: cwd->slug->uid resolution and FAIL-CLOSED,
# via the wrapper's no-exec `--resolve-only` diagnostic against a MOCK registry.
#
# The ownership anchor is exercised faithfully without root: the runner's own uid is the
# legitimate workspace owner, and a mismatched uid simulates a coder-made look-alike directory
# (the /tmp/clientb spoof) that MUST fail closed.

set -u

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
WS_LAUNCH="$SCRIPT_DIR/ws-launch"

TMP_BASE=$(mktemp -d "${TMPDIR:-/tmp}/ws-launch-test.XXXXXX") || exit 2
ERRF="$TMP_BASE/stderr"
trap 'chmod -R u+rwx "$TMP_BASE" 2>/dev/null; rm -rf "$TMP_BASE"' EXIT INT TERM

MOCK_REG="$TMP_BASE/reg"
MOCK_ROOT="$TMP_BASE/work"
OUTSIDE="$TMP_BASE/outside/nowhere"

MY_UID=$(id -u)
MY_GID=$(id -g)
if [ "$MY_UID" -eq 0 ]; then
	# Root can chown, so exercise the ownership anchor against a non-root owner (never uid 0,
	# which the wrapper rejects). Keeps the harness portable to a root CI runner.
	LEGIT_UID=4243; LEGIT_GID=4243; CHOWN_LEGIT=1
else
	LEGIT_UID=$MY_UID; LEGIT_GID=$MY_GID; CHOWN_LEGIT=0
fi
SPOOF_UID=4242; SPOOF_GID=4242   # deliberately != LEGIT_UID: the look-alike's registered owner

mkdir -p "$MOCK_REG" "$MOCK_ROOT" "$OUTSIDE"
mkdir -p "$MOCK_ROOT/personal/proj" "$MOCK_ROOT/personal/clientb" \
         "$MOCK_ROOT/clientb" "$MOCK_ROOT/unreg" "$MOCK_ROOT/badslug" \
         "$MOCK_ROOT/nouid" "$MOCK_ROOT/rootws" "$MOCK_ROOT/baduid" "$MOCK_ROOT/unreadable"

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
cat > "$MOCK_REG/unreadable.conf" <<EOF
SLUG=unreadable
UID=$LEGIT_UID
GID=$LEGIT_GID
EOF
chmod 000 "$MOCK_REG/unreadable.conf"

if [ "$CHOWN_LEGIT" -eq 1 ]; then
	chown -R "$LEGIT_UID:$LEGIT_GID" "$MOCK_ROOT/personal" "$MOCK_ROOT/clientb" \
	        "$MOCK_ROOT/unreg" "$MOCK_ROOT/badslug" "$MOCK_ROOT/nouid" \
	        "$MOCK_ROOT/rootws" "$MOCK_ROOT/baduid" "$MOCK_ROOT/unreadable" 2>/dev/null
fi

# --- runner + assertions -----------------------------------------------------
pass=0; fail=0

run_resolve() {   # $1=cwd  [$2=registry override, default $MOCK_REG]
	_reg=${2:-$MOCK_REG}
	OUT=$(cd "$1" 2>/dev/null && WS_LAUNCH_REGISTRY="$_reg" sh "$WS_LAUNCH" --resolve-only 2>"$ERRF")
	RC=$?
	ERR=$(cat "$ERRF" 2>/dev/null)
}

check_ok() {      # $1=name $2=cwd $3=slug $4=uid $5=gid
	run_resolve "$2"
	if [ "$RC" -eq 0 ] && [ "$OUT" = "slug=$3 uid=$4 gid=$5" ]; then
		echo "PASS $1"; pass=$((pass + 1))
	else
		echo "FAIL $1 : rc=$RC out='$OUT' err='$ERR'"; fail=$((fail + 1))
	fi
}

check_closed() {  # $1=name $2=cwd [$3=registry override]
	run_resolve "$2" "${3:-}"
	# Fail-closed contract: non-zero AND no resolved slug on stdout (no actionable resolution the
	# launch path could act on => it can never fall through to a coder launch).
	if [ "$RC" -ne 0 ] && ! printf '%s' "$OUT" | grep -q 'slug='; then
		echo "PASS $1"; pass=$((pass + 1))
	else
		echo "FAIL $1 : rc=$RC out='$OUT' err='$ERR'"; fail=$((fail + 1))
	fi
}

# T0 — the wrapper is present, executable, and a /bin/sh script.
if [ -f "$WS_LAUNCH" ] && [ -x "$WS_LAUNCH" ] && head -1 "$WS_LAUNCH" | grep -q '^#!/bin/sh'; then
	echo "PASS T0-artifact-executable-shebang"; pass=$((pass + 1))
else
	echo "FAIL T0-artifact-executable-shebang : x=$([ -x "$WS_LAUNCH" ] && echo y || echo n)"; fail=$((fail + 1))
fi

# T1/T2/T12 — legitimate resolution (owner matches the registered uid).
check_ok     T1-under-registered-slug        "$MOCK_ROOT/personal/proj"    personal "$LEGIT_UID" "$LEGIT_GID"
check_ok     T2-at-workspace-dir             "$MOCK_ROOT/personal"         personal "$LEGIT_UID" "$LEGIT_GID"
check_ok     T12-nested-lookalike-bypassed   "$MOCK_ROOT/personal/clientb" personal "$LEGIT_UID" "$LEGIT_GID"

# T3/T4 — no registered workspace owns cwd.
check_closed T3-unregistered-slug            "$MOCK_ROOT/unreg"
check_closed T4-outside-workspaces-root      "$OUTSIDE"

# T5 — CRITICAL: look-alike dir whose registered owner differs (the /tmp/clientb spoof).
check_closed T5-ownership-spoof              "$MOCK_ROOT/clientb"

# T6..T9 — malformed registry entries all fail closed.
check_closed T6-slug-filename-mismatch       "$MOCK_ROOT/badslug"
check_closed T7-missing-uid                  "$MOCK_ROOT/nouid"
check_closed T8-uid-zero-root                "$MOCK_ROOT/rootws"
check_closed T9-uid-non-numeric              "$MOCK_ROOT/baduid"

# T10 — registry directory unreadable/absent.
check_closed T10-registry-absent             "$MOCK_ROOT/personal" "/no/such/registry"

# T11 — registered conf exists but is unreadable (skip when running as root: root reads anything).
if [ "$MY_UID" -ne 0 ]; then
	check_closed T11-conf-unreadable         "$MOCK_ROOT/unreadable"
else
	echo "SKIP T11-conf-unreadable (running as root)"
fi

# --- verdict -----------------------------------------------------------------
echo "-----------------------------------------"
echo "ws-launch resolution/fail-closed tests: $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
exit 0
