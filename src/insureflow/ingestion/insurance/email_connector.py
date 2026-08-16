"""IMAP email connector for broker submission intake.

Polls an IMAP mailbox for emails with PDF/XML attachments,
downloads them, and returns documents in the standard format
used by the insurance ingestion pipeline.

Environment variables:
    IMAP_HOST       - IMAP server hostname (e.g. imap.gmail.com)
    IMAP_PORT       - IMAP server port (default 993)
    IMAP_USERNAME   - Mailbox username / email address
    IMAP_PASSWORD   - Mailbox password or app password
    IMAP_MAILBOX    - Mailbox to search (default INBOX)
    IMAP_USE_SSL    - Use SSL (default true)
"""

from __future__ import annotations

import base64
import email
import imaplib
import logging
import os
import re
from email.header import decode_header
from email.message import Message
from pathlib import Path
from typing import Any

from insureflow.ingestion.structured_docs import email_body_text

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".xml",
    ".json",
    ".txt",
    ".md",
    ".csv",
    ".xlsx",
    ".xls",
    ".xlsm",
    ".docx",
    ".doc",
    ".eml",
    ".msg",
    ".html",
    ".htm",
    ".png",
    ".jpg",
    ".jpeg",
    ".tiff",
    ".bmp",
    ".tif",
}

BINARY_EXTENSIONS = frozenset(
    {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".tif", ".xlsx", ".xls", ".xlsm", ".docx", ".doc", ".eml", ".msg"}
)

MAX_ATTACHMENT_SIZE_MB = 25
MAX_EMAILS = 50


