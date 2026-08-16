"""Dynamic multi-model ensemble routing (technique #5).

A lightweight router inspects the file (type, page density, image count, layout
spread, table likelihood) and picks the cheapest parser that can safely handle
it: clean text PDFs go to pdfplumber/pdfminer, table-heavy docs to the table
engines, scans to OCR/vision, and dense multi-column layouts escalate to VLM
parsing. This keeps the expensive engines on the messy minority of documents.

Enabled by default via ``USE_DOCUMENT_ROUTER``; ``ROUTER_FORCE`` overrides the
decision for testing/diagnostics (e.g. ``ROUTER_FORCE=vlm``).
"""

# mypy: disable-error-code="no-untyped-call"

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_STRUCTURED_EXTS = frozenset({".xlsx", ".xls", ".xlsm", ".csv", ".docx", ".eml", ".msg", ".html", ".htm", ".json", ".xml"})
_PDF_IMAGE_EXTS = frozenset({".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".tif"})


class RouteKind(str, Enum):
    STRUCTURED = "structured"
    STANDARD = "standard"
    TABLE_HEAVY = "table_heavy"
    SCANNED = "scanned"
    VLM = "vlm"
    AGENTIC = "agentic"
    CODE = "code"


@dataclass
class DocumentProfile:
    filename: str
    extension: str = ""
    page_count: int = 0
    image_count: int = 0
    text_chars: int = 0
    text_density: float = 0.0
    column_span: float = 0.0
    table_heuristic: float = 0.0

    @property
    def is_structured(self) -> bool:
        return self.extension in _STRUCTURED_EXTS

    @property
    def is_visual(self) -> bool:
        return self.extension in _PDF_IMAGE_EXTS


@dataclass
class RouteDecision:
    route: RouteKind
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)


def profile_document(path: str, data: bytes | None = None) -> DocumentProfile:
    """Heuristic profile of a document without running a full parse."""
    filename = Path(path).name
    ext = Path(path).suffix.lower()
    profile = DocumentProfile(filename=filename, extension=ext)
    if ext == ".pdf":
        _profile_pdf(profile, path, data)
    elif ext in _PDF_IMAGE_EXTS:
        profile.page_count = 1
        profile.image_count = 1
        profile.text_chars = 0
    return profile


def _profile_pdf(profile: DocumentProfile, path: str, data: bytes | None) -> None:
    try:
        if data is not None:
            import io

            import pymupdf

            doc: Any = pymupdf.open(stream=io.BytesIO(data))
        else:
            import pymupdf

            doc = pymupdf.open(path)
    except Exception as exc:
        logger.debug("router pdf profile failed: %s", exc)
        return
    try:
        profile.page_count = doc.page_count
        profile.image_count = 0
        profile.text_chars = 0
        total_area = 0.0
        for page in doc:
            total_area += page.rect.width * page.rect.height
            profile.image_count += len(page.get_images(full=True))
            text = page.get_text("text") or ""
            profile.text_chars += len(text)
            # column span heuristic: spread of x-centroids of text spans
            blocks = page.get_text("dict") or {}
            xs: list[float] = []
            for block in blocks.get("blocks", []):
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    if spans:
                        x = min(s["bbox"][0] for s in spans)
                        x1 = max(s["bbox"][2] for s in spans)
                        xs.append((x + x1) / 2)
            if len(xs) >= 4:
                mean = sum(xs) / len(xs)
                var = sum((x - mean) ** 2 for x in xs) / len(xs)
                profile.column_span = min(1.0, var / (page.rect.width / 6) ** 2)
    finally:
        doc.close()
    if profile.page_count:
        profile.text_density = min(1.0, profile.text_chars / (profile.page_count * 2200))


def route_document(profile: DocumentProfile) -> RouteDecision:
    """Pick the cheapest engine that can safely parse ``profile``."""
    forced = os.getenv("ROUTER_FORCE", "").strip().lower()
    valid = {r.value for r in RouteKind}
    if forced in valid:
        return RouteDecision(route=RouteKind(forced), score=1.0, reasons=[f"ROUTER_FORCE={forced}"])

    if profile.is_structured:
        return RouteDecision(route=RouteKind.STRUCTURED, score=1.0, reasons=["structured extension"])

    if not profile.is_visual:
        return RouteDecision(route=RouteKind.STANDARD, score=0.9, reasons=["plain text"])

    if profile.page_count == 0:
        return RouteDecision(route=RouteKind.SCANNED, score=0.8, reasons=["unreadable page profile → treat as scan"])

    if profile.text_chars == 0 or (profile.text_density < 0.06 and profile.image_count > 0):
        return RouteDecision(
            route=RouteKind.SCANNED,
            score=0.85,
            reasons=["image-only pages with no extractable text layer"],
        )

    if profile.column_span >= 0.55 and profile.text_density >= 0.15:
        return RouteDecision(
            route=RouteKind.VLM,
            score=min(0.9, 0.5 + profile.column_span),
            reasons=[f"multi-column layout span {profile.column_span:.2f} → VLM semantic parse"],
        )

    if profile.table_heuristic >= 0.6 or profile.image_count >= 4:
        return RouteDecision(
            route=RouteKind.TABLE_HEAVY,
            score=0.8,
            reasons=["table-heavy or image-rich document"],
        )

    return RouteDecision(route=RouteKind.STANDARD, score=0.9, reasons=["text PDF"])


def router_enabled() -> bool:
    raw = os.getenv("USE_DOCUMENT_ROUTER", "1").strip().lower()
    return raw not in {"0", "false", "off", "no", "none"}
