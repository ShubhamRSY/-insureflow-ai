"""Layered extraction-verification tests: deterministic math constraints,
range/format guardrails, layout masking, footnote triangulation, epistemic
variance, critic + dual-model consensus, external registry, PDF forensics,
and the aggregating VerificationEngine wired into the loader."""

from __future__ import annotations

import json

import pytest

try:
    import fitz  # noqa: F401

    HAS_PYMUPDF = True
except ImportError:
    try:
        import pymupdf  # noqa: F401

        HAS_PYMUPDF = True
    except ImportError:
        HAS_PYMUPDF = False


def _field(key, value, confidence=1.0, page=None):
    from insureflow.models.submissions import ExtractedField

    return ExtractedField(field_name=key, value=value, confidence=confidence, page_number=page)


def _fields(mapping):
    return {k: [_field(k, v)] for k, v in mapping.items()}


# ── 1. Deterministic math constraints ───────────────────────────────────────


def test_balance_sheet_identity_balanced():
    from insureflow.verification.arithmetic import balance_sheet_identity

    assert balance_sheet_identity(_fields({"total_assets": "1000", "total_liabilities": "600", "total_equity": "400"})) == []


def test_balance_sheet_identity_mismatch():
    from insureflow.verification.arithmetic import balance_sheet_identity

    issues = balance_sheet_identity(_fields({"total_assets": "1000", "total_liabilities": "600", "total_equity": "300"}))
    assert issues and issues[0].code == "balance_sheet_identity"
    assert issues[0].severity == "error"
    assert "Assets (1,000.00)" in issues[0].message


def test_balance_sheet_partial_side_clean():
    from insureflow.verification.arithmetic import balance_sheet_identity

    assert balance_sheet_identity(_fields({"total_liabilities": "600", "total_equity": "400"})) == []


def test_sum_to_total_explicit():
    from insureflow.verification.arithmetic import sum_to_total_verification

    issues = sum_to_total_verification(_fields({"total_premium": "1000", "premium_1": "600", "premium_2": "400"}), "total_premium", ["premium_1", "premium_2"])
    assert issues == []
    bad = sum_to_total_verification(_fields({"total_premium": "2000", "premium_1": "600", "premium_2": "400"}), "total_premium", ["premium_1", "premium_2"])
    assert bad and bad[0].code == "sum_to_total"


def test_auto_sum_to_total_detects_family():
    from insureflow.verification.arithmetic import auto_sum_to_total

    good = auto_sum_to_total(_fields({"total_premium": "1000", "premium_1": "600", "premium_2": "400"}))
    assert good == []
    bad = auto_sum_to_total(_fields({"total_premium": "2500", "premium_1": "600", "premium_2": "400"}))
    assert bad and bad[0].code == "sum_to_total"


def test_auto_sum_to_total_ignores_count_totals():
    from insureflow.verification.arithmetic import auto_sum_to_total

    issues = auto_sum_to_total(_fields({"total_claims": "2", "claim_1": "1000", "claim_2": "2000"}))
    assert issues == []  # a count must not be summed against currency items


def test_cross_page_reconciliation():
    from insureflow.verification.arithmetic import cross_page_reconciliation

    assert cross_page_reconciliation({"net_income": [("page 1", "10000"), ("page 4", "10000")]}) == []
    issues = cross_page_reconciliation({"net_income": [("page 1", "10000"), ("page 4", "12500")]})
    assert issues and issues[0].code == "cross_page_reconciliation"
    assert "page 1" in issues[0].message and "page 4" in issues[0].message


def test_group_values_by_page():
    from insureflow.verification.arithmetic import group_values_by_page

    grouped = group_values_by_page({"total_incurred": [_field("total_incurred", "5000", page=2), _field("total_incurred", "4990", page=3)]})
    assert grouped["total_incurred"] == [("page 2", 5000.0), ("page 3", 4990.0)]


# ── 1b. Cross-field logic & conditional bounds ───────────────────────────────


def test_license_after_policy_start_flagged():
    from insureflow.verification.cross_field import chronological_dates

    issues = chronological_dates(_fields({"driver_license_issue_date": "2026-06-01", "effective_date": "2026-01-01"}))
    assert issues and issues[0].code == "date_order"


def test_expiration_before_effective_flagged():
    from insureflow.verification.cross_field import chronological_dates

    issues = chronological_dates(_fields({"effective_date": "2026-06-01", "expiration_date": "2026-01-01"}))
    assert issues and issues[0].code == "date_order"


