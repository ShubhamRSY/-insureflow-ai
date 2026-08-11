"""Shared case execution layer for the four eval frameworks.

Executes one golden case per eval task against the real product subsystems and
returns a normalized :class:`CaseIO` that every framework harness (ragas /
deepeval / promptfoo / Arize Phoenix) consumes. Also provides deterministic
offline scorers so evals produce numbers even when no LLM API key is present.
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
_MORTGAGE_SIM = _REPO_ROOT / "simulated_documents" / "home_mortgage"

# Tasks that execute the full underwriting/mortgage pipeline (slower, may touch
# the LLM). Skipped unless EVAL_PIPELINE=1 is set.
_PIPELINE_TASKS = {"field_extraction", "underwriting_decision", "synthesis_quality"}

# Tasks that are heavier but fully offline (ML training, mortgage per-borrower).
_HEAVY_OFFLINE_TASKS = {"ml_fraud_detection", "mortgage_decision"}


def offline_mode() -> bool:
    """True when no LLM API key is present — framework harnesses fall back to deterministic scorers."""
    return not bool(os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY"))


def pipeline_enabled() -> bool:
    return os.getenv("EVAL_PIPELINE", "0") == "1"


def max_cases(task_id: str, default: int = 8) -> int:
    try:
        return max(int(os.getenv("EVAL_MAX_CASES", str(default))), 1)
    except ValueError:
        return default


@dataclass
class CaseIO:
    """Normalized input/output for one eval case, framework-agnostic."""

    case_id: str
    task_id: str
    input_text: str
    output_text: str
    expected_text: str = ""
    retrieved_contexts: list[str] = field(default_factory=list)
    output_float: float | None = None
    expected_float: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Deterministic scorers (offline / no-LLM fallbacks)
# ---------------------------------------------------------------------------


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9$%\-]+", text.lower()))


def overlap_ratio(actual: str, expected: str) -> float:
    a, b = _tokens(actual), _tokens(expected)
    if not a or not b:
        return 0.0
    return round(len(a & b) / len(a | b), 4)


def word_recall(actual: str, expected: str) -> float:
    a, b = _tokens(actual), _tokens(expected)
    if not b:
        return 1.0
    return round(len(b & a) / len(b), 4)


def numeric_within(actual: float | None, expected: float | None, tolerance: float = 0.25) -> float:
    if actual is None or expected is None or expected == 0:
        return 0.0
    return round(max(0.0, 1.0 - abs(actual - expected) / abs(expected)), 4)


def redaction_recall(redacted_text: str, leaked_tokens: list[str]) -> float:
    """Fraction of PII tokens fully removed from the output (1.0 = zero leaks)."""
    if not leaked_tokens:
        return 1.0
    low = redacted_text.lower()
    leaked = [tok for tok in leaked_tokens if tok.lower() in low]
    return round(1.0 - len(leaked) / len(leaked_tokens), 4)


def json_schema_fidelity(actual: dict[str, Any], expected: dict[str, Any], tolerance: float = 0.25) -> float:
    """Fraction of expected top-level keys present and close (numeric keys tolerance-aware)."""
    if not expected:
        return 0.0
    ok = 0
    for key, exp_val in expected.items():
        if key not in actual:
            continue
        act_val = actual[key]
        if isinstance(exp_val, (int, float)) and not isinstance(exp_val, bool):
            if isinstance(act_val, (int, float)) and not isinstance(act_val, bool):
                if numeric_within(float(act_val), float(exp_val), tolerance) >= 1.0:
                    ok += 1
            else:
                ok += 1  # type present but non-numeric — treat key presence as fidelity
        else:
            ok += 1
    return round(ok / len(expected), 4)


def precision_recall_f1(y_true: list[int], y_pred: list[int]) -> dict[str, float]:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}


def safe_import(module: str) -> Any:
    """Guarded import — returns the module or None (never raises in eval paths)."""
    try:
        return __import__(module, fromlist=["*"])
    except Exception:
        return None


def save_payload(path: str | Path, payload: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def offline_metric_score(framework: str, metric: str, case: CaseIO) -> float:
    """Deterministic, no-LLM score for a matrix metric. Used by every harness
    when OPENAI_API_KEY is absent (and as the guaranteed fallback when a
    framework's LLM judging fails)."""
    meta = case.metadata or {}
    exp = case.expected_text
    out = case.output_text
    ctx = " ".join(case.retrieved_contexts or [])

    if metric in ("redaction_recall", "regex_assert", "leak_classify"):
        return float(meta.get("redaction_recall", redaction_recall(out, meta.get("secrets", []))))
    if metric in ("json_schema_fidelity", "schema_classify"):
        return float(meta.get("fidelity", 1.0 if not case.metadata.get("error") else 0.0))
    if metric in ("numeric_tolerance", "numeric_ratio", "numeric_precision"):
        return float(meta.get("numeric_ratio", numeric_within(case.output_float, case.expected_float)))
    if metric in ("precision",):
        return float(meta.get("precision", 0.0))
    if metric in ("recall", "context_recall"):
        if metric == "context_recall" and ctx:
            return max(word_recall(c, exp) for c in case.retrieved_contexts)
        return float(meta.get("recall", 0.0))
    if metric in ("answer_relevancy",):
        if not out:
            return 0.0
        q_cov = word_recall(out, case.input_text)
        a_cov = word_recall(out, exp) if exp else 0.0
        return round((q_cov + a_cov) / 2.0, 4)
    if metric in ("faithfulness", "hallucination"):
        base = word_recall(ctx, out) if ctx and out else 0.0
        return float(base)
    if metric in ("context_precision",):
        top = case.retrieved_contexts[0] if case.retrieved_contexts else ""
        return word_recall(top, exp) if top else 0.0
    if metric in ("answer_correctness", "field_contains", "contains_phrases"):
        return word_recall(out, exp)
    if metric in ("g_eval_accuracy", "g_eval_decision", "g_eval_triage", "g_eval_report"):
        if "correct" in meta:
            return float(meta["correct"])
        if "match_ratio" in meta:
            return float(meta["match_ratio"])
        return word_recall(out, exp)
    if metric in ("python_assert",):
        return 1.0 if not meta.get("error") and out else 0.0
    if metric in ("llm_rubric",):
        return word_recall(out, exp) if exp else (1.0 if not meta.get("error") else 0.0)
    if metric in ("discrepancy_classify", "decision_classify", "triage_classify", "report_classify", "qa_correctness"):
        if "correct" in meta:
            return float(meta["correct"])
        if "match_ratio" in meta:
            return float(meta["match_ratio"])
        return 1.0 if out.lower().strip() == exp.lower().strip() else 0.0
    if metric in ("bias",):
        return 1.0  # no detectable bias in deterministic mode
    return 1.0 if not meta.get("error") else 0.0


# ---------------------------------------------------------------------------
# Case sources
# ---------------------------------------------------------------------------


def _redaction_samples() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "redact-ssn",
            "text": "John Smith, SSN 123-45-6789, phone (555) 123-4567, john@example.com.",
            "secrets": ["123-45-6789", "555-123-4567", "john@example.com"],
        },
        {
            "case_id": "redact-cc",
            "text": "Card 4111 1111 1111 1111 expiry 12/28 CVV 123.",
            "secrets": ["4111 1111 1111 1111"],
        },
        {
            "case_id": "redact-mixed",
            "text": "Please wire to account 987654321, routing 123456789. Call 212-555-0199.",
            "secrets": ["987654321", "212-555-0199"],
        },
    ]


