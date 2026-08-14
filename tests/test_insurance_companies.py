from __future__ import annotations

from insureflow.insurance.companies import add_company, list_companies, resolve_company


def test_default_panel_has_choice_of_companies() -> None:
    companies = list_companies("default")
    names = {c["name"] for c in companies}
    assert "InsureFlow Pilot Carrier" in names
    assert "Meridian Mutual" in names
    assert len(companies) >= 3


def test_resolve_known_company_by_id() -> None:
    company = resolve_company(company_id="meridian-mutual", org_id="default")
    assert company["id"] == "meridian-mutual"
    assert company["name"] == "Meridian Mutual"


def test_resolve_custom_name() -> None:
    company = resolve_company(company_name="Acme Specialty Ins", org_id="default")
    assert "Acme" in company["name"]
    assert company["id"]


def test_add_company_to_org_panel(tmp_path, monkeypatch) -> None:
    import insureflow.insurance.companies as companies_mod

    monkeypatch.setattr(companies_mod, "_ORG_PANELS", tmp_path)
    created = add_company("acme-org", name="Lakewood Mutual")
    assert created["id"] == "lakewood-mutual"
    names = {c["name"] for c in list_companies("acme-org")}
    assert "Lakewood Mutual" in names
    assert "Meridian Mutual" in names
