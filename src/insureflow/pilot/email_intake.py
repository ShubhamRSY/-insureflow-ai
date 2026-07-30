"""Ingest broker emails into pilot_packages/ folders for shadow UW."""

from __future__ import annotations

import base64
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from insureflow.pilot.auto_redact import redact_pilot_package
from insureflow.pilot.package_loader import load_pilot_package

BINARY_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".tif"}


def _slug(value: str, fallback: str = "submission") -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", (value or "").strip()).strip("-").lower()
    return cleaned[:48] or fallback


def documents_to_pilot_package(
    documents: list[dict[str, Any]],
    *,
    partner: str,
    submission_id: str | None = None,
    root: Path | None = None,
    meta: dict[str, Any] | None = None,
    auto_redact: bool = True,
) -> dict[str, Any]:
    """Persist pulled documents (email/source hub format) as a pilot package."""
    base = root or Path.cwd() / "pilot_packages"
    partner_slug = _slug(partner, "partner")
    sub_id = _slug(submission_id or f"mail-{datetime.now(tz=timezone.utc).strftime('%Y%m%d-%H%M%S')}")
    dest = base / partner_slug / sub_id
    dest.mkdir(parents=True, exist_ok=True)

    saved: list[str] = []
    for i, doc in enumerate(documents):
        filename = str(doc.get("filename") or f"document_{i + 1}.txt")
        content = doc.get("content") or ""
        encoding = str(doc.get("encoding") or "utf-8")
        low = filename.lower()
        suffix = Path(filename).suffix.lower()

        if low.endswith(".xml") or "acord" in low:
            target = dest / ("acord.xml" if not (dest / "acord.xml").exists() else filename)
        elif "loss" in low:
            target = dest / ("loss_run.md" if not (dest / "loss_run.md").exists() else filename)
        elif "sov" in low or "schedule" in low:
            target = dest / ("sov.md" if not (dest / "sov.md").exists() else filename)
        elif "inspect" in low:
            target = dest / ("inspection.md" if not (dest / "inspection.md").exists() else filename)
        else:
            supp = dest / "supplemental"
            supp.mkdir(exist_ok=True)
            target = supp / filename

        if encoding == "base64":
            raw = base64.b64decode(content) if isinstance(content, str) else bytes(content)
            target.write_bytes(raw)
            if suffix in BINARY_SUFFIXES:
                note_dir = dest / "supplemental"
                note_dir.mkdir(exist_ok=True)
                (note_dir / f"{Path(filename).stem}_binary_note.md").write_text(
                    f"# Binary attachment stored\n\nOriginal filename: {filename}\nProvide a text extract or run OCR before shadow underwriting.\n",
                    encoding="utf-8",
                )
        else:
            text = content if isinstance(content, str) else str(content)
            target.write_text(text, encoding="utf-8")
        saved.append(str(target.relative_to(dest)))

    payload = {
        "insured_name": (meta or {}).get("insured_name") or sub_id,
        "source": "email_intake",
        "ingested_at": datetime.now(tz=timezone.utc).isoformat(),
        "files": saved,
        **(meta or {}),
    }
    (dest / "meta.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    pkg = load_pilot_package(dest, partner=partner_slug)
    result: dict[str, Any] = {
        "partner": partner_slug,
        "submission_id": dest.name,
        "path": str(dest),
        "files": saved,
        "has_acord": bool(pkg.acord_xml),
    }
    if auto_redact:
        result["redaction"] = redact_pilot_package(pkg, inplace=True)
    return result


def ingest_imap_to_pilot(
    *,
    partner: str = "email",
    unread_only: bool = True,
    limit: int = 10,
    root: Path | None = None,
    auto_redact: bool = True,
) -> dict[str, Any]:
    """Pull recent IMAP emails with attachments into pilot_packages/."""
    from insureflow.ingestion.insurance.email_connector import ImapConnection, pull_email_submissions

    conn = ImapConnection()
    if not conn.is_configured:
        return {
            "ok": False,
            "error": "IMAP not configured — set IMAP_HOST, IMAP_USERNAME, IMAP_PASSWORD",
            "packages": [],
        }

    pulled = pull_email_submissions(unread_only=unread_only, limit=limit)
    packages: list[dict[str, Any]] = []
    for item in pulled.get("emails") or []:
        docs = item.get("documents") or []
        if not docs:
            continue
        subject = str(item.get("subject") or "email-submission")
        msg_id = str(item.get("id") or subject)
        packages.append(
            documents_to_pilot_package(
                docs,
                partner=partner,
                submission_id=msg_id,
                root=root,
                meta={
                    "subject": subject,
                    "from": item.get("from") or item.get("sender"),
                    "insured_name": subject,
                },
                auto_redact=auto_redact,
            )
        )
    return {
        "ok": True,
        "count": len(packages),
        "emails_found": pulled.get("emails_found", 0),
        "packages": packages,
    }