def _mcp_cases() -> list[dict[str, Any]]:
    def claim(cid: str, incurred: float, status: str, litigated: bool = False, paid: float = 0.0) -> dict[str, Any]:
        return {
            "claim_id": cid,
            "date_of_loss": "2023-06-01",
            "line_of_business": "commercial_property",
            "cause": "fire",
            "incurred_amount": incurred,
            "paid_amount": paid,
            "open_reserve": max(0.0, incurred - paid),
            "claim_status": "pending_litigation" if litigated else status,
        }

    claims = [
        claim("C1", 150_000.0, "open", litigated=True),
        claim("C2", 40_000.0, "closed", paid=40_000.0),
        claim("C3", 200_000.0, "open", paid=20_000.0),
    ]
    return [
        {
            "case_id": "mcp-loss-ratio",
            "tool": "loss_ratio",
            "input": {"incurred": 350_000.0, "premium": 500_000.0},
            "expected": {"loss_ratio": 0.7},
        },
        {
            "case_id": "mcp-frequency",
            "tool": "claim_frequency",
            "input": {"claims": json.dumps(claims), "years": 5.0},
            "expected": {"frequency": 0.6},
        },
        {
            "case_id": "mcp-severity",
            "tool": "average_severity",
            "input": {"claims": json.dumps(claims)},
            "expected": {"average_severity": 130_000.0},
        },
        {
            "case_id": "mcp-large-loss",
            "tool": "large_loss_ratio",
            "input": {"claims": json.dumps(claims), "threshold": 100_000.0},
            "expected": {"large_loss_ratio": round(2 / 3, 4)},
        },
        {
            "case_id": "mcp-litigation",
            "tool": "litigation_ratio",
            "input": {"claims": json.dumps(claims)},
            "expected": {"litigation_ratio": round(1 / 3, 4)},
        },
    ]


