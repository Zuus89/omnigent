#!/usr/bin/env python3
"""Validate the Personal AI Platform workspace registry (workspaces.yaml).

Two layers, selectable by flag:

  * structural  (--schema-only): shape + law checks that hold ANYWHERE, including
    a pre-commit run on a notebook where no ``ws-*`` user exists. This is what the
    pre-commit hook runs so off-box commits never break.
  * live        (default / --full): the structural layer PLUS host-state checks —
    each ``unix_user`` must resolve (NSS) and each ``root`` must exist on disk.
    This is the Step-8 ``$VALIDATE_CMD``; it is what makes a registry/live-state
    mismatch (a "ghost" entry naming a user/root that do not exist) fail loudly.

Loud-fail contract: on ANY problem the script prints every finding — each one
prefixed with the offending workspace slug (or, for a raw-text credential hit,
the file:line) — and exits non-zero. It never fails silently and never fails
with a bare "invalid".

YAML parsing: PyYAML is used when importable (the pre-commit hook installs it via
``additional_dependencies``; Step-8 hosts install it per the alpha's PF-8). When
PyYAML is absent the script falls back to a strict, minimal block-YAML reader for
the constrained registry subset, so it still runs on the code-server base image,
which ships neither PyYAML nor jq. The fallback fails loud on anything outside the
documented subset rather than guessing.
"""

from __future__ import annotations

import argparse
import os
import pwd
import re
import sys
from pathlib import Path

# Registry location relative to this script (scripts/ -> repo root -> deploy/...).
# Resolving from __file__ makes $VALIDATE_CMD work regardless of the caller's cwd.
DEFAULT_REGISTRY = (
    Path(__file__).resolve().parent.parent
    / "deploy"
    / "personal-platform"
    / "workspaces.yaml"
)

