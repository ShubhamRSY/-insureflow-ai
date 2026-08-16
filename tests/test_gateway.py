"""Tests for the bundled Rytera integration gateway."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from insureflow.api import app
from insureflow.config import settings

client = TestClient(app)
GATEWAY_KEY = settings.integration_gateway_api_key
AUTH = {"Authorization": f"Bearer {GATEWAY_KEY}"}


def test_gateway_health_requires_auth() -> None:
    resp = client.get("/integrations/oracles/clue/v2/health")
    assert resp.status_code == 401


def test_gateway_clue_health_ok() -> None:
    resp = client.get("/integrations/oracles/clue/v2/health", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["service"] == "clue"


def test_gateway_clue_query() -> None:
    resp = client.post(
        "/integrations/oracles/clue/v2/queries",
        headers=AUTH,
        json={"legal_name": "Pacific Marine LLC"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_claims_found"] >= 1


def test_gateway_ncci_experience() -> None:
    resp = client.post(
        "/integrations/oracles/ncci/v2/experience",
        headers=AUTH,
        json={"legal_name": "Pacific Marine LLC", "fein": "12-3456789"},
    )
    assert resp.status_code == 200
    assert resp.json()["experience_mods"]


def test_bundled_gateway_health_when_configured() -> None:
    from insureflow.gateway.health import bundled_gateway_health

    health = bundled_gateway_health(
        "http://127.0.0.1:8002/integrations/oracles/clue/v2",
        settings.integration_gateway_api_key,
    )
    assert health is not None
    assert health["reachable"] is True
    assert health.get("bundled") is True


def test_gateway_bureau_query() -> None:
    resp = client.post(
        "/integrations/oracles/bureau/v2/queries",
        headers=AUTH,
        json={"tax_id": "12-3456789", "legal_name": "Veririsk Construction"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["paydex_score"] == 35
    assert data["has_bankruptcy_indicator"] is True


def test_gateway_public_records_query() -> None:
    resp = client.post(
        "/integrations/oracles/public-records/v2/queries",
        headers=AUTH,
        json={"legal_name": "Veririsk Construction"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_bankruptcy"] is True
    assert data["total_judgment_amount"] == 125000


def test_gateway_osha_search() -> None:
    resp = client.post(
        "/integrations/oracles/osha/v1/searches",
        headers=AUTH,
        json={"legal_name": "Veririsk Construction"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["safety_rating"] == "critical"
    assert data["has_willful_violation"] is True


def test_gateway_rating_agency_query() -> None:
    resp = client.post(
        "/integrations/oracles/rating-agency/v2/entities",
        headers=AUTH,
        json={"legal_name": "Veririsk Construction"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["issuer_rating"] == "B"
    assert data["outlook"] == "negative"


def test_gateway_new_feeds_health_ok() -> None:
    expected = {
        "/integrations/oracles/bureau/v2/health": "bureau",
        "/integrations/oracles/public-records/v2/health": "public_records",
        "/integrations/oracles/osha/v1/health": "osha",
        "/integrations/oracles/rating-agency/v2/health": "rating_agency",
    }
    for path, service in expected.items():
        resp = client.get(path, headers=AUTH)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert resp.json()["service"] == service


def test_integration_health_service_feed_shape() -> None:
    from insureflow.integrations.health import IntegrationHealthService

    feeds = IntegrationHealthService().check_all()["feeds"]
    names = {f["name"] for f in feeds}
    assert "CLUE" in names
    assert "Credit Bureau" in names
    assert "Public Records" in names
    assert "OSHA" in names
    assert "Rating Agency" in names
    assert "Telematics" in names
    assert "Cyber Scan" in names
    assert all("mode" in f and "reachable" in f for f in feeds)


def test_landing_page_html() -> None:
    resp = client.get("/", headers={"Accept": "text/html"})
    assert resp.status_code == 200
    assert "Rytera" in resp.text
    assert "Stop hunting PDFs" in resp.text
    assert "Start underwriting" in resp.text
    assert "we know the pile" in resp.text.lower()
    assert "The messy file is the problem" in resp.text
    assert "bind-ready memo" in resp.text.lower() or "The memo" in resp.text
    assert "Their names never leave the gate" in resp.text
    assert "Trust. Buy. Profit." in resp.text
    assert "How we catch a wrong number" in resp.text
    assert "A photo can lie" in resp.text
    assert "The same ring, new letterhead" in resp.text
    assert "The questionnaire is not the car" in resp.text
    assert "EXIF / ELA" in resp.text
    assert "Pick the company. Then underwrite." in resp.text

    default = client.get("/")
    assert default.status_code == 200
    assert "text/html" in default.headers.get("content-type", "")

    api = client.get("/", headers={"Accept": "application/json"})
    assert api.status_code == 200
    assert api.json()["service"] == "Rytera"

    robots = client.get("/robots.txt")
    assert robots.status_code == 200
    assert "Sitemap:" in robots.text

    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200
    assert "ryterainc.com" in sitemap.text

    favicon = client.get("/favicon.ico")
    assert favicon.status_code == 200

    og = client.get("/og-image.png")
    assert og.status_code == 200
    assert og.headers.get("content-type", "").startswith("image/")


def test_landing_subpages_html() -> None:
    landing_pages = {
        "platform": ["Platform capabilities", "Human-in-the-loop by design", "Named insureds never leave the gate", "Choose the insurance company", "How we catch a wrong number", "A photo can lie", "EXIF / ELA"],
        "technology": ["Zero Token Architecture", "Every decision defensible", "Named insureds never leave the gate"],
        "underwriting": ["Built for the desks that decide", "Rates built like an actuary builds them", "Named insureds never leave the gate"],
        "integrations": ["Connects to the systems you already use", "Live, simulated, or auto", "Named insureds never leave the gate"],
        "company": ["About Rytera", "Frequently asked questions", "Named insureds never leave the gate"],
        "pricing": ["They will not buy if", "Your SERFF / carrier leaf filings", "no re-key", "Named insureds never leave the gate"],
    }
    for slug, markers in landing_pages.items():
        resp = client.get(f"/{slug}", headers={"Accept": "text/html"})
        assert resp.status_code == 200, f"/{slug} expected 200, got {resp.status_code}"
        assert "text/html" in resp.headers.get("content-type", "")
        for marker in markers:
            assert marker in resp.text, f"/{slug} missing {marker!r}"

    unknown = client.get("/not-a-page")
    assert unknown.status_code == 404


def test_landing_static_assets() -> None:
    css = client.get("/static/landing.css")
    assert css.status_code == 200
    assert "text/css" in css.headers.get("content-type", "")
    assert "--grad" in css.text

    js = client.get("/static/landing.js")
    assert js.status_code == 200
    assert "landing.js" in js.headers.get("content-type", "") or "javascript" in js.headers.get("content-type", "")
    assert "IntersectionObserver" in js.text

    pages = ["", "platform", "technology", "underwriting", "integrations", "company", "pricing"]
    for slug in pages:
        path = "/" if not slug else f"/{slug}"
        html = client.get(path).text
        assert "/static/landing.css" in html
        assert "/static/landing.js" in html


def test_landing_pages_reference_existing_anchors() -> None:
    pages = ["", "platform", "technology", "underwriting", "integrations", "company", "pricing"]
    for slug in pages:
        path = "/" if not slug else f"/{slug}"
        html = client.get(path).text
        ids = set()
        for m in re.finditer(r'id="([^"]+)"', html):
            ids.add(m.group(1))
        for href in re.findall(r'href="#([^"]+)"', html):
            assert href in ids, f"{path}: missing anchor #{href}"
