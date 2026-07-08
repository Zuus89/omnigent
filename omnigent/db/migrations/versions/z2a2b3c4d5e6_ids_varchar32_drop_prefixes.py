"""Shrink omnigent id columns to VARCHAR(32) and drop their textual prefixes.

Revision ID: z2a2b3c4d5e6
Revises: z1a2b3c4d5e6
Create Date: 2026-07-08 00:00:00.000000

Every omnigent-minted id was a bare 32-char uuid4 hex carrying a textual
prefix (``ag_``, ``conv_``, ``file_``, ``host_``, ``pol_`` and the item-type
prefixes ``msg_``/``fc_``/``fco_``/``err_``/``rs_``/``cmp_``/``nt_``/``rse_``/
``sc_``/``tc_``/``rd_``), so the columns were declared ``String(64)``. The
generators now mint bare hex; this migration strips the prefixes from existing
rows and narrows every such column to ``String(32)``.

Excluded (not a bare omnigent uuid, left as-is):
  - ``conversations.runner_id`` — holds ``runner_``/``runner_token_`` ids,
    the latter a keyed derivation on the tunnel-binding secret (auth path).
  - ``conversation_items.response_id`` — polymorphic harness turn ids
    (``resp_claude_<digest>``, ``kimi:...``), not our uuid.
  - ``conversations.external_session_id`` — runtime-native session id.
  - ``users.id`` / ``account_tokens.id`` / all ``user_id`` / ``created_by`` /
    ``owner`` — emails / opaque tokens.
  - ``hosts.token_hash`` (sha256) / ``hosts.sandbox_id`` (provider id).

``comments.id`` was a dashed uuid4 (``str(uuid4())``, 36 chars) rather than a
prefixed hex id, so it is stripped of dashes instead of a prefix.

Order matters: data is stripped *first* (while columns are still
``String(64)``) then narrowed — PostgreSQL/MySQL reject a ``varchar(32)``
alter while 37-char values remain. The strip is idempotent (a bare value has
no ``_``/``-`` so the guarded UPDATE is a no-op), so re-running is safe.

SQLite-family dialects mirror ``conversation_items.id`` /
``conversation_id`` into the standalone ``conversation_items_fts`` table;
those columns are stripped too so full-text search of pre-migration items
keeps matching the migrated rows.

Dialect strategy mirrors the surrounding migrations: SQLite cannot alter a
column type in place, so ``batch_alter_table(recreate="always")`` rebuilds
each table (reflection preserves the PK, unique/check constraints, and
partial indexes — see r1a2b3c4d5e6 / w1a2b3c4d5e6); PostgreSQL/MySQL use
native ``ALTER`` via ``recreate="auto"``. The correctness-critical partial
unique index ``ix_conversations_parent_title_unique`` (whose
``parent_conversation_id`` column changes width) is dropped and recreated
explicitly with its dialect ``WHERE`` clauses, following w1a2b3c4d5e6.

No PRAGMA foreign_keys guard is needed — all FK constraints were removed in
p1a2b3c4d5e6.

Downgrade widens the columns back to ``String(64)`` but does not restore the
prefixes or the comment-id dashes (lossy, same convention as prior
prefix/format migrations).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "z2a2b3c4d5e6"
down_revision: str | None = "z1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FTS_TABLE = "conversation_items_fts"
# SQLite-family dialects that carry the FTS5 mirror (see db/utils.py).
_FTS5_DIALECTS = frozenset({"sqlite", "cloudflare_d1"})

_PARENT_TITLE_INDEX = "ix_conversations_parent_title_unique"

# table -> [(column, nullable)] for the bare-uuid id columns that get their
# prefix stripped and width narrowed String(64) -> String(32). ``comments.id``
# is dash-stripped rather than prefix-stripped (see _dash_strip below) but is
# still narrowed here.
_ID_COLUMNS: dict[str, list[tuple[str, bool]]] = {
    "agents": [("id", False)],
    "files": [("id", False), ("session_id", True)],
    "session_permissions": [("conversation_id", False)],
    "conversations": [
        ("id", False),
        ("parent_conversation_id", True),
        ("root_conversation_id", False),
        ("agent_id", True),
        ("host_id", True),
    ],
    "conversation_items": [("id", False), ("conversation_id", False)],
    "conversation_labels": [("conversation_id", False)],
    "comments": [("id", False), ("conversation_id", False)],
    "policies": [("id", False), ("session_id", True)],
    "hosts": [("host_id", False)],
}


def _dialect() -> str:
    return op.get_bind().dialect.name


def _is_sqlite() -> bool:
    return _dialect() == "sqlite"


def _strip_prefix_sql(col: str) -> tuple[str, str]:
    """Return ``(value_expr, guard_expr)`` to strip a leading ``<prefix>_``.

    The value expression returns everything after the first ``_``; the guard
    restricts the UPDATE to rows that actually carry a ``_`` so already-bare
    ids are untouched (idempotent). A bare uuid hex never contains ``_``, so
    the first ``_`` is always the prefix delimiter.
    """
    dialect = _dialect()
    if dialect == "postgresql":
        return f"substr({col}, strpos({col}, '_') + 1)", f"strpos({col}, '_') > 0"
    if dialect == "mysql":
        return f"SUBSTRING({col}, LOCATE('_', {col}) + 1)", f"LOCATE('_', {col}) > 0"
    # sqlite / cloudflare_d1
    return f"substr({col}, instr({col}, '_') + 1)", f"instr({col}, '_') > 0"


def _index_exists(table: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table))


def _table_exists(table: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table)


def _strip_data() -> None:
    """Strip prefixes (and comment-id dashes) from existing rows in place."""
    for table, cols in _ID_COLUMNS.items():
        for col, _nullable in cols:
            if table == "comments" and col == "id":
                continue  # dashed uuid, stripped below
            value_expr, guard = _strip_prefix_sql(col)
            op.execute(
                sa.text(
                    f"UPDATE {table} SET {col} = {value_expr} WHERE {col} IS NOT NULL AND {guard}"
                )
            )

    # comments.id was a dashed uuid4; collapse to bare hex.
    op.execute(sa.text("UPDATE comments SET id = replace(id, '-', '') WHERE id LIKE '%-%'"))

    # Mirror the strip into the FTS index (SQLite-family only; the virtual
    # table may not exist yet on a brand-new database, where there is nothing
    # to migrate anyway).
    if _dialect() in _FTS5_DIALECTS and _table_exists(_FTS_TABLE):
        for col in ("item_id", "conversation_id"):
            op.execute(
                sa.text(
                    f"UPDATE {_FTS_TABLE} "
                    f"SET {col} = substr({col}, instr({col}, '_') + 1) "
                    f"WHERE instr({col}, '_') > 0"
                )
            )


def _alter_all(from_len: int, to_len: int) -> None:
    """Alter every id column from ``String(from_len)`` to ``String(to_len)``."""
    sqlite = _is_sqlite()
    for table, cols in _ID_COLUMNS.items():
        with op.batch_alter_table(table, recreate="always" if sqlite else "auto") as batch_op:
            for col, nullable in cols:
                batch_op.alter_column(
                    col,
                    existing_type=sa.String(from_len),
                    type_=sa.String(to_len),
                    existing_nullable=nullable,
                )


def _recreate_parent_title_index() -> None:
    op.create_index(
        _PARENT_TITLE_INDEX,
        "conversations",
        ["parent_conversation_id", "title"],
        unique=True,
        sqlite_where=sa.text("parent_conversation_id IS NOT NULL"),
        postgresql_where=sa.text("parent_conversation_id IS NOT NULL"),
        mysql_length={"title": 512},
    )


def upgrade() -> None:
    """Strip id prefixes from data, then narrow the columns to VARCHAR(32)."""
    _strip_data()

    # The partial unique index covers parent_conversation_id, whose width is
    # changing; drop it around the rebuild and recreate with dialect WHERE
    # clauses (w1a2b3c4d5e6 pattern).
    if _index_exists("conversations", _PARENT_TITLE_INDEX):
        op.drop_index(_PARENT_TITLE_INDEX, table_name="conversations")

    _alter_all(from_len=64, to_len=32)

    _recreate_parent_title_index()


def downgrade() -> None:
    """Widen the columns back to VARCHAR(64). Prefixes are not restored."""
    if _index_exists("conversations", _PARENT_TITLE_INDEX):
        op.drop_index(_PARENT_TITLE_INDEX, table_name="conversations")

    _alter_all(from_len=32, to_len=64)

    _recreate_parent_title_index()