def test_dates_in_order_clean():
    from insureflow.verification.cross_field import chronological_dates

    assert chronological_dates(_fields({"driver_license_issue_date": "2020-01-01", "effective_date": "2026-01-01", "expiration_date": "2027-01-01"})) == []


def test_payroll_without_employees_flagged():
    from insureflow.verification.cross_field import payroll_vs_headcount

    issues = payroll_vs_headcount(_fields({"annual_payroll": "5000000", "employees": "0"}))
    assert issues and issues[0].code == "payroll_without_employees"


def test_payroll_with_staff_clean():
    from insureflow.verification.cross_field import payroll_vs_headcount

    assert payroll_vs_headcount(_fields({"annual_payroll": "5000000", "employees": "40"})) == []


def test_small_home_huge_replacement_flagged():
    from insureflow.verification.cross_field import replacement_cost_vs_area

    issues = replacement_cost_vs_area(_fields({"square_footage": "1200", "replacement_cost": "15000000"}))
    assert issues and issues[0].code == "replacement_vs_area"


def test_large_property_high_value_clean():
    from insureflow.verification.cross_field import replacement_cost_vs_area

    assert replacement_cost_vs_area(_fields({"square_footage": "80000", "replacement_cost": "15000000"})) == []


def test_deductible_exceeds_limit_flagged():
    from insureflow.verification.cross_field import deductible_vs_limit

    issues = deductible_vs_limit(_fields({"deductible": "25000", "limit": "10000"}))
    assert issues and issues[0].code == "deductible_exceeds_limit"


def test_engine_runs_cross_field_and_self_consistency():
    from insureflow.verification.engine import VerificationEngine

    fields = {
        "total_incurred": [_field("total_incurred", "500000", page=1), _field("total_incurred", "120000", page=4)],
        "square_footage": [_field("square_footage", "1200")],
        "replacement_cost": [_field("replacement_cost", "15000000")],
    }
    report = VerificationEngine().run(fields, document_type="sov")
    assert "cross_field" in report.checks_run
    assert "self_consistency" in report.checks_run
    assert "cross_page" in report.checks_run
    assert any(i.code == "replacement_vs_area" for i in report.issues)
    assert any(i.code in {"epistemic_variance", "cross_page_reconciliation"} for i in report.issues)


def test_variance_from_extracted_fields_flags_disagreement():
    from insureflow.verification.uncertainty import uncertainty_issues, variance_from_extracted_fields

    fields = {"total_incurred": [_field("total_incurred", "1000"), _field("total_incurred", "5000")]}
    cv = variance_from_extracted_fields(fields)
    assert cv["total_incurred"] > 0.05
    issues = uncertainty_issues(cv)
    assert issues and issues[0].code == "epistemic_variance"


# ── 2. Guardrails: range / regex / schema ───────────────────────────────────


def test_range_checks_bounds():
    from insureflow.verification.guardrails import range_checks

    issues = range_checks(_fields({"credit_score": "900", "debt_to_income": "1.5"}))
    codes = {i.code for i in issues}
    assert "range_bound" in codes
    assert any("credit_score" in i.message for i in issues)
    assert any("debt_to_income" in i.message for i in issues)


def test_range_checks_negative_magnitude():
    from insureflow.verification.guardrails import range_checks

    issues = range_checks(_fields({"total_assets": "-500000"}))
    assert issues and issues[0].code == "negative_value"


def test_range_checks_clean():
    from insureflow.verification.guardrails import range_checks

    assert range_checks(_fields({"credit_score": "720", "debt_to_income": "0.3", "total_assets": "500000"})) == []


def test_pattern_checks_ein_and_ssn():
    from insureflow.verification.guardrails import pattern_checks

    assert pattern_checks(_fields({"ein": "95-1234567", "ssn": "123-45-6789"})) == []
    issues = pattern_checks(_fields({"ein": "95-12345O7"}))
    assert issues and issues[0].code == "ein_format"


def test_pattern_checks_aba_checksum():
    from insureflow.verification.guardrails import pattern_checks

    assert pattern_checks(_fields({"routing_number": "021000021"})) == []
    issues = pattern_checks(_fields({"routing_number": "021000022"}))
    assert issues and issues[0].code == "aba_checksum"


def test_pattern_checks_policy_number():
    from insureflow.verification.guardrails import pattern_checks

    assert pattern_checks(_fields({"policy_number": "GLC-8839201"})) == []
    issues = pattern_checks(_fields({"policy_number": "!!not a number!!"}))
    assert issues and issues[0].code == "policy_format"


