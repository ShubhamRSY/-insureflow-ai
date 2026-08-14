"""Vision LLM analyzer — GPT-4V / Claude Vision for property condition assessment.

Sends property photos to a vision-capable LLM and extracts structured findings
about building condition, visible damage, construction materials, and risk factors.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any

from insureflow.ml.vision.models import PhotoAnalysis, VisualFinding, VisualRisk

logger = logging.getLogger(__name__)

PROPERTY_ANALYSIS_PROMPT = """Analyze this property photo for commercial insurance underwriting.

Identify and describe:
1. BUILDING CONDITION: Overall structural condition (excellent/good/fair/poor/deteriorated)
2. CONSTRUCTION MATERIALS: Visible materials (brick, wood siding, metal, concrete, stucco, etc.)
3. ROOF CONDITION: If visible — material, age estimate, visible damage (curling, missing tabs, ponding, moss)
4. VISIBLE DAMAGE: Any damage indicators — cracks, staining, water damage, settling, vegetation intrusion
5. EXTERIOR FEATURES: Windows, doors, gutters, downspouts, parking, fencing, signage
6. HAZARD INDICATORS: Neighboring risks, overhanging trees, utility proximity, drainage issues
7. FIRE PROTECTION: Sprinkler heads visible, fire hydrant proximity, fire department access
8. SECURITY: Fencing, cameras, lighting, alarm systems visible
9. OCCUPANCY CLUES: Signs of active use, vacancy indicators, tenant mix
10. ENVIRONMENTAL: Vegetation health, soil conditions, evidence of flooding or erosion

Return a JSON object with exactly these keys:
{
  "building_condition": "excellent|good|fair|poor|deteriorated",
  "construction_materials": ["list", "of", "visible", "materials"],
  "roof_condition": "description if visible, 'not visible' if not",
  "visible_damage": [{"type": "damage type", "location": "where", "severity": "minor|moderate|severe", "description": "..."}],
  "exterior_features": ["list", "of", "features"],
  "hazard_indicators": [{"type": "hazard type", "description": "...", "risk_level": "low|medium|high"}],
  "fire_protection": "description of fire protection features",
  "security_features": ["list", "of", "security", "features"],
  "occupancy_clues": "description of occupancy indicators",
  "environmental_notes": "environmental observations",
  "overall_risk": "low|moderate|high|critical",
  "risk_summary": "one paragraph risk summary",
  "underwriting_flags": ["list of flags for the underwriter"]
}

Be specific and factual. If something is not visible, say so rather than guessing."""


def _detect_vision_provider() -> str:
    if os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"):
        return "openai"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    return "none"


def _encode_image_b64(image_data: bytes) -> str:
    return base64.b64encode(image_data).decode("utf-8")


def _guess_media_type(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if lower.endswith(".gif"):
        return "image/gif"
    if lower.endswith(".webp"):
        return "image/webp"
    return "image/jpeg"


def _call_openai_vision(image_data: bytes, filename: str) -> dict[str, Any]:
    try:
        import openai

        api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        base_url = os.getenv("OPENAI_API_BASE")
        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        client = openai.OpenAI(**client_kwargs)

        b64 = _encode_image_b64(image_data)
        media_type = _guess_media_type(filename)

        response = client.chat.completions.create(
            model=os.getenv("VISION_MODEL", "gpt-4o"),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROPERTY_ANALYSIS_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{b64}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
            max_tokens=1500,
            temperature=0.1,
        )
        text = response.choices[0].message.content or "{}"
        return _parse_json_response(text)
    except Exception as exc:
        logger.warning("OpenAI Vision API failed: %s", exc)
        return {}


def _call_anthropic_vision(image_data: bytes, filename: str) -> dict[str, Any]:
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        b64 = _encode_image_b64(image_data)
        media_type = _guess_media_type(filename)

        response = client.messages.create(
            model=os.getenv("VISION_MODEL", "claude-sonnet-4-20250514"),
            max_tokens=1500,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": PROPERTY_ANALYSIS_PROMPT},
                    ],
                }
            ],
        )
        text = response.content[0].text if response.content else "{}"
        return _parse_json_response(text)
    except Exception as exc:
        logger.warning("Anthropic Vision API failed: %s", exc)
        return {}


def _parse_json_response(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        result: dict[str, Any] = json.loads(text)
        return result
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                result = json.loads(text[start:end])
                return result
            except json.JSONDecodeError:
                pass
    return {}


def _risk_from_string(risk: str) -> VisualRisk:
    risk = risk.lower().strip()
    if risk in ("critical", "severe"):
        return VisualRisk.CRITICAL
    if risk in ("high", "significant"):
        return VisualRisk.HIGH
    if risk in ("moderate", "medium", "moderate_risk"):
        return VisualRisk.MODERATE
    return VisualRisk.LOW


class VisionLLMAnalyzer:
    def __init__(self, provider: str | None = None) -> None:
        self.provider = provider or _detect_vision_provider()

    @property
    def available(self) -> bool:
        return self.provider != "none"

    def analyze_photo(
        self,
        image_data: bytes,
        filename: str,
        photo_id: str = "",
    ) -> dict[str, Any]:
        if not self.available:
            return {}
        try:
            from insureflow.privacy.data_plane import allow_vision_egress

            if not allow_vision_egress():
                logger.warning(
                    "Vision LLM egress blocked — property photos stay in the customer environment. "
                    "Set ALLOW_VISION_EGRESS=true only with a bank-approved private model."
                )
                return {}
        except Exception:
            logger.warning("Vision egress gate failed closed", exc_info=True)
            return {}
        if self.provider == "openai":
            return _call_openai_vision(image_data, filename)
        if self.provider == "anthropic":
            return _call_anthropic_vision(image_data, filename)
        return {}

    def enrich_analysis(
        self,
        analysis: PhotoAnalysis,
        image_data: bytes,
    ) -> PhotoAnalysis:
        result = self.analyze_photo(image_data, analysis.filename, analysis.photo_id)
        if not result:
            analysis.ai_description = "Vision LLM unavailable — quality assessment only"
            return analysis

        analysis.ai_description = result.get("risk_summary", "")

        condition = result.get("building_condition", "")
        if condition:
            analysis.detected_features.append(f"building_condition:{condition}")

        for mat in result.get("construction_materials", []):
            analysis.detected_features.append(f"material:{mat}")

        for damage in result.get("visible_damage", []):
            severity_map = {"minor": "info", "moderate": "warning", "severe": "critical"}
            analysis.findings.append(
                VisualFinding(
                    category="damage",
                    description=f"{damage.get('type', 'Unknown')}: {damage.get('description', '')} ({damage.get('location', 'unspecified')})",
                    severity=severity_map.get(damage.get("severity", "minor"), "info"),
                    confidence=0.8,
                )
            )

        for hazard in result.get("hazard_indicators", []):
            risk_map = {"low": "info", "medium": "warning", "high": "critical"}
            analysis.findings.append(
                VisualFinding(
                    category="hazard",
                    description=f"{hazard.get('type', 'Unknown')}: {hazard.get('description', '')}",
                    severity=risk_map.get(hazard.get("risk_level", "low"), "info"),
                    confidence=0.75,
                )
            )

        overall = result.get("overall_risk", "low")
        analysis.visual_risk = _risk_from_string(overall)

        for flag in result.get("underwriting_flags", []):
            analysis.findings.append(
                VisualFinding(
                    category="underwriting_flag",
                    description=flag,
                    severity="warning",
                    confidence=0.7,
                )
            )

        return analysis
