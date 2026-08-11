"""Hardening: durable stores, lending ingest, ML real-data path."""

from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch


def test_file_job_store_survives_reload(tmp_path: Path) -> None:
    from insureflow.storage.file_job_store import FileJobStore

    store = FileJobStore(tmp_path / "jobs")
    store.set("insurance", "job-1", {"status": "completed", "x": 1}, org_id="org-a")
    got = store.get("insurance", "job-1", org_id="org-a")
    assert got is not None
    assert got["x"] == 1

    store2 = FileJobStore(tmp_path / "jobs")
    got2 = store2.get("insurance", "job-1", org_id="org-a")
    assert got2 is not None
    assert got2["status"] == "completed"
    assert "job-1" in store2.list_ids("insurance", org_id="org-a")


def test_job_store_auto_falls_back_to_file_not_memory(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
    monkeypatch.setenv("JOB_STORE_BACKEND", "auto")
    monkeypatch.setenv("BANK_MODE", "false")
    monkeypatch.setenv("ENVIRONMENT", "development")

    # Force new store instance
    import insureflow.storage.job_store as js

    store = js.get_job_store()
    assert store.__class__.__name__ == "FileJobStore"
    store.set("t", "a", {"ok": True})
    assert (tmp_path / "data" / "job_store").exists()


def test_portfolio_store_persists(tmp_path: Path) -> None:
    from insureflow.portfolio.store import PortfolioPolicy, PortfolioStore

    path = tmp_path / "policies.json"
    store = PortfolioStore(path=path)
    store.add_policy(
        PortfolioPolicy(
            policy_id="p1",
            bundle_id="b1",
            insured_name="Acme",
            state="TX",
            naics_code="531120",
            tiv=1_000_000,
        )
    )
    store2 = PortfolioStore(path=path)
    assert any(p.policy_id == "p1" for p in store2.list_policies())


def test_portfolio_records_producer_name(tmp_path: Path) -> None:
    from insureflow.portfolio.store import PortfolioPolicy, PortfolioStore

    path = tmp_path / "policies.json"
    store = PortfolioStore(path=path)
    store.add_policy(
        PortfolioPolicy(
            policy_id="p1",
            bundle_id="b1",
            insured_name="Acme",
            producer_name="Acme Brokerage",
            state="TX",
            naics_code="531120",
            tiv=1_000_000,
        )
    )
    policy = next(p for p in store.list_policies() if p.policy_id == "p1")
    assert policy.producer_name == "Acme Brokerage"


def test_portfolio_record_loss_development_feeds_feedback_loop(tmp_path: Path) -> None:
    from insureflow.portfolio.store import PortfolioPolicy, PortfolioStore

    path = tmp_path / "policies.json"
    store = PortfolioStore(path=path)
    store.add_policy(
        PortfolioPolicy(
            policy_id="p1",
            bundle_id="b1",
            insured_name="Acme",
            state="TX",
            naics_code="531120",
            tiv=1_000_000,
            premium=10_000,
            risk_score=0.75,
        )
    )

    recorded = store.record_loss_development("p1", incurred_loss=9_000, experience_periods=1.0)
    assert recorded is not None
    assert recorded.incurred_loss == 9_000
    assert recorded.loss_data_available is True

    reloaded = PortfolioStore(path=path)
    policy = next(p for p in reloaded.list_policies() if p.policy_id == "p1")
    assert policy.incurred_loss == 9_000
    assert policy.loss_data_available is True

    assert store.record_loss_development("missing", incurred_loss=1.0) is None


def test_ml_load_training_csv(tmp_path: Path) -> None:
    from insureflow.ml.features import DEFAULT_FEATURE_NAMES
    from insureflow.ml.training import load_training_csv

    cols = DEFAULT_FEATURE_NAMES + ["target"]
    row = ",".join(["1.0"] * len(DEFAULT_FEATURE_NAMES) + ["42.0"])
    path = tmp_path / "loss_prediction.csv"
    path.write_text(",".join(cols) + "\n" + row + "\n", encoding="utf-8")
    X, y, meta = load_training_csv(path)
    assert X.shape == (1, len(DEFAULT_FEATURE_NAMES))
    assert y[0] == 42.0
    assert meta["source"] == "csv"


def test_lending_document_ingest_builds_application(tmp_path: Path) -> None:
    from insureflow.ingestion.lending import application_from_documents, load_lending_documents_from_directory
    from insureflow.lending import LendingPipeline
    from insureflow.lending.models import LoanDecision

    pkg = tmp_path / "app"
    pkg.mkdir()
    (pkg / "loan_application.txt").write_text(
        "Business Name: Riverside Widgets LLC\n"
        "Industry: Manufacturing\n"
        "Annual Revenue: $2,500,000\n"
        "Net Income: $180,000\n"
        "EBITDA: $320,000\n"
        "Debt Service: $90,000\n"
        "Loan Amount: $250,000\n"
        "Years in Business: 8\n",
        encoding="utf-8",
    )
    docs = load_lending_documents_from_directory(pkg)
    assert len(docs) == 1
    app = application_from_documents(docs)
    from insureflow.lending.models import BusinessLoanApplication

    assert isinstance(app, BusinessLoanApplication)
    assert "Riverside" in app.business_name
    assert app.requested_amount == 250_000
    assert app.financials[0].annual_revenue == 2_500_000

    result = LendingPipeline().run(
        app,
        documents=[{"filename": d.filename, "content": d.content} for d in docs],
        require_documents=True,
    )
    assert result.decision != LoanDecision.SUSPENDED
    assert result.document_count == 1


def test_lending_missing_financials_refers() -> None:
    from insureflow.lending import LendingPipeline
    from insureflow.lending.models import BusinessFinancialData, BusinessLoanApplication, LoanDecision

    app = BusinessLoanApplication(
        business_name="Empty Co",
        requested_amount=100_000,
        requested_term_months=12,
        financials=[BusinessFinancialData()],
    )
    result = LendingPipeline().run(app)
    assert result.decision == LoanDecision.REFERRED
    assert result.human_review_required is True