def test_pattern_checks_impossible_slash_date():
    from insureflow.verification.guardrails import pattern_checks

    issues = pattern_checks(_fields({"policy_period_start": "02/30/2025"}))
    assert issues and issues[0].code == "date_format"


def test_schema_validation_types():
    from insureflow.verification.guardrails import schema_validation

    assert schema_validation(_fields({"total_claims": "3", "total_incurred": "500000", "loss_ratio": "0.42"})) == []
    codes = {i.code for i in schema_validation(_fields({"total_claims": "3.5", "total_incurred": "abc", "loss_ratio": "high"}))}
    assert codes == {"schema_type"}


def test_schema_validation_bad_date():
    from insureflow.verification.guardrails import schema_validation

    assert schema_validation(_fields({"policy_period_end": "2026-13-40"}))
    assert schema_validation(_fields({"policy_period_end": "2026-06-30"})) == []


# ── 3. Layout masking / spatial graph ───────────────────────────────────────


def test_detect_columns():
    from insureflow.ingestion.spatial_graph import detect_columns

    lines = {"a": [0.05, 0.1, 0.4, 0.12], "b": [0.5, 0.1, 0.9, 0.12]}
    assert len(detect_columns(lines)) == 2


def test_column_alignment_flags_merged_row(tmp_path):
    from insureflow.ingestion.spatial_graph import column_alignment_check

    spatial = {
        1: {
            "header col1": [0.05, 0.10, 0.40, 0.12],
            "header col2": [0.50, 0.10, 0.90, 0.12],
            "value col1": [0.05, 0.105, 0.40, 0.125],
            "value col2": [0.50, 0.105, 0.90, 0.125],
            "merged 1,200": [0.05, 0.108, 0.90, 0.128],  # spans both columns
        }
    }
    issues = column_alignment_check(spatial)
    assert issues and issues[0].code == "column_misalignment"
    assert issues[0].page_number == 1
    assert "merged 1,200" in issues[0].message


def test_column_alignment_single_column_clean():
    from insureflow.ingestion.spatial_graph import column_alignment_check

    spatial = {1: {"a": [0.1, 0.1, 0.9, 0.12], "b": [0.1, 0.15, 0.9, 0.17]}}
    assert column_alignment_check(spatial) == []


# ── 4. Semantic triangulation (footnote binding) ────────────────────────────


def test_triangulation_binds_modifier_footnote():
    from insureflow.verification.semantic_triangulation import triangulation_issues

    md = "| Building | Value |\n| --- | --- |\n| Warehouse | 4,000,000 [1] |\n\n[1] Excluding detached structures not on foundation."
    issues = triangulation_issues(md)
    assert any(i.code == "footnote_modifier" for i in issues)


def test_triangulation_dangling_marker():
    from insureflow.verification.semantic_triangulation import triangulation_issues

    md = "| A | B |\n| --- | --- |\n| 1 | 100 [9] |"
    issues = triangulation_issues(md)
    assert any(i.code == "dangling_footnote" for i in issues)


def test_triangulation_clean():
    from insureflow.verification.semantic_triangulation import triangulation_issues

    md = "| Item | Value |\n| --- | --- |\n| Equipment | 350,000 |"
    assert triangulation_issues(md) == []


# ── 5. Bayesian uncertainty calibration ─────────────────────────────────────


def test_uncertainty_deterministic_sampler_clean():
    from insureflow.verification.uncertainty import estimate_uncertainty, uncertainty_issues

    cv = estimate_uncertainty(lambda: {"total_incurred": 5000.0}, n_passes=3)
    assert cv["total_incurred"] == 0.0
    assert uncertainty_issues(cv) == []


def test_uncertainty_high_variance_flagged():
    from insureflow.verification.uncertainty import estimate_uncertainty, uncertainty_issues

    values = iter([4000.0, 6000.0, 3500.0, 6500.0, 5000.0])

    def jittered():
        return {"total_incurred": next(values)}

    cv = estimate_uncertainty(jittered, n_passes=5)
    assert cv["total_incurred"] > 0.05
    assert uncertainty_issues(cv)


# ── 6. Critic + dual-model consensus ────────────────────────────────────────


def test_critic_disabled_by_default(monkeypatch):
    monkeypatch.delenv("USE_CRITIC_REVIEW", raising=False)
    from insureflow.verification.critic import critic_enabled, critic_review

    assert critic_enabled() is False
    assert critic_review("text", _fields({"total": "1"}), llm=None) == []


class _FakeLLM:
    api_key = "test-key"

    def __init__(self, response):
        self.response = response

    def complete(self, prompt, **kwargs):
        return self.response


