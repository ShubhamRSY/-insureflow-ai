"""LLM-assisted extraction for lending documents (parity with mortgage)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from insureflow.config import settings
from insureflow.lending.models import LendingDocumentType
from insureflow.llm.client import LLMClient

logger = logging.getLogger(__name__)

PROMPT = """\
You are a commercial/consumer lending document extraction specialist.
Extract structured financial fields from the document text.

Document type hint: {doc_type}
Source file: {source_path}

Return ONLY valid JSON:
{{
  "business_name": "",
  "industry": "",
  "annual_revenue": null,
  "net_income": null,
  "ebitda": null,
  "debt_service": null,
  "total_assets": null,
  "total_liabilities": null,
  "annual_income": null,
  "credit_score": null,
  "requested_amount": null,
  "years_in_business": null,
  "warnings": []
}}

Use numbers without currency symbols. Null when unknown.
"""


class LendingLLMExtractor:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient(model_tier="cheap")

    @property
    def is_available(self) -> bool:
        return bool(settings.llm_api_key or settings.llm_cheap_api_key or settings.claude_api_key)

    def needs_llm(self, extracted: dict[str, Any], raw_text: str) -> bool:
        if not self.is_available:
            return False
        money_keys = ("annual_revenue", "net_income", "annual_income", "requested_amount", "credit_score")
        filled = sum(1 for k in money_keys if extracted.get(k) not in (None, "", 0, 0.0))
        if filled < 2:
            return True
        if re.search(r"(?i)handwritten|illegible|smudged|\?\?\?", raw_text):
            return True
        return False

    def extract(self, raw_text: str, doc_type: LendingDocumentType, source_path: str = "") -> dict[str, Any]:
        if not self.is_available:
            return {}
        prompt = PROMPT.format(doc_type=doc_type.value, source_path=source_path or "unknown")
        try:
            response = self.llm.complete(
                system_prompt="Extract lending fields as JSON only.",
                user_prompt=f"{prompt}\n\n---\n{raw_text[:12000]}",
            )
            text = response if isinstance(response, str) else str(getattr(response, "content", response) or "")
            match = re.search(r"\{[\s\S]*\}", text)
            if not match:
                return {}
            data = json.loads(match.group(0))
            out: dict[str, Any] = {}
            for key in (
                "business_name",
                "industry",
                "annual_revenue",
                "net_income",
                "ebitda",
                "debt_service",
                "total_assets",
                "total_liabilities",
                "annual_income",
                "credit_score",
                "requested_amount",
                "years_in_business",
            ):
                val = data.get(key)
                if val in (None, "", []):
                    continue
                if key in {"business_name", "industry"}:
                    out[key] = str(val)
                else:
                    try:
                        out[key] = float(val) if key != "credit_score" else int(float(val))
                    except (TypeError, ValueError):
                        continue
            out["extraction_method"] = "llm"
            return out
        except Exception:  # noqa: BLE001
            logger.exception("Lending LLM extraction failed")
            return {}
