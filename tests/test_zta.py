from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from insureflow.agents.extraction_agent import ExtractionAgent
from insureflow.agents.supervisor import SupervisorAgent
from insureflow.api import app
from insureflow.ingestion.insurance.sources import load_package
from insureflow.insurance.pipeline import InsurancePipeline
from insureflow.zta.config import ZtaConfig
from insureflow.zta.models import RouteContext, RouteDecision, ZtaTask
from insureflow.zta.report import ZtaReporter, get_zta_stats
from insureflow.zta.router import ZeroTokenRouter, estimate_tokens

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "insurance"


def _router(**config_kwargs: object) -> ZeroTokenRouter:
    config = ZtaConfig()
    for k, v in config_kwargs.items():
        setattr(config, k, v)
    return ZeroTokenRouter(config=config)


class TestRouter:
    def test_structured_always_deterministic(self) -> None:
        r = ZeroTokenRouter()
        result = r.route(ZtaTask.EXTRACT_STRUCTURED, {})
        assert result.decision == RouteDecision.DETERMINISTIC

    def test_unstructured_good_coverage_deterministic(self) -> None:
        r = ZeroTokenRouter()
        result = r.route(
            ZtaTask.EXTRACT_UNSTRUCTURED,
            RouteContext(text="a" * 400, regex_field_count=7, doc_type="loss_run"),
        )
        assert result.decision == RouteDecision.DETERMINISTIC
        assert result.tokens_saved_est == 100

    def test_unstructured_low_coverage_uses_llm(self) -> None:
        r = ZeroTokenRouter()
        result = r.route(
            ZtaTask.EXTRACT_UNSTRUCTURED,
            RouteContext(text="a" * 400, regex_field_count=1, doc_type="loss_run"),
        )
        assert result.decision == RouteDecision.LLM
        assert r._llm_tasks_used == 1

    def test_unstructured_no_text_escalates(self) -> None:
        result = ZeroTokenRouter().route(ZtaTask.EXTRACT_UNSTRUCTURED, RouteContext(text=""))
        assert result.decision == RouteDecision.ESCALATE_HUMAN

    def test_reconcile_no_conflicts_deterministic(self) -> None:
        result = ZeroTokenRouter().route(ZtaTask.RECONCILE, RouteContext(conflict_count=0))
        assert result.decision == RouteDecision.DETERMINISTIC

    def test_reconcile_conflicts_use_llm(self) -> None:
        result = ZeroTokenRouter().route(ZtaTask.RECONCILE, RouteContext(conflict_count=3))
        assert result.decision == RouteDecision.LLM

    def test_score_with_required_features_deterministic(self) -> None:
        result = ZeroTokenRouter().route(ZtaTask.SCORE, RouteContext(required_features_present=True))
        assert result.decision == RouteDecision.DETERMINISTIC

    def test_score_missing_features_escalates(self) -> None:
        result = ZeroTokenRouter().route(
            ZtaTask.SCORE,
            RouteContext(required_features_present=False, missing_required=["Loss run"]),
        )
        assert result.decision == RouteDecision.ESCALATE_HUMAN

    def test_price_and_decide_deterministic(self) -> None:
        r = ZeroTokenRouter()
        assert r.route(ZtaTask.PRICE, {}).decision == RouteDecision.DETERMINISTIC
        assert r.route(ZtaTask.DECIDE, {}).decision == RouteDecision.DETERMINISTIC

    def test_memo_uses_llm_when_allowed(self) -> None:
        result = _router(memo_llm=True).route(ZtaTask.MEMO, {})
        assert result.decision == RouteDecision.LLM

    def test_memo_deterministic_when_llm_unavailable(self) -> None:
        r = ZeroTokenRouter(llm_available=False)
        result = r.route(ZtaTask.MEMO, {})
        assert result.decision == RouteDecision.DETERMINISTIC
        assert result.tokens_saved_est == 600

    def test_memo_deterministic_by_default(self) -> None:
        result = ZeroTokenRouter().route(ZtaTask.MEMO, {})
        assert result.decision == RouteDecision.DETERMINISTIC
        assert result.tokens_saved_est == 600

    def test_vision_skipped_when_llm_unavailable(self) -> None:
        r = ZeroTokenRouter(llm_available=False)
        result = r.route(ZtaTask.VISION, RouteContext(photo_count=2))
        assert result.decision == RouteDecision.SKIP

    def test_vision_uses_llm_when_available(self) -> None:
        result = ZeroTokenRouter().route(ZtaTask.VISION, RouteContext(photo_count=2))
        assert result.decision == RouteDecision.LLM

    def test_strict_mode_never_calls_llm(self) -> None:
        r = _router(enabled=True, strict=True)
        for task in (ZtaTask.EXTRACT_UNSTRUCTURED, ZtaTask.RECONCILE, ZtaTask.MEMO, ZtaTask.VISION):
            result = r.route(task, RouteContext(text="x" * 400, regex_field_count=0, conflict_count=2, photo_count=1))
            assert result.decision != RouteDecision.LLM
            assert result.decision in (RouteDecision.DETERMINISTIC, RouteDecision.ESCALATE_HUMAN, RouteDecision.SKIP)

    def test_llm_budget_enforced(self) -> None:
        r = _router(memo_llm=True)
        r.config.max_llm_tasks_per_job = 2
        assert r.route(ZtaTask.MEMO, {}).decision == RouteDecision.LLM
        assert r.route(ZtaTask.MEMO, {}).decision == RouteDecision.LLM
        # budget exhausted -> fall back to deterministic template memo, no more LLM calls
        assert r.route(ZtaTask.MEMO, {}).decision == RouteDecision.DETERMINISTIC
        assert r._llm_tasks_used == 2

    def test_dict_context_coerced(self) -> None:
        result = ZeroTokenRouter().route(ZtaTask.RECONCILE, {"conflict_count": 2})
        assert result.decision == RouteDecision.LLM

    def test_estimate_tokens(self) -> None:
        assert estimate_tokens(None) == 0
        assert estimate_tokens("") == 0
        assert estimate_tokens("a" * 100) == 25
        assert estimate_tokens("a") == 1


