"""Golden packages: intake → retrieve → rate → decide for commercial specialty lines."""

from __future__ import annotations

from pathlib import Path

import pytest

from insureflow.audit.store import AuditStore
from insureflow.insurance.pipeline import InsurancePipeline
from insureflow.rag.rag_agent import RAGAgent
from insureflow.rating.models import InsuranceLine

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "insurance"

GOLDENS = [
    ("directors_and_officers", InsuranceLine.DIRECTORS_AND_OFFICERS, ("DO-001", "DO-002")),
    ("trade_credit", InsuranceLine.TRADE_CREDIT, ("TC-001",)),
    ("errors_and_omissions", InsuranceLine.ERRORS_AND_OMISSIONS, ("EO-001",)),
    ("key_person", InsuranceLine.KEY_PERSON, ("KP-001",)),
]


def _docs_from_dir(subdir: str) -> list[dict[str, str]]:
    root = EXAMPLES / subdir
    assert root.is_dir(), f"missing golden package: {root}"
    docs: list[dict[str, str]] = []
    for path in sorted(root.glob("*")):
        if path.is_file() and path.suffix.lower() in {".md", ".txt", ".json", ".xml"}:
            docs.append({"filename": path.name, "content": path.read_text(encoding="utf-8")})
    assert docs, f"empty golden package: {root}"
    return docs


@pytest.fixture
def audit_store(tmp_path: Path) -> AuditStore:
    return AuditStore(base_path=tmp_path / "audit")


@pytest.mark.parametrize("subdir,line,guide_ids", GOLDENS)
def test_golden_intake_retrieve_rate_decide(
    audit_store: AuditStore,
    subdir: str,
    line: InsuranceLine,
    guide_ids: tuple[str, ...],
) -> None:
    docs = _docs_from_dir(subdir)
    result = InsurancePipeline(org_id="specialty-e2e", use_llm=False, audit_store=audit_store).run(
        documents=docs,
        insurance_line=line.value,
        bundle_id=f"e2e-{subdir}",
        skip_oracles=True,
        skip_portfolio=True,
        skip_reinsurance=True,
    )

    assert result["status"] == "completed"
    assert result["insurance_line"] == line.value
    quote = result["quote"]
    assert quote["insurance_line"] == line.value
    assert quote.get("specialty") is True
    assert quote["eligible"] is True
    assert quote["adjusted_premium"] > 0
    # Must not silently behave like property COPE rating
    assert quote.get("exposure_basis")
    assert result["ai_decision"] in ("accept", "conditional_accept", "refer", "decline")

    retrieval = result.get("specialty_retrieval") or {}
    assert retrieval.get("line_of_business") == line.value
    assert retrieval.get("no_context") is False
    retrieved_ids = set(retrieval.get("guideline_ids") or [])
    assert retrieved_ids.intersection(guide_ids), f"expected one of {guide_ids} in {retrieved_ids}"


def test_trade_credit_refer_golden_concentration(audit_store: AuditStore) -> None:
    docs = _docs_from_dir("trade_credit_refer")
    result = InsurancePipeline(org_id="specialty-e2e", use_llm=False, audit_store=audit_store).run(
        documents=docs,
        insurance_line="trade_credit",
        bundle_id="e2e-trade-credit-refer",
        skip_oracles=True,
        skip_portfolio=True,
        skip_reinsurance=True,
    )
    assert result["insurance_line"] == "trade_credit"
    assert result["quote"]["specialty"] is True
    assert result["ai_decision"] in ("refer", "decline")
    assert result["human_review_required"] is True
    ids = set((result.get("specialty_retrieval") or {}).get("guideline_ids") or [])
    assert "TC-001" in ids


def test_retrieval_line_filter_excludes_other_specialty() -> None:
    rag = RAGAgent(use_knowledge_graph=False)
    tc = rag.retrieve_contexts("buyer concentration receivables", top_k=5, line_of_business="trade_credit")
    assert "TC-001" in (tc.get("guideline_ids") or [])
    assert "DO-001" not in (tc.get("guideline_ids") or [])
    assert "EO-001" not in (tc.get("guideline_ids") or [])

    do = rag.retrieve_contexts("pending litigation securities", top_k=5, line_of_business="directors_and_officers")
    assert "DO-001" in (do.get("guideline_ids") or [])
    assert "TC-001" not in (do.get("guideline_ids") or [])


def test_property_package_still_not_specialty(audit_store: AuditStore) -> None:
    acord = EXAMPLES / "pacific_coast_acord.xml"
    if not acord.exists():
        pytest.skip("pacific coast missing")
    result = InsurancePipeline(org_id="specialty-e2e", use_llm=False, audit_store=audit_store).run(
        acord_xml=acord.read_text(encoding="utf-8"),
        insurance_line="commercial_property",
        bundle_id="e2e-property-control",
        skip_oracles=True,
        skip_portfolio=True,
        skip_reinsurance=True,
    )
    assert result["insurance_line"] == "commercial_property"
    assert result["quote"].get("specialty") in (False, None)
    assert result.get("specialty_retrieval") is None
