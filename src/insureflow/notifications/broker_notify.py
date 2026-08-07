"""Notify brokers of document / info requests (email + durable outbox)."""

from __future__ import annotations

import logging
import os
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _outbox_root() -> Path:
    root = Path(os.getenv("BROKER_EMAIL_OUTBOX", "./audit_logs/broker_outbox"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def compose_document_request(
    *,
    insured_name: str,
    bundle_id: str,
    documents: list[str],
    notes: str = "",
    share_url: str = "",
    broker_name: str = "",
    requested_by: str = "Underwriting",
) -> tuple[str, str]:
    docs = [d for d in documents if str(d).strip()]
    doc_lines = "\n".join(f"  • {d}" for d in docs) or "  • (see underwriter notes)"
    greeting = f"Hi {broker_name}," if broker_name else "Hello,"
    note_block = f"\nUnderwriter notes:\n{notes.strip()}\n" if notes.strip() else ""
    link_block = f"\nRespond / upload status here (no login required):\n{share_url}\n" if share_url else "\nYour underwriter will follow up with a status link shortly.\n"
    subject = f"Action required: documents for {insured_name or bundle_id}"
    body = f"""{greeting}

{requested_by} needs the following items to continue underwriting for {insured_name or "this submission"} ({bundle_id}):

{doc_lines}
{note_block}{link_block}
Please reply on the status link when the package is ready so we can clear conditions and move to decision.

Thank you,
{requested_by}
Rytera Underwriting
"""
    return subject, body.strip() + "\n"


def write_outbox(
    *,
    to_email: str,
    subject: str,
    body: str,
    bundle_id: str,
    meta: dict[str, Any] | None = None,
) -> Path:
    stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_bundle = "".join(c if c.isalnum() or c in "-_" else "_" for c in bundle_id)[:48]
    path = _outbox_root() / f"{stamp}_{safe_bundle}.eml.txt"
    payload = {
        "created_at": _now(),
        "to": to_email,
        "subject": subject,
        "body": body,
        "bundle_id": bundle_id,
        **(meta or {}),
    }
    import json

    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _smtp_configured() -> bool:
    return bool(os.getenv("SMTP_HOST", "").strip())


def send_smtp_email(*, to_email: str, subject: str, body: str, from_addr: str | None = None) -> dict[str, Any]:
    host = os.getenv("SMTP_HOST", "").strip()
    if not host:
        return {"sent": False, "mode": "outbox", "reason": "SMTP_HOST not configured"}
    port = int(os.getenv("SMTP_PORT", "587") or "587")
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes"}
    sender = (from_addr or os.getenv("SMTP_FROM") or os.getenv("BROKER_NOTIFY_FROM") or user or "noreply@rytera.local").strip()

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            if use_tls:
                smtp.starttls()
            if user and password:
                smtp.login(user, password)
            smtp.send_message(msg)
        return {"sent": True, "mode": "smtp", "from": sender, "to": to_email}
    except Exception as exc:
        logger.warning("SMTP broker notify failed: %s", exc)
        return {"sent": False, "mode": "smtp_failed", "error": str(exc), "from": sender, "to": to_email}


def notify_broker_document_request(
    *,
    to_email: str,
    insured_name: str,
    bundle_id: str,
    documents: list[str],
    notes: str = "",
    share_url: str = "",
    broker_name: str = "",
    requested_by: str = "Underwriting",
) -> dict[str, Any]:
    subject, body = compose_document_request(
        insured_name=insured_name,
        bundle_id=bundle_id,
        documents=documents,
        notes=notes,
        share_url=share_url,
        broker_name=broker_name,
        requested_by=requested_by,
    )
    mailto = ""
    if to_email:
        from urllib.parse import quote

        mailto = f"mailto:{to_email}?subject={quote(subject)}&body={quote(body[:1800])}"

    outbox_path = write_outbox(
        to_email=to_email or "(no recipient)",
        subject=subject,
        body=body,
        bundle_id=bundle_id,
        meta={"share_url": share_url, "documents": documents},
    )

    result: dict[str, Any] = {
        "subject": subject,
        "body": body,
        "to": to_email or "",
        "mailto": mailto,
        "outbox_path": str(outbox_path),
        "sent": False,
        "mode": "outbox",
    }

    if to_email and _smtp_configured():
        smtp_result = send_smtp_email(to_email=to_email, subject=subject, body=body)
        result.update(smtp_result)
    elif not to_email:
        result["reason"] = "No broker email on file — share link + draft saved for manual send"
    else:
        result["reason"] = "SMTP not configured — draft saved; use mailto or share link"

    return result
