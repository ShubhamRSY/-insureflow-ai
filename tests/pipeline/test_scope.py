from __future__ import annotations

from pathlib import Path

import pytest

import scope
import sources

INBOX = Path(__file__).resolve().parents[2] / "simulation" / "inbox"


def doc(name: str, text: str, **kw: object) -> dict:
    return {"name": name, "text": text, **kw}


def codes(docs: list[dict]) -> list[str]:
    return scope.detect(docs)["reasons"] and [r["code"] for r in scope.detect(docs)["reasons"]]


@pytest.fixture(scope="module")
def sub233():
    return sources.read_folder(INBOX / "SUB-233")


def test_sub233_is_multiple_locations(sub233):
    result = scope.detect(sub233)
    assert result["in_scope"] is False
    assert [r["code"] for r in result["reasons"]] == ["multiple_locations"]
    assert result["version"] == scope.VERSION


def test_a_plain_typed_application_is_in_scope():
    docs = [
        doc("application.md", "Named Insured: Example LLC\nPremises: 100 Main St\nEffective Date: 2026-01-01\n"
                              "Construction: masonry\nYear Built: 1990\nOperations: office\nEmployees: 5\nSales: 100000\n"),
        doc("email.md", "Please quote the attached application. Thank you for the business."),
    ]
    assert scope.detect(docs) == {"version": scope.VERSION, "in_scope": True, "reasons": []}


def test_no_identifiable_application_is_manual_intake():
    docs = [doc("email.md", "Please see the attached file. Thanks.")]
    assert "not_identified" in codes(docs)


def test_a_scanned_application_is_manual_intake():
    docs = [doc("application.pdf", "Named Insured: Example LLC", needs_human=True, ocr_words={"application.pdf": []})]
    assert "scanned_application" in codes(docs)


def test_a_spanish_application_is_manual_intake():
    docs = [doc("solicitud.md", "Nombre del asegurado: Ejemplo LLC\nDireccion: Calle 1\nOperaciones: tienda\nLos empleados son cinco y las ventas son buenas para la tienda de la esquina.\n")]
    assert "non_english" in codes(docs)


def test_two_locations_on_a_schedule_are_manual_intake():
    docs = [
        doc("application.md", "Named Insured: Example LLC\nPremises: 100 Main St\nEffective Date: 2026-01-01\nConstruction: masonry\nOperations: office\n"),
        doc("schedule.csv", "location,address\n1,100 Main St\n2,200 Oak Ave\n"),
    ]
    assert "multiple_locations" in codes(docs)


def test_a_building_count_is_not_a_second_location():
    docs = [doc("application.md", "Named Insured: Example LLC\nPremises: 100 Main St\nNumber of buildings: 2\nEffective Date: 2026-01-01\nConstruction: masonry\nOperations: office\n")]
    assert "multiple_locations" not in codes(docs)


def test_reasons_text_is_empty_for_an_in_scope_file():
    assert scope.reasons_text({"version": scope.VERSION, "in_scope": True, "reasons": []}) == []


def test_reasons_text_names_each_reason():
    assert scope.reasons_text(scope.detect([doc("email.md", "Thanks.")])) == [scope.REASONS["not_identified"]]
