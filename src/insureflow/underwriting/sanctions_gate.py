"""OFAC / SDN screening on the insurance UW and bind path."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from insureflow.aml.sanctions import SanctionsScreener
from insureflow.models.agents import Finding, RiskSeverity
from insureflow.models.submissions import SubmissionBundle
from insureflow.underwriting.personal_lines import _blob


@dataclass
class InsuranceSanctionsResult:
    cleared: bool
    incomplete: bool = False
    queries: list[str] = field(default_factory=list)
    hits: list[dict[str, Any]] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    recommended_action: str = "clear"

    def to_metadata(self) -> dict[str, Any]:
        return {
            "ofac_cleared": self.cleared and not self.incomplete and not self.hits,
            "ofac_incomplete": self.incomplete,
            "ofac_queries": list(self.queries),
            "ofac_hits": list(self.hits),
            "ofac_action": self.recommended_action,
        }


def _subjects(bundle: SubmissionBundle) -> list[tuple[str, str]]:
    names: list[tuple[str, str]] = []
    if bundle.structured and bundle.structured.named_insured:
        ni = bundle.structured.named_insured
        if ni.legal_name:
            names.append((ni.legal_name, "organization"))
        dba = getattr(ni, "dba", None) or getattr(ni, "trade_name", None)
        if dba:
            names.append((str(dba), "organization"))
    blob = _blob(bundle)
    import re

    for m in re.finditer(r"(?:beneficial\s+owner|ubo|officer|director|applicant)\s*[:=]\s*([A-Za-z][A-Za-z .'-]{2,60})", blob, re.I):
        names.append((m.group(1).strip(), "individual"))
    # Life applicant often equals named insured; also scan "insured:"
    for m in re.finditer(r"(?:insured|proposed\s+insured|applicant)\s*[:=]\s*([A-Za-z][A-Za-z .'-]{2,60})", blob, re.I):
        names.append((m.group(1).strip(), "individual"))
    # Dedupe preserving order
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for name, kind in names:
        key = name.strip().lower()
        if len(key) < 3 or key in seen:
            continue
        seen.add(key)
        out.append((name.strip(), kind))
    return out


def screen_submission(bundle: SubmissionBundle) -> InsuranceSanctionsResult:
    screener = SanctionsScreener()
    queries: list[str] = []
    hits: list[dict[str, Any]] = []
    findings: list[Finding] = []
    action = "clear"
    subjects = _subjects(bundle)
    if not subjects:
        findings.append(
            Finding(
                title="Sanctions screening incomplete — no named insured on file",
                description=(
                    "OFAC / AML screening could not be run because the application does not show a "
                    "named insured or applicant. Obtain the applicant's full legal name and re-run "
                    "the screening before proceeding."
                ),
                severity=RiskSeverity.HIGH,
                category="sanctions",
            )
        )
        return InsuranceSanctionsResult(
            cleared=False,
            incomplete=True,
            findings=findings,
            recommended_action="refer_aml_officer",
        )

    for name, _ in subjects:
        queries.append(name)
        result = screener.screen(name)
        if result.hits:
            action = result.recommended_action or "refer_aml_officer"
            for hit in result.hits:
                hits.append(
                    {
                        "query": name,
                        "matched_name": hit.matched_name,
                        "list": hit.list_name,
                        "score": hit.score,
                        "program": hit.program,
                    }
                )
            findings.append(
                Finding(
                    title=f"OFAC hit: {name}",
                    description=f"{len(result.hits)} watchlist match(es) — {result.recommended_action}. Do not quote or bind.",
                    severity=RiskSeverity.CRITICAL,
                    category="sanctions",
                    evidence=[h.matched_name for h in result.hits[:5]],
                    source_document="OFAC SDN watchlist screening",
                    extraction_method="rule_engine",
                )
            )

    cleared = not hits
    if cleared:
        findings.append(
            Finding(
                title="OFAC: no watchlist match",
                description=f"Screened {len(queries)} name(s) against the embedded SDN subset.",
                severity=RiskSeverity.LOW,
                category="sanctions",
                source_document="OFAC SDN watchlist screening",
                extraction_method="rule_engine",
            )
        )
    return InsuranceSanctionsResult(
        cleared=cleared,
        queries=queries,
        hits=hits,
        findings=findings,
        recommended_action=action if hits else "clear",
    )