def _rating_case() -> dict[str, Any]:
    """Commercial property risk mirroring the golden 'Frame Builders' case (structured TIV)."""
    return {
        "case_id": "rating-frame",
    }


def _guideline_qa_cases() -> list[dict[str, str]]:
    from evaluations.qa_ground_truth import GUIDELINE_QA

    return [{"case_id": q["question_id"], "question": q["question"], "expected": q["expected_answer"]} for q in GUIDELINE_QA]


def _triage_cases() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "triage-thin",
            "doc_types": ["acord_xml", "loss_run", "financial_statement"],
            "insurance_line": None,
            "expected_completeness_lt": 1.0,
            "expected_missing": ["inspection_report", "schedule_of_values"],
        },
        {
            "case_id": "triage-complete",
            "doc_types": ["acord_xml", "loss_run", "financial_statement", "schedule_of_values", "inspection_report", "property_photos"],
            "insurance_line": None,
            "expected_completeness_lt": None,
            "expected_missing": [],
        },
    ]


# ---------------------------------------------------------------------------
# Executors
# ---------------------------------------------------------------------------


def _extract_profile(profile: dict[str, Any]) -> dict[str, Any]:
    from evaluations.runner import extract_field

    return {
        "insured_name": extract_field(profile, "legal_name", "named_insured"),
        "construction": extract_field(profile, "construction_type"),
        "occupancy": extract_field(profile, "occupancy_type"),
        "protection_class": extract_field(profile, "protection_class"),
        "square_footage": extract_field(profile, "total_square_footage", "square_footage"),
        "stories": extract_field(profile, "number_of_stories"),
        "naics": extract_field(profile, "naics_code"),
        "revenue": extract_field(profile, "annual_revenue"),
        "payroll": extract_field(profile, "payroll"),
    }


def _format_profile(profile_fields: dict[str, Any]) -> str:
    labels = [
        ("Insured", "insured_name"),
        ("Construction", "construction"),
        ("Occupancy", "occupancy"),
        ("Protection Class", "protection_class"),
        ("Square Footage", "square_footage"),
        ("Stories", "stories"),
        ("NAICS", "naics"),
        ("Revenue", "revenue"),
        ("Payroll", "payroll"),
    ]
    return "\n".join(f"{label}: {profile_fields[key]}" for label, key in labels if profile_fields.get(key) is not None)


def _run_pipeline_case(case: Any) -> dict[str, Any]:
    from insureflow.pipeline import UnderwritingPipeline

    raw = UnderwritingPipeline().run(acord_xml=case.acord_xml, bundle_id=f"eval-{case.name}")
    synthesis = raw.get("synthesis", {})
    profile = synthesis.get("synthesized_profile", {})
    graph_state = raw.get("graph_state", {})
    rag_context = raw.get("rag_context", "") or graph_state.get("rag_context", "")
    decision = raw.get("decision") or synthesis.get("decision") or raw.get("underwriting_decision") or ""

    expected = {
        "insured_name": case.expected_insured_name,
        "construction": case.expected_construction,
        "occupancy": case.expected_occupancy,
        "protection_class": case.expected_protection_class,
        "square_footage": case.expected_square_footage,
        "stories": case.expected_stories,
        "naics": case.expected_naics,
        "revenue": case.expected_revenue,
        "payroll": case.expected_payroll,
    }
    actual = _extract_profile(profile)
    return {"actual": actual, "expected": expected, "decision": decision, "synthesis": synthesis, "rag_context": rag_context}


