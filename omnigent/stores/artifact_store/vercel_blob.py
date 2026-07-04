"""Vercel Blob implementation of ArtifactStore.

Stores artifact blobs in a **private** Vercel Blob store over the network,
so the artifact store survives an ephemeral or multi-replica deployment —
the Vercel-native counterpart of :class:`~omnigent.stores.artifact_store.s3.S3ArtifactStore`
for deploys where no S3-compatible bucket is available (Vercel has no
persistent disk and its marketplace offers no object storage).

Authentication uses the ``BLOB_READ_WRITE_TOKEN`` environment variable,
which Vercel injects automatically when a Blob store is connected to the
project (``vercel blob create-store <name> --access private --yes``). The
token is a long-lived static credential that Vercel documents as usable
from code running outside Vercel too.

Storage location format::

    vercel-blob://[<prefix>]

Requirements::

    pip install vercel
"""

from __future__ import annotations

import os
from pathlib import PurePosixPath, PureWindowsPath

from omnigent.stores.artifact_store import ArtifactStore

_TOKEN_ENV = "BLOB_READ_WRITE_TOKEN"


def _ensure_sdk() -> None:
    """
    Verify that the official ``vercel`` SDK is installed.

    :raises ImportError: If the package is not available.
    """
    try:
        import vercel.blob  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "VercelBlobArtifactStore requires the official 'vercel' SDK. "
            "Install with: pip install vercel"
        ) from exc


def _parse_blob_uri(storage_location: str) -> str:
    """
    Extract the optional pathname prefix from a ``vercel-blob://`` URI.

    :param storage_location: The full URI, e.g. ``"vercel-blob://artifacts"``.
    :returns: The prefix without leading/trailing slashes, ``""`` when absent.
    :raises ValueError: If the URI doesn't start with ``vercel-blob://``.
    """
    if not storage_location.startswith("vercel-blob://"):
        raise ValueError(
            f"storage_location must start with 'vercel-blob://', got: {storage_location!r}"
        )
    return storage_location[len("vercel-blob://") :].strip("/")


def _validate_key(key: str) -> None:
    """
    Validate an artifact key against traversal attacks.

    Same validation as the other backends — reject empty keys, ``..``
    sequences, backslashes, and absolute paths — so a crafted key can't
    escape the configured prefix.

    :param key: Forward-slash-separated artifact key, e.g.
        ``"agents/agent_abc123/bundle.tar.gz"``.
    :raises ValueError: If the key is invalid.
    """
    parts = PurePosixPath(key).parts
    if (
        not parts
        or ".." in parts
        or "\\" in key
        or PurePosixPath(key).is_absolute()
        or PureWindowsPath(key).is_absolute()
    ):
        raise ValueError(f"invalid artifact key: {key!r}")


class VercelBlobArtifactStore(ArtifactStore):
    """
    Stores binary blobs in a private Vercel Blob store.

    All I/O goes through the official ``vercel`` SDK — no local filesystem —
    so the store is durable and shared across replicas. The
    ``storage_location`` is a ``vercel-blob://[prefix]`` URI; keys are stored
    under the prefix::

        vercel-blob://artifacts
            artifacts/agents/agent_abc123/bundle.tar.gz
            artifacts/executor_storage/conv_123/agent.tar.gz

    The Blob store must be created with **private** access; artifact blobs
    (agent bundles, user files) must not be world-readable.

    :param storage_location: Blob URI, e.g. ``"vercel-blob://artifacts"``.
    :param token: Optional read-write token (for tests). When omitted, the
        ``BLOB_READ_WRITE_TOKEN`` environment variable is required.
    """

    def __init__(self, storage_location: str, token: str | None = None) -> None:
        """
        Initialize the Vercel Blob artifact store.

        :param storage_location: Blob URI, e.g. ``"vercel-blob://artifacts"``.
        :param token: Optional read-write token override.
        :raises ImportError: If the ``vercel`` SDK is not installed.
        :raises ValueError: If the URI format is invalid or no token is set.
        """
        _ensure_sdk()
        super().__init__(storage_location)
        self._prefix = _parse_blob_uri(storage_location)
        self._token = token or os.environ.get(_TOKEN_ENV) or ""
        if not self._token:
            raise ValueError(
                f"VercelBlobArtifactStore requires the {_TOKEN_ENV} environment "
                "variable (injected by Vercel when a Blob store is connected to "
                "the project), or an explicit token."
            )

    def _resolve(self, key: str) -> str:
        """
        Map an artifact key to a full Blob pathname (prefix + key).

        :param key: Forward-slash-separated artifact key.
        :returns: The Blob pathname, e.g. ``"artifacts/agents/abc/bundle.tar.gz"``.
        :raises ValueError: If the key is invalid.
        """
        _validate_key(key)
        return f"{self._prefix}/{key}" if self._prefix else key

    # ── ArtifactStore interface ──────────────────────────────

    def put(self, key: str, data: bytes) -> None:
        """
        Upload bytes to the Blob store. Overwrites if the key exists.

        :param key: Forward-slash-separated artifact key.
        :param data: Raw bytes to store.
        """
        from vercel import blob

        blob.put(
            self._resolve(key),
            data,
            access="private",
            overwrite=True,
            token=self._token,
        )

    def get(self, key: str) -> bytes:
        """
        Download bytes for a key.

        :param key: Forward-slash-separated artifact key.
        :returns: The raw bytes of the stored blob.
        :raises KeyError: If no blob exists for the key.
        """
        from vercel import blob

        try:
            return blob.get(self._resolve(key), access="private", token=self._token).content
        except blob.BlobNotFoundError:
            raise KeyError(key) from None

    def delete(self, key: str) -> None:
        """
        Remove a blob. No-op if the key does not exist (Blob deletes are
        idempotent).

        :param key: Forward-slash-separated artifact key.
        """
        from vercel import blob

        blob.delete(self._resolve(key), token=self._token)

    def exists(self, key: str) -> bool:
        """
        Check whether a blob exists, via a metadata lookup (no download).

        :param key: Forward-slash-separated artifact key.
        :returns: ``True`` if the blob exists, ``False`` otherwise.
        """
        from vercel import blob

        try:
            blob.head(self._resolve(key), token=self._token)
            return True
        except blob.BlobNotFoundError:
            return False
