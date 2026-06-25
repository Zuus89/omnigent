"""Tests for the runner's auto-forwarder registry + shared-bridge adoption.

A claude-native ``/clear`` rotates the live terminal's bridge onto a fresh
session while its transcript forwarder keeps running under the PRIOR session
id. :func:`_adopt_forwarder_on_shared_bridge` re-keys that forwarder onto the
new session so the new session's auto-create skips spawning a SECOND forwarder
on the same transcript (external conversation items have no server-side dedup,
so two forwarders persist every item twice — the duplicate-bubble bug).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Coroutine
from typing import Any

import pytest

from omnigent.runner import app as runner_app
from omnigent.runner.app import (
    _adopt_forwarder_on_shared_bridge,
    _cancel_auto_forwarder_task,
    _register_auto_forwarder_task,
)


@pytest.fixture(autouse=True)
async def _clean_registry() -> AsyncIterator[None]:
    """Isolate the module-level forwarder registry per test."""
    runner_app._AUTO_FORWARDER_TASKS.clear()
    runner_app._AUTO_FORWARDER_BRIDGE_DIRS.clear()
    yield
    # Cancel any tasks a test left behind so asyncio doesn't warn about
    # pending/destroyed tasks, then clear the maps.
    for task in list(runner_app._AUTO_FORWARDER_TASKS.values()):
        task.cancel()
    runner_app._AUTO_FORWARDER_TASKS.clear()
    runner_app._AUTO_FORWARDER_BRIDGE_DIRS.clear()


def _never() -> Coroutine[Any, Any, None]:
    """A coroutine that blocks forever — a stand-in for a live forwarder."""
    return asyncio.Event().wait()


@pytest.mark.asyncio
async def test_adopt_rekeys_live_forwarder_on_shared_bridge() -> None:
    """A live forwarder on the same bridge is moved onto the new session."""
    task = asyncio.create_task(_never())
    _register_auto_forwarder_task("conv_old", task, bridge_dir="/bridges/abc")

    adopted = _adopt_forwarder_on_shared_bridge("conv_new", "/bridges/abc")

    assert adopted is True
    # The task is now owned by the new session; the old key is gone.
    assert runner_app._AUTO_FORWARDER_TASKS.get("conv_new") is task
    assert "conv_old" not in runner_app._AUTO_FORWARDER_TASKS
    assert runner_app._AUTO_FORWARDER_BRIDGE_DIRS.get("conv_new") == "/bridges/abc"
    assert "conv_old" not in runner_app._AUTO_FORWARDER_BRIDGE_DIRS


@pytest.mark.asyncio
async def test_adopt_returns_false_when_no_forwarder_shares_the_bridge() -> None:
    """A fresh session (different bridge) is left to auto-create normally."""
    task = asyncio.create_task(_never())
    _register_auto_forwarder_task("conv_old", task, bridge_dir="/bridges/abc")

    adopted = _adopt_forwarder_on_shared_bridge("conv_new", "/bridges/other")

    assert adopted is False
    assert runner_app._AUTO_FORWARDER_TASKS.get("conv_old") is task
    assert "conv_new" not in runner_app._AUTO_FORWARDER_TASKS


@pytest.mark.asyncio
async def test_adopt_does_not_adopt_its_own_forwarder() -> None:
    """A session never adopts the forwarder already registered under itself."""
    task = asyncio.create_task(_never())
    _register_auto_forwarder_task("conv_x", task, bridge_dir="/bridges/abc")

    adopted = _adopt_forwarder_on_shared_bridge("conv_x", "/bridges/abc")

    assert adopted is False
    assert runner_app._AUTO_FORWARDER_TASKS.get("conv_x") is task


@pytest.mark.asyncio
async def test_adopt_ignores_a_finished_forwarder() -> None:
    """A done task on the bridge is not adopted (its forwarder already ended)."""

    async def _noop() -> None:
        return None

    task = asyncio.create_task(_noop())
    _register_auto_forwarder_task("conv_old", task, bridge_dir="/bridges/abc")
    await task  # let it finish

    adopted = _adopt_forwarder_on_shared_bridge("conv_new", "/bridges/abc")

    assert adopted is False
    assert "conv_new" not in runner_app._AUTO_FORWARDER_TASKS


@pytest.mark.asyncio
async def test_cancel_clears_bridge_map() -> None:
    """Cancelling a forwarder also drops its bridge-dir tracking entry."""
    task = asyncio.create_task(_never())
    _register_auto_forwarder_task("conv_old", task, bridge_dir="/bridges/abc")
    assert "conv_old" in runner_app._AUTO_FORWARDER_BRIDGE_DIRS

    await _cancel_auto_forwarder_task("conv_old")

    assert "conv_old" not in runner_app._AUTO_FORWARDER_TASKS
    assert "conv_old" not in runner_app._AUTO_FORWARDER_BRIDGE_DIRS


@pytest.mark.asyncio
async def test_register_without_bridge_dir_does_not_track() -> None:
    """Non-claude forwarders (no bridge_dir) are invisible to adoption."""
    task = asyncio.create_task(_never())
    _register_auto_forwarder_task("conv_codex", task)

    assert "conv_codex" not in runner_app._AUTO_FORWARDER_BRIDGE_DIRS
    # Nothing to adopt onto another session.
    assert _adopt_forwarder_on_shared_bridge("conv_new", "/bridges/abc") is False