def test_critic_grounds_values(monkeypatch):
    monkeypatch.setenv("USE_CRITIC_REVIEW", "1")
    from insureflow.verification.critic import critic_review

    llm = _FakeLLM('{"verdicts": [{"field": "total", "grounded": true, "note": "ok"}]}')
    assert critic_review("Total: 1", _fields({"total": "1"}), llm) == []


def test_critic_flags_ungrounded(monkeypatch):
    monkeypatch.setenv("USE_CRITIC_REVIEW", "1")
    from insureflow.verification.critic import critic_review

    llm = _FakeLLM('```json\n{"verdicts": [{"field": "total", "grounded": false, "note": "not in source"}]}\n```')
    issues = critic_review("Nothing here", _fields({"total": "99999"}), llm)
    assert issues and issues[0].code == "critic_ungrounded"
    assert issues[0].severity == "error"


def test_dual_model_consensus_divergence():
    from insureflow.verification.critic import dual_model_consensus

    issues = dual_model_consensus(_fields({"total_incurred": "500000"}), _fields({"total_incurred": "575000"}), tolerance=0.05)
    assert issues and issues[0].code == "consensus_divergence"
    assert issues[0].severity == "error"


def test_dual_model_consensus_agrees():
    from insureflow.verification.critic import dual_model_consensus

    assert dual_model_consensus(_fields({"total_incurred": "500000"}), _fields({"total_incurred": "505000"}), tolerance=0.05) == []


# ── 7. External registry cross-referencing ──────────────────────────────────


def test_external_lookup_disabled_without_url(monkeypatch):
    monkeypatch.delenv("EXTERNAL_REGISTRY_API_URL", raising=False)
    monkeypatch.delenv("EXTERNAL_REGISTRY_API_KEY", raising=False)
    from insureflow.verification.external_lookup import external_lookup_enabled, lookup_entity

    assert external_lookup_enabled() is False
    assert lookup_entity("Acme Corp") is None


def test_external_lookup_rejects_non_https(monkeypatch):
    monkeypatch.setenv("EXTERNAL_REGISTRY_API_URL", "http://registry.insecure.local")
    from insureflow.verification.external_lookup import external_lookup_enabled

    assert external_lookup_enabled() is False


def test_external_lookup_matched(monkeypatch):
    import urllib.request

    monkeypatch.setenv("EXTERNAL_REGISTRY_API_URL", "https://registry.example.com")
    from insureflow.verification import external_lookup as el

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return json.dumps({"match": True}).encode()

    monkeypatch.setattr(urllib.request, "urlopen", lambda request, timeout=10: _Resp())
    result = el.lookup_entity("Acme Corp")
    assert result is not None and result.matched is True


def test_registry_verification_issues_unconfirmed(monkeypatch):
    monkeypatch.setenv("EXTERNAL_REGISTRY_API_URL", "https://registry.example.com")
    from insureflow.verification.external_lookup import RegistryLookup, registry_verification_issues

    issues = registry_verification_issues(
        _fields({"named_insured": "Acme Corp", "ein": "95-1234567"}),
        lookup=lambda name, addr, ein: RegistryLookup(matched=False, entity_name=name, message="no record"),
    )
    assert issues and issues[0].code == "registry_unconfirmed"


def test_registry_verification_disabled_returns_nothing(monkeypatch):
    monkeypatch.delenv("EXTERNAL_REGISTRY_API_URL", raising=False)
    from insureflow.verification.external_lookup import registry_verification_issues

    assert registry_verification_issues(_fields({"named_insured": "Acme Corp"})) == []


# ── 8. PDF forensics ────────────────────────────────────────────────────────


@pytest.mark.skipif(not HAS_PYMUPDF, reason="pymupdf not installed")
def test_inspect_pdf_generated():
    import fitz

    from insureflow.ingestion.forensics import inspect_pdf

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Loss run Pacific Coast. Incurred 500000.")
    pdf_bytes = doc.tobytes()
    doc.close()
    forensics = inspect_pdf(pdf_bytes)
    assert forensics is not None
    assert forensics.pages == 1


def test_inspect_pdf_garbage_bytes():
    from insureflow.ingestion.forensics import inspect_pdf

    assert inspect_pdf(b"not a pdf at all") is None


def test_tampering_issues_synthetic():
    from insureflow.ingestion.forensics import PdfForensics, tampering_issues

    forensics = PdfForensics(
        pages=3,
        non_embedded_fonts=["Helvetica"],
        full_page_image_pages=[2],
        producer="CutePDF Writer",
    )
    codes = {i.code for i in tampering_issues(forensics)}
    assert {"non_embedded_font", "rasterized_page", "unexpected_producer"} <= codes


