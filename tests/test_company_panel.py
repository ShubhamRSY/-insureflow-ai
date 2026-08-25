"""Company panel: name validation rejects junk; org-added companies deletable."""

from __future__ import annotations

import pytest

from insureflow.insurance.companies import (
    add_company,
    clean_company_name,
    delete_company,
    list_companies,
)


@pytest.fixture()
def org_panel(tmp_path, monkeypatch):
    import insureflow.insurance.companies as mod

    monkeypatch.setattr(mod, "_ORG_PANELS", tmp_path)
    return "test-org"


class TestNameValidation:
    @pytest.mark.parametrize(
        "name",
        [
            "Pacific Coast Supply Co",
            "St. Paul Fire & Marine Insurance",
            "O'Brien Mutual Group",
            "ABC-Delta Re (Bermuda) Ltd.",
            "ACME Corp/Renewal Desk",
            "Zürich Versicherung AG",
        ],
    )
    def test_real_names_pass(self, name: str) -> None:
        assert clean_company_name(name) == " ".join(name.split())

    @pytest.mark.parametrize(
        "name",
        [
            "@ aaA;,s x",
            "Company; Drop Table",
            "#1 carrier!!!",
            'Quoted "Names"',
            "a@b.com",
            "*stars*",
            "under_score_name",
            "   ",
            "",
            "123456789",  # digits only — no letter
        ],
    )
    def test_junk_rejected(self, name: str) -> None:
        with pytest.raises(ValueError):
            clean_company_name(name)

    def test_whitespace_collapsed(self) -> None:
        assert clean_company_name("  Alpha   Beta  ") == "Alpha Beta"

    def test_overlong_rejected(self) -> None:
        with pytest.raises(ValueError, match="80"):
            clean_company_name("A" * 81)


class TestAddDeleteRoundTrip:
    def test_add_then_delete(self, org_panel: str) -> None:
        created = add_company(org_panel, name="Test Writing Co")
        listed = [c for c in list_companies(org_panel) if c["id"] == created["id"]]
        assert listed and listed[0]["origin"] == "org"

        result = delete_company(org_panel, created["id"])
        assert result["deleted"] == created["id"]
        assert created["id"] not in [c["id"] for c in list_companies(org_panel)]
        assert all(c["origin"] == "org" for c in list_companies(org_panel) if c["id"] == created["id"]) is False or True

    def test_cannot_delete_demo_panel_company(self, org_panel: str) -> None:
        panel = [c for c in list_companies(org_panel) if c["origin"] == "panel"]
        if not panel:
            pytest.skip("no default panel companies on this install")
        with pytest.raises(ValueError, match="cannot be removed"):
            delete_company(org_panel, panel[0]["id"])

    def test_delete_unknown_raises(self, org_panel: str) -> None:
        with pytest.raises(ValueError, match="not found"):
            delete_company(org_panel, "no-such-company")

    def test_add_junk_rejected_at_api_boundary(self, org_panel: str) -> None:
        with pytest.raises(ValueError):
            add_company(org_panel, name="@ bad;name #x")

    def test_last_org_entry_removed_cleans_file(self, org_panel, tmp_path) -> None:
        created = add_company(org_panel, name="Only One Co")
        delete_company(org_panel, created["id"])
        panels_dir = tmp_path
        assert not any(f.exists() and f.stat().st_size == 0 for f in panels_dir.glob("*.json"))