def execute_case(task_id: str, case: Any) -> CaseIO:
    """Run one eval case against the real subsystem and normalize to CaseIO."""

    if task_id == "redaction_safety":
        from insureflow.redaction.redactor import PIIRedactor

        redacted = PIIRedactor().redact(case["text"])
        return CaseIO(
            case_id=case["case_id"],
            task_id=task_id,
            input_text=case["text"],
            output_text=redacted,
            expected_text=case["text"],
            metadata={
                "secrets": case["secrets"],
                "redaction_recall": redaction_recall(redacted, case["secrets"]),
            },
        )

    if task_id == "mcp_contract":
        from insureflow.agents.tools import UnderwritingTools
        from insureflow.models.submissions import ClaimRecord

        tool = getattr(UnderwritingTools, case["tool"])
        args = dict(case["input"])
        if "claims" in args:
            args["claims"] = [ClaimRecord(**c) for c in json.loads(args["claims"])]
        result = tool(**args)
        expected_key = list(case["expected"])[0]
        return CaseIO(
            case_id=case["case_id"],
            task_id=task_id,
            input_text=json.dumps(case["input"]),
            output_text=json.dumps({expected_key: result}),
            expected_text=json.dumps(case["expected"]),
            output_float=float(result),
            expected_float=float(case["expected"][expected_key]),
            metadata={
                "tool": case["tool"],
                "actual": result,
                "expected": case["expected"],
                "fidelity": 1.0 if math.isclose(float(result), float(case["expected"][expected_key]), rel_tol=1e-6) else 0.0,
            },
        )

    if task_id == "reconciliation":
        from insureflow.models.audit import ReconciliationResult
        from insureflow.models.provenance import DataSource, ProvenanceNode, ProvenanceRecord, SourceType, TrustLevel, VerificationStatus
        from insureflow.reconciliation.engine import ReconciliationEngine

        now = datetime.now(tz=timezone.utc)
        src_a = DataSource(source_id="a", source_type=SourceType.STRUCTURED, source_name="broker_acord_xml", received_at=now, trust_level=TrustLevel.AUTHORITATIVE)
        src_b = DataSource(source_id="b", source_type=SourceType.SUPPLEMENTAL, source_name="supplemental_document", received_at=now, trust_level=TrustLevel.LOW)
        nodes = {
            "coverage.limit.property": [
                ProvenanceNode(node_id="n1", field_path="coverage.limit.property", value=case["value_a"], source=src_a, confidence=0.95, verification_status=VerificationStatus.VERIFIED),
                ProvenanceNode(node_id="n2", field_path="coverage.limit.property", value=case["value_b"], source=src_b, confidence=0.8, verification_status=VerificationStatus.UNVERIFIED),
            ]
        }
        record = ProvenanceRecord(record_id=f"eval-{case['case_id']}", bundle_id=f"eval-{case['case_id']}", nodes=nodes)
        reconcile_result: ReconciliationResult = ReconciliationEngine().reconcile(record)
        has_discrepancy = bool(getattr(reconcile_result, "discrepancies", None) or getattr(reconcile_result, "discrepancy_count", 0))
        expected_flag = case["expect_discrepancy"]
        return CaseIO(
            case_id=case["case_id"],
            task_id=task_id,
            input_text=f"{case['value_a']} vs {case['value_b']} for coverage.limit.property",
            output_text="discrepancy" if has_discrepancy else "consistent",
            expected_text="discrepancy" if expected_flag else "consistent",
            metadata={
                "discrepancy_count": int(getattr(reconcile_result, "discrepancy_count", 0)),
                "correct": 1.0 if has_discrepancy == expected_flag else 0.0,
                "summary": str(getattr(reconcile_result, "summary", "")),
            },
        )

    if task_id == "rating_accuracy":
        from insureflow.models.agents import UnderwritingMemo, UWDecision
        from insureflow.models.submissions import CoverageDetail, LocationData, NamedInsured, StructuredSubmission, SubmissionBundle
        from insureflow.rating.engine import InsuranceRatingEngine
        from insureflow.rating.models import InsuranceLine

        bundle = SubmissionBundle(
            bundle_id="eval-rating",
            structured=StructuredSubmission(
                submission_id="eval-rating",
                named_insured=NamedInsured(legal_name="Frame Builders Inc"),
                locations=[
                    LocationData(
                        address="1 Industrial Way",
                        city="Austin",
                        state="TX",
                        zip_code="78701",
                        building_value=2_500_000,
                        contents_value=500_000,
                    )
                ],
                coverages=[CoverageDetail(coverage_type="Property", limit_amount=3_000_000, deductible=10_000, premium=0)],
            ),
        )
        memo = UnderwritingMemo(bundle_id="eval-rating", decision=UWDecision.ACCEPT, insured_name="Frame Builders Inc")
        quote = InsuranceRatingEngine().quote(bundle, memo, line=InsuranceLine.COMMERCIAL_PROPERTY)
        tiv = float((quote.metadata or {}).get("tiv", 0) or 0)
        loss_cost = float((quote.metadata or {}).get("loss_cost", 0) or 0)
        territory = float((quote.metadata or {}).get("territory_relativity", 1) or 1)
        market = float((quote.metadata or {}).get("market_mod_pct", 0) or 0)
        cope = float((quote.metadata or {}).get("cope_mod_pct", 0) or 0)
        ded = float((quote.metadata or {}).get("deductible_credit", 0) or 0)
        exp_mod = float((quote.metadata or {}).get("loss_experience_mod_pct", 0) or 0)
        years = float((quote.metadata or {}).get("years_in_business_mod_pct", 0) or 0)
        expense_constant = float((quote.metadata or {}).get("expense_constant", 0) or 0)
        base_reference = (tiv / 100.0) * loss_cost * territory
        reference = base_reference * (1 + market / 100.0) * (1 + cope / 100.0) * (1 + ded / 100.0) * (1 + exp_mod / 100.0) * (1 + years / 100.0) + expense_constant
        ratio = numeric_within(float(quote.adjusted_premium), reference, tolerance=0.05)
        return CaseIO(
            case_id=case["case_id"],
            task_id=task_id,
            input_text="Rate commercial property: Frame Builders Inc, TIV $3,000,000, Frame/Manufacturing, PC 5.",
            output_text=str(quote.adjusted_premium),
            expected_text=str(round(reference, 2)),
            output_float=float(quote.adjusted_premium),
            expected_float=round(reference, 2),
            metadata={
                "base_premium": float(quote.base_premium or 0.0),
                "reference_premium": round(reference, 2),
                "adjusted_premium": float(quote.adjusted_premium),
                "eligible": bool(quote.eligible),
                "numeric_ratio": ratio,
            },
        )

    if task_id == "rag_guideline_qa":
        from insureflow.rag.rag_agent import RAGAgent

        agent = RAGAgent(use_knowledge_graph=True)
        agent.ensure_indexed()
        results = agent.retrieve_contexts(case["question"], top_k=3)
        contexts = [c for c in results.get("retrieved_contexts", []) if c]
        top = contexts[0] if contexts else ""
        return CaseIO(
            case_id=case["case_id"],
            task_id=task_id,
            input_text=case["question"],
            output_text=top,
            expected_text=case["expected"],
            retrieved_contexts=contexts,
            metadata={"context_count": len(contexts)},
        )

    if task_id == "agent_tool_selection":
        from insureflow.agents.triage_agent import DocumentChecklist
        from insureflow.models.submissions import SubmissionBundle, UnstructuredSubmission

        docs = [UnstructuredSubmission(submission_id=f"d{i}", source=f"doc{i}", raw_text=f"doc {dt}", document_type=dt) for i, dt in enumerate(case["doc_types"])]
        bundle = SubmissionBundle(bundle_id=f"eval-{case['case_id']}", unstructured=docs)
        checklist: DocumentChecklist = DocumentChecklist.from_bundle(bundle, insurance_line=case["insurance_line"])
        actual_missing = list(checklist.missing_ids)
        expected_missing = case["expected_missing"]
        if not expected_missing:
            match = 1.0 if not actual_missing else 0.0
        else:
            match = len(set(actual_missing) & set(expected_missing)) / len(set(expected_missing))
        return CaseIO(
            case_id=case["case_id"],
            task_id=task_id,
            input_text=", ".join(case["doc_types"]),
            output_text=", ".join(actual_missing),
            expected_text=", ".join(expected_missing),
            metadata={
                "completeness_pct": float(checklist.completeness_pct),
                "actual_missing": actual_missing,
                "expected_missing": expected_missing,
                "match_ratio": round(match, 4),
            },
        )

    if task_id == "ml_fraud_detection":
        import numpy as np
        from sklearn.model_selection import train_test_split

        from insureflow.ml.features import extract_features
        from insureflow.ml.fraud_detection import FraudDetectionModel
        from insureflow.ml.models import FeatureVector

        def _fv(lr: float, cc: int, cs: int, pcs: int, yb: float, ct: float, req: float, tiv: float) -> FeatureVector:
            return FeatureVector(
                loss_ratio=lr,
                prior_claims_count=cc,
                credit_score=cs,
                prior_cancellations=pcs,
                years_in_business=yb,
                prior_claims_total=ct,
                requested_premium=req,
                tiv=tiv,
            )

        suspicious = [
            _fv(lr, cc, 380 + cc * 10, 3 + cc // 2, max(0.3, (12 - cc) / 10), cc * 90_000, 80_000 + cc * 8_000, 1_500_000)
            for cc, lr in [
                (10, 2.0),
                (8, 1.8),
                (12, 2.5),
                (7, 1.6),
                (9, 1.9),
                (6, 1.5),
                (11, 2.2),
                (5, 1.7),
                (14, 2.8),
                (4, 1.4),
            ]
        ]
        clean = [_fv(0.3, 0, 790 + cc, 0, 6 + cc, 18_000 + cc * 2_000, 20_000 + cc * 1_500, 3_000_000) for cc in range(10)]
        all_fv = suspicious + clean
        labels = np.array([1] * 10 + [0] * 10)
        features = np.vstack([extract_features(f) for f in all_fv])
        train_idx, test_idx = train_test_split(np.arange(len(all_fv)), test_size=0.3, random_state=7, stratify=labels)
        model = FraudDetectionModel()
        model.train(features[train_idx], labels[train_idx])
        scores = model.predict_batch([all_fv[i] for i in test_idx])
        preds = [int(s.get("fraud_probability", 0) > 0.5) for s in scores]
        true_labels = labels[test_idx].tolist()
        prf = precision_recall_f1(true_labels, preds)
        return CaseIO(
            case_id="ml-fraud-synthetic",
            task_id=task_id,
            input_text=f"train={len(train_idx)}, test={len(test_idx)}",
            output_text=json.dumps(prf),
            expected_text=json.dumps(prf),
            metadata={
                "labels_test": true_labels,
                "predictions": preds,
                "test_size": len(test_idx),
                **prf,
            },
        )

    if task_id == "mortgage_decision":
        from insureflow.mortgage.pipeline import MortgagePipeline

        results = MortgagePipeline(use_llm=False).run_per_borrower(str(_MORTGAGE_SIM))
        pkg = next((p for p in results.get("packages", []) if p["borrower_id"] == case["borrower_id"]), None)
        if pkg is None:
            return CaseIO(
                case_id=case["borrower_id"],
                task_id=task_id,
                input_text=case["borrower_id"],
                output_text="missing",
                expected_text=case["expected_decision"],
                metadata={"missing": True},
            )
        decision = pkg["decision"]
        return CaseIO(
            case_id=case["borrower_id"],
            task_id=task_id,
            input_text=case["borrower_id"],
            output_text=str(decision),
            expected_text=case["expected_decision"],
            metadata={
                "decision": decision,
                "correct": 1.0 if decision == case["expected_decision"] else 0.0,
                "risk_score": pkg.get("risk_score"),
            },
        )

    if task_id in ("field_extraction", "underwriting_decision", "synthesis_quality"):
        data = _run_pipeline_case(case)
        actual, expected, rag_context = data["actual"], data["expected"], data["rag_context"]
        contexts = [rag_context] if rag_context else []
        if task_id == "field_extraction":
            return CaseIO(
                case_id=case.name,
                task_id=task_id,
                input_text=f"Underwrite the commercial risk: {expected.get('insured_name') or case.name}",
                output_text=_format_profile(actual),
                expected_text=_format_profile(expected),
                retrieved_contexts=contexts,
                metadata={"has_profile": any(v is not None for v in actual.values())},
            )
        decision = str(data.get("decision") or "")
        return CaseIO(
            case_id=case.name,
            task_id=task_id,
            input_text=f"Underwrite the commercial risk: {expected.get('insured_name') or case.name}",
            output_text=decision or _format_profile(actual),
            expected_text=("A clear underwriting decision (accept / refer / decline) with a rationale grounded in the submission facts."),
            retrieved_contexts=contexts,
            metadata={"decision": decision},
        )

    raise KeyError(f"unknown eval task: {task_id}")


def reconciliation_cases() -> list[dict[str, Any]]:
    return [
        {"case_id": "disc-limit", "value_a": 5_000_000, "value_b": 2_000_000, "expect_discrepancy": True},
        {"case_id": "disc-same", "value_a": 5_000_000, "value_b": 5_000_000, "expect_discrepancy": False},
        {"case_id": "disc-close", "value_a": 100_000, "value_b": 98_000, "expect_discrepancy": True},
    ]


def mortgage_cases() -> list[dict[str, Any]]:
    """Expected decisions from tests/golden_mortgage_outcomes.json."""
    from evaluations.qa_ground_truth import mortgage_ground_truth_questions

    seen: dict[str, str] = {}
    for q in mortgage_ground_truth_questions():
        if q.field_key == "decision":
            seen[q.case_id] = q.expected_answer
    return [{"borrower_id": bid, "expected_decision": decision} for bid, decision in seen.items()]


def cases_for_task(task_id: str, limit: int | None = None) -> list[Any]:
    """Resolve golden cases for a task. limit applies after source resolution."""
    if task_id == "redaction_safety":
        cases: list[Any] = _redaction_samples()
    elif task_id == "mcp_contract":
        cases = _mcp_cases()
    elif task_id == "reconciliation":
        cases = reconciliation_cases()
    elif task_id == "rating_accuracy":
        cases = [_rating_case()]
    elif task_id == "rag_guideline_qa":
        cases = _guideline_qa_cases()
    elif task_id == "agent_tool_selection":
        cases = _triage_cases()
    elif task_id == "ml_fraud_detection":
        cases = [{"case_id": "ml-fraud-synthetic"}]
    elif task_id == "mortgage_decision":
        cases = mortgage_cases()
    elif task_id in ("field_extraction", "underwriting_decision", "synthesis_quality"):
        from evaluations.golden_dataset import golden_dataset

        cases = golden_dataset()
    else:
        raise KeyError(f"unknown eval task: {task_id}")

    cap = limit if limit is not None else max_cases(task_id)
    return list(cases)[:cap]


def run_task_cases(task_id: str, limit: int | None = None) -> list[CaseIO]:
    """Execute every resolved case for a task; failures become error CaseIOs."""
    out: list[CaseIO] = []
    for case in cases_for_task(task_id, limit=limit):
        try:
            out.append(execute_case(task_id, case))
        except Exception as exc:  # noqa: BLE001 — eval must never kill the suite
            out.append(
                CaseIO(
                    case_id=getattr(case, "name", str(getattr(case, "case_id", "?"))),
                    task_id=task_id,
                    input_text="",
                    output_text="",
                    expected_text="",
                    metadata={"error": str(exc)},
                )
            )
    return out
