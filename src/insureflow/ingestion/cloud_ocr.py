"""Cloud OCR providers: AWS Textract and Google Document AI.

These are opt-in per the repo's configuration discipline: an engine activates
only when (a) its SDK is installed, (b) its name is listed in ``USE_CLOUD_OCR``
(e.g. ``USE_CLOUD_OCR=textract,documentai``), and (c) credentials are present.
Otherwise every call returns ``None`` and the local
pdfplumber/pdfminer/tesseract chain is left untouched.

Credentials / config:
    AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY   (boto3 standard resolution)
    TEXTRACT_REGION                             default: AWS_REGION / us-east-1
    GCP_PROJECT_ID, GCP_LOCATION, GCP_PROCESSOR_ID  (Document AI)
"""

from __future__ import annotations

import base64
import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

_IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".tiff": "image/tiff", ".tif": "image/tiff", ".bmp": "image/bmp", ".pdf": "application/pdf"}

_MAX_TEXTTRACT_SYNC_BYTES = 5 * 1024 * 1024  # analyze_document limit


@dataclass
class CloudOcrResult:
    text: str
    tables: str = ""
    provider: str = ""
    # Spatial grounding: page number -> { line text -> normalized [x0,y0,x1,y1] }
    lines: dict[int, dict[str, list[float]]] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.lines is None:
            self.lines = {}


def configured_providers() -> list[str]:
    raw = os.getenv("USE_CLOUD_OCR", "").strip().lower()
    if not raw or raw in {"0", "false", "off", "none"}:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def cloud_extract(data: bytes, filename: str) -> CloudOcrResult | None:
    """Run the first configured cloud OCR provider that succeeds."""
    for provider in configured_providers():
        if provider == "textract":
            result = textract_extract(data, filename)
        elif provider == "documentai":
            result = documentai_extract(data, filename)
        else:
            logger.debug("unknown cloud OCR provider: %s", provider)
            continue
        if result is not None and result.text.strip():
            return result
    return None


# --------------------------------------------------------------------------- #
# AWS Textract
# --------------------------------------------------------------------------- #
def textract_extract(data: bytes, filename: str) -> CloudOcrResult | None:
    try:
        import boto3
    except ImportError:
        return None
    try:
        region = os.getenv("TEXTRACT_REGION") or os.getenv("AWS_REGION") or "us-east-1"
        client = boto3.client("textract", region_name=region)
        if len(data) <= _MAX_TEXTTRACT_SYNC_BYTES:
            response = client.analyze_document(Document={"Bytes": data}, FeatureTypes=["FORMS", "TABLES"])
        else:  # async multi-page analysis
            start = client.start_document_analysis(
                DocumentLocation={"Bytes": data},
                FeatureTypes=["FORMS", "TABLES"],
            )
            response = _textract_wait_and_get(client, start["JobId"])
    except Exception as exc:
        logger.warning("Textract OCR failed: %s", exc)
        return None
    return _textract_blocks_to_result(response)


def _textract_wait_and_get(client: Any, job_id: str) -> dict[str, Any]:
    import time

    for _ in range(120):
        status = client.get_document_analysis(JobId=job_id)
        if status["JobStatus"] in {"SUCCEEDED", "FAILED"}:
            return dict(status)
        time.sleep(2)
    raise TimeoutError("Textract analysis timed out")


def _textract_blocks_to_result(response: dict[str, Any]) -> CloudOcrResult:
    blocks = response.get("Blocks", [])
    by_id = {b["Id"]: b for b in blocks if b.get("Id")}

    lines: list[str] = []
    tables: list[str] = []
    spatial: dict[int, dict[str, list[float]]] = {}
    for block in blocks:
        if block["BlockType"] == "LINE":
            lines.append(block.get("Text", ""))
            _textract_ground_line(block, spatial)
        elif block["BlockType"] == "TABLE":
            rows: dict[int, dict[int, str]] = {}
            for rel in block.get("Relationships", []):
                if rel["Type"] != "CHILD":
                    continue
                for child_id in rel.get("Ids", []):
                    cell = by_id.get(child_id)
                    if cell is None or cell["BlockType"] != "CELL":
                        continue
                    row, col = cell.get("RowIndex", 1) - 1, cell.get("ColumnIndex", 1) - 1
                    text = _textract_cell_text(cell, by_id)
                    rows.setdefault(row, {})[col] = text
            if rows:
                tables.append(_textract_rows_to_markdown(rows))
    return CloudOcrResult(
        text="\n".join(lines),
        tables="\n\n".join(tables),
        provider="textract",
        lines=spatial,
    )


