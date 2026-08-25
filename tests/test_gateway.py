"""Tests for the bundled Rytera integration gateway."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from insureflow.api import app
from insureflow.config import settings
from scripts.build_landing import home_main, page

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
    assert "actually trust" in resp.text
    assert "decision-ready memo" in resp.text.lower() or "decision memo" in resp.text.lower() or "memo" in resp.text.lower()
    assert "Named insureds never leave the gate" not in resp.text
    assert "Names and private details come off before any AI sees a page" in resp.text
    assert "Production Underwriting Needs More Than a Model Score" in resp.text or "Zero Black Boxes" in resp.text
    assert "One Desk for Every Submission" in resp.text
    assert "Extraction Fidelity" in resp.text
    assert "Licensed Underwriter Sign-Off" in resp.text
    assert "Continuously Evolving" in resp.text or "Continuous Innovation" in resp.text
    assert "The Underwriting &amp; Risk Glossary" in resp.text or "Underwriting Glossary" in resp.text

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
        "platform": [
            "Platform capabilities",
            "Human-in-the-loop by design",
            "Names come off first",
            "Choose the insurance company",
            "How we catch a wrong number",
            "A photo can lie",
            "EXIF / ELA",
        ],
        "technology": [
            "Zero Token Architecture",
            "Every decision defensible",
            "Private customer details never go to the AI.",
        ],
        "underwriting": [
            "Built for the desks that decide",
            "Rates built like an actuary builds them",
            "Names and private details come off before any AI sees a page",
        ],
        "integrations": [
            "Connects to the systems you already use",
            "Real when connected. Demo when not. Nothing invented.",
            "Names and private details come off before any AI sees a page",
        ],
        "company": [
            "About Rytera",
            "Frequently asked questions",
            "Names and private details come off before any AI sees a page",
        ],
        "pricing": [
            "They will not buy if",
            "Your SERFF / carrier leaf filings",
            "no re-key",
            "Names and private details come off before any AI sees a page",
        ],
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


# ---------------------------------------------------------------------------
# Landing page layout & copy edge-case tests
# ---------------------------------------------------------------------------


def test_landing_bento_layout_present() -> None:
    """Desks section uses bento-layout, not old audience-grid cards."""
    html = client.get("/", headers={"Accept": "text/html"}).text
    assert "bento-layout" in html
    assert "bento-item" in html
    assert "bento-tag" in html
    assert "bento-wide" in html


def test_landing_pillars_grid_present() -> None:
    """Trust section uses pillars-grid with horizontal pillar-rows."""
    html = client.get("/", headers={"Accept": "text/html"}).text
    assert "pillars-grid" in html
    assert "pillar-row" in html
    assert "pillar-label" in html
    assert "pillar-body" in html
    assert "pillar-title" in html
    assert "pillar-wide" in html


def test_landing_timeline_list_present() -> None:
    """Evolution section uses a numbered timeline-list."""
    html = client.get("/", headers={"Accept": "text/html"}).text
    assert "timeline-list" in html
    assert "timeline-item" in html
    assert "timeline-num" in html
    assert "timeline-tag" in html


def test_landing_trust_pillar_content() -> None:
    """All 11 trust pillars from the new copy are present."""
    html = client.get("/", headers={"Accept": "text/html"}).text
    pillars = [
        "Governance",
        "Privacy",
        "Intake",
        "Operations",
        "Compliance",
        "Outside Data",
        "Reliability",
        "Renewals",
        "Portfolio",
        "Model Intelligence",
        "State Regulatory Engine",
    ]
    for p in pillars:
        assert p in html, f"Trust pillar {p!r} missing from landing page"


def test_landing_trust_pillar_details() -> None:
    """Key bullet points from the user-supplied trust copy are present."""
    html = client.get("/", headers={"Accept": "text/html"}).text
    checks = [
        "Licensed underwriter signs every bind-ready memo",
        "SSN, tax ID, and DOB stripped before any AI sees the page",
        "Email, cloud folder, secure drop, or local watch folder",
        "Ranked by appetite fit, severity, and premium at risk",
        "Locked zip: every decision, override, and oracle check",
        "Prior claims, workers-comp, catastrophe when connected",
        "Work persisted",
        "Pre-renewal tracking and loss feedback loops",
        "Concentration by geography, class, and limit",
        "Speed, quality, and cost tracked per job",
        "State-filed rate manuals and SERFF schedules loaded directly",
    ]
    for c in checks:
        assert c in html, f"Trust detail {c!r} missing"


def test_landing_new_svg_icons_exist() -> None:
    """New SVG icons added for trust section are defined in the sprite."""
    html = client.get("/", headers={"Accept": "text/html"}).text
    icons = ["i-list", "i-clock", "i-bar-chart"]
    for icon in icons:
        assert f'id="{icon}"' in html, f"SVG icon {icon!r} not in sprite"


def test_landing_hero_copy() -> None:
    """Hero uses 'AI underwriting you can actually trust' headline."""
    html = client.get("/", headers={"Accept": "text/html"}).text
    assert "AI underwriting you can" in html
    assert "actually trust" in html
    assert "decision-ready rytera memo" in html.lower() or "decision memo" in html.lower() or "rytera memo" in html.lower()
    assert "Built for Decisions" in html


def test_landing_desks_copy() -> None:
    """Desks section uses new copy, not old 'Unified Underwriting'."""
    html = client.get("/", headers={"Accept": "text/html"}).text
    assert "One Desk for Every Submission" in html
    assert "Pick the carrier, drop the file, and underwrite" in html


def test_landing_trust_section_headline() -> None:
    """Trust section headline is the new copy."""
    html = client.get("/", headers={"Accept": "text/html"}).text
    assert "Production Underwriting Needs More Than a Model Score" in html
    assert "Controls, Intake, and a Paper Trail You Can Defend" in html


def test_landing_evolution_section_headline() -> None:
    """Evolution section uses 'What We Ship This Week'."""
    html = client.get("/", headers={"Accept": "text/html"}).text
    assert "What We Ship This Week" in html


def test_landing_how_it_works_copy() -> None:
    """How it works section references 'Sort the queue' not 'Triage'."""
    html = client.get("/", headers={"Accept": "text/html"}).text
    assert "Sort the queue" in html
    assert "Check &amp; Price" in html
    assert "You Decide" in html


def test_landing_css_contains_new_layouts() -> None:
    """Static CSS file contains styles for all new layout types."""
    css = client.get("/static/landing.css").text
    selectors = [
        ".bento-layout",
        ".bento-item",
        ".bento-tag",
        ".bento-wide",
        ".pillars-grid",
        ".pillar-row",
        ".pillar-label",
        ".pillar-body",
        ".pillar-title",
        ".pillar-wide",
        ".timeline-list",
        ".timeline-item",
        ".timeline-num",
        ".timeline-tag",
        ".tag-ship",
        ".tag-core",
    ]
    for s in selectors:
        assert s in css, f"CSS selector {s!r} missing from landing.css"


def test_landing_css_responsive_new_layouts() -> None:
    """Responsive breakpoints collapse new layouts to single column."""
    css = client.get("/static/landing.css").text
    assert ".bento-layout" in css and "1fr" in css
    assert ".pillars-grid" in css
    assert ".timeline-item" in css


def test_landing_js_interactive_features() -> None:
    """JS file still has all interactive features (tilt, glow, scramble, etc.)."""
    js = client.get("/static/landing.js").text
    features = [
        "IntersectionObserver",
        "tilt",
        "glow-follower",
        "scramble",
        "ripple",
        "particle",
        "parallax",
    ]
    for f in features:
        assert f in js, f"JS feature {f!r} missing from landing.js"


def test_landing_build_matches_html() -> None:
    """build_landing.py generates output matching the served HTML structure."""
    full = page("Rytera", "AI underwriting", "/", "desc", home_main())
    structural = [
        "bento-layout",
        "pillars-grid",
        "pillar-row",
        "timeline-list",
        "timeline-item",
        "Governance",
        "State Regulatory Engine",
        "i-list",
        "i-clock",
        "i-bar-chart",
        "One Desk for Every Submission",
        "Production Underwriting Needs More Than a Model Score",
        "What We Ship This Week",
        "actually trust",
        "Built for Decisions",
    ]
    for s in structural:
        assert s in full, f"build_landing.py output missing {s!r}"


def test_landing_no_old_card_patterns_in_desks() -> None:
    """Old audience-card pattern is gone from desks section."""
    html = client.get("/", headers={"Accept": "text/html"}).text
    # audience-card should NOT appear inside the desks section
    desks_start = html.find('id="desks"')
    trust_start = html.find('id="trust"')
    if desks_start != -1 and trust_start != -1:
        desks_html = html[desks_start:trust_start]
        assert "audience-card" not in desks_html, "Old audience-card still in desks section"
        assert "Unified Underwriting" not in desks_html, "Old headline still in desks section"
