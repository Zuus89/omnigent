"""Tests for the id-varchar32 / drop-prefixes migration (z2a2b3c4d5e6)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from sqlalchemy.engine import Engine

from omnigent.db.utils import (
    _build_alembic_config,
    clear_engine_cache,
    get_or_create_engine,
)

_PREV = "z1a2b3c4d5e6"
_NOW = 1_700_000_000
_CONV = "conv_1111111111111111111111111111aaaa"
_CONV_BARE = "1111111111111111111111111111aaaa"


@pytest.fixture
def db_engine(tmp_path: Path) -> Iterator[Engine]:
    """Fresh SQLite database with the full migration chain applied (at head)."""
    engine = get_or_create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    try:
        yield engine
    finally:
        engine.dispose()
        clear_engine_cache()


def _seed_prefixed_rows(engine: Engine, config) -> None:
    """Downgrade below y1 and insert rows carrying the legacy id prefixes."""
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.downgrade(config, _PREV)
    with engine.begin() as c:
        c.execute(
            sa.text(
                "INSERT INTO agents "
                "(workspace_id,id,created_at,name,bundle_location,version,kind) "
                "VALUES (0,'ag_aaaa1111aaaa1111aaaa1111aaaa1111',:t,'tmpl','loc',1,1)"
            ),
            {"t": _NOW},
        )
        c.execute(
            sa.text(
                "INSERT INTO conversations (workspace_id,id,created_at,updated_at,title,kind,"
                "parent_conversation_id,root_conversation_id,agent_id,runner_id,host_id,"
                "external_session_id,workspace) VALUES (0,:conv,:t,:t,'root',1,NULL,:conv,"
                "'ag_aaaa1111aaaa1111aaaa1111aaaa1111',"
                "'runner_9999888877776666555544443333aaaa',"
                "'host_5b6e33d0e4f749a39bab562a5a72b421','ext-session-with-dashes-1','/w')"
            ),
            {"conv": _CONV, "t": _NOW},
        )
        c.execute(
            sa.text(
                "INSERT INTO conversations (workspace_id,id,created_at,updated_at,title,kind,"
                "parent_conversation_id,root_conversation_id) VALUES "
                "(0,'conv_2222222222222222222222222222bbbb',:t,:t,'child',2,:conv,:conv)"
            ),
            {"conv": _CONV, "t": _NOW},
        )
        c.execute(
            sa.text(
                "INSERT INTO files (workspace_id,id,created_at,filename,bytes,session_id) "
                "VALUES (0,'file_ffff2222ffff2222ffff2222ffff2222',:t,'f',10,:conv)"
            ),
            {"conv": _CONV, "t": _NOW},
        )
        for iid, typ, rid, pos in [
            ("msg_dddd3333dddd3333dddd3333dddd3333", 1, "resp_claude_abc", 0),
            ("fc_eeee4444eeee4444eeee4444eeee4444", 2, "kimi:a0b2-79", 1),
        ]:
            c.execute(
                sa.text(
                    "INSERT INTO conversation_items (workspace_id,id,conversation_id,response_id,"
                    "created_at,status,position,type,data,search_text) "
                    "VALUES (0,:id,:conv,:rid,:t,1,:pos,:typ,'{}','hello world')"
                ),
                {"id": iid, "conv": _CONV, "rid": rid, "t": _NOW, "pos": pos, "typ": typ},
            )
        c.execute(
            sa.text(
                "INSERT INTO session_permissions (workspace_id,user_id,conversation_id,level) "
                "VALUES (0,'alice@example.com',:conv,4)"
            ),
            {"conv": _CONV},
        )
        c.execute(
            sa.text(
                "INSERT INTO conversation_labels "
                "(workspace_id,conversation_id,key,value,updated_at) "
                "VALUES (0,:conv,'omni_project','proj',:t)"
            ),
            {"conv": _CONV, "t": _NOW},
        )
        c.execute(
            sa.text(
                "INSERT INTO comments (workspace_id,id,conversation_id,path,start_index,end_index,"
                "body,created_at,updated_at,status) VALUES "
                "(0,'a1b2c3d4-e5f6-7890-abcd-ef1234567890',:conv,'p',0,1,'b',:t,:t2,1)"
            ),
            {"conv": _CONV, "t": _NOW, "t2": _NOW * 1_000_000},
        )
        c.execute(
            sa.text(
                "INSERT INTO policies "
                "(workspace_id,id,name,name_cksum,session_id,type,scope,handler,created_at) "
                "VALUES (0,'pol_cccc5555cccc5555cccc5555cccc5555','p',:ck,:conv,1,2,'h',:t)"
            ),
            {"conv": _CONV, "ck": b"\x00" * 32, "t": _NOW},
        )
        c.execute(
            sa.text(
                "INSERT INTO hosts "
                "(workspace_id,host_id,owner,name,status,created_at,updated_at,token_hash) "
                "VALUES "
                "(0,'host_5b6e33d0e4f749a39bab562a5a72b421','alice@example.com','laptop',1,:t,:t,:th)"
            ),
            {"t": _NOW, "th": "0" * 64},
        )
        # FTS mirror rows (SQLite) carrying prefixed ids.
        c.execute(
            sa.text(
                "CREATE VIRTUAL TABLE IF NOT EXISTS conversation_items_fts USING fts5("
                "item_id UNINDEXED, conversation_id UNINDEXED, search_text)"
            )
        )
        for iid in ("msg_dddd3333dddd3333dddd3333dddd3333", "fc_eeee4444eeee4444eeee4444eeee4444"):
            c.execute(
                sa.text(
                    "INSERT INTO conversation_items_fts (item_id,conversation_id,search_text) "
                    "VALUES (:id,:conv,'hello world')"
                ),
                {"id": iid, "conv": _CONV},
            )
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.upgrade(config, "head")


def _col_type(engine: Engine, table: str, col: str) -> str:
    for c in sa.inspect(engine).get_columns(table):
        if c["name"] == col:
            return str(c["type"])
    raise AssertionError(f"{table}.{col} not found")


def test_in_scope_id_columns_are_varchar32(db_engine: Engine) -> None:
    """Every omnigent-uuid id column is narrowed to VARCHAR(32)."""
    for table, col in [
        ("agents", "id"),
        ("files", "id"),
        ("files", "session_id"),
        ("session_permissions", "conversation_id"),
        ("conversations", "id"),
        ("conversations", "parent_conversation_id"),
        ("conversations", "root_conversation_id"),
        ("conversations", "agent_id"),
        ("conversations", "host_id"),
        ("conversation_items", "id"),
        ("conversation_items", "conversation_id"),
        ("conversation_labels", "conversation_id"),
        ("comments", "id"),
        ("comments", "conversation_id"),
        ("policies", "id"),
        ("policies", "session_id"),
        ("hosts", "host_id"),
    ]:
        assert _col_type(db_engine, table, col) == "VARCHAR(32)", f"{table}.{col}"


def test_excluded_columns_stay_wide(db_engine: Engine) -> None:
    """Non-uuid id columns keep their original width."""
    assert _col_type(db_engine, "conversations", "runner_id") == "VARCHAR(64)"
    assert _col_type(db_engine, "conversation_items", "response_id") == "VARCHAR(64)"
    assert _col_type(db_engine, "conversations", "external_session_id") == "VARCHAR(128)"
    assert _col_type(db_engine, "hosts", "token_hash") == "VARCHAR(64)"


def test_prefixes_stripped_from_existing_rows(tmp_path: Path) -> None:
    """Upgrade strips id prefixes (and comment-id dashes) from existing rows."""
    uri = f"sqlite:///{tmp_path / 'strip.db'}"
    engine = get_or_create_engine(uri)
    _seed_prefixed_rows(engine, _build_alembic_config(uri))
    with engine.begin() as c:
        assert (
            c.execute(sa.text("SELECT id FROM agents")).scalar()
            == "aaaa1111aaaa1111aaaa1111aaaa1111"
        )
        conv = c.execute(
            sa.text("SELECT id, agent_id, host_id FROM conversations WHERE title='root'")
        ).fetchone()
        assert conv.id == _CONV_BARE
        assert conv.agent_id == "aaaa1111aaaa1111aaaa1111aaaa1111"
        assert conv.host_id == "5b6e33d0e4f749a39bab562a5a72b421"
        assert c.execute(sa.text("SELECT session_id FROM files")).scalar() == _CONV_BARE
        items = (
            c.execute(sa.text("SELECT id FROM conversation_items ORDER BY position"))
            .scalars()
            .all()
        )
        assert items == ["dddd3333dddd3333dddd3333dddd3333", "eeee4444eeee4444eeee4444eeee4444"]
        assert (
            c.execute(sa.text("SELECT id FROM policies")).scalar()
            == "cccc5555cccc5555cccc5555cccc5555"
        )
        assert (
            c.execute(sa.text("SELECT host_id FROM hosts")).scalar()
            == "5b6e33d0e4f749a39bab562a5a72b421"
        )
        # comments.id: dashed uuid collapsed to bare hex
        assert (
            c.execute(sa.text("SELECT id FROM comments")).scalar()
            == "a1b2c3d4e5f67890abcdef1234567890"
        )
    engine.dispose()
    clear_engine_cache()


def test_excluded_values_untouched_on_upgrade(tmp_path: Path) -> None:
    """runner_id / response_id / external_session_id keep their exact values."""
    uri = f"sqlite:///{tmp_path / 'excl.db'}"
    engine = get_or_create_engine(uri)
    _seed_prefixed_rows(engine, _build_alembic_config(uri))
    with engine.begin() as c:
        conv = c.execute(
            sa.text("SELECT runner_id, external_session_id FROM conversations WHERE title='root'")
        ).fetchone()
        assert conv.runner_id == "runner_9999888877776666555544443333aaaa"
        assert conv.external_session_id == "ext-session-with-dashes-1"
        rids = (
            c.execute(sa.text("SELECT response_id FROM conversation_items ORDER BY position"))
            .scalars()
            .all()
        )
        assert rids == ["resp_claude_abc", "kimi:a0b2-79"]
    engine.dispose()
    clear_engine_cache()


def test_fts_mirror_stripped_and_search_matches(tmp_path: Path) -> None:
    """FTS item_id/conversation_id are stripped so search still joins post-migration."""
    uri = f"sqlite:///{tmp_path / 'fts.db'}"
    engine = get_or_create_engine(uri)
    _seed_prefixed_rows(engine, _build_alembic_config(uri))
    with engine.begin() as c:
        rows = (
            c.execute(
                sa.text(
                    "SELECT ci.id FROM conversation_items_fts f "
                    "JOIN conversation_items ci ON ci.id = f.item_id "
                    "WHERE f.conversation_id = :conv AND f.search_text MATCH 'hello'"
                ),
                {"conv": _CONV_BARE},
            )
            .scalars()
            .all()
        )
        assert len(rows) == 2, "FTS search must join to migrated (bare) item ids"
    engine.dispose()
    clear_engine_cache()


def test_parent_title_unique_index_preserved(tmp_path: Path) -> None:
    """The partial unique index survives the column rebuild."""
    uri = f"sqlite:///{tmp_path / 'idx.db'}"
    engine = get_or_create_engine(uri)
    _seed_prefixed_rows(engine, _build_alembic_config(uri))
    with pytest.raises(sa.exc.IntegrityError):
        with engine.begin() as c:
            c.execute(
                sa.text(
                    "INSERT INTO conversations (workspace_id,id,created_at,updated_at,title,kind,"
                    "parent_conversation_id,root_conversation_id) VALUES "
                    "(0,'33333333333333333333333333333333',1,1,'child',2,:conv,:conv)"
                ),
                {"conv": _CONV_BARE},
            )  # duplicate (parent, title) as the migrated child
    engine.dispose()
    clear_engine_cache()


def test_downgrade_widens_columns(tmp_path: Path) -> None:
    """Downgrade restores VARCHAR(64) (prefixes are intentionally not restored)."""
    uri = f"sqlite:///{tmp_path / 'down.db'}"
    engine = get_or_create_engine(uri)
    assert _col_type(engine, "conversations", "id") == "VARCHAR(32)"
    config = _build_alembic_config(uri)
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.downgrade(config, _PREV)
    assert _col_type(engine, "conversations", "id") == "VARCHAR(64)"
    assert _col_type(engine, "conversation_items", "id") == "VARCHAR(64)"
    engine.dispose()
    clear_engine_cache()
