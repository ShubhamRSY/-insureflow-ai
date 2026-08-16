"""Vision-language model native parsing (technique #1).

Documents are rendered as high-resolution page images and passed through a
VLM (GPT-4o / Claude 3.5 Sonnet / Mistral OCR) that "sees" reading order,
nested tables, and handwritten margin notes the way a human would, returning
clean Markdown instead of a flat text layer.

Opt-in and degradation-safe: ``USE_VLM_PARSING`` enables the path, the provider
is auto-selected from installed SDKs/keys (``VLM_PROVIDER`` may force one), and
every call returns ``None`` when the path is not configured — leaving the
local/pdfplumber chain untouched.
"""

# mypy: disable-error-code="no-untyped-call"

from __future__ import annotations

import base64
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, cast

logger = logging.getLogger(__name__)

_VLM_PROMPT = (
    "You are a document parser for commercial insurance underwriting. "
    "Transcribe the document page image into clean Markdown. Preserve reading "
    "order across columns, represent tables as Markdown pipe tables with their "
    "headers intact, keep monetary amounts and dates exactly as written, and "
    "include any handwritten annotations verbatim. Output Markdown only, no preamble."
)


def vlm_enabled() -> bool:
    raw = os.getenv("USE_VLM_PARSING", "").strip().lower()
    return raw not in {"", "0", "false", "off", "no", "none"}


def selected_provider() -> str:
    forced = os.getenv("VLM_PROVIDER", "").strip().lower()
    if forced:
        return forced
    for provider, available in (
        ("mistral", _mistral_available()),
        ("anthropic", _anthropic_available()),
        ("openai", _openai_available()),
    ):
        if available:
            return provider
    return ""


def _openai_available() -> bool:
    if not (os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")):
        return False
    try:
        import openai  # noqa: F401

        return True
    except ImportError:
        return False


def _anthropic_available() -> bool:
    if not (os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY")):
        return False
    try:
        import anthropic  # noqa: F401

        return True
    except ImportError:
        return False


def _mistral_available() -> bool:
    if not os.getenv("MISTRAL_API_KEY"):
        return False
    try:
        import mistralai  # noqa: F401

        return True
    except ImportError:
        return False


def render_pdf_to_images(path: str, dpi: int = 200) -> list[bytes]:
    """Render each PDF page to PNG bytes at ``dpi``."""
    try:
        try:
            import pymupdf
        except ImportError:  # pragma: no cover - older package name
            import fitz as pymupdf  # type: ignore[no-redef]
    except ImportError:
        return []
    scale = dpi / 72.0
    images: list[bytes] = []
    doc: Any = pymupdf.open(path)
    try:
        for page in doc:
            pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale))
            images.append(pix.tobytes("png"))
    finally:
        doc.close()
    return images


def vlm_parse_document(data: bytes, filename: str) -> tuple[str, str] | None:
    """Parse a PDF/image via the selected VLM; returns ``(markdown, provider)``."""
    if not vlm_enabled():
        return None
    provider = selected_provider()
    if not provider:
        return None
    ext = Path(filename).suffix.lower()
    try:
        if ext == ".pdf":
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(data)
                tmp_path = tmp.name
            try:
                images = render_pdf_to_images(tmp_path)
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        else:
            images = [data]
        if not images:
            return None
        if provider == "openai":
            return _openai_vision(images), "vlm:openai"
        if provider == "anthropic":
            return _anthropic_vision(images), "vlm:anthropic"
        if provider == "mistral":
            return _mistral_ocr(data, filename), "vlm:mistral"
    except Exception as exc:
        logger.warning("VLM parsing failed: %s", exc)
    return None


def _openai_vision(images: list[bytes]) -> str:
    from openai import OpenAI

    model = os.getenv("VLM_MODEL", "gpt-4o")
    key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=key)
    contents: list[dict[str, Any]] = []
    for i, image in enumerate(images):
        b64 = base64.b64encode(image).decode("ascii")
        contents.append({"type": "text", "text": f"--- Page {i + 1} ---"})
        contents.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
    contents.append({"type": "text", "text": _VLM_PROMPT})
    response = client.chat.completions.create(
        model=model,
        messages=cast(Any, [{"role": "user", "content": contents}]),
        max_tokens=int(os.getenv("VLM_MAX_TOKENS", "4096")),
    )
    return response.choices[0].message.content or ""


def _anthropic_vision(images: list[bytes]) -> str:
    import anthropic

    model = os.getenv("VLM_MODEL", "claude-3-5-sonnet-20241022")
    key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("LLM_API_KEY")
    client = anthropic.Anthropic(api_key=key)
    blocks: list[dict[str, Any]] = []
    for i, image in enumerate(images):
        b64 = base64.b64encode(image).decode("ascii")
        blocks.append({"type": "text", "text": f"--- Page {i + 1} ---"})
        blocks.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}})
    blocks.append({"type": "text", "text": _VLM_PROMPT})
    message = client.messages.create(
        model=model,
        max_tokens=int(os.getenv("VLM_MAX_TOKENS", "4096")),
        messages=[{"role": "user", "content": cast(Any, blocks)}],
    )
    return "".join(getattr(block, "text", "") or "" for block in message.content if getattr(block, "type", "") == "text")


def _mistral_ocr(data: bytes, filename: str) -> str:
    from mistralai import Mistral

    client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
    with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix or ".pdf", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        uploaded = client.files.upload(file={"file_name": Path(tmp_path).name, "content": Path(tmp_path).read_bytes()})
        signed = client.files.get_signed_url(file_id=uploaded.id)
        response = client.ocr.process(model="mistral-ocr-latest", document={"type": "document_url", "document_url": signed.url})
        pages = getattr(response, "pages", None) or []
        return "\n\n".join(page.markdown or "" for page in pages)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
