"""Document forensics & tampering checks (pre-parse integrity layer).

Digitally altered bank statements, tax returns or financial schedules are a
class of fraud this pipeline checks *before* parsing. Using PyMuPDF (guarded),
inspect the PDF's object structure:

- **Font embedding**: non-embedded fonts mean text can be re-rendered differently
  on the reader's machine — a substitution/tampering red flag.
- **Producer/Creator metadata**: generic or missing tooling metadata.
- **Rasterization patterns**: pages whose content is essentially a single
  full-page image (e.g. a screen grab of an edited statement) with a suspiciously
  thin vector layer.

All checks degrade to clean when PyMuPDF is unavailable or the bytes are not a
PDF; nothing here can crash the load path.
"""

# mypy: disable-error-code="no-untyped-call"

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

from insureflow.models.submissions import VerificationIssue
from insureflow.verification.common import SEVERITY_INFO, SEVERITY_WARNING

logger = logging.getLogger(__name__)

_IMAGE_ONLY_FRACTION = 0.9
_UNEXPECTED_PRODUCERS = ("CutePDF", "PDFCreator", "Nitro", "WPS PDF", "Foxit Phantom")


@dataclass
class PdfForensics:
    pages: int = 0
    fonts: list[dict[str, object]] = field(default_factory=list)
    non_embedded_fonts: list[str] = field(default_factory=list)
    images: int = 0
    full_page_image_pages: list[int] = field(default_factory=list)
    producer: str = ""
    creator: str = ""

    def has_anomalies(self) -> bool:
        return bool(self.non_embedded_fonts or self.full_page_image_pages)


def tamper_checks_enabled() -> bool:
    raw = os.getenv("USE_TAMPER_CHECKS", "1").strip().lower()
    return raw not in {"0", "false", "off", "no", "none"}


def inspect_pdf(pdf_bytes: bytes) -> PdfForensics | None:
    """Inspect a PDF's fonts, metadata and rasterization; None when unavailable."""
    if not pdf_bytes or not pdf_bytes.startswith(b"%PDF"):
        return None
    try:
        import fitz  # PyMuPDF 1.x API

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except ImportError:
        try:
            import pymupdf as doc_mod  # PyMuPDF >= 1.24 exposes `pymupdf`
        except ImportError:
            logger.debug("pymupdf not installed — skipping document forensics")
            return None
        except Exception:
            return None
        else:
            try:
                doc = doc_mod.open(stream=pdf_bytes, filetype="pdf")
            except Exception as exc:
                logger.warning("forensic PDF open failed: %s", exc)
                return None
    except Exception as exc:
        logger.warning("forensic PDF open failed: %s", exc)
        return None

    try:
        forensics = PdfForensics(pages=doc.page_count)
        metadata = doc.metadata or {}
        forensics.producer = metadata.get("producer", "")
        forensics.creator = metadata.get("creator", "")
        for page_index in range(doc.page_count):
            page = doc.load_page(page_index)
            for font_info in page.get_fonts():
                fname = str(font_info[3]) if len(font_info) > 3 else str(font_info)
                embedded = bool(font_info[1]) if len(font_info) > 1 else True
                forensics.fonts.append({"name": fname, "embedded": embedded})
                if not embedded and fname not in forensics.non_embedded_fonts:
                    forensics.non_embedded_fonts.append(fname)
            image_list = page.get_images(full=True)
            forensics.images += len(image_list)
            rect = page.rect
            text_coverage = 0.0
            try:
                for _ in page.get_text("dict")["blocks"]:
                    pass
                page_area = float(rect.width * rect.height)
                drawn = page.get_drawings()
                ink_area = sum(abs(float(p.rect.width * p.rect.height)) for p in drawn)
                text_area = 0.0
                for block in page.get_text("dict")["blocks"]:
                    text_area += abs(float((block["bbox"][2] - block["bbox"][0]) * (block["bbox"][3] - block["bbox"][1])))
                text_coverage = (text_area + ink_area) / page_area if page_area else 0.0
            except Exception:
                text_coverage = 0.0
            if image_list and text_coverage < (1.0 - _IMAGE_ONLY_FRACTION):
                forensics.full_page_image_pages.append(page_index + 1)
        return forensics
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("forensic inspection failed: %s", exc)
        return None
    finally:
        try:
            doc.close()
        except Exception:
            pass


def tampering_issues(forensics: PdfForensics | None) -> list[VerificationIssue]:
    """Turn a :class:`PdfForensics` result into review issues."""
    if forensics is None:
        return []
    issues: list[VerificationIssue] = []
    for font in forensics.non_embedded_fonts:
        issues.append(
            VerificationIssue(
                code="non_embedded_font",
                severity=SEVERITY_WARNING,
                message=(f"PDF uses non-embedded font {font!r}; text can be re-rendered by the viewer — substitution or tampering risk, verify figures against the image layer"),
            )
        )
    for page in forensics.full_page_image_pages:
        issues.append(
            VerificationIssue(
                code="rasterized_page",
                severity=SEVERITY_WARNING,
                message=(f"page {page} is essentially a full-page image with almost no vector/text content — common in doctored statements; treat extraction cautiously"),
                page_number=page,
            )
        )
    producer = (forensics.producer or "").lower()
    if any(sus.lower() in producer for sus in _UNEXPECTED_PRODUCERS):
        issues.append(
            VerificationIssue(
                code="unexpected_producer",
                severity=SEVERITY_WARNING,
                message=f"PDF was produced by {forensics.producer!r}, an unusual tool for source financials",
            )
        )
    if not (forensics.producer or forensics.creator):
        issues.append(
            VerificationIssue(
                code="no_pdf_metadata",
                severity=SEVERITY_INFO,
                message="PDF has no Producer/Creator metadata — origin cannot be verified",
            )
        )
    return issues
