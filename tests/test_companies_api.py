"""Company pages API: login required to change anything, owner from the token, admin-only verification, fail-closed ownership."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from insureflow.api import companies
from insureflow.auth import Role
from insureflow.auth.dependencies import get_current_user
from insureflow.auth.models import TokenData

USER = {"who": None}


@pytest.fixture()
def client():
    companies._COMPANIES.clear()
    app = FastAPI()
    app.include_router(companies.router, prefix="/api")

    def fake_user() -> TokenData:
        if USER["who"] is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=401, detail="Not authenticated")
        name, role = USER["who"]
        return TokenData(username=name, role=role)

    app.dependency_overrides[get_current_user] = fake_user
    yield TestClient(app)
    companies._COMPANIES.clear()
    USER["who"] = None


def as_user(name: str | None, role: Role = Role.UNDERWRITER) -> None:
    USER["who"] = None if name is None else (name, role)


BODY = {"name": "Acme Mutual", "slug": "acme"}


def test_mutations_without_login_are_refused():
    companies._COMPANIES.clear()
    app = FastAPI()
    app.include_router(companies.router, prefix="/api")  # real dependency: no bearer token
    raw = TestClient(app)
    assert raw.post("/api/companies", json=BODY).status_code in (401, 403)
    companies._COMPANIES["acme"] = {"slug": "acme", "owner_id": "alice"}
    assert raw.put("/api/companies/acme", json={"about": "x"}).status_code in (401, 403)
    assert raw.delete("/api/companies/acme").status_code in (401, 403)
    assert raw.get("/api/companies/acme").status_code == 200  # reading stays public
    companies._COMPANIES.clear()


def test_owner_comes_from_the_signed_in_user(client):
    as_user("alice")
    r = client.post("/api/companies", json={**BODY, "owner_id": "mallory"})
    assert r.status_code == 201 and r.json()["owner_id"] == "alice"


def test_only_admin_sets_verified(client):
    as_user("alice")
    assert client.post("/api/companies", json={**BODY, "is_verified": True}).status_code == 403
    assert client.post("/api/companies", json=BODY).json()["is_verified"] is False
    assert client.put("/api/companies/acme", json={"is_verified": True}).status_code == 403
    as_user("root", Role.ADMIN)
    r = client.put("/api/companies/acme", json={"is_verified": True})
    assert r.status_code == 200 and r.json()["is_verified"] is True


def test_non_owner_cannot_edit_or_delete(client):
    as_user("alice")
    client.post("/api/companies", json=BODY)
    as_user("bob")
    assert client.put("/api/companies/acme", json={"about": "pwned"}).status_code == 403
    assert client.delete("/api/companies/acme").status_code == 403
    as_user("alice")
    assert client.put("/api/companies/acme", json={"about": "ours"}).status_code == 200
    assert client.delete("/api/companies/acme").status_code == 200


def test_ownerless_company_is_admin_only(client):
    companies._COMPANIES["orphan"] = {"slug": "orphan", "owner_id": None}
    as_user("bob")
    assert client.put("/api/companies/orphan", json={"about": "x"}).status_code == 403
    assert client.delete("/api/companies/orphan").status_code == 403
    as_user("root", Role.ADMIN)
    assert client.delete("/api/companies/orphan").status_code == 200
