"""Document relevance validation for multi-file packages."""

from __future__ import annotations

from insureflow.ingestion.insurance.classifier import InsuranceDocumentClassifier, InsuranceDocumentType
from insureflow.insurance.relevance import score_document_relevance, validate_documents_relevance


def test_acord_xml_is_relevant():
    r = score_document_relevance(
        filename="submission.xml",
        content='<?xml version="1.0"?><ACORD xmlns="http://www.acord.org"><NamedInsured>Acme</NamedInsured></ACORD>',
    )
    assert r.relevant is True
    assert r.doc_type == InsuranceDocumentType.ACORD_XML.value


def test_menu_is_irrelevant():
    r = score_document_relevance(
        filename="dinner.txt",
        content="Restaurant menu\nCalories\nIngredients for pasta",
    )
    assert r.relevant is False
    assert r.doc_type == InsuranceDocumentType.IRRELEVANT.value


def test_validate_package_blocks_all_irrelevant():
    docs = [
        {"filename": "menu.txt", "content": "Restaurant menu with calories and ingredients", "encoding": "utf-8"},
        {"filename": "playlist.txt", "content": "Spotify playlist favorites", "encoding": "utf-8"},
    ]
    result = validate_documents_relevance(docs, vertical="insurance", strict=False)
    assert result["can_run"] is False
    assert result["irrelevant_count"] == 2


def test_validate_package_allows_mixed_with_relevant():
    docs = [
        {"filename": "menu.txt", "content": "Restaurant menu with calories", "encoding": "utf-8"},
        {
            "filename": "loss_run.md",
            "content": "Loss run\nClaim #123\nTotal incurred 50000\nDate of loss 2024-01-01",
            "encoding": "utf-8",
        },
    ]
    result = validate_documents_relevance(docs, vertical="insurance", strict=False)
    assert result["can_run"] is True
    assert result["relevant_count"] >= 1
    assert result["irrelevant_count"] >= 1


def test_classifier_marks_irrelevant():
    dtype = InsuranceDocumentClassifier.classify("Restaurant menu\nCalories\nIngredients", "menu.txt")
    assert dtype == InsuranceDocumentType.IRRELEVANT
