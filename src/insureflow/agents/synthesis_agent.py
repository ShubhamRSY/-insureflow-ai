from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from insureflow.llm.client import LLMClient
from insureflow.llm.prompts import SYNTHESIS_PROMPT
from insureflow.models.audit import ReconciliationResult, SynthesisOutput
from insureflow.models.provenance import ProvenanceRecord
from insureflow.verification.citation_gate import gate_memo_claims


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
        grounded_keys: list[str] = []

        for field_path, field_result in reconciliation_result.field_reconciliation.items():
            field_name = field_path.replace("risk_profile.", "").replace("location.", "").replace("financial.", "")
            profile[field_name] = field_result.get("resolved_value")
            confidence[field_path] = field_result.get("confidence", 0.0)
            source = field_result.get("authoritative_source", "unknown")
            provenance_summary[field_path] = {
                "source": source,
                "consensus": field_result.get("consensus_rate", 0.0),
                "page_number": field_result.get("page_number"),
                "bbox": field_result.get("bbox"),
                "source_ref": field_result.get("source_ref") or source,
            }
            if field_result.get("page_number") is not None or field_result.get("bbox") or field_result.get("source_ref") or source not in {"unknown", "llm", "ai"}:
                grounded_keys.append(field_path)
                grounded_keys.append(field_name)

        if self.llm.api_key:
            try:
                import json

                # Freeze pre-LLM keys so the model cannot invent new critical facts.
                pre_llm_keys = set(profile.keys())
                pre_llm_values = {k: profile[k] for k in pre_llm_keys}

                context = {
                    "field_reconciliation": reconciliation_result.field_reconciliation,
                    "discrepancies": [d.model_dump() for d in reconciliation_result.discrepancies],
                    "match_rate": reconciliation_result.match_rate,
                    "overall_status": reconciliation_result.overall_status,
                    "rag_context": rag_context,
                    "citation_rule": (
                        "Do not add numeric or coverage facts that lack a page/bbox/source_ref. "
                        "You may only rephrase existing reconciled fields. Hallucination count must stay 0."
                    ),
                    "allowed_keys": sorted(pre_llm_keys),
                }

                llm_refined = self.llm.complete(
                    SYNTHESIS_PROMPT,
                    json.dumps(context, default=str, indent=2),
                )

                try:
                    parsed = json.loads(llm_refined)
                    if isinstance(parsed, dict):
                        if "risk_profile" in parsed and isinstance(parsed["risk_profile"], dict):
                            # Constrained merge: only overwrite keys that already existed and were grounded.
                            for k, v in parsed["risk_profile"].items():
                                if k not in pre_llm_keys:
                                    continue  # drop invented keys
                                if k not in grounded_keys and f"risk_profile.{k}" not in grounded_keys:
                                    continue
                                profile[k] = v
                        if "confidence_scores" in parsed and isinstance(parsed["confidence_scores"], dict):
                            for k, v in parsed["confidence_scores"].items():
                                if k in confidence or k in pre_llm_keys:
                                    confidence[k] = v
                        if "provenance_metadata" in parsed and isinstance(parsed["provenance_metadata"], dict):
                            for k, v in parsed["provenance_metadata"].items():
                                if k in provenance_summary or k in pre_llm_keys:
                                    provenance_summary[k] = v
                except (json.JSONDecodeError, TypeError):
                    # On parse failure, restore pre-LLM profile (never keep partial inventions).
                    profile.clear()
                    profile.update(pre_llm_values)
            except Exception:
                pass

        # Hard gate: profile keys that look like money/limits without provenance → human review.
        memo_claims = []
        for key, value in profile.items():
            prov = provenance_summary.get(key) or provenance_summary.get(f"risk_profile.{key}") or {}
            memo_claims.append(
                {
                    "field_name": key,
                    "title": f"{key}={value}",
                    "description": str(value),
                    "page_number": prov.get("page_number"),
                    "bbox": prov.get("bbox"),
                    "source_ref": prov.get("source_ref") or prov.get("source"),
                }
            )
        uncited = gate_memo_claims(memo_claims, grounded_keys=grounded_keys)
        if uncited:
            for issue in uncited:
                if issue.field_name and issue.field_name in profile:
                    # Strip uncited critical inventions from the bind-ready profile.
                    profile.pop(issue.field_name, None)
                    confidence[issue.field_name] = min(confidence.get(issue.field_name, 0.0), 0.2)
            output.human_review_required = True
            output.review_fields = list({*output.review_fields, *[i.field_name for i in uncited if i.field_name]})
            provenance_summary["_citation_gate"] = {
                "uncited_count": len(uncited),
                "codes": [i.code for i in uncited],
            }

        output.synthesized_profile = profile
        output.confidence_scores = confidence
        output.provenance_summary = provenance_summary
        output.discrepancies_found = len(reconciliation_result.discrepancies)
        output.discrepancies_resolved = sum(1 for d in reconciliation_result.discrepancies if d.resolved)
        if any(d.severity.value == "critical" for d in reconciliation_result.discrepancies):
            output.human_review_required = True
        if output.human_review_required and not output.review_fields:
            output.review_fields = [d.field_path for d in reconciliation_result.discrepancies if d.severity.value == "critical"]
        output.completed_at = datetime.now(timezone.utc)

        return output
