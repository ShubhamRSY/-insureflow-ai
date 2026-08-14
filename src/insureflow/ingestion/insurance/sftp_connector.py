"""SFTP broker-drop fetch (when host + credentials are present).

Not Airbyte/Fivetran — a direct pull of ACORD/PDF drops from the broker's box.
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TEXT_EXT = {".xml", ".json", ".txt", ".md", ".csv", ".html"}
BINARY_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".tif"}
MAX_FILES = 40
MAX_BYTES = 25 * 1024 * 1024


def sftp_configured(host: str | None = None) -> bool:
    h = (host or os.getenv("SFTP_HOST") or "").strip()
    user = os.getenv("SFTP_USERNAME", "").strip()
    secret = os.getenv("SFTP_PASSWORD", "").strip() or os.getenv("SFTP_KEY_PATH", "").strip()
    return bool(h and user and secret)


def _apply_host_key_policy(client: Any) -> None:
    """Reject unknown hosts in bank/production; AutoAdd only in lab."""
    import paramiko

    known = os.getenv("SFTP_KNOWN_HOSTS", "").strip()
    default_kh = Path.home() / ".ssh" / "known_hosts"
    if known and Path(known).is_file():
        client.load_host_keys(known)
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        return
    from insureflow.security.posture import resolve_security_posture

    if default_kh.is_file():
        client.load_host_keys(str(default_kh))
    if resolve_security_posture().is_hardened:
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
    else:
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())


def pull_sftp_submissions(
    *,
    host: str | None = None,
    remote_dir: str | None = None,
    max_files: int = MAX_FILES,
) -> dict[str, Any]:
    """List and download supported files from an SFTP intake directory."""
    try:
        import paramiko
    except ImportError as exc:
        raise ConnectionError("paramiko not installed — pip install paramiko for SFTP intake") from exc

    hostname = (host or os.getenv("SFTP_HOST") or "").strip()
    username = os.getenv("SFTP_USERNAME", "").strip()
    password = os.getenv("SFTP_PASSWORD", "").strip() or None
    key_path = os.getenv("SFTP_KEY_PATH", "").strip() or None
    port = int(os.getenv("SFTP_PORT", "22") or 22)
    directory = (remote_dir or os.getenv("SFTP_REMOTE_DIR") or ".").strip() or "."
    if not hostname or not username:
        raise ConnectionError("SFTP not configured — set SFTP_HOST and SFTP_USERNAME")
    if not password and not key_path:
        raise ConnectionError("SFTP not configured — set SFTP_PASSWORD or SFTP_KEY_PATH")

    client = paramiko.SSHClient()
    _apply_host_key_policy(client)
    pkey = None
    if key_path:
        pkey = paramiko.PKey.from_private_key_file(key_path)
    try:
        client.connect(
            hostname,
            port=port,
            username=username,
            password=password,
            pkey=pkey,
            timeout=15,
            allow_agent=False,
            look_for_keys=False,
        )
        sftp = client.open_sftp()
        documents: list[dict[str, str]] = []
        listed = 0
        for entry in sftp.listdir_attr(directory):
            name = entry.filename
            if name in {".", ".."} or name.startswith("."):
                continue
            ext = Path(name).suffix.lower()
            if ext not in TEXT_EXT | BINARY_EXT:
                continue
            remote = f"{directory.rstrip('/')}/{name}"
            listed += 1
            size = int(getattr(entry, "st_size", 0) or 0)
            if size > MAX_BYTES:
                logger.warning("Skipping oversized SFTP file %s (%s bytes)", remote, size)
                continue
            with sftp.file(remote, "rb") as fh:
                body = fh.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                continue
            if ext in BINARY_EXT:
                documents.append(
                    {
                        "filename": name,
                        "content": base64.b64encode(body).decode("ascii"),
                        "encoding": "base64",
                        "sftp_path": remote,
                    }
                )
            else:
                documents.append(
                    {
                        "filename": name,
                        "content": body.decode("utf-8", errors="replace"),
                        "encoding": "utf-8",
                        "sftp_path": remote,
                    }
                )
            if len(documents) >= max_files:
                break
        sftp.close()
    finally:
        client.close()

    return {
        "host": hostname,
        "remote_dir": directory,
        "documents": documents,
        "documents_found": len(documents),
        "objects_considered": listed,
    }