# --- credential patterns (Hard Rule 6) --------------------------------------
# A registry that carries a live token or a connection string with embedded
# userinfo is a governance violation, not merely a style issue. These patterns
# are scanned against the RAW file text (not just parsed values) so a token
# hidden in a comment or a URL is caught too. The uppercase KEY=VALUE pattern
# mirrors the alpha test's own inline-credential grep (C7) exactly.
_INLINE_ASSIGNMENT = re.compile(r"^\s*[A-Z][A-Z0-9_]{2,}=\S+")
_CREDENTIAL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("github token", re.compile(r"gh[posru]_[A-Za-z0-9]{10,}")),
    ("github fine-grained token", re.compile(r"github_pat_[A-Za-z0-9_]{20,}")),
    ("gitlab token", re.compile(r"glpat-[A-Za-z0-9_-]{10,}")),
    ("aws access key id", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("slack token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("openai key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    # user:password@host userinfo inside a URL (e.g. a tokenised git remote).
    ("credentials embedded in url", re.compile(r"://[^\s/@]+:[^\s/@]+@")),
)

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_KB_RE = re.compile(r"^kb-ws-.+")
# A secret_store / credential_helper reference is scheme:target (e.g.
# keychain:personal) or an absolute path (e.g. /var/run/secrets/...).
_REFERENCE_RE = re.compile(r"^([a-z][a-z0-9+.-]*:.+|/.+)$")

_REQUIRED_FIELDS = (
    "slug",
    "unix_user",
    "root",
    "config_dir",
    "kb_repo",
    "secret_store",
    "workspace_id",
)


class RegistryError(Exception):
    """A fatal parse/shape error that prevents per-entry validation entirely."""


# --- YAML loading ------------------------------------------------------------


def load_registry(path: Path) -> object:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml
    except ImportError:
        return _minimal_yaml_load(text)
    return yaml.safe_load(text)


def _scalar(token: str) -> object:
    if len(token) >= 2 and token[0] == token[-1] and token[0] in ("'", '"'):
        return token[1:-1]
    if re.fullmatch(r"-?\d+", token):
        return int(token)
    if token in ("true", "True"):
        return True
    if token in ("false", "False"):
        return False
    if token in ("null", "~", ""):
        return None
    return token


class _MiniYAML:
    """A deliberately small, strict reader for the registry's block-YAML subset.

    Handles: block mappings, block sequences, sequences of block mappings, one
    level of nesting for ``git:`` / ``projects:``, scalar strings/ints/bools, and
    full-line ``#`` comments. Anything else raises RegistryError — the reader
    never silently mis-parses a file it does not fully understand.
    """

    def __init__(self, text: str) -> None:
        self.lines: list[list] = []  # each: [indent, content]
        for n, raw in enumerate(text.split("\n"), start=1):
            stripped = raw.strip()
            if stripped == "" or stripped.startswith("#"):
                continue
            leading = raw[: len(raw) - len(raw.lstrip(" "))]
            if "\t" in raw[: len(raw) - len(raw.lstrip())]:
                raise RegistryError(f"line {n}: tabs are not allowed in indentation")
            self.lines.append([len(leading), stripped])
        self.pos = 0

    def _peek(self) -> list | None:
        return self.lines[self.pos] if self.pos < len(self.lines) else None

    def parse(self) -> object:
        if self._peek() is None:
            return None
        value = self._parse_block(self.lines[0][0])
        if self.pos != len(self.lines):
            indent, content = self.lines[self.pos]
            raise RegistryError(
                f"unexpected content at indentation {indent}: {content!r}"
            )
        return value

    def _parse_block(self, indent: int) -> object:
        first = self._peek()
        if first is None:
            return None
        if first[1].startswith("- "):
            return self._parse_seq(indent)
        return self._parse_map(indent)

    def _parse_map(self, indent: int) -> dict:
        result: dict = {}
        while True:
            cur = self._peek()
            if cur is None or cur[0] < indent:
                break
            if cur[0] > indent:
                raise RegistryError(
                    f"unexpected indent {cur[0]} (expected {indent}): {cur[1]!r}"
                )
            if cur[1].startswith("- "):
                break
            key, sep, rest = cur[1].partition(":")
            if sep == "":
                raise RegistryError(f"expected 'key: value', got: {cur[1]!r}")
            key = key.strip()
            rest = rest.strip()
            self.pos += 1
            if rest != "":
                result[key] = _scalar(rest)
                continue
            child = self._peek()
            if child is not None and child[0] > indent:
                result[key] = self._parse_block(child[0])
            else:
                result[key] = None
        return result

    def _parse_seq(self, indent: int) -> list:
        items: list = []
        while True:
            cur = self._peek()
            if cur is None or cur[0] < indent:
                break
            if not cur[1].startswith("- "):
                if cur[0] == indent:
                    raise RegistryError(
                        f"expected a '- ' sequence item, got: {cur[1]!r}"
                    )
                break
            # Rewrite the marker line as the item mapping's first entry, aligned
            # at indent+2, then parse the whole item as a block mapping.
            cur[0] = indent + 2
            cur[1] = cur[1][2:].strip()
            items.append(self._parse_map(indent + 2))
        return items


def _minimal_yaml_load(text: str) -> object:
    return _MiniYAML(text).parse()


# --- validation --------------------------------------------------------------


def _rows(reg: object) -> list:
    # Mirror the alpha's ws_field: reg.get("workspaces", reg) then iterate rows.
    rows = reg.get("workspaces", reg) if isinstance(reg, dict) else reg
    if not isinstance(rows, list) or not rows:
        raise RegistryError("registry must have a non-empty top-level 'workspaces' list")
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RegistryError(f"workspace entry #{i} is not a mapping")
    return rows


def _tag(row: dict, index: int) -> str:
    slug = row.get("slug")
    return str(slug) if slug else f"entry#{index}"


def _looks_like_credential(value: str) -> bool:
    return any(pat.search(value) for _, pat in _CREDENTIAL_PATTERNS)


def _is_reference(value: object) -> bool:
    if not isinstance(value, str):
        return False
    return bool(_REFERENCE_RE.match(value.strip())) and not _looks_like_credential(value)


def structural_errors(rows: list) -> list[str]:
    errors: list[str] = []
    seen_ids: dict[int, str] = {}
    seen_slugs: dict[str, int] = {}
    seen_users: dict[str, str] = {}

    for i, row in enumerate(rows):
        tag = _tag(row, i)

        for field in _REQUIRED_FIELDS:
            if row.get(field) in (None, ""):
                errors.append(f"[{tag}] missing required field '{field}'")

        slug = row.get("slug")
        if isinstance(slug, str) and slug:
            if not _SLUG_RE.match(slug):
                errors.append(
                    f"[{tag}] slug '{slug}' is not a safe lowercase token "
                    "(^[a-z0-9][a-z0-9._-]*$)"
                )
            seen_slugs[slug] = seen_slugs.get(slug, 0) + 1

        unix_user = row.get("unix_user")
        if isinstance(slug, str) and slug and isinstance(unix_user, str):
            if unix_user != f"ws-{slug}":
                errors.append(
                    f"[{tag}] unix_user '{unix_user}' must equal 'ws-{slug}' "
                    "(ws-<slug> law)"
                )
            if unix_user in seen_users:
                errors.append(
                    f"[{tag}] unix_user '{unix_user}' also used by "
                    f"'{seen_users[unix_user]}'"
                )
            else:
                seen_users[unix_user] = tag

        for pathfield in ("root", "config_dir"):
            val = row.get(pathfield)
            if isinstance(val, str) and val and not val.startswith("/"):
                errors.append(f"[{tag}] {pathfield} '{val}' must be an absolute path")

        kb = row.get("kb_repo")
        if isinstance(kb, str) and kb and not _KB_RE.match(kb):
            errors.append(f"[{tag}] kb_repo '{kb}' must match ^kb-ws-.+")

        ss = row.get("secret_store")
        if ss not in (None, "") and not _is_reference(ss):
            errors.append(
                f"[{tag}] secret_store '{ss}' must be a reference "
                "(scheme:target or /path), never an inline credential"
            )

        errors += _workspace_id_errors(row, tag, seen_ids)
        errors += _git_errors(row, tag)
        errors += _project_errors(row, tag)

    for slug, count in seen_slugs.items():
        if count > 1:
            errors.append(f"[{slug}] slug is duplicated {count} times")

    return errors


def _workspace_id_errors(row: dict, tag: str, seen_ids: dict[int, str]) -> list[str]:
    wid = row.get("workspace_id")
    if wid is None:
        return []
    if not isinstance(wid, int) or isinstance(wid, bool):
        return [f"[{tag}] workspace_id '{wid}' must be an integer"]
    if wid == 0:
        return [
            f"[{tag}] workspace_id 0 is a reserved/rejected sentinel; "
            "assign a non-zero id"
        ]
    if wid in seen_ids:
        return [f"[{tag}] workspace_id {wid} is not unique (also '{seen_ids[wid]}')"]
    seen_ids[wid] = tag
    return []


def _git_errors(row: dict, tag: str) -> list[str]:
    git = row.get("git")
    if git in (None, ""):
        return [f"[{tag}] missing required field 'git' (name/email/credential_helper)"]
    if not isinstance(git, dict):
        return [f"[{tag}] git must be a mapping with name/email/credential_helper"]
    errors: list[str] = []
    for k in ("name", "email"):
        if git.get(k) in (None, ""):
            errors.append(f"[{tag}] git.{k} is required and must be non-empty")
    helper = git.get("credential_helper")
    if helper in (None, ""):
        errors.append(
            f"[{tag}] git.credential_helper is required "
            "(a reference to the helper, not a token)"
        )
    elif not _is_reference(helper):
        errors.append(
            f"[{tag}] git.credential_helper '{helper}' must be a reference "
            "(scheme:target or /path), never a token"
        )
    return errors


def _project_errors(row: dict, tag: str) -> list[str]:
    projects = row.get("projects")
    if projects in (None, ""):
        return [f"[{tag}] missing required field 'projects' (at least one project)"]
    if not isinstance(projects, list) or not projects:
        return [f"[{tag}] projects must be a non-empty list"]
    errors: list[str] = []
    for j, proj in enumerate(projects):
        if not isinstance(proj, dict):
            errors.append(f"[{tag}] project #{j} is not a mapping")
            continue
        if proj.get("repo") in (None, ""):
            errors.append(f"[{tag}] project #{j} missing 'repo' url")
        elif _looks_like_credential(str(proj["repo"])):
            errors.append(f"[{tag}] project #{j} repo url embeds a credential (Hard Rule 6)")
        if proj.get("branch") in (None, ""):
            errors.append(f"[{tag}] project #{j} missing 'branch'")
    return errors


def raw_credential_errors(path: Path) -> list[str]:
    errors: list[str] = []
    for n, line in enumerate(path.read_text(encoding="utf-8").split("\n"), start=1):
        if _INLINE_ASSIGNMENT.match(line):
            errors.append(
                f"{path.name}:{n} inline KEY=VALUE assignment looks like a "
                f"credential: {line.strip()!r}"
            )
        for label, pat in _CREDENTIAL_PATTERNS:
            if pat.search(line):
                errors.append(
                    f"{path.name}:{n} {label} detected (Hard Rule 6): {line.strip()!r}"
                )
    return errors


def live_errors(rows: list) -> list[str]:
    errors: list[str] = []
    for i, row in enumerate(rows):
        tag = _tag(row, i)
        unix_user = row.get("unix_user")
        if isinstance(unix_user, str) and unix_user:
            try:
                pwd.getpwnam(unix_user)
            except KeyError:
                errors.append(
                    f"[{tag}] unix_user '{unix_user}' does not exist on this host "
                    "(getent passwd)"
                )
        root = row.get("root")
        if isinstance(root, str) and root and not os.path.isdir(root):
            errors.append(f"[{tag}] root '{root}' does not exist on this host")
    return errors


def validate(path: Path, schema_only: bool) -> list[str]:
    if not path.is_file():
        return [f"registry not found: {path}"]
    errors = raw_credential_errors(path)
    try:
        reg = load_registry(path)
        rows = _rows(reg)
    except RegistryError as exc:
        return [*errors, f"registry structure error: {exc}"]
    except Exception as exc:  # noqa: BLE001
        # A parse failure must fail loud with a labelled message, not crash.
        return [*errors, f"failed to parse registry: {exc}"]
    errors += structural_errors(rows)
    if not schema_only:
        errors += live_errors(rows)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the workspace registry (workspaces.yaml)."
    )
    parser.add_argument(
        "registry",
        nargs="?",
        default=str(DEFAULT_REGISTRY),
        help="path to workspaces.yaml",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--schema-only",
        action="store_true",
        help="structural checks only (no host-state; pre-commit safe)",
    )
    mode.add_argument(
        "--full",
        action="store_true",
        help="structural + live host-state checks (default)",
    )
    args = parser.parse_args()

    path = Path(args.registry).resolve()
    errors = validate(path, schema_only=args.schema_only)
    mode_name = "schema-only" if args.schema_only else "full"

    if errors:
        print(f"workspace registry validation FAILED ({mode_name}): {path}")
        for err in errors:
            print(f"  - {err}")
        return 1
    print(f"workspace registry OK ({mode_name}): {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
