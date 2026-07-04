"""Vercel entrypoint for the Omnigent server: bind first, migrate behind a 503.

Vercel container functions must accept TCP connections within **15 s** of
boot, but the standard entrypoint (``deploy/docker/entrypoint.py``) binds
only after running Alembic migrations — and a first boot against a fresh
remote Postgres (Neon) spends ~1 minute on them, so that order can never
fit the window. This wrapper inverts it: uvicorn binds immediately on a
deferring ASGI shim that answers ``503`` (with ``Retry-After``) while
config resolution, migrations, and app construction run in a worker
thread; once the real app is ready, its lifespan is entered on the
serving loop and every request is delegated to it.

Ships only in the Vercel image: ``Dockerfile.vercel`` copies this file
next to the standard entrypoint (``/app/entrypoint.py``, imported below)
and swaps the ``CMD``. Every other platform keeps migrate-then-bind.

Importing this module has no side effects beyond importing the standard
entrypoint module (itself side-effect free); nothing touches the network
or database until ``main()`` runs.
"""

from __future__ import annotations

import asyncio
import logging
import os
import traceback
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING, Any

import entrypoint  # the standard entrypoint, shipped at /app/entrypoint.py

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from entrypoint import _BuiltApp, _ResolvedConfig

# Named under the omnigent.* hierarchy so post-boot lines still emit once the
# app's logging config takes over the root logger.
logger = logging.getLogger("omnigent.deploy.vercel")

_STARTING_BODY = b'{"detail": "server starting (running database migrations); retry shortly"}'
_FAILED_BODY = b'{"detail": "server failed to boot; see the deployment logs"}'


def _log_fatal(prefix: str) -> None:
    """Log the current exception on one line.

    Vercel's log stream records each stderr line as a separate event and
    can drop a multi-line traceback's continuation lines, so flatten it.
    """
    logger.error("FATAL: %s: %s", prefix, traceback.format_exc().replace("\n", " | "))


def _migrate_and_build(resolved_config: _ResolvedConfig) -> _BuiltApp:
    """Run the slow, blocking half of the standard entrypoint's ``main()``."""
    entrypoint.run_migrations(resolved_config.database_url)
    return entrypoint.build_app(resolved_config)


class _DeferredApp:
    """ASGI shim: 503 until the real app is ready, then pure delegation.

    :param resolved_config: The pre-resolved startup config, or ``None``
        when config resolution already failed (the shim then serves 500s
        so the failure is visible in ``vercel logs`` instead of surfacing
        as the platform's opaque could-not-connect error).
    """

    def __init__(self, resolved_config: _ResolvedConfig | None) -> None:
        self._resolved_config = resolved_config
        self._real_app: Callable[..., Awaitable[None]] | None = None
        self._boot_failed = resolved_config is None
        self._lifespan_stack: AsyncExitStack | None = None

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        if scope["type"] == "lifespan":
            await self._lifespan(receive, send)
            return
        if self._real_app is not None:
            await self._real_app(scope, receive, send)
            return
        status = 500 if self._boot_failed else 503
        body = _FAILED_BODY if self._boot_failed else _STARTING_BODY
        headers = [
            (b"content-type", b"application/json"),
            (b"retry-after", b"5"),
        ]
        if scope["type"] == "websocket":
            # Refuse the upgrade with a retryable 5xx where the server
            # supports denial responses: a bare pre-accept close surfaces
            # as a generic 403, which tunnel clients treat as fatal instead
            # of retrying into the ready server.
            await receive()
            if "websocket.http.response" in (scope.get("extensions") or {}):
                await send(
                    {"type": "websocket.http.response.start", "status": status, "headers": headers}
                )
                await send({"type": "websocket.http.response.body", "body": body})
            else:
                await send({"type": "websocket.close", "code": 1013})
            return
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": body})

    async def _lifespan(
        self,
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        await receive()  # lifespan.startup
        boot_task = asyncio.get_running_loop().create_task(self._boot())
        await send({"type": "lifespan.startup.complete"})
        await receive()  # lifespan.shutdown
        boot_task.cancel()
        if self._lifespan_stack is not None:
            await self._lifespan_stack.aclose()
        await send({"type": "lifespan.shutdown.complete"})

    async def _boot(self) -> None:
        """Migrate + build off-loop, then enter the app's lifespan on-loop."""
        if self._resolved_config is None:
            return
        try:
            loop = asyncio.get_running_loop()
            built = await loop.run_in_executor(None, _migrate_and_build, self._resolved_config)
            stack = AsyncExitStack()
            await stack.enter_async_context(built.app.router.lifespan_context(built.app))
            self._lifespan_stack = stack
            self._real_app = built.app
            logger.info("Omnigent server ready; shim now delegating requests.")
        except Exception:  # noqa: BLE001 — boot catch-all so failures land in logs
            self._boot_failed = True
            _log_fatal("omnigent server failed to boot")


def main() -> None:
    """Bind uvicorn on the deferring shim and boot the server behind it."""
    import uvicorn

    from omnigent.runner.transports.ws_tunnel.limits import RUNNER_TUNNEL_MAX_MESSAGE_BYTES

    try:
        # Env/config parsing only — no database traffic, so well inside the
        # startup window. The slow parts run behind the shim in _boot().
        resolved_config = entrypoint._resolve_config()
        host, port = resolved_config.host, resolved_config.port
    except Exception:  # noqa: BLE001 — startup catch-all so failures land in logs
        _log_fatal("omnigent server configuration failed")
        resolved_config = None
        host = os.environ.get("HOST", "0.0.0.0")
        port = int(os.environ.get("PORT", "8000"))

    logger.info("Starting omnigent server (deferred boot) on %s:%d", host, port)
    try:
        uvicorn.run(
            _DeferredApp(resolved_config),
            host=host,
            port=port,
            ws_max_size=RUNNER_TUNNEL_MAX_MESSAGE_BYTES,
        )
    except Exception:
        _log_fatal("uvicorn exited")
        raise


if __name__ == "__main__":
    main()
