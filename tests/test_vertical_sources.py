"""Vertical-aware "Connect & pull": source listing, pulls, and bundle runs for
mortgage / lending that mirror the insurance source hub."""

from __future__ import annotations

from fastapi.testclient import TestClient

from insureflow.api import app
from insureflow.auth import Role
from insureflow.auth.jwt import create_access_token
from insureflow.auth.models import User
from insureflow.auth.store import clear_user_store, get_user_store

client = TestClient(app)


def _headers(role: Role = Role.VIEWER, org_id: str = "acme") -> dict[str, str]:
    clear_user_store()
    get_user_store()["uw"] = User(username="uw", hashed_password="x", role=role, org_id=org_id)
    token = create_access_token({"sub": "uw", "role": role.value, "org_id": org_id})
    return {"Authorization": f"Bearer {token}"}


def _demo_package_ids(vertical: str) -> set[str]:
    h = _headers()
    sources = client.get(f"/api/insurance/sources?vertical={vertical}", headers=h).json()["sources"]
    return {s["id"] for s in sources if s["category"] == "Demo Packages"}


def test_mortgage_sources_list_vertical_packages() -> None:
    h = _headers()
    sources = client.get("/api/insurance/sources?vertical=mortgage", headers=h).json()["sources"]
    ids = {s["id"] for s in sources}
    assert "johnson-residential" in ids
    assert "midwest-commercial" in ids
    # Insurance example packages must not leak into the mortgage hub
    assert "pacific-coast" not in ids
    # Enterprise connectors and the server folder remain available
    assert any(s["id"] == "google-drive" for s in sources)
    assert any(s["id"] == "server-folder" for s in sources)


def test_lending_sources_list_vertical_packages() -> None:
    h = _headers()
    sources = client.get("/api/insurance/sources?vertical=lending", headers=h).json()["sources"]
    ids = {s["id"] for s in sources}
    assert "blue-harbor-bakery" in ids
    assert "keller-logistics" in ids
    assert "pacific-coast" not in ids
    assert any(s["id"] == "sharepoint" for s in sources)


def test_insurance_sources_unchanged_by_vertical_flag() -> None:
    ids = _demo_package_ids("insurance")
    assert {"pacific-coast", "northwind"}.issubset(ids)
    assert "johnson-residential" not in ids


def test_mortgage_package_pull() -> None:
    h = _headers()
    resp = client.post(
        "/api/insurance/sources/johnson-residential/pull?vertical=mortgage",
        headers=h,
        json={},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["simulated"] is False
    assert data["file_count"] >= 3
    assert all(d["filename"] for d in data["documents"])
    assert all(d.get("content") for d in data["documents"])


def test_lending_package_pull() -> None:
    h = _headers()
    resp = client.post(
        "/api/insurance/sources/keller-logistics/pull?vertical=lending",
        headers=h,
        json={},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["file_count"] >= 5
    assert any("loan_application" in d["filename"] for d in data["documents"])


def test_insurance_package_not_available_in_mortgage() -> None:
    h = _headers()
    resp = client.post(
        "/api/insurance/sources/pacific-coast/pull?vertical=mortgage",
        headers=h,
        json={},
    )
    assert resp.status_code == 404


def test_demo_connector_pull_with_vertical_package() -> None:
    h = _headers()
    resp = client.post(
        "/api/insurance/sources/google-drive/pull?vertical=lending",
        headers=h,
        json={"package_id": "keller-logistics", "folder_id": "1x2y3z"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["simulated"] is True
    assert data["package_id"] == "keller-logistics"
    assert data["file_count"] >= 5


def test_demo_connector_requires_config() -> None:
    h = _headers()
    resp = client.post(
        "/api/insurance/sources/google-drive/pull?vertical=lending",
        headers=h,
        json={"package_id": "keller-logistics"},
    )
    assert resp.status_code == 400


def test_mortgage_bundle_run() -> None:
    h = _headers()
    bundle = client.post("/pipeline/bundles", headers=h, json={"name": "mort-connect"}).json()
    bundle_id = bundle["bundle_id"]
    pull = client.post(
        "/api/insurance/sources/johnson-residential/pull?vertical=mortgage",
        headers=h,
        json={"bundle_id": bundle_id},
    )
    assert pull.status_code == 200
    assert pull.json()["accumulated"]["document_count"] >= 3

    run = client.post(
        f"/pipeline/bundles/{bundle_id}/run?vertical=mortgage&use_llm=false",
        headers=h,
        json={},
    )
    assert run.status_code == 202
    data = run.json()
    assert data["vertical"] == "mortgage"
    assert data["status"] == "processing"
    assert data["job_id"].startswith("mort-")

    job = client.get(f"/mortgage/pipeline/jobs/{data['job_id']}", headers=h).json()
    assert job["status"] == "completed"
    assert job["results"]["product_line"] in ("residential_mortgage", "commercial_mortgage")


def test_lending_bundle_run() -> None:
    h = _headers()
    bundle = client.post("/pipeline/bundles", headers=h, json={"name": "lend-connect"}).json()
    bundle_id = bundle["bundle_id"]
    pull = client.post(
        "/api/insurance/sources/keller-logistics/pull?vertical=lending",
        headers=h,
        json={"bundle_id": bundle_id},
    )
    assert pull.status_code == 200

    run = client.post(
        f"/pipeline/bundles/{bundle_id}/run?vertical=lending",
        headers=h,
        json={},
    )
    assert run.status_code == 202
    data = run.json()
    assert data["vertical"] == "lending"
    assert data["documents_ingested"] >= 5
    assert data["result"]["decision"] in (
        "approved",
        "approved_with_conditions",
        "declined",
        "referred",
        "suspended",
    )


def test_bundle_run_defaults_to_insurance() -> None:
    h = _headers()
    bundle = client.post("/pipeline/bundles", headers=h, json={"name": "ins-connect"}).json()
    bundle_id = bundle["bundle_id"]
    client.post(
        "/api/insurance/sources/pacific-coast/pull",
        headers=h,
        json={"bundle_id": bundle_id},
    )
    run = client.post(f"/pipeline/bundles/{bundle_id}/run", headers=h, json={})
    assert run.status_code == 202
    data = run.json()
    assert data["job_id"].startswith("job-")
    assert "vertical" not in data
