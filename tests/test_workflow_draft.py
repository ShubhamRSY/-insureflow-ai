"""Natural-language workflow drafting."""

from __future__ import annotations

from fastapi.testclient import TestClient

from insureflow.api import app
from insureflow.auth import Role
from insureflow.auth.jwt import create_access_token
from insureflow.auth.models import User
from insureflow.auth.store import clear_user_store, get_user_store
from insureflow.workflow.draft import draft_workflow

client = TestClient(app)


def _headers(role: Role = Role.VIEWER, org_id: str = "acme") -> dict[str, str]:
    clear_user_store()
    get_user_store()["uw"] = User(username="uw", hashed_password="x", role=role, org_id=org_id)
    token = create_access_token({"sub": "uw", "role": role.value, "org_id": org_id})
    return {"Authorization": f"Bearer {token}"}


def test_draft_parses_when_if_then_and_sequence() -> None:
    prompt = "When a commercial property submission arrives, extract SOV, run CLUE, then price. If TIV > $10M then require co-sign. Then notify the broker."
    draft = draft_workflow(prompt)
    assert draft.draft_id.startswith("WD-")
    assert draft.triggers
    actions = [s.action for s in draft.steps]
    assert "extract" in actions
    assert "run_oracle" in actions
    assert "price" in actions
    assert "require_cosign" in actions
    assert "notify" in actions
    cosign = next(s for s in draft.steps if s.action == "require_cosign")
    assert "tiv" in cosign.condition
    assert cosign.metadata.get("value") == 10_000_000
    assert draft.compiled["entry"] == draft.steps[0].step_id


def test_draft_sanctions_and_sar_verbs() -> None:
    draft = draft_workflow("Screen OFAC sanctions then file SAR if hit, then refer to UW.")
    actions = {s.action for s in draft.steps}
    assert "sanctions_screen" in actions
    assert "file_sar" in actions or "refer" in actions


def test_empty_prompt_raises() -> None:
    import pytest

    with pytest.raises(ValueError, match="prompt"):
        draft_workflow("   ")


def test_workflow_draft_api() -> None:
    h = _headers()
    resp = client.post(
        "/workflow/draft",
        headers=h,
        json={"prompt": "When a WC submission arrives, run NCCI then price and bind.", "title": "WC desk"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "WC desk"
    assert any(s["action"] == "run_oracle" for s in body["steps"])
    assert any(s["action"] == "price" for s in body["steps"])

    bad = client.post("/workflow/draft", headers=h, json={"prompt": ""})
    assert bad.status_code == 400
