"""Cross-process file locking and atomic writes.

A multi-worker web server means several processes can write the same JSON or
JSONL store at once (auth users, registry entries, metrics). Naive ``write_text``
last-writer-wins corrupts files and loses writes. This module provides two small
primitives:

- ``FileLock`` — advisory OS-level lock (``fcntl.flock`` on POSIX, no-op on
  Windows) held via ``with``. Serializes writers across processes.
- ``atomic_write`` — write to a temp file in the same directory, fsync, then
  ``os.replace`` so readers never observe a partially written file.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

fcntl: Any
try:
    import fcntl

    _HAS_FCNTL = True
except ImportError:  # pragma: no cover - Windows
    fcntl = None
    _HAS_FCNTL = False


class FileLock:
    """Advisory cross-process lock bound to a sidecar ``.lock`` file."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._fd: int | None = None

    def __enter__(self) -> FileLock:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(self._path, os.O_CREAT | os.O_RDWR, 0o600)
        if _HAS_FCNTL:
            fcntl.flock(self._fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc: Any) -> None:
        self.release()

    def release(self) -> None:
        if self._fd is not None:
            if _HAS_FCNTL:
                try:
                    fcntl.flock(self._fd, fcntl.LOCK_UN)
                except OSError:
                    pass
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None

    def __del__(self) -> None:
        self.release()


def atomic_write(path: Path | str, data: str | bytes, encoding: str = "utf-8") -> None:
    """Write ``data`` to ``path`` atomically via temp file + ``os.replace``."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            if isinstance(data, bytes):
                f.write(data.decode(encoding))
            else:
                f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, target)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def atomic_append(path: Path | str, line: str, encoding: str = "utf-8") -> None:
    """Append a single line to a JSONL-style file under a cross-process lock."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not line.endswith("\n"):
        line += "\n"
    with FileLock(str(target) + ".lock"):
        with open(target, "a", encoding=encoding) as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
