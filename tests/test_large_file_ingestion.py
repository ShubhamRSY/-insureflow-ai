from __future__ import annotations

from unittest.mock import patch

from insureflow.ingestion.insurance.loader import InsuranceDocumentLoader
from insureflow.storage.object_storage import MAX_PROCESSABLE_BYTES


def test_oversized_s3_ref_document_is_flagged_not_downloaded() -> None:
    """A file that fits the upload cap (object_storage.MAX_UPLOAD_BYTES, 5GB)
    but exceeds the much lower auto-processing cap must never be pulled into
    this process's memory — that's the OOM risk this gate exists to close."""
    loader = InsuranceDocumentLoader()
    with (
        patch("insureflow.storage.object_storage.head_object", return_value={"size_bytes": 3_000_000_000, "content_type": "application/pdf"}),
        patch("insureflow.storage.object_storage.download_object_bytes") as mock_download,
    ):
        bundle = loader.load_from_documents(
            [{"filename": "huge.pdf", "content": "draft-uploads/org/bundle/huge.pdf", "encoding": "s3_ref"}],
            bundle_id="b1",
        )
    assert mock_download.called is False
    assert "too large to auto-process" in bundle.unstructured[0].raw_text


def test_processable_s3_ref_document_is_downloaded_and_parsed() -> None:
    loader = InsuranceDocumentLoader()
    with (
        patch("insureflow.storage.object_storage.head_object", return_value={"size_bytes": 100, "content_type": "text/plain"}),
        patch("insureflow.storage.object_storage.download_object_bytes", return_value=b"real extracted content") as mock_download,
    ):
        bundle = loader.load_from_documents(
            [{"filename": "small.txt", "content": "draft-uploads/org/bundle/small.txt", "encoding": "s3_ref"}],
            bundle_id="b1",
        )
    assert mock_download.called is True
    assert bundle.unstructured[0].raw_text == "real extracted content"


def test_file_right_at_the_processable_boundary_is_downloaded() -> None:
    loader = InsuranceDocumentLoader()
    with (
        patch("insureflow.storage.object_storage.head_object", return_value={"size_bytes": MAX_PROCESSABLE_BYTES, "content_type": "text/plain"}),
        patch("insureflow.storage.object_storage.download_object_bytes", return_value=b"ok") as mock_download,
    ):
        loader.load_from_documents(
            [{"filename": "boundary.txt", "content": "draft-uploads/org/bundle/boundary.txt", "encoding": "s3_ref"}],
            bundle_id="b1",
        )
    assert mock_download.called is True