def _decode_header_value(raw: str | None) -> str:
    """Decode an RFC 2047 encoded header value."""
    if not raw:
        return ""
    parts = decode_header(raw)
    decoded = []
    for data, charset in parts:
        if isinstance(data, bytes):
            decoded.append(data.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(data)
    return "".join(decoded)


def _sanitize_filename(name: str) -> str:
    """Remove path components and sanitize the filename."""
    name = Path(name).name
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    return name.strip() or "attachment"


def _extract_attachments(msg: Message) -> list[dict[str, str]]:
    """Extract supported attachments from an email message."""
    docs: list[dict[str, str]] = []
    max_bytes = MAX_ATTACHMENT_SIZE_MB * 1024 * 1024

    for part in msg.walk():
        content_disposition = part.get("Content-Disposition", "")
        if "attachment" not in content_disposition:
            continue

        filename = part.get_filename()
        if not filename:
            continue

        filename = _decode_header_value(filename)
        filename = _sanitize_filename(filename)
        ext = Path(filename).suffix.lower()

        if ext not in SUPPORTED_EXTENSIONS:
            logger.debug("Skipping unsupported attachment: %s", filename)
            continue

        payload = part.get_payload(decode=True)
        if payload is None or not isinstance(payload, bytes):
            continue

        if len(payload) > max_bytes:
            logger.warning(
                "Attachment %s exceeds %dMB limit, skipping",
                filename,
                MAX_ATTACHMENT_SIZE_MB,
            )
            continue

        is_binary = ext in BINARY_EXTENSIONS

        if is_binary:
            docs.append(
                {
                    "filename": filename,
                    "content": base64.b64encode(payload).decode("ascii"),
                    "encoding": "base64",
                }
            )
        else:
            text = payload.decode("utf-8", errors="replace")
            docs.append(
                {
                    "filename": filename,
                    "content": text,
                    "encoding": "utf-8",
                }
            )

    return docs


def _parse_email_date(date_str: str | None) -> str:
    """Best-effort extraction of a date string from email Date header."""
    if not date_str:
        return ""
    return date_str.strip()


class ImapConnection:
    """Manages an IMAP connection and searches for broker submission emails."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        mailbox: str | None = None,
        use_ssl: bool = True,
    ):
        self.host = host or os.environ.get("IMAP_HOST", "")
        self.port = port or int(os.environ.get("IMAP_PORT", "993"))
        self.username = username or os.environ.get("IMAP_USERNAME", "")
        self.password = password or os.environ.get("IMAP_PASSWORD", "")
        self.mailbox = mailbox or os.environ.get("IMAP_MAILBOX", "INBOX")
        self.use_ssl = use_ssl

        self._conn: imaplib.IMAP4_SSL | imaplib.IMAP4 | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self.host and self.username and self.password)

    def connect(self) -> None:
        """Open the IMAP connection and authenticate."""
        if not self.is_configured:
            raise ConnectionError("IMAP not configured. Set IMAP_HOST, IMAP_USERNAME, and IMAP_PASSWORD environment variables.")

        host = str(self.host)
        port = int(self.port) if self.port else 993
        username = str(self.username)
        password = str(self.password)

        if self.use_ssl:
            self._conn = imaplib.IMAP4_SSL(host, port)
        else:
            self._conn = imaplib.IMAP4(host, port)

        self._conn.login(username, password)
        logger.info("Connected to %s as %s", host, username)

    def select_mailbox(self) -> int:
        """Select the target mailbox and return the message count."""
        if self._conn is None:
            raise ConnectionError("Not connected")
        status, data = self._conn.select(str(self.mailbox))
        if status != "OK":
            raise ConnectionError(f"Failed to select mailbox {self.mailbox}: {data}")
        raw = data[0] if data else b"0"
        return int(raw) if raw else 0

    def search_unread(self) -> list[str]:
        """Search for unread message IDs in the selected mailbox."""
        if self._conn is None:
            raise ConnectionError("Not connected")
        status, data = self._conn.search(None, "UNSEEN")
        if status != "OK" or not data:
            return []
        raw: bytes = data[0] if data else b""
        return [s.decode("ascii") for s in raw.split() if isinstance(s, bytes)]

    def search_all(self, limit: int = MAX_EMAILS) -> list[str]:
        """Search for recent messages (newest first), limited to ``limit``."""
        if self._conn is None:
            raise ConnectionError("Not connected")
        status, data = self._conn.search(None, "ALL")
        if status != "OK" or not data:
            return []
        raw: bytes = data[0] if data else b""
        all_ids = [s.decode("ascii") for s in raw.split() if isinstance(s, bytes)]
        return all_ids[-limit:][::-1]

    def fetch_message(self, msg_id: str) -> Message | None:
        """Fetch a single message by ID and return the parsed Message object."""
        if self._conn is None:
            raise ConnectionError("Not connected")
        status, data = self._conn.fetch(msg_id, "(RFC822)")
        if status != "OK" or not data or not data[0]:
            return None
        raw_email = data[0][1]
        if not isinstance(raw_email, bytes):
            return None
        return email.message_from_bytes(raw_email)

    def close(self) -> None:
        """Close the connection."""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            try:
                self._conn.logout()
            except Exception:
                pass
            self._conn = None


def pull_email_submissions(
    mailbox: str | None = None,
    unread_only: bool = False,
    limit: int = MAX_EMAILS,
    host: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> dict[str, Any]:
    """Connect to IMAP, search for broker submission emails, extract attachments.

    Credentials can be passed directly (from UI) or read from env vars.
    """
    conn = ImapConnection(
        host=host,
        username=username,
        password=password,
        mailbox=mailbox,
    )
    if not conn.is_configured:
        raise ConnectionError("Email integration not configured. Set IMAP_HOST, IMAP_USERNAME, and IMAP_PASSWORD in your environment.")

    try:
        conn.connect()
        conn.select_mailbox()

        if unread_only:
            msg_ids = conn.search_unread()
        else:
            msg_ids = conn.search_all(limit=limit)

        emails: list[dict[str, Any]] = []
        all_documents: list[dict[str, str]] = []

        for idx, msg_id in enumerate(msg_ids[:limit]):
            msg = conn.fetch_message(msg_id)
            if msg is None:
                continue

            subject = _decode_header_value(msg.get("Subject"))
            from_addr = _decode_header_value(msg.get("From"))
            date_str = _parse_email_date(msg.get("Date"))
            attachments = _extract_attachments(msg)
            body = email_body_text(msg)

            # Body-only emails still carry the submission narrative — surface it
            # as a document so the pipeline has something to chew on.
            if not attachments and body:
                attachments = [
                    {
                        "filename": f"{_sanitize_filename(subject) or 'submission'}-body.txt",
                        "content": body,
                        "encoding": "utf-8",
                    }
                ]

            email_entry: dict[str, Any] = {
                "id": f"email-{idx}",
                "subject": subject,
                "from": from_addr,
                "date": date_str,
                "body": body,
                "attachment_count": len(attachments),
                "documents": attachments,
            }
            emails.append(email_entry)
            all_documents.extend(attachments)

        return {
            "emails": emails,
            "documents": all_documents,
            "emails_found": len(msg_ids),
            "documents_found": len(all_documents),
        }

    finally:
        conn.close()


def filter_emails_by_ids(
    emails: list[dict[str, Any]],
    selected_ids: list[str],
) -> list[dict[str, str]]:
    """Filter email list by IDs and return flat document list."""
    selected = {eid for eid in selected_ids}
    docs: list[dict[str, str]] = []
    for email_entry in emails:
        if email_entry["id"] in selected:
            docs.extend(email_entry.get("documents", []))
    return docs
