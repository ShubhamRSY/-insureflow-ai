"""Landing-page demo-request endpoint: honeypot field silently drops bot submissions."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from insureflow.api import app, main

client = TestClient(app)


@pytest.fixture(autouse=True)
def _isolate_leads_file(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("LEAD_NOTIFY_TO", "")
    return tmp_path / "data" / "demo_requests.jsonl"


def _payload(**overrides):
    body = {"name": "Alex Chen", "email": "alex@carrier.com", "company": "Meridian Mutual"}
    body.update(overrides)
    return body


def test_normal_submission_is_recorded(_isolate_leads_file):
    resp = client.post("/api/contact/demo-request", json=_payload())
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert _isolate_leads_file.exists()
    rows = _isolate_leads_file.read_text().strip().splitlines()
    assert len(rows) == 1
    assert json.loads(rows[0])["email"] == "alex@carrier.com"


def test_honeypot_filled_is_silently_dropped(_isolate_leads_file):
    resp = client.post("/api/contact/demo-request", json=_payload(website="http://spam.example"))
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert not _isolate_leads_file.exists()
