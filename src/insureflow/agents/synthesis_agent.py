from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from insureflow.llm.client import LLMClient
from insureflow.llm.prompts import SYNTHESIS_PROMPT
from insureflow.models.audit import SynthesisOutput
from insureflow.models.provenance import ProvenanceRecord
from insureflow.reconciliation.engine import ReconciliationResult


class SynthesisAgent:
    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        self.llm = llm_client or LLMClient()

    def synthesize(
        self,
        provenance_record: ProvenanceRecord,
        reconciliation_result: ReconciliationResult,
        rag_context: str = "",
    ) -> SynthesisOutput:
        output = SynthesisOutput(
            bundle_id=provenance_record.bundle_id,
        )

        output.rag_context_used = bool(rag_context)

        profile: dict[str, Any] = {}
        confidence: dict[str, float] = {}
        provenance_summary: dict[str, Any] = {}

        for field_path, field_result in reconciliation_result.field_reconciliation.items():
            field_name = field_path.replace("risk_profile.", "").replace("location.", "").replace("financial.", "")
            profile[field_name] = field_result.get("resolved_value")
            confidence[field_path] = field_result.get("confidence", 0.0)
            provenance_summary[field_path] = {
                "source": field_result.get("authoritative_source", "unknown"),
                "consensus": field_result.get("consensus_rate", 0.0),
            }

        if self.llm.api_key:
            try:
                import json

                context = {
                    "field_reconciliation": reconciliation_result.field_reconciliation,
                    "discrepancies": [
                        d.model_dump() for d in reconciliation_result.discrepancies
                    ],
                    "match_rate": reconciliation_result.match_rate,
                    "overall_status": reconciliation_result.overall_status,
                    "rag_context": rag_context,
                }

                llm_refined = self.llm.complete(
                    SYNTHESIS_PROMPT,
                    json.dumps(context, default=str, indent=2),
                )

                try:
                    parsed = json.loads(llm_refined)
                    if isinstance(parsed, dict):
                        if "risk_profile" in parsed:
                            profile.update(parsed["risk_profile"])
                        if "confidence_scores" in parsed:
                            confidence.update(parsed["confidence_scores"])
                        if "provenance_metadata" in parsed:
                            provenance_summary.update(parsed["provenance_metadata"])
                except (json.JSONDecodeError, TypeError):
                    pass
            except Exception:
                pass

        output.synthesized_profile = profile
        output.confidence_scores = confidence
        output.provenance_summary = provenance_summary
        output.discrepancies_found = len(reconciliation_result.discrepancies)
        output.discrepancies_resolved = sum(
            1 for d in reconciliation_result.discrepancies if d.resolved
        )
        output.human_review_required = any(
            d.severity.value == "critical" for d in reconciliation_result.discrepancies
        )
        if output.human_review_required:
            output.review_fields = [
                d.field_path
                for d in reconciliation_result.discrepancies
                if d.severity.value == "critical"
            ]
        output.completed_at = datetime.now(timezone.utc)

        return output