def _textract_ground_line(block: dict[str, Any], spatial: dict[int, dict[str, list[float]]]) -> None:
    """Record a Textract LINE's normalized bounding box keyed by page."""
    try:
        box = block.get("Geometry", {}).get("BoundingBox", {})
        left, top, width, height = box["Left"], box["Top"], box["Width"], box["Height"]
        page = int(block.get("Page", 1))
        spatial.setdefault(page, {})[block.get("Text", "")] = [left, top, left + width, top + height]
    except (KeyError, TypeError):
        pass


def _textract_cell_text(cell: dict[str, Any], by_id: dict[str, Any]) -> str:
    parts: list[str] = []
    for rel in cell.get("Relationships", []):
        if rel["Type"] != "CHILD":
            continue
        for child_id in rel.get("Ids", []):
            word = by_id.get(child_id)
            if word is not None and word.get("BlockType") == "WORD":
                parts.append(word.get("Text", ""))
    return " ".join(parts)


def _textract_rows_to_markdown(rows: dict[int, dict[int, str]]) -> str:
    width = max((max(cols.keys()) + 1) for cols in rows.values()) if rows else 0
    ordered = [rows[r] for r in sorted(rows)]
    header = " | ".join(str(ordered[0].get(c, "")).strip() for c in range(width)) if ordered else ""
    lines = [f"| {header} |", "|" + " --- |" * width]
    for row in ordered[1:]:
        lines.append("| " + " | ".join(str(row.get(c, "")).strip().replace("\n", " ") for c in range(width)) + " |")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Google Document AI
# --------------------------------------------------------------------------- #
def documentai_extract(data: bytes, filename: str) -> CloudOcrResult | None:
    project = os.getenv("GCP_PROJECT_ID", "").strip()
    processor = os.getenv("GCP_PROCESSOR_ID", "").strip()
    if not (project and processor):
        return None
    try:
        from google.cloud import documentai  # type: ignore[attr-defined]
    except ImportError:
        return None
    try:
        location = os.getenv("GCP_LOCATION", "us").strip() or "us"
        client = documentai.DocumentProcessorServiceClient()
        name = client.processor_path(project, location, processor)
        mime = _IMAGE_TYPES.get(os.path.splitext(filename)[1].lower(), "application/pdf")
        response = client.process_document(
            request={
                "name": name,
                "raw_document": {"content": base64.b64decode(data) if not isinstance(data, bytes) else data, "mime_type": mime},
            }
        )
        doc = response.document
        return CloudOcrResult(
            text=doc.text or "",
            tables=_documentai_tables(doc),
            provider="documentai",
            lines=_documentai_lines(doc),
        )
    except Exception as exc:
        logger.warning("Document AI failed: %s", exc)
        return None


def _documentai_lines(doc: Any) -> dict[int, dict[str, list[float]]]:
    """Collect normalized bounding boxes for Document AI text blocks per page."""
    result: dict[int, dict[str, list[float]]] = {}
    for page_index, page in enumerate(getattr(doc, "pages", None) or [], start=1):
        page_map: dict[str, list[float]] = {}
        for block in getattr(page, "blocks", None) or []:
            layout = getattr(block, "layout", None)
            text = _anchor_text(doc, getattr(layout, "text_anchor", None))
            if not text:
                continue
            bbox = _normalized_bbox(layout)
            if bbox is None:
                continue
            page_map[text] = bbox
        if page_map:
            result[page_index] = page_map
    return result


def _normalized_bbox(layout: Any) -> list[float] | None:
    try:
        poly = getattr(layout, "bounding_poly", None)
        vertices = getattr(poly, "normalized_vertices", None) or getattr(poly, "vertices", None)
        if not vertices:
            return None
        xs = [v.x for v in vertices]
        ys = [v.y for v in vertices]
        return [min(xs), min(ys), max(xs), max(ys)]
    except Exception:
        return None


def _documentai_tables(doc: Any) -> str:
    """Rebuild Document AI table bodies into markdown via text anchors."""
    pages = getattr(doc, "pages", None) or []
    blocks: list[str] = []
    for page in pages:
        for table in getattr(page, "tables", None) or []:
            rows: list[list[str]] = []
            for body_row in getattr(table, "body_rows", None) or []:
                cells = []
                for cell in getattr(body_row, "cells", None) or []:
                    anchor = getattr(cell, "layout", None)
                    segments = getattr(anchor, "text_anchor", None)
                    cells.append(_anchor_text(doc, segments))
                rows.append(cells)
            if rows:
                blocks.append("\n".join("| " + " | ".join(row) + " |" for row in rows))
    return "\n\n".join(blocks)


def _anchor_text(doc: Any, segments: Any) -> str:
    try:
        text = doc.text or ""
        parts: list[str] = []
        for seg in getattr(segments, "text_segments", None) or []:
            start = getattr(seg, "start_index", None)
            end = getattr(seg, "end_index", None)
            if start is None or end is None:
                continue
            parts.append(text[start:end])
        return " ".join(parts).strip()
    except Exception:
        return ""
