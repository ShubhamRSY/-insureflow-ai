from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from insureflow.api import app
from insureflow.auth import Role
from insureflow.auth.dependencies import _USER_STORE
from insureflow.auth.jwt import create_access_token
from insureflow.auth.models import User
from insureflow.mortgage.pricing import LoanPricingEngine, LoanProduct
from insureflow.mortgage.webhooks import WebhookDispatcher
from insureflow.storage.encryption import EnvelopeEncryption
from insureflow.storage.job_store import MemoryJobStore


class TestEnvelopeEncryption:
    def test_round_trip_with_key(self) -> None:
        key = EnvelopeEncryption.generate_key()
        enc = EnvelopeEncryption(key)
        assert enc.enabled
        ciphertext = enc.encrypt_text("sensitive borrower data")
        assert ciphertext.startswith("ENC:v1:")
        assert enc.decrypt_text(ciphertext) == "sensitive borrower data"

    def test_no_key_passthrough(self) -> None:
        enc = EnvelopeEncryption("")
        assert not enc.enabled
        assert enc.encrypt_text("plain") == "plain"

    def test_json_round_trip(self, tmp_path: Path) -> None:
        key = EnvelopeEncryption.generate_key()
        enc = EnvelopeEncryption(key)
        payload = {"borrower": "Thompson", "ssn_last4": "1234"}
        path = tmp_path / "bundle.json"
        enc.write_encrypted_file(str(path), payload)
        loaded = enc.read_encrypted_file(str(path))
        assert loaded == payload


class TestJobStore:
    def test_org_isolation(self) -> None:
        store = MemoryJobStore()
        store.set("mortgage", "job-a", {"status": "completed"}, org_id="bank-a")
        store.set("mortgage", "job-a", {"status": "failed"}, org_id="bank-b")
        assert store.get("mortgage", "job-a", org_id="bank-a")["status"] == "completed"
        assert store.get("mortgage", "job-a", org_id="bank-b")["status"] == "failed"
        assert store.get("mortgage", "job-a", org_id="bank-c") is None

    def test_list_ids_scoped_by_org(self) -> None:
        store = MemoryJobStore()
        store.set("mortgage", "j1", {"status": "processing"}, org_id="org-1")
        store.set("mortgage", "j2", {"status": "processing"}, org_id="org-1")
        store.set("mortgage", "j3", {"status": "processing"}, org_id="org-2")
        assert sorted(store.list_ids("mortgage", org_id="org-1")) == ["j1", "j2"]
        assert store.list_ids("mortgage", org_id="org-2") == ["j3"]


class TestLoanPricing:
    def test_quote_returns_rate_lock(self) -> None:
        from insureflow.models.mortgage import MortgageBundle, MortgageDecision, MortgageMemo, ProductLine

        engine = LoanPricingEngine()
        bundle = MortgageBundle(bundle_id="test", product_line=ProductLine.RESIDENTIAL_MORTGAGE)
        memo = MortgageMemo(
            bundle_id="test",
            product_line=ProductLine.RESIDENTIAL_MORTGAGE,
            borrower_name="John Thompson",
            decision=MortgageDecision.APPROVE,
            risk_score=0.72,
            dti_ratio=35.0,
            ltv_ratio=80.0,
        )
        quote = engine.quote(bundle, memo, loan_amount=400_000, product=LoanProduct.CONVENTIONAL_30_FIXED)
        assert quote.adjusted_rate > 0
        assert quote.rate_lock_expires
        assert quote.monthly_pi > 0


class TestWebhooks:
    def test_register_and_dispatch(self) -> None:
        dispatcher = WebhookDispatcher()
        sub = dispatcher.register("test-org", "http://localhost/hook", secret="test-secret")

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
            results = dispatcher.dispatch("mortgage.completed", "test-org", {"job_id": "abc"})
            assert len(results) == 1
            assert results[0]["status"] == "delivered"
            mock_open.assert_called_once()

        assert dispatcher.unregister(sub.subscription_id, "test-org")
        assert dispatcher.list_for_org("test-org") == []


class TestMortgageAPIIntegration:
    @pytest.fixture(autouse=True)
    def reset_users(self) -> None:
        _USER_STORE.clear()

    def _auth_headers(self, org_id: str = "acme-bank", role: Role = Role.ADMIN) -> dict[str, str]:
        _USER_STORE["admin"] = User(
            username="admin",
            hashed_password="unused",
            role=role,
            org_id=org_id,
        )
        token = create_access_token({"sub": "admin", "role": role.value, "org_id": org_id})
        return {"Authorization": f"Bearer {token}"}

    def test_login_includes_org_in_me(self) -> None:
        client = TestClient(app)
        headers = self._auth_headers("first-national")
        resp = client.get("/auth/me", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["org_id"] == "first-national"

    def test_org_scoped_jobs(self) -> None:
        client = TestClient(app)
        headers = self._auth_headers("bank-a")

        resp = client.post(
            "/mortgage/pipeline/run",
            json={"directory": "simulated_documents/home_mortgage", "use_llm": False, "per_borrower": False},
            headers=headers,
        )
        assert resp.status_code == 202
        job_id = resp.json()["job_id"]
        assert resp.json()["org_id"] == "bank-a"

        _USER_STORE["other"] = User(
            username="other",
            hashed_password="unused",
            role=Role.ADMIN,
            org_id="bank-b",
        )
        token_b = create_access_token({"sub": "other", "role": "admin", "org_id": "bank-b"})
        assert (
            client.get(
                f"/mortgage/pipeline/jobs/{job_id}",
                headers={"Authorization": f"Bearer {token_b}"},
            ).status_code
            == 404
        )

    def test_webhook_registration(self) -> None:
        client = TestClient(app)
        headers = self._auth_headers()
        resp = client.post(
            "/mortgage/webhooks",
            json={"url": "https://example.com/hook", "events": ["mortgage.completed"]},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["org_id"] == "acme-bank"
        assert "subscription_id" in data

    def test_loan_products_endpoint(self) -> None:
        client = TestClient(app)
        headers = self._auth_headers()
        resp = client.get("/mortgage/products", headers=headers)
        assert resp.status_code == 200
        products = resp.json()["products"]
        assert len(products) >= 7
        assert any(p["id"] == "conventional_30_fixed" for p in products)

    def test_dashboard_served(self) -> None:
        client = TestClient(app)
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert "InsureFlow" in resp.text
