"""Aggregates the verification layers into a ``VerificationReport``.

Deterministic layers (arithmetic, guardrails, layout, forensics, registry) run
on every document when ``USE_VERIFICATION`` is on (default). Agentic layers
(critic review) run only when explicitly enabled *and* an LLM is available.
The result drives straight-through processing: ``auto_approve`` requires zero
error-severity issues and every critical numeric field at or above
``STP_CONFIDENCE_THRESHOLD`` (default 95%).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Iterable, Mapping

from insureflow.ingestion.forensics import inspect_pdf, tamper_checks_enabled, tampering_issues
from insureflow.ingestion.spatial_graph import column_alignment_check
from insureflow.models.submissions import ExtractedField, VerificationIssue, VerificationReport
from insureflow.verification.arithmetic import auto_sum_to_total, balance_sheet_identity
from insureflow.verification.common import SEVERITY_ERROR, verification_enabled
from insureflow.verification.critic import critic_review
from insureflow.verification.external_lookup import registry_verification_issues
from insureflow.verification.guardrails import pattern_checks, range_checks, schema_validation
from insureflow.verification.semantic_triangulation import triangulation_issues

logger = logging.getLogger(__name__)

_CRITICAL_TERMS = (
    "total",
    "assets",
    "revenue",
    "incurred",
    "premium",
    "limit",
    "deductible",
    "value",
    "net_income",
)


def _critical_field_keys(fields: Mapping[str, Iterable[ExtractedField]]) -> list[str]:
    return [k for k in fields if any(term in k.lower() for term in _CRITICAL_TERMS)]


class VerificationEngine:
    def __init__(self, llm: Any = None) -> None:
        self.llm = llm

    def run(
        self,
        fields: Mapping[str, list[ExtractedField]],
        raw_text: str = "",
        document_type: str = "",
        spatial_lines: Mapping[int, Mapping[str, list[float]]] | None = None,
        pdf_bytes: bytes | None = None,
        markdown: str | None = None,
    ) -> VerificationReport:
        """Run every enabled layer and aggregate into a :class:`VerificationReport`.

        Never raises: each layer is wrapped so a bad input degrades to a logged
        skip rather than failing the load path.
        """
        if not verification_enabled():
            return VerificationReport(passed=True, auto_approve=True, checks_run=["verification_disabled"])
        issues: list[VerificationIssue] = []
        checks_run: list[str] = []
        stp_threshold = float(os.getenv("STP_CONFIDENCE_THRESHOLD", "0.95"))

        for layer, fn in (
            ("balance_sheet", lambda: balance_sheet_identity(fields)),
            ("sum_to_total", lambda: auto_sum_to_total(fields)),
            ("range_checks", lambda: range_checks(fields)),
            ("pattern_checks", lambda: pattern_checks(fields)),
            ("schema_validation", lambda: schema_validation(fields)),
        ):
            try:
                layer_issues = fn()
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("verification layer %s failed: %s", layer, exc)
                continue
            checks_run.append(layer)
            issues.extend(layer_issues)

        if spatial_lines:
            try:
                issues.extend(column_alignment_check(spatial_lines))
                checks_run.append("spatial_graph")
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("spatial graph check failed: %s", exc)

        if markdown:
            try:
                issues.extend(triangulation_issues(markdown))
                checks_run.append("semantic_triangulation")
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("semantic triangulation failed: %s", exc)

        if tamper_checks_enabled() and pdf_bytes:
            forensics = None
            try:
                forensics = inspect_pdf(pdf_bytes)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("forensic inspection failed: %s", exc)
            if forensics is not None:
                issues.extend(tampering_issues(forensics))
                checks_run.append("forensics")

        registry_issues = []
        try:
            registry_issues = registry_verification_issues(fields)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("registry verification failed: %s", exc)
        if registry_issues:
            checks_run.append("external_lookup")
        issues.extend(registry_issues)

        if self.llm is not None:
            try:
                issues.extend(critic_review(raw_text, fields, self.llm))
                checks_run.append("critic")
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("critic review failed: %s", exc)

        issues.extend(_stp_confidence_issues(fields, stp_threshold))
        checks_run.append("stp_gate")

        errors = [i for i in issues if i.severity == SEVERITY_ERROR]
        return VerificationReport(
            passed=not errors,
            auto_approve=not errors,
            flagged_for_review=bool(errors),
            checks_run=checks_run,
            issues=issues,
        )


def _stp_confidence_issues(
    fields: Mapping[str, Iterable[ExtractedField]],
    stp_threshold: float,
) -> list[VerificationIssue]:
    issues: list[VerificationIssue] = []
    for key in _critical_field_keys(fields):
        entries = list(fields[key])
        if not entries:
            continue
        field = entries[0]
        if not field.value or not field.value.strip():
            continue
        if field.confidence < stp_threshold:
            issues.append(
                VerificationIssue(
                    code="stp_block_low_confidence",
                    severity=SEVERITY_ERROR,
                    message=(
                        f"critical field {key}={field.value!r} has confidence {field.confidence:.3f} "
                        f"< {stp_threshold:.3f} — blocks straight-through processing"
                    ),
                    field_name=key,
                    page_number=field.page_number,
                    bbox=field.bbox,
                )
            )
    return issues
