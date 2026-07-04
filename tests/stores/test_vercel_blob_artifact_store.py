"""Unit tests for VercelBlobArtifactStore against a faked ``vercel.blob`` SDK.

The official ``vercel`` SDK is an optional runtime dependency (installed only
in the Vercel deploy image), so these tests install an in-memory fake of the
``vercel.blob`` module surface the store uses — ``put`` / ``get`` / ``head`` /
``delete`` / ``BlobNotFoundError`` — and exercise the store's key resolution,
error mapping, and token handling on top of it.
"""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass

import pytest

_TOKEN = "vercel_blob_rw_test_token"


@dataclass
class _FakeGetResult:
    content: bytes


def _install_fake_blob_sdk(monkeypatch: pytest.MonkeyPatch) -> tuple[dict[str, bytes], list]:
    """Install an in-memory ``vercel.blob`` fake; returns (blobs, put_calls)."""
    blobs: dict[str, bytes] = {}
    put_calls: list[dict] = []

    blob_module = types.ModuleType("vercel.blob")

    class BlobNotFoundError(Exception):
        pass

    def put(path: str, body: bytes, *, access: str, overwrite: bool, token: str) -> None:
        put_calls.append({"path": path, "access": access, "overwrite": overwrite, "token": token})
        blobs[path] = body

    def get(path: str, *, access: str, token: str) -> _FakeGetResult:
        if path not in blobs:
            raise BlobNotFoundError()
        return _FakeGetResult(content=blobs[path])

    def head(path: str, *, token: str) -> object:
        if path not in blobs:
            raise BlobNotFoundError()
        return object()

    def delete(path: str, *, token: str) -> None:
        blobs.pop(path, None)

    blob_module.BlobNotFoundError = BlobNotFoundError
    blob_module.put = put
    blob_module.get = get
    blob_module.head = head
    blob_module.delete = delete

    vercel_module = types.ModuleType("vercel")
    vercel_module.blob = blob_module
    monkeypatch.setitem(sys.modules, "vercel", vercel_module)
    monkeypatch.setitem(sys.modules, "vercel.blob", blob_module)
    return blobs, put_calls


@pytest.fixture()
def fake_sdk(monkeypatch: pytest.MonkeyPatch) -> tuple[dict[str, bytes], list]:
    return _install_fake_blob_sdk(monkeypatch)


@pytest.fixture()
def blob_store(fake_sdk):
    from omnigent.stores.artifact_store.vercel_blob import VercelBlobArtifactStore

    return VercelBlobArtifactStore("vercel-blob://artifacts", token=_TOKEN)


def test_put_and_get_roundtrip(blob_store) -> None:
    blob_store.put("agents/agent_abc/bundle.tar.gz", b"bundle-data")
    assert blob_store.get("agents/agent_abc/bundle.tar.gz") == b"bundle-data"


def test_keys_are_prefixed_and_private(blob_store, fake_sdk) -> None:
    """Keys land under the URI prefix, uploaded private with overwrite —
    artifact blobs must never be world-readable and re-puts must win."""
    blobs, put_calls = fake_sdk
    blob_store.put("k", b"v")
    assert list(blobs) == ["artifacts/k"]
    assert put_calls == [
        {"path": "artifacts/k", "access": "private", "overwrite": True, "token": _TOKEN}
    ]


def test_no_prefix_uri(fake_sdk) -> None:
    from omnigent.stores.artifact_store.vercel_blob import VercelBlobArtifactStore

    blobs, _ = fake_sdk
    store = VercelBlobArtifactStore("vercel-blob://", token=_TOKEN)
    store.put("agents/a/bundle.tar.gz", b"x")
    assert list(blobs) == ["agents/a/bundle.tar.gz"]


def test_get_missing_raises_key_error(blob_store) -> None:
    """A missing key must raise KeyError (not the SDK's BlobNotFoundError) so
    callers like the agent-bundle loader catch a stable exception type."""
    with pytest.raises(KeyError, match="no-such-key"):
        blob_store.get("no-such-key")


def test_exists_and_delete_idempotent(blob_store) -> None:
    assert not blob_store.exists("k")
    blob_store.put("k", b"v")
    assert blob_store.exists("k")
    blob_store.delete("k")
    blob_store.delete("k")  # idempotent
    assert not blob_store.exists("k")


@pytest.mark.parametrize("bad_key", ["", "../escape", "a/../../b", "/absolute", "back\\slash"])
def test_invalid_keys_rejected(blob_store, bad_key: str) -> None:
    with pytest.raises(ValueError, match="invalid artifact key"):
        blob_store.put(bad_key, b"x")


def test_bad_uri_scheme_rejected(fake_sdk) -> None:
    from omnigent.stores.artifact_store.vercel_blob import VercelBlobArtifactStore

    with pytest.raises(ValueError, match="vercel-blob://"):
        VercelBlobArtifactStore("s3://bucket", token=_TOKEN)


def test_token_from_env(fake_sdk, monkeypatch: pytest.MonkeyPatch) -> None:
    from omnigent.stores.artifact_store.vercel_blob import VercelBlobArtifactStore

    _, put_calls = fake_sdk
    monkeypatch.setenv("BLOB_READ_WRITE_TOKEN", "env-token")
    VercelBlobArtifactStore("vercel-blob://").put("k", b"v")
    assert put_calls[0]["token"] == "env-token"


def test_missing_token_rejected(fake_sdk, monkeypatch: pytest.MonkeyPatch) -> None:
    from omnigent.stores.artifact_store.vercel_blob import VercelBlobArtifactStore

    monkeypatch.delenv("BLOB_READ_WRITE_TOKEN", raising=False)
    with pytest.raises(ValueError, match="BLOB_READ_WRITE_TOKEN"):
        VercelBlobArtifactStore("vercel-blob://")
