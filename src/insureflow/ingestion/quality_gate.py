from __future__ import annotations

import logging
from typing import Any

from insureflow.ingestion.doc_quality import DocumentQualityScorer

logger = logging.getLogger(__name__)


class DocQualityGate:
    """Quality gate that evaluates document batch and decides: PASS, WARN, or BLOCK.

    This gate runs BEFORE extraction. If documents are too poor quality,
    the submission is blocked and resubmit is requested.
    """

    # Thresholds
    REJECT_THRESHOLD = 0.3  # Any doc below this → block
    BATCH_WARN_THRESHOLD = 0.5  # If >30% of docs are warn-level → warn
    MIN_PASS_COUNT = 1  # At least this many docs must pass

    def __init__(self) -> None:
        self._scorer = DocumentQualityScorer()

    def evaluate(self, documents: list[dict[str, Any]]) -> dict[str, Any]:
        """Evaluate document batch quality.

        Returns:
            decision: "pass" | "warn" | "block"
            score: overall batch score (0.0-1.0)
            results: per-document quality results
            issues: aggregated issues
            resubmit_required: list of filenames that need resubmission
        """
        if not documents:
            return {
                "decision": "block",
                "score": 0.0,
                "results": [],
                "issues": ["No documents provided"],
                "resubmit_required": [],
            }

        results = self._scorer.score_batch(documents)

        scores = [r.score for r in results]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        reject_count = sum(1 for r in results if r.status == "reject")
        warn_count = sum(1 for r in results if r.status == "warn")
        pass_count = sum(1 for r in results if r.status == "pass")

        issues: list[str] = []
        resubmit_required: list[str] = []

        for r in results:
            if r.status == "reject":
                issues.append(f"REJECTED: {r.filename} — {'; '.join(r.issues)}")
                resubmit_required.append(r.filename)
            elif r.status == "warn":
                issues.append(f"WARNING: {r.filename} — {'; '.join(r.issues)}")

        # Decision logic
        if reject_count > 0:
            decision = "block"
        elif pass_count < self.MIN_PASS_COUNT:
            decision = "block"
            issues.append(f"Too few passing documents: {pass_count}/{len(documents)}")
        elif warn_count / max(len(documents), 1) > 0.3:
            decision = "warn"
        else:
            decision = "pass"

        return {
            "decision": decision,
            "score": avg_score,
            "results": [r.to_dict() for r in results],
            "issues": issues,
            "resubmit_required": resubmit_required,
        }
