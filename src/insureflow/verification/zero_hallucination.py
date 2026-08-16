"""Zero-hallucination enforcement for underwriting memos.

Target: hallucination_count == 0 on any bind-ready path.
Any uncited money/limit/total, any invented guideline id, or any finding that
asserts a dollar figure not present in grounded sources forces REFER and strips
the claim. Deterministic by default. Optional LLM debate is additive only.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from insureflow.models.agents import Finding, RiskSeverity, UnderwritingMemo, UWDecision
from insureflow.models.submissions import ExtractedField, SubmissionBundle, VerificationIssue
from insureflow.verification.citation_gate import citation_issues, gate_memo_claims, is_grounded
from insureflow.verification.common import SEVERITY_ERROR, to_number
from insureflow.verification.uncertainty import estimate_uncertainty, uncertainty_issues

_MONEY_RE = re.compile(
    r"(?:USD|US\$|\$|€|£)\s*-?\d[\d,]*(?:\.\d+)?|(?<![\w.])-?\d{1,3}(?:,\d{3})+(?:\.\d+)?",
    re.I,
)
_GUIDELINE_RE = re.compile(r"\b(?:guideline|rule)\s*([A-Z]{0,4}-?\d{2,6})\b", re.I)
_DEFAULT_MAX_HALLUCINATIONS = 0  # under or at zero


def zero_hallucination_enabled() -> bool:
    raw = os.getenv("USE_ZERO_HALLUCINATION", "1").strip().lower()
    return raw not in {"0", "false", "off", "no", "none"}


def max_allowed_hallucinations() -> int:
    try:
        return max(0, int(os.getenv("MAX_HALLUCINATIONS", str(_DEFAULT_MAX_HALLUCINATIONS))))
    except ValueError:
        return _DEFAULT_MAX_HALLUCINATIONS


@dataclass
class HallucinationHit:
    code: str
    message: str
    field_name: str = ""
    claim_text: str = ""

    def to_issue(self) -> VerificationIssue:
        return VerificationIssue(
            code=self.code,
            severity=SEVERITY_ERROR,
            message=self.message,
            field_name=self.field_name,
        )

    def to_finding(self) -> Finding:
        return Finding(
            title="Hallucination blocked — uncited claim",
            description=self.message,
            severity=RiskSeverity.CRITICAL,
            category="hallucination",
            field_path=self.field_name,
            confidence=1.0,
            evidence=[self.claim_text] if self.claim_text else [],
        )


@dataclass
class ZeroHallucinationReport:
    hallucination_count: int = 0
    max_allowed: int = 0
    passed: bool = True
    hits: list[HallucinationHit] = field(default_factory=list)
    stripped_finding_titles: list[str] = field(default_factory=list)
    checks_run: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hallucination_count": self.hallucination_count,
            "max_allowed": self.max_allowed,
            "passed": self.passed,
            "hits": [{"code": h.code, "message": h.message, "field_name": h.field_name} for h in self.hits],
            "stripped_finding_titles": list(self.stripped_finding_titles),
            "checks_run": list(self.checks_run),
        }


def _normalize_money_token(raw: str) -> str:
    cleaned = re.sub(r"[^0-9.\-]", "", raw or "")
    try:
        return f"{float(cleaned):.2f}"
    except ValueError:
        return cleaned


def grounded_money_set(
    fields: Mapping[str, Sequence[ExtractedField]] | None = None,
    *,
    extra_values: Iterable[Any] = (),
) -> set[str]:
    """Canonical money strings that appear in grounded sources."""
    out: set[str] = set()
    for key, entries in (fields or {}).items():
        if not entries:
            continue
        ef = entries[0]
        if not is_grounded(ef):
            continue
        num = to_number(ef.value)
        if num is not None:
            out.add(f"{num:.2f}")
        for m in _MONEY_RE.findall(ef.value or ""):
            out.add(_normalize_money_token(m))
    for value in extra_values:
        if value is None:
            continue
        num = to_number(str(value))
        if num is not None:
            out.add(f"{num:.2f}")
        for m in _MONEY_RE.findall(str(value)):
            out.add(_normalize_money_token(m))
    return {x for x in out if x and x not in {"-", "."}}


def collect_bundle_fields(bundle: SubmissionBundle) -> dict[str, list[ExtractedField]]:
    merged: dict[str, list[ExtractedField]] = {}
    for doc in (*bundle.unstructured, *bundle.supplemental):
        for key, entries in (doc.extracted_fields or {}).items():
            if entries:
                merged.setdefault(key, []).extend(entries)
    return merged


def structured_grounded_values(bundle: SubmissionBundle) -> list[Any]:
    vals: list[Any] = []
    if not bundle.structured:
        return vals
    s = bundle.structured
    for cov in s.coverages or []:
        vals.extend([cov.limit_amount, cov.deductible, cov.premium])
    for loc in s.locations or []:
        vals.extend([loc.building_value, loc.contents_value, loc.bi_value])
    if s.financial and s.financial.loss_run:
        vals.append(s.financial.loss_run.total_incurred)
        vals.append(s.financial.loss_run.total_paid)
        for c in s.financial.loss_run.claims or []:
            vals.extend([c.incurred_amount, c.paid_amount, c.open_reserve])
    return vals


def scan_text_for_ungrounded_money(text: str, allowed: set[str]) -> list[str]:
    """Return money tokens in ``text`` that are not in the grounded set."""
    bad: list[str] = []
    for match in _MONEY_RE.finditer(text or ""):
        token = _normalize_money_token(match.group(0))
        if not token:
            continue
        if token in allowed:
            continue
        # Allow integers that match float forms already present (12000 vs 12000.00)
        try:
            as_float = f"{float(token):.2f}"
        except ValueError:
            as_float = token
        if as_float in allowed:
            continue
        bad.append(match.group(0).strip())
    return bad


def scan_findings_for_hallucinations(
    findings: Sequence[Finding],
    *,
    allowed_money: set[str],
    allowed_guideline_ids: Iterable[str] = (),
) -> list[HallucinationHit]:
    allowed_g = {g.lower() for g in allowed_guideline_ids}
    hits: list[HallucinationHit] = []
    for finding in findings:
        blob = f"{finding.title}\n{finding.description}\n" + "\n".join(finding.evidence or [])
        # Findings that are themselves about hallucination/verification stay.
        if (finding.category or "").lower() in {"hallucination", "data_quality", "citation"}:
            # Still check money in description unless it's reporting the block itself
            if finding.category == "hallucination":
                continue
        bad_money = scan_text_for_ungrounded_money(blob, allowed_money)
        for tok in bad_money:
            hits.append(
                HallucinationHit(
                    code="finding_uncited_money",
                    message=f"Finding asserts {tok!r} with no grounded source figure — stripped",
                    field_name=finding.field_path or "",
                    claim_text=f"{finding.title}: {tok}",
                )
            )
        for gmatch in _GUIDELINE_RE.finditer(blob):
            gid = gmatch.group(1).lower()
            if allowed_g and gid not in allowed_g and gmatch.group(0).lower() not in allowed_g:
                hits.append(
                    HallucinationHit(
                        code="finding_invented_guideline",
                        message=f"Finding cites guideline {gmatch.group(1)!r} not in retrieved set — stripped",
                        field_name=finding.field_path or "",
                        claim_text=finding.title,
                    )
                )
    return hits


def multi_pass_consistency_issues(
    sample: Any = None,
    *,
    fields: Mapping[str, Sequence[ExtractedField]] | None = None,
    n_passes: int = 3,
) -> list[VerificationIssue]:
    """Default self-consistency: multi-sample CV, or multi-read extracted fields."""
    if sample is not None:
        cv = estimate_uncertainty(sample, n_passes=n_passes)
        return uncertainty_issues(cv)
    if fields is None:
        return []
    from insureflow.verification.uncertainty import variance_from_extracted_fields

    return uncertainty_issues(variance_from_extracted_fields(fields))


def debate_claims(
    claims: Sequence[Mapping[str, Any]],
    *,
    grounded_keys: Iterable[str] = (),
    allowed_money: set[str] | None = None,
) -> list[HallucinationHit]:
    """Proposer vs challenger (deterministic): challenger wins if claim lacks grounding."""
    allowed_money = allowed_money or set()
    grounded = {k.lower() for k in grounded_keys}
    hits: list[HallucinationHit] = []
    # Proposer side is the claim list; challenger applies citation + money rules.
    for issue in gate_memo_claims(claims, grounded_keys=grounded):
        hits.append(
            HallucinationHit(
                code="debate_challenger_win",
                message=f"Auditor rejected claim: {issue.message}",
                field_name=issue.field_name,
                claim_text=issue.message,
            )
        )
    for claim in claims:
        blob = f"{claim.get('title', '')} {claim.get('description', '')}"
        for tok in scan_text_for_ungrounded_money(blob, allowed_money):
            hits.append(
                HallucinationHit(
                    code="debate_uncited_money",
                    message=f"Auditor rejected ungrounded amount {tok!r} in claim",
                    field_name=str(claim.get("field_name") or ""),
                    claim_text=blob[:160],
                )
            )
    return hits


def evaluate_zero_hallucination(
    bundle: SubmissionBundle,
    *,
    memo: UnderwritingMemo | None = None,
    guideline_ids: Iterable[str] = (),
    profile: Mapping[str, Any] | None = None,
) -> ZeroHallucinationReport:
    """Return a pass/fail report. ``passed`` is True only when count ≤ max_allowed (default 0)."""
    if not zero_hallucination_enabled():
        return ZeroHallucinationReport(passed=True, checks_run=["zero_hallucination_disabled"])

    max_allowed = max_allowed_hallucinations()
    hits: list[HallucinationHit] = []
    checks: list[str] = []

    fields = collect_bundle_fields(bundle)
    checks.append("citation_gate")
    for issue in citation_issues(fields):
        if issue.severity == SEVERITY_ERROR:
            hits.append(
                HallucinationHit(
                    code=issue.code,
                    message=issue.message,
                    field_name=issue.field_name,
                    claim_text=issue.field_name,
                )
            )

    checks.append("self_consistency")
    for issue in multi_pass_consistency_issues(fields=fields):
        if issue.severity in {SEVERITY_ERROR, "warning"} and "CV" in issue.message:
            # High variance is treated as potential hallucination risk → count toward gate
            hits.append(
                HallucinationHit(
                    code="epistemic_variance",
                    message=issue.message,
                    field_name=issue.field_name,
                )
            )

    allowed_money = grounded_money_set(fields, extra_values=structured_grounded_values(bundle))
    checks.append("grounded_money_lexicon")

    if profile:
        claims = [{"field_name": k, "title": f"{k}={v}", "description": str(v)} for k, v in profile.items()]
        grounded_keys = [k for k, entries in fields.items() if entries and is_grounded(entries[0])]
        checks.append("debate")
        hits.extend(debate_claims(claims, grounded_keys=grounded_keys, allowed_money=allowed_money))

    stripped: list[str] = []
    if memo is not None:
        checks.append("finding_money_scan")
        finding_hits = scan_findings_for_hallucinations(
            list(memo.key_findings or []),
            allowed_money=allowed_money,
            allowed_guideline_ids=guideline_ids,
        )
        hits.extend(finding_hits)

    # Deduplicate by code+message
    seen: set[str] = set()
    unique: list[HallucinationHit] = []
    for h in hits:
        key = f"{h.code}:{h.message}:{h.field_name}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(h)

    count = len(unique)
    return ZeroHallucinationReport(
        hallucination_count=count,
        max_allowed=max_allowed,
        passed=count <= max_allowed,
        hits=unique,
        stripped_finding_titles=stripped,
        checks_run=checks,
    )


def enforce_zero_hallucination_on_memo(
    memo: UnderwritingMemo,
    bundle: SubmissionBundle,
    *,
    guideline_ids: Iterable[str] = (),
) -> ZeroHallucinationReport:
    """Strip hallucinated findings, force REFER when count > max_allowed (default 0)."""
    report = evaluate_zero_hallucination(bundle, memo=memo, guideline_ids=guideline_ids)
    if not zero_hallucination_enabled():
        return report

    allowed_money = grounded_money_set(
        collect_bundle_fields(bundle),
        extra_values=structured_grounded_values(bundle),
    )
    kept: list[Finding] = []
    stripped: list[str] = []
    for finding in list(memo.key_findings or []):
        if (finding.category or "").lower() == "hallucination":
            kept.append(finding)
            continue
        blob = f"{finding.title}\n{finding.description}\n" + "\n".join(finding.evidence or [])
        bad = scan_text_for_ungrounded_money(blob, allowed_money)
        # If guideline ids provided, drop invented ones; if none retrieved, drop any guideline citation
        drop = bool(bad)
        if _GUIDELINE_RE.search(blob):
            allowed_g = {g.lower() for g in guideline_ids}
            for m in _GUIDELINE_RE.finditer(blob):
                if m.group(1).lower() not in allowed_g:
                    drop = True
                    break
        if drop:
            stripped.append(finding.title)
            continue
        kept.append(finding)

    for hit in report.hits:
        kept.append(hit.to_finding())

    # Dedupe hallucination findings by description
    seen_desc: set[str] = set()
    deduped: list[Finding] = []
    for f in kept:
        key = f"{f.category}:{f.title}:{f.description}"
        if key in seen_desc:
            continue
        seen_desc.add(key)
        deduped.append(f)
    memo.key_findings = deduped
    report.stripped_finding_titles = stripped

    if not report.passed:
        memo.human_review_required = True
        reason = (
            f"Zero-hallucination gate failed: {report.hallucination_count} uncited claim(s) "
            f"(max allowed {report.max_allowed})"
        )
        if reason not in (memo.human_review_reasons or []):
            memo.human_review_reasons = list(memo.human_review_reasons or []) + [reason]
        if memo.decision not in (UWDecision.DECLINE, UWDecision.REFER):
            memo.decision = UWDecision.REFER
        memo.conditions = list(memo.conditions or []) + [
            "SUBJECT TO grounding: every money/limit/total in the memo must cite a page or source box"
        ]

    return report
