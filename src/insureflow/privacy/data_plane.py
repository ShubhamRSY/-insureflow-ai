"""What we are allowed to keep after a run.

In a bank landing zone the source of truth is *their* PAS, object store, or
file share. We read it for the job, decide, then drop the raw file. What
remains on disk is a decision artifact (memo, scores, routing) plus
PII-free pattern memory — never bank statements, ACORD XML, or W-2 text.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Keys that are the customer's source file, not our decision.
_SOURCE_KEYS = {
    "raw_text",
    "raw_xml",
    "raw_json",
    "chunks",
    "image_data",
    "image_b64",
    "file_bytes",
    "pdf_bytes",
    "statement_text",
    "bank_statement",
    "w2_text",
    "paystub_text",
}
_LONG_SOURCE_KEYS = {"content", "text", "body", "narrative"}

# Identity fields we keep only as redacted tokens on disk.
_IDENTITY_KEYS = {
    "legal_name",
    "dba",
    "tax_id",
    "address",
    "contact_name",
    "contact_email",
    "insured_name",
    "applicant_name",
    "borrower_name",
    "ssn",
    "account_number",
    "routing_number",
}


def retain_source_documents() -> bool:
    """True when raw submission text may be written to audit storage.

    Bank/production defaults to False. Dev keeps current full-bundle behavior
    unless RETAIN_SOURCE_DOCS is set.
    """
    explicit = os.getenv("RETAIN_SOURCE_DOCS", "").strip().lower()
    if explicit in {"1", "true", "yes", "on"}:
        return True
    if explicit in {"0", "false", "no", "off"}:
        return False
    try:
        from insureflow.security.posture import resolve_security_posture

        return not resolve_security_posture().is_hardened
    except Exception:
        return True


def allow_vision_egress() -> bool:
    """Cloud vision sends the photo bytes to a model vendor — off in bank mode."""
    explicit = os.getenv("ALLOW_VISION_EGRESS", "").strip().lower()
    if explicit in {"1", "true", "yes", "on"}:
        return True
    if explicit in {"0", "false", "no", "off"}:
        return False
    try:
        from insureflow.security.posture import resolve_security_posture

        return not resolve_security_posture().is_hardened
    except Exception:
        return True


def allow_embedding_egress() -> bool:
    """OpenAI/Cohere embeddings leave the VPC. Bank mode stays on local vectors."""
    explicit = os.getenv("ALLOW_EMBEDDING_EGRESS", "").strip().lower()
    if explicit in {"1", "true", "yes", "on"}:
        return True
    if explicit in {"0", "false", "no", "off"}:
        return False
    try:
        from insureflow.security.posture import resolve_security_posture

        return not resolve_security_posture().is_hardened
    except Exception:
        return True


def allow_langsmith_in_bank() -> bool:
    """LangSmith traces leave the VPC. Bank mode requires an explicit opt-in."""
    return os.getenv("LANGSMITH_ALLOW_IN_BANK", "").strip().lower() in {"1", "true", "yes", "on"}


def strip_source_documents(payload: Any) -> Any:
    """Drop source-file fields; leave decision structure in place."""
    if isinstance(payload, dict):
        out: dict[str, Any] = {}
        for key, value in payload.items():
            lowered = str(key).lower()
            if lowered in _SOURCE_KEYS:
                if isinstance(value, str):
                    out[key] = ""
                elif isinstance(value, list):
                    out[key] = []
                else:
                    out[key] = None
                continue
            if lowered in _LONG_SOURCE_KEYS and isinstance(value, str) and len(value) > 400:
                out[key] = ""
                continue
            out[key] = strip_source_documents(value)
        return out
    if isinstance(payload, list):
        return [strip_source_documents(item) for item in payload]
    return payload


def sanitize_for_persist(payload: Any) -> Any:
    """Strip source docs and mask remaining PII before anything hits disk."""
    from insureflow.redaction.redactor import PIIRedactor

    stripped = strip_source_documents(payload)
    redactor = PIIRedactor()
    return _redact_walk(stripped, redactor)


def _redact_walk(payload: Any, redactor: Any) -> Any:
    if isinstance(payload, dict):
        out: dict[str, Any] = {}
        for key, value in payload.items():
            lowered = str(key).lower()
            if lowered in _IDENTITY_KEYS and isinstance(value, str) and value:
                redacted = redactor.redact(value, mask=False)
                out[key] = redacted if redacted != value else "[REDACTED]"
            else:
                out[key] = _redact_walk(value, redactor)
        return out
    if isinstance(payload, list):
        return [_redact_walk(item, redactor) for item in payload]
    if isinstance(payload, str) and payload:
        detected = redactor.detector.detect(payload)
        if detected:
            return redactor.redact(payload, mask=False)
    return payload


def prepare_persisted_payload(payload: Any) -> Any:
    """Choke point for every audit write: strip in bank/prod, pass through in lab."""
    if retain_source_documents():
        return payload
    if not isinstance(payload, (dict, list)):
        return payload
    try:
        return sanitize_for_persist(payload)
    except Exception:
        logger.warning("Persist sanitizer failed — dropping payload rather than writing raw PII", exc_info=True)
        return {"redacted": True, "reason": "persist_sanitizer_failed"}
