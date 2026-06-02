from __future__ import annotations

from typing import Optional

from insureflow.llm.client import LLMClient
from insureflow.llm.prompts import VERIFICATION_PROMPT
from insureflow.models.audit import ReconciliationResult
from insureflow.models.provenance import ProvenanceRecord, TrustLevel, VerificationStatus
from insureflow.provenance.hierarchy import ProvenanceEngine
from insureflow.reconciliation.engine import ReconciliationEngine
from insureflow.provenance.trust_scorer import TrustScorer


class VerificationAgent:
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
    ) -> None:
        self.llm = llm_client or LLMClient()
        self.provenance = ProvenanceEngine()
        self.reconciliation = ReconciliationEngine()
        self.scorer = TrustScorer()

    def verify(
        self, provenance_record: ProvenanceRecord
    ) -> tuple[ReconciliationResult, dict[str, float]]:
        result = self.reconciliation.reconcile(provenance_record)
        scores = self.scorer.score(provenance_record)

        trust_level = self.scorer.overall_trust_level(scores["overall"])

        for field_path, nodes in provenance_record.nodes.items():
            if len(nodes) >= 2:
                for node in nodes:
                    authority = max(
                        nodes,
                        key=lambda n: n.source.hierarchy_rank,
                    )
                    if str(node.value) == str(authority.value):
                        node.verification_status = VerificationStatus.VERIFIED
                    else:
                        node.verification_status = VerificationStatus.CONTRADICTED

        return result, scores

    def needs_human_review(self, result: ReconciliationResult) -> bool:
        return self.scorer.needs_human_review(result)
