"""LlamaParse (LlamaCloud) wrapper for PDFs — opt-in via ``LLAMA_CLOUD_API_KEY``.

Only used when the SDK is installed and an API key is present; otherwise
``llamaparse_available()`` is False and every parse returns None, leaving the
local pdfplumber/pdfminer/tesseract chain in charge.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def llamaparse_available() -> bool:
    if not os.getenv("LLAMA_CLOUD_API_KEY"):
        return False
    try:
        import llama_parse  # noqa: F401

        return True
    except ImportError:
        return False


def parse_pdf_with_llamaparse(file_path: str) -> str | None:
    """Parse a PDF into markdown via LlamaParse; returns None when unavailable."""
    if not llamaparse_available():
        return None
    try:
        from llama_parse import LlamaParse

        parser = LlamaParse(result_type="markdown")
        if file_path.lower().endswith(".pdf"):
            docs = parser.load_data(file_path)
        else:
            with tempfile.NamedTemporaryFile(suffix=Path(file_path).suffix, delete=False) as tmp:
                tmp.write(Path(file_path).read_bytes())
                tmp_path = tmp.name
            try:
                docs = parser.load_data(tmp_path)
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        parts = [str(doc.get_content() if hasattr(doc, "get_content") else doc) for doc in (docs or [])]
        text = "\n\n".join(parts).strip()
        return text or None
    except Exception as exc:
        logger.warning("LlamaParse failed: %s", exc)
        return None
