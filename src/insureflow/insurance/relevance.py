"""Document relevance validation for insurance / mortgage / lending packages.

Flags files that look unrelated to underwriting (menus, resumes, random scans)
so intake can warn or block before the pipeline burns cycles on junk.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from insureflow.ingestion.insurance.classifier import InsuranceDocumentClassifier, InsuranceDocumentType

# Strong signals that content belongs in an insurance/mortgage/lending package
_RELEVANT_KEYWORDS: tuple[str, ...] = (
    "acord",
    "named insured",
    "loss run",
    "claims history",
    "schedule of values",
    "total insurable",
    "policy number",
    "underwriting",
    "certificate of insurance",
    "general liability",
    "workers compensation",
    "workers' compensation",
    "commercial property",
    "business interruption",
    "deductible",
    "premium",
    "coverage",
    "endorsement",
    "declaration",
    "inspection report",
    "financial statement",
    "balance sheet",
    "mortgage",
    "appraisal",
    "loan application",
    "borrower",
    "collateral",
    "credit report",
    "d&o",
    "directors and officers",
    "errors and omissions",
    "trade credit",
    "accounts receivable",
    "naics",
    "tiv",
    "building value",
    "occupancy",
)

# Strong signals of obviously-irrelevant content
_IRRELEVANT_KEYWORDS: tuple[str, ...] = (
    "restaurant menu",
    "ingredients",
    "calories",
    "curriculum vitae",
    "curriculum vitae",
    "linkedin profile",
    "wedding invitation",
    "birthday party",
    "spotify playlist",
    "homework assignment",
    "recipe for",
    "terms of service for facebook",
    "unsubscribe from this email",
)

_INSURANCE_EXT = {".xml", ".json", ".pdf", ".txt", ".md", ".doc", ".docx", ".csv", ".xlsx", ".xls", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}
_TYPED = {t for t in InsuranceDocumentType if t not in {InsuranceDocumentType.SUPPLEMENTAL, InsuranceDocumentType.IRRELEVANT}}


@dataclass
class RelevanceResult:
    filename: str
    relevant: bool
    score: float
    doc_type: str
    reason: str
    signals: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _preview_text(content: str, encoding: str = "utf-8", limit: int = 6000) -> str:
    if not content:
        return ""
    if (encoding or "utf-8").lower() == "base64":
        # Binary uploads — rely on filename / extension only
        return ""
    return str(content)[:limit]


def score_document_relevance(
    *,
    filename: str,
    content: str = "",
    encoding: str = "utf-8",
    vertical: str = "insurance",
) -> RelevanceResult:
    """Score whether a single file looks relevant to the vertical package."""
    name = (filename or "document").strip() or "document"
    lower_name = name.lower()
    ext = ""
    if "." in lower_name:
        ext = "." + lower_name.rsplit(".", 1)[-1]

    preview = _preview_text(content, encoding)
    combined = f"{lower_name}\n{preview}".lower()
    signals: list[str] = []

    # Extension gate
    if ext and ext not in _INSURANCE_EXT:
        return RelevanceResult(
            filename=name,
            relevant=False,
            score=0.05,
            doc_type=InsuranceDocumentType.IRRELEVANT.value,
            reason=f"Unsupported file type ({ext}) for {vertical} underwriting packages",
            signals=["unsupported_extension"],
        )

    # Hard irrelevant phrases
    for kw in _IRRELEVANT_KEYWORDS:
        if kw in combined:
            return RelevanceResult(
                filename=name,
                relevant=False,
                score=0.1,
                doc_type=InsuranceDocumentType.IRRELEVANT.value,
                reason=f"Content looks unrelated to {vertical} (matched “{kw}”)",
                signals=[f"irrelevant:{kw}"],
            )

    classified = InsuranceDocumentClassifier.classify(preview or lower_name, filename=name)
    if classified in _TYPED:
        signals.append(f"classified:{classified.value}")
        return RelevanceResult(
            filename=name,
            relevant=True,
            score=0.95,
            doc_type=classified.value,
            reason=f"Classified as {classified.value.replace('_', ' ')}",
            signals=signals,
        )

    # Keyword scoring for borderline / supplemental
    hits = [kw for kw in _RELEVANT_KEYWORDS if kw in combined]
    signals.extend(f"keyword:{h}" for h in hits[:8])
    score = min(0.85, 0.15 + 0.12 * len(hits))

    # Filename hints (SOV, ACORD, loss, etc.)
    name_hints = ("acord", "loss", "sov", "inspection", "policy", "application", "dec", "financial", "mortgage", "loan")
    if any(h in lower_name for h in name_hints):
        score = max(score, 0.7)
        signals.append("filename_hint")

    # Empty / tiny text with generic name → low confidence supplemental (still allow with warning)
    if not preview and (encoding or "").lower() == "base64":
        # PDFs/images often have no text preview client-side — soft-pass with review flag
        score = max(score, 0.55)
        signals.append("binary_upload")
        return RelevanceResult(
            filename=name,
            relevant=True,
            score=score,
            doc_type=InsuranceDocumentType.SUPPLEMENTAL.value,
            reason="Binary upload — will OCR on ingest; flagged for UW review if text has no insurance signals",
            signals=signals,
        )

    if score >= 0.45 or hits:
        return RelevanceResult(
            filename=name,
            relevant=True,
            score=round(score, 2),
            doc_type=InsuranceDocumentType.SUPPLEMENTAL.value,
            reason="Looks related to the package (keyword / filename signals)",
            signals=signals,
        )

    # No insurance signals at all
    return RelevanceResult(
        filename=name,
        relevant=False,
        score=round(max(score, 0.15), 2),
        doc_type=InsuranceDocumentType.IRRELEVANT.value,
        reason=f"No {vertical} underwriting signals found — file may be irrelevant",
        signals=signals or ["no_signals"],
    )


def validate_documents_relevance(
    documents: list[dict[str, Any]],
    *,
    vertical: str = "insurance",
    strict: bool = False,
) -> dict[str, Any]:
    """Validate a multi-file package. Returns per-file results + package gate."""
    results: list[RelevanceResult] = []
    for doc in documents or []:
        if not isinstance(doc, dict):
            continue
        results.append(
            score_document_relevance(
                filename=str(doc.get("filename") or "document"),
                content=str(doc.get("content") or ""),
                encoding=str(doc.get("encoding") or "utf-8"),
                vertical=vertical,
            )
        )

    relevant = [r for r in results if r.relevant]
    irrelevant = [r for r in results if not r.relevant]
    can_run = len(relevant) > 0
    if strict and irrelevant:
        can_run = False

    warnings: list[str] = []
    if irrelevant:
        names = ", ".join(r.filename for r in irrelevant[:5])
        extra = f" (+{len(irrelevant) - 5} more)" if len(irrelevant) > 5 else ""
        warnings.append(f"{len(irrelevant)} file(s) look irrelevant: {names}{extra}")
    if not results:
        warnings.append("No documents provided")
        can_run = False
    elif not relevant:
        warnings.append("All files look irrelevant — add ACORD, loss runs, SOV, or other underwriting docs")

    return {
        "vertical": vertical,
        "strict": strict,
        "can_run": can_run,
        "document_count": len(results),
        "relevant_count": len(relevant),
        "irrelevant_count": len(irrelevant),
        "documents": [r.to_dict() for r in results],
        "irrelevant": [r.to_dict() for r in irrelevant],
        "warnings": warnings,
        "message": ("Package ready to run" if can_run and not irrelevant else (warnings[0] if warnings else "Review flagged files before running")),
    }


_NON_UW_NAME = re.compile(r"(menu|resume|cv|playlist|homework|recipe|invitation)", re.I)


def classify_with_relevance(text: str, filename: str = "") -> InsuranceDocumentType:
    """Classify, then demote clearly irrelevant content to IRRELEVANT."""
    typed = InsuranceDocumentClassifier.classify(text, filename=filename)
    if typed != InsuranceDocumentType.SUPPLEMENTAL:
        return typed
    result = score_document_relevance(filename=filename, content=text, encoding="utf-8")
    if not result.relevant:
        return InsuranceDocumentType.IRRELEVANT
    if _NON_UW_NAME.search(filename or "") and result.score < 0.6:
        return InsuranceDocumentType.IRRELEVANT
    return typed