def test_tampering_issues_clean():
    from insureflow.ingestion.forensics import PdfForensics, tampering_issues

    assert tampering_issues(PdfForensics(pages=1, producer="Adobe Acrobat")) == []


# ── 9. Aggregating engine ───────────────────────────────────────────────────


def test_engine_clean_document():
    from insureflow.verification.engine import VerificationEngine

    fields = _fields({"total_assets": "1000", "total_liabilities": "600", "total_equity": "400", "credit_score": "720"})
    report = VerificationEngine().run(fields, raw_text="clean", document_type="financial_statement")
    assert report.passed is True
    assert report.auto_approve is True
    assert {"balance_sheet", "sum_to_total", "range_checks", "pattern_checks", "schema_validation", "stp_gate"} <= set(report.checks_run)


def test_engine_flagged_on_arithmetic_error():
    from insureflow.verification.engine import VerificationEngine

    fields = _fields({"total_assets": "1000", "total_liabilities": "600", "total_equity": "200"})
    report = VerificationEngine().run(fields, document_type="financial_statement")
    assert report.passed is False
    assert report.flagged_for_review is True
    assert report.auto_approve is False
    assert any(i.code == "balance_sheet_identity" for i in report.errors)


def test_engine_stp_blocks_low_confidence_critical():
    from insureflow.verification.engine import VerificationEngine

    fields = {"total_incurred": [_field("total_incurred", "500000", confidence=0.82)]}
    report = VerificationEngine().run(fields, document_type="loss_run")
    assert any(i.code == "stp_block_low_confidence" for i in report.errors)


@pytest.mark.skipif(not HAS_PYMUPDF, reason="pymupdf not installed")
def test_engine_forensics_on_pdf_bytes():
    try:
        import fitz
    except ImportError:
        import pymupdf as fitz

    from insureflow.verification.engine import VerificationEngine

    doc = fitz.open()
    doc.new_page().insert_text((72, 100), "Balance sheet Assets 1000")
    pdf_bytes = doc.tobytes()
    doc.close()
    report = VerificationEngine().run(_fields({"total_assets": "1000"}), pdf_bytes=pdf_bytes)
    assert "forensics" in report.checks_run


def test_engine_disabled(monkeypatch):
    monkeypatch.setenv("USE_VERIFICATION", "0")
    from insureflow.verification.engine import VerificationEngine

    report = VerificationEngine().run(_fields({}), raw_text="x")
    assert report.passed is True
    assert report.auto_approve is True
    assert report.checks_run == ["verification_disabled"]


def test_verification_enabled_by_default(monkeypatch):
    monkeypatch.delenv("USE_VERIFICATION", raising=False)
    from insureflow.verification import verification_enabled

    assert verification_enabled() is True


def test_engine_critic_layer(monkeypatch):
    monkeypatch.setenv("USE_CRITIC_REVIEW", "1")
    from insureflow.verification.engine import VerificationEngine

    report = VerificationEngine(llm=_FakeLLM('{"verdicts": [{"field": "total_assets", "grounded": false}]}')).run(_fields({"total_assets": "999999"}), raw_text="no source")
    assert "critic" in report.checks_run
    assert any(i.code == "critic_ungrounded" for i in report.errors)


# ── 10. Loader integration ──────────────────────────────────────────────────


def test_loader_attaches_verification_report():
    from insureflow.ingestion.insurance.loader import InsuranceDocumentLoader

    bundle = InsuranceDocumentLoader().load_from_documents(
        [{"filename": "sov.csv", "content": "type,value\nBuilding,1000000\nEquipment,500000\n", "encoding": "utf-8"}],
        bundle_id="verify-integration",
    )
    sub = bundle.unstructured[0]
    assert sub.verification is not None
    assert sub.verification.checks_run


@pytest.mark.skipif(not HAS_PYMUPDF, reason="pymupdf not installed")
def test_loader_verification_on_pdf():
    import fitz

    from insureflow.ingestion.insurance.loader import InsuranceDocumentLoader

    doc = fitz.open()
    doc.new_page().insert_text((72, 100), "Loss run total incurred 500000")
    pdf_bytes = doc.tobytes()
    doc.close()

    bundle = InsuranceDocumentLoader().load_from_documents(
        [{"filename": "loss.pdf", "content": __import__("base64").b64encode(pdf_bytes).decode("ascii"), "encoding": "base64"}],
        bundle_id="verify-pdf",
    )
    sub = bundle.unstructured[0]
    assert sub.verification is not None
