from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_EMPTY_CONTENT_THRESHOLD = 50
_SHORT_CONTENT_THRESHOLD = 200
_MIN_CONTENT_LENGTH = 10


@dataclass
class DocQualityResult:
    """Per-document quality evaluation result."""

    filename: str
    score: float
    status: str  # "pass" | "warn" | "reject"
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "score": self.score,
            "status": self.status,
            "issues": self.issues,
        }


class DocumentQualityScorer:
    """Score individual documents and batches for ingestion quality.

    Evaluates content presence, length, encoding validity, and
    basic structural signals to assign a 0.0–1.0 quality score.
    """

    # Thresholds
    REJECT_SCORE = 0.3
    WARN_SCORE = 0.5

    def score_batch(self, documents: list[dict[str, Any]]) -> list[DocQualityResult]:
        """Score every document in a batch."""
        return [self.score_document(doc) for doc in documents]

    def score_document(self, document: dict[str, Any]) -> DocQualityResult:
        """Score a single document for quality."""
        filename = document.get("filename", "unknown")
        content = document.get("content", "")
        encoding = document.get("encoding", "utf-8")

        issues: list[str] = []
        penalties = 0.0

        # 1. Content presence
        if not content or not content.strip():
            issues.append("Empty or missing content")
            penalties += 0.5

        content_len = len(content.strip()) if content else 0

        # 2. Very short content
        if content_len < _MIN_CONTENT_LENGTH:
            issues.append(f"Content extremely short ({content_len} chars)")
            penalties += 0.3
        elif content_len < _SHORT_CONTENT_THRESHOLD:
            issues.append(f"Content unusually short ({content_len} chars)")
            penalties += 0.15

        # 3. Base64 but no meaningful decoded content
        if encoding == "base64":
            import base64 as b64

            try:
                decoded = b64.b64decode(content)
                if len(decoded) < _EMPTY_CONTENT_THRESHOLD:
                    issues.append("Base64 decoded to near-empty payload")
                    penalties += 0.4
            except Exception:
                issues.append("Invalid base64 encoding")
                penalties += 0.5

        # 4. OCR failure signals
        if "[OCR: No text" in content or "[OCR:" in content[:100]:
            issues.append("Content contains OCR failure marker")
            penalties += 0.3

        # 5. Filename heuristics
        if not filename or filename == "unknown":
            issues.append("No filename provided")
            penalties += 0.1
        elif filename.lower().endswith((".exe", ".bat", ".cmd", ".sh", ".ps1")):
            issues.append("Executable file type detected")
            penalties += 0.4

        # 6. Garbled / encoding corruption signals
        replacement_count = content.count("\ufffd")
        if replacement_count > 5:
            issues.append(f"High replacement character count ({replacement_count}) — possible encoding corruption")
            penalties += 0.2

        score = max(0.0, min(1.0, 1.0 - penalties))

        if score < self.REJECT_SCORE:
            status = "reject"
        elif score < self.WARN_SCORE:
            status = "warn"
        else:
            status = "pass"

        return DocQualityResult(
            filename=filename,
            score=round(score, 4),
            status=status,
            issues=issues,
        )

    def batch_statistics(self, results: list[DocQualityResult]) -> dict[str, Any]:
        """Compute summary statistics from a list of per-document results."""
        if not results:
            return {"avg_score": 0.0, "pass_count": 0, "warn_count": 0, "reject_count": 0}
        scores = [r.score for r in results]
        return {
            "avg_score": round(statistics.mean(scores), 4),
            "median_score": round(statistics.median(scores), 4),
            "pass_count": sum(1 for r in results if r.status == "pass"),
            "warn_count": sum(1 for r in results if r.status == "warn"),
            "reject_count": sum(1 for r in results if r.status == "reject"),
        }
