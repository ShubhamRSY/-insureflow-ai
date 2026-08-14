"""Guideline embeddings — local by default in bank mode.

Do not send submission text to OpenAI/Cohere embedding APIs unless
``ALLOW_EMBEDDING_EGRESS=true``. Dimension is 1536 so pgvector schema stays put.
``text-embedding-3-large`` / E5 are optional cloud/local backends, not required.
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 1536
_OPENAI_SMALL = "text-embedding-3-small"


def embedding_dim() -> int:
    raw = os.getenv("EMBEDDING_DIM", "").strip()
    return int(raw) if raw else EMBEDDING_DIM


def hashed_embedding(text: str, dim: int | None = None) -> list[float]:
    """Stable hashing-trick vector — same result on API and Celery workers."""
    size = dim or embedding_dim()
    cleaned = re.sub(r"[^a-z0-9]", "", (text or "").lower())
    vec = [0.0] * size
    if len(cleaned) < 3:
        return vec
    for i in range(len(cleaned) - 2):
        ng = cleaned[i : i + 3]
        h = int(hashlib.sha256(ng.encode("utf-8")).hexdigest(), 16)
        vec[h % size] += 1.0
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def _redact(text: str) -> str:
    if not text:
        return text
    from insureflow.redaction.redactor import PIIRedactor

    return str(PIIRedactor().redact(text, mask=False))


def _pad_or_trim(vec: list[float], dim: int) -> list[float]:
    if len(vec) == dim:
        return vec
    if len(vec) > dim:
        return vec[:dim]
    return vec + [0.0] * (dim - len(vec))


def embed_text(text: str) -> list[float]:
    """Embed guideline/query text. Bank mode never calls a cloud embedding API."""
    dim = embedding_dim()
    safe = _redact(text)[:8000]
    backend = os.getenv("EMBEDDING_BACKEND", "").strip().lower()

    from insureflow.privacy.data_plane import allow_embedding_egress

    if backend in {"local", "hash", "hashed"} or not allow_embedding_egress():
        return hashed_embedding(safe, dim)

    if backend in {"e5", "sentence_transformers", "st"}:
        local = _sentence_transformer_embed(safe)
        if local is not None:
            return _pad_or_trim(local, dim)
        logger.warning("Local sentence-transformers embed unavailable; using hashed vectors")
        return hashed_embedding(safe, dim)

    cloud = _openai_embed(safe)
    if cloud is not None:
        return _pad_or_trim(cloud, dim)
    logger.warning("Cloud embedding failed; using hashed vectors")
    return hashed_embedding(safe, dim)


def _sentence_transformer_embed(text: str) -> list[float] | None:
    model_name = os.getenv("EMBEDDING_MODEL", "intfloat/e5-large-v2").strip()
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(model_name)
        vec = model.encode(text)
        return [float(x) for x in vec]
    except Exception as exc:
        logger.debug("sentence-transformers embed failed: %s", exc)
        return None


def _openai_embed(text: str) -> list[float] | None:
    model = os.getenv("EMBEDDING_MODEL", _OPENAI_SMALL).strip() or _OPENAI_SMALL
    try:
        from openai import OpenAI

        kwargs: dict[str, Any] = {}
        key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
        if key:
            kwargs["api_key"] = key
        base = os.getenv("EMBEDDING_BASE_URL") or os.getenv("LLM_BASE_URL") or ""
        if base:
            kwargs["base_url"] = base
        client = OpenAI(**kwargs)
        resp = client.embeddings.create(model=model, input=text)
        return list(resp.data[0].embedding)
    except Exception as exc:
        logger.warning("OpenAI embedding failed: %s", exc)
        return None
