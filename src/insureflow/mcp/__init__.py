from __future__ import annotations

from collections.abc import Callable

_run_server: Callable[..., None] | None = None
try:
    from insureflow.mcp.server import run_server as _run_server
except ImportError:
    pass


def run_server(*args: object, **kwargs: object) -> None:
    if _run_server is None:
        raise ImportError("mcp package is not installed. Run: pip install mcp>=1.0")
    _run_server(*args, **kwargs)


__all__ = ["run_server"]
