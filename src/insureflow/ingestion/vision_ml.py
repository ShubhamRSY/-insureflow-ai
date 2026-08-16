"""Vision ML OCR and layout-aware document features.

Heavy models are guarded, lazy, and off by default: nothing is imported until
``USE_VISION_ML`` names a feature (e.g. ``USE_VISION_ML=paddleocr,hf_ocr``),
and each function returns ``None`` rather than raising when its SDK/model is
unavailable. This keeps the cold path (installs without torch/transformers/
paddle) fully functional while enabling PaddleOCR, HuggingFace image-to-text
(Donut / TrOCR / LayoutLM-style), table transformers (TATR) and document NER
pipelines where they are installed.

    USE_VISION_ML           comma list: paddleocr, hf_ocr, hf_tables, hf_dner
    VISION_OCR_MODEL        HF image-to-text model (default: naver-clova-ix/donut-base)
    VISION_TABLE_MODEL      HF table-structure model (default: microsoft/table-transformer-structure-recognition)
    VISION_USE_GPU          set to any truthy value to request GPU placements
"""

# mypy: disable-error-code="no-untyped-call"

from __future__ import annotations

import logging
import os
from typing import Any, cast

logger = logging.getLogger(__name__)

_DEFAULT_OCR_MODEL = "naver-clova-ix/donut-base"
_DEFAULT_TABLE_MODEL = "microsoft/table-transformer-structure-recognition"


def enabled_features() -> set[str]:
    raw = os.getenv("USE_VISION_ML", "").strip().lower()
    if not raw or raw in {"0", "false", "off", "none"}:
        return set()
    return {f.strip() for f in raw.split(",") if f.strip()}


# --------------------------------------------------------------------------- #
# PaddleOCR
# --------------------------------------------------------------------------- #
def paddleocr_extract_image(image_path: str) -> str | None:
    """OCR a single image with PaddleOCR; returns plain text or None."""
    if "paddleocr" not in enabled_features():
        return None
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        return None
    try:
        ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        result = ocr.ocr(image_path, cls=True)
        lines: list[str] = []
        for page in result or []:
            for item in page or []:
                if item and len(item) >= 2:
                    text = item[1][0] if isinstance(item[1], (list, tuple)) else str(item[1])
                    lines.append(text.strip())
        return "\n".join(line for line in lines if line)
    except Exception as exc:
        logger.warning("PaddleOCR failed: %s", exc)
        return None


# --------------------------------------------------------------------------- #
# HuggingFace image-to-text OCR (Donut / TrOCR)
# --------------------------------------------------------------------------- #
def hf_ocr_extract_image(image_path: str) -> str | None:
    if "hf_ocr" not in enabled_features():
        return None
    try:
        from transformers import pipeline
    except ImportError:
        return None
    try:
        model = os.getenv("VISION_OCR_MODEL", _DEFAULT_OCR_MODEL)
        pipe = pipeline("image-to-text", model=model)
        results = pipe(image_path)
        return "\n".join(str(r.get("generated_text", "")).strip() for r in results if r.get("generated_text"))
    except Exception as exc:
        logger.warning("HF image-to-text OCR failed: %s", exc)
        return None


# --------------------------------------------------------------------------- #
# Table Transformer (TATR) — table structure recognition
# --------------------------------------------------------------------------- #
def hf_table_structure(image_path: str) -> str | None:
    if "hf_tables" not in enabled_features():
        return None
    try:
        from transformers import pipeline
    except ImportError:
        return None
    try:
        model = os.getenv("VISION_TABLE_MODEL", _DEFAULT_TABLE_MODEL)
        pipe = pipeline("image-to-text", model=model)
        results = pipe(image_path)
        return "\n".join(str(r.get("generated_text", "")).strip() for r in results if r.get("generated_text"))
    except Exception as exc:
        logger.warning("HF table-structure failed: %s", exc)
        return None


# --------------------------------------------------------------------------- #
# Layout-aware document NER (LayoutLM-family token classification)
# --------------------------------------------------------------------------- #
def hf_document_ner_on_image(image_path: str) -> list[dict[str, Any]]:
    if "hf_dner" not in enabled_features():
        return []
    try:
        from PIL import Image
        from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline
    except ImportError:
        return []
    try:
        model = os.getenv("VISION_DNER_MODEL", "")
        if not model:
            return []
        tokenizer = AutoTokenizer.from_pretrained(model)
        model_obj = AutoModelForTokenClassification.from_pretrained(model)
        pipe = pipeline("token-classification", model=model_obj, tokenizer=tokenizer)
        image = cast(Any, Image.open(image_path).convert("RGB"))
        return list(pipe(image))
    except Exception as exc:
        logger.warning("HF document NER failed: %s", exc)
        return []


def vision_extract_image(image_path: str) -> str:
    """Aggregate enabled vision-ML extractors for a single image, newest first."""
    parts: list[str] = []
    for extractor in (hf_ocr_extract_image, paddleocr_extract_image):
        text = extractor(image_path)
        if text:
            parts.append(text)
    return "\n\n".join(parts)