class TestReporter:
    def test_report_structure(self) -> None:
        r = ZeroTokenRouter(llm_available=False)
        rep = ZtaReporter(r)
        rep.route(ZtaTask.EXTRACT_STRUCTURED, {})
        rep.route(ZtaTask.MEMO, {})
        report = rep.report()
        assert report["mode"] in {"legacy", "zta", "strict"}
        assert report["totals"]["tasks"] == 2
        assert report["totals"]["deterministic"] == 2
        assert report["totals"]["llm"] == 0
        assert report["policy"]
        assert len(report["tasks"]) == 2

    def test_process_wide_accumulator(self) -> None:
        before = get_zta_stats()["jobs"]
        r = ZeroTokenRouter(llm_available=False)
        rep = ZtaReporter(r)
        rep.route(ZtaTask.EXTRACT_STRUCTURED, {})
        rep.report()
        assert get_zta_stats()["jobs"] == before + 1

    def test_reset_job_budget(self) -> None:
        r = _router(memo_llm=True)
        r.config.max_llm_tasks_per_job = 1
        assert r.route(ZtaTask.MEMO, {}).decision == RouteDecision.LLM
        r.reset_job()
        assert r.route(ZtaTask.MEMO, {}).decision == RouteDecision.LLM


class TestExtractionEnhance:
    def test_enhance_no_llm_returns_unchanged(self) -> None:
        agent = ExtractionAgent(llm_client=None)
        from insureflow.models.submissions import UnstructuredSubmission

        sub = UnstructuredSubmission(submission_id="doc-1", raw_text="no llm here")
        result = agent.enhance_unstructured(sub)
        assert result is sub
        assert result.extracted_fields == {}

    def test_extract_unstructured_returns_regex_based(self) -> None:
        agent = ExtractionAgent(llm_client=None)
        text = "Named Insured: Pacific Coast\nTIV: $4,350,000"
        result = agent.extract_unstructured(text, "b-1")
        assert result.submission_id == "b-1"
        assert result.raw_text == text


class TestSupervisorResolveWithLlm:
    def test_resolve_with_llm_false_avoids_llm(self) -> None:
        from insureflow.models.submissions import SubmissionBundle

        supervisor = SupervisorAgent(llm=ExtractionAgent().llm.__class__())  # has no api_key -> deterministic anyway
        memo = supervisor.analyze_submission(
            SubmissionBundle(bundle_id="b-llm"),
            parallel=True,
            use_celery=False,
            resolve_with_llm=False,
        )
        assert memo.bundle_id == "b-llm"


class TestPipelineIntegration:
    def test_pipeline_emits_zta_report(self) -> None:
        docs = load_package(EXAMPLES, "pacific-coast")
        pipe = InsurancePipeline(org_id="zta-test", use_llm=False)
        result = pipe.run(documents=docs, bundle_id="zta-pipe", skip_core_integration=True)
        assert result["zta_mode"] == "legacy"
        report = result["zta_report"]
        assert report["totals"]["tasks"] >= 6
        assert report["totals"]["deterministic"] >= 2
        tasks = {t["task"] for t in report["tasks"]}
        assert {"score", "price", "decide", "extract_unstructured"}.issubset(tasks)

    def test_pipeline_strict_mode_skips_vision(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ZTA_ENABLED", "1")
        monkeypatch.setenv("ZTA_STRICT", "1")
        docs = load_package(EXAMPLES, "pacific-coast")
        pipe = InsurancePipeline(org_id="zta-strict", use_llm=True)
        result = pipe.run(documents=docs, bundle_id="zta-strict", skip_core_integration=True)
        assert result["zta_mode"] == "strict"
        report = result["zta_report"]
        llm_tasks = [t for t in report["tasks"] if t["decision"] == "llm"]
        assert llm_tasks == []
        assert report["config"]["strict"] is True


class TestZtaApi:
    def test_status_endpoint(self) -> None:
        with TestClient(app) as client:
            resp = client.get("/api/zta/status")
            assert resp.status_code == 200
            body = resp.json()
            assert "config" in body
            assert body["config"]["mode"] in {"legacy", "zta", "strict"}

    def test_route_endpoint(self) -> None:
        with TestClient(app) as client:
            resp = client.post(
                "/api/zta/route",
                json={"task": "reconcile", "conflict_count": 2},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["route"]["task"] == "reconcile"
            assert body["route"]["decision"] == "llm"

    def test_route_endpoint_unknown_task(self) -> None:
        with TestClient(app) as client:
            resp = client.post("/api/zta/route", json={"task": "nope"})
            assert resp.status_code == 400

    def test_route_endpoint_unstructured(self) -> None:
        with TestClient(app) as client:
            resp = client.post(
                "/api/zta/route",
                json={
                    "task": "extract_unstructured",
                    "text": "a" * 400,
                    "regex_field_count": 6,
                    "doc_type": "loss_run",
                },
            )
            assert resp.status_code == 200
            assert resp.json()["route"]["decision"] == "deterministic"
