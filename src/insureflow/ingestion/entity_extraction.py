"""Local named-entity extraction (spaCy) for broker documents.

spaCy runs fully offline on a locally-loaded model, so organizations, people,
dates, and money can be surfaced as extracted fields without sending text to a
cloud API. The import and model load are guarded: when spaCy or the model is
missing — or ``USE_SPACY_NER=0`` — extraction returns nothing and the pipeline
continues on the regex extractors untouched.

Config:
    USE_SPACY_NER   any of 0/false/no disables (default enabled when model present)
    SPACY_MODEL     pipeline to load (default ``en_core_web_sm``)
"""

from __future__ import annotations

import logging
import os
from typing import Any

from insureflow.models.submissions import ExtractedField

logger = logging.getLogger(__name__)

_LABEL_FIELDS = {
    "ORG": "insured_name",
    "PERSON": "person",
    "DATE": "date",
    "MONEY": "amount",
    "GPE": "address",
    "LOC": "address",
    "FAC": "address",
    "PRODUCT": "product",
    "EVENT": "event",
}

# spaCy over-tags bare numbers and quantities; these add noise, not signal.
_WEAK_LABELS = frozenset({"CARDINAL", "ORDINAL", "QUANTITY", "PERCENT", "LAW", "NORP", "WORK_OF_ART"})

_MAX_CHARS = 200_000
_MISSING: Any = object()
_nlp: Any = _MISSING


def _get_nlp() -> Any | None:
    """Load (once) the spaCy pipeline. Returns None when disabled/unavailable."""
    global _nlp
    if _nlp is not _MISSING:
        return _nlp if _nlp is not None else None
    if os.getenv("USE_SPACY_NER", "1").lower() in {"0", "false", "no", "off"}:
        _nlp = None
        return None
    try:
        import spacy

        _nlp = spacy.load(os.getenv("SPACY_MODEL", "en_core_web_sm"))
    except Exception as exc:
        logger.debug("spaCy NER unavailable: %s", exc)
        _nlp = None
    return _nlp


def _normalize(label: str, value: str) -> str:
    from insureflow.ingestion.insurance.value_normalizers import normalize_amount, normalize_date

    if label == "MONEY":
        return normalize_amount(value)
    if label == "DATE":
        return normalize_date(value)
    return value.strip()


def extract_named_entities(raw_text: str) -> dict[str, list[ExtractedField]]:
    """Run spaCy NER over ``raw_text``, returning ``spacy.<field>`` groups."""
    nlp = _get_nlp()
    if nlp is None or not raw_text or not raw_text.strip():
        return {}
    try:
        doc = nlp(raw_text[:_MAX_CHARS])
    except Exception as exc:
        logger.warning("spaCy processing failed: %s", exc)
        return {}

    fields: dict[str, list[ExtractedField]] = {}
    seen: set[tuple[str, str]] = set()
    for ent in doc.ents:
        label = ent.label_
        if label in _WEAK_LABELS:
            continue
        field = _LABEL_FIELDS.get(label)
        if field is None:
            continue
        value = _normalize(label, ent.text)
        if not value:
            continue
        key = (field, value.lower())
        if key in seen:
            continue
        seen.add(key)
        sentence = ent.sent.text[:240].strip() if ent.sent is not None else ""
        fields.setdefault(f"spacy.{field}", []).append(
            ExtractedField(
                field_name=f"spacy.{field}",
                value=value,
                confidence=0.9,
                context=sentence,
            )
        )
    return fields
