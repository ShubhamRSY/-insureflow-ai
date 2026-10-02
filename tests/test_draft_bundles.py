from __future__ import annotations

import base64
import threading
import time
from unittest.mock import patch

import pytest

from insureflow.storage.draft_bundle_store import (
    MAX_BUNDLE_TOTAL_BYTES,
    MAX_DOCUMENT_BYTES,
    BundleTooLargeError,
    DraftBundleStore,
)
from insureflow.storage.job_store import MemoryJobStore


def _make_store() -> DraftBundleStore:
    return DraftBundleStore(MemoryJobStore())


def test_create_bundle() -> None:
    store = _make_store()
    bundle = store.create(org_id="test-org", name="Test submission")
    assert bundle["bundle_id"].startswith("draft-")
    assert bundle["name"] == "Test submission"
    assert bundle["status"] == "assembling"
    assert bundle["documents"] == []


def test_get_bundle() -> None:
    store = _make_store()
    bundle = store.create(org_id="test")
    fetched = store.get(bundle["bundle_id"], org_id="test")
    assert fetched is not None
    assert fetched["bundle_id"] == bundle["bundle_id"]


def test_get_missing_bundle() -> None:
    store = _make_store()
    assert store.get("draft-nonexistent") is None


def test_add_documents() -> None:
    store = _make_store()
    bundle = store.create(org_id="test")
    docs = [
        {"filename": "acord.xml", "content": "<xml/>", "encoding": "utf-8"},
        {"filename": "loss_run.md", "content": "# Loss Run", "encoding": "utf-8"},
    ]
    result = store.add_documents(bundle["bundle_id"], docs, source_id="email-inbox", connection_label="Email", org_id="test")
    assert result is not None
    assert len(result["documents"]) == 2
    assert result["documents"][0]["source_id"] == "email-inbox"
    assert result["documents"][0]["doc_id"].startswith("doc-")
    assert result["documents"][0]["filename"] == "acord.xml"


def test_add_documents_accumulates() -> None:
    store = _make_store()
    bundle = store.create(org_id="test")
    store.add_documents(bundle["bundle_id"], [{"filename": "a.xml", "content": "<a/>", "encoding": "utf-8"}], org_id="test")
    store.add_documents(
        bundle["bundle_id"],
        [{"filename": "b.md", "content": "# b", "encoding": "utf-8"}],
        source_id="s3",
        org_id="test",
    )
    result = store.get(bundle["bundle_id"], org_id="test")
    assert result is not None
    assert len(result["documents"]) == 2
    assert result["documents"][0]["source_id"] == ""
    assert result["documents"][1]["source_id"] == "s3"


def test_remove_document() -> None:
    store = _make_store()
    bundle = store.create(org_id="test")
    store.add_documents(
        bundle["bundle_id"],
        [{"filename": "a.xml", "content": "<a/>", "encoding": "utf-8"}, {"filename": "b.md", "content": "# b", "encoding": "utf-8"}],
        org_id="test",
    )
    full = store.get(bundle["bundle_id"], org_id="test")
    assert full is not None
    doc_id = full["documents"][0]["doc_id"]
    result = store.remove_document(bundle["bundle_id"], doc_id, org_id="test")
    assert result is not None
    assert len(result["documents"]) == 1
    assert result["documents"][0]["filename"] == "b.md"


def test_delete_bundle() -> None:
    store = _make_store()
    bundle = store.create(org_id="test")
    assert store.delete(bundle["bundle_id"], org_id="test") is True
    assert store.get(bundle["bundle_id"], org_id="test") is None


def test_list_all() -> None:
    store = _make_store()
    store.create(org_id="test", name="First")
    store.create(org_id="test", name="Second")
    bundles = store.list_all(org_id="test")
    assert len(bundles) == 2


def test_to_pipeline_documents() -> None:
    store = _make_store()
    bundle = store.create(org_id="test")
    store.add_documents(
        bundle["bundle_id"],
        [
            {"filename": "acord.xml", "content": "<xml/>", "encoding": "utf-8"},
            {"filename": "loss.md", "content": "# Loss", "encoding": "utf-8"},
        ],
        org_id="test",
    )
    docs = store.to_pipeline_documents(bundle["bundle_id"], org_id="test")
    assert len(docs) == 2
    assert docs[0]["filename"] == "acord.xml"
    assert "content" in docs[0]
    # Should not include metadata fields
    assert "doc_id" not in docs[0]
    assert "source_id" not in docs[0]


def test_file_tree_groups_by_source_and_directory() -> None:
    store = _make_store()
    bundle = store.create(org_id="test")
    store.add_documents(
        bundle["bundle_id"],
        [
            {"filename": "acord.xml", "path": "pacific-coast/acord.xml", "directory": "pacific-coast", "content": "<xml/>", "encoding": "utf-8"},
            {"filename": "loss.md", "path": "pacific-coast/loss.md", "directory": "pacific-coast", "content": "# Loss", "encoding": "utf-8"},
        ],
        source_id="google-drive",
        connection_label="Google Drive › Broker Submissions",
        org_id="test",
    )
    store.add_documents(
        bundle["bundle_id"],
        [{"filename": "clue.json", "path": "clue/clue.json", "directory": "clue", "content": "{}", "encoding": "utf-8"}],
        source_id="clue",
        connection_label="LexisNexis CLUE",
        org_id="test",
    )
    tree = store.file_tree(bundle["bundle_id"], org_id="test")
    assert tree is not None
    assert tree["document_count"] == 3
    by_source = {s["source_id"]: s for s in tree["sources"]}
    assert by_source["google-drive"]["file_count"] == 2
    assert by_source["google-drive"]["directories"][0]["path"] == "pacific-coast"
    assert by_source["clue"]["label"] == "LexisNexis CLUE"
    drive_files = by_source["google-drive"]["directories"][0]["files"]
    preview = store.get_document(bundle["bundle_id"], drive_files[0]["doc_id"], org_id="test")
    assert preview is not None
    from insureflow.storage.draft_bundle_store import preview_document

    shown = preview_document(preview)
    assert shown["previewable"] is True
    assert shown["content"]


def test_org_isolation() -> None:
    store = _make_store()
    b1 = store.create(org_id="org-a", name="A")
    store.create(org_id="org-b", name="B")
    assert store.get(b1["bundle_id"], org_id="org-a") is not None
    assert store.get(b1["bundle_id"], org_id="org-b") is None
    assert len(store.list_all(org_id="org-a")) == 1
    assert len(store.list_all(org_id="org-b")) == 1


def test_oversized_document_is_skipped_not_accepted() -> None:
    store = _make_store()
    bundle = store.create(org_id="test")
    huge = base64.b64encode(b"x" * (MAX_DOCUMENT_BYTES + 1024)).decode()
    result = store.add_documents(bundle["bundle_id"], [{"filename": "huge.pdf", "content": huge, "encoding": "base64"}], org_id="test")
    assert result is not None
    assert result["documents"] == []
    assert result["last_skipped_oversized"][0]["filename"] == "huge.pdf"

    # A normal file in the same batch still goes through.
    result2 = store.add_documents(
        bundle["bundle_id"],
        [
            {"filename": "huge.pdf", "content": huge, "encoding": "base64"},
            {"filename": "small.txt", "content": "hello", "encoding": "utf-8"},
        ],
        org_id="test",
    )
    assert result2 is not None
    assert len(result2["documents"]) == 1
    assert result2["documents"][0]["filename"] == "small.txt"


def test_add_object_reference_stores_key_not_bytes() -> None:
    store = _make_store()
    bundle = store.create(org_id="test")
    result = store.add_object_reference(
        bundle["bundle_id"],
        storage_key="draft-uploads/test/bundle-x/roof.pdf",
        filename="roof.pdf",
        size_bytes=2_147_483_648,
        content_type="application/pdf",
        org_id="test",
    )
    assert result is not None
    doc = result["documents"][0]
    assert doc["encoding"] == "s3_ref"
    assert doc["content"] == "draft-uploads/test/bundle-x/roof.pdf"
    assert doc["size_bytes"] == 2_147_483_648
    # The reference itself must stay tiny regardless of the file's real size.
    assert len(str(result)) < 2000


def test_bundle_total_size_cap_rejects_object_reference() -> None:
    store = _make_store()
    bundle = store.create(org_id="test")
    store.add_object_reference(
        bundle["bundle_id"],
        storage_key="k1",
        filename="big1.pdf",
        size_bytes=MAX_BUNDLE_TOTAL_BYTES - 1000,
        org_id="test",
    )
    with pytest.raises(BundleTooLargeError):
        store.add_object_reference(bundle["bundle_id"], storage_key="k2", filename="big2.pdf", size_bytes=5000, org_id="test")
    # The rejected file must not have been added.
    result = store.get(bundle["bundle_id"], org_id="test")
    assert result is not None
    assert len(result["documents"]) == 1


def test_bundle_total_size_cap_skips_in_batch_add() -> None:
    store = _make_store()
    bundle = store.create(org_id="test")
    store.add_object_reference(
        bundle["bundle_id"],
        storage_key="k1",
        filename="big1.pdf",
        size_bytes=MAX_BUNDLE_TOTAL_BYTES - 100,
        org_id="test",
    )
    result = store.add_documents(bundle["bundle_id"], [{"filename": "tiny.txt", "content": "x" * 1000, "encoding": "utf-8"}], org_id="test")
    assert result is not None
    assert len(result["documents"]) == 1  # the batch file was skipped, not added
    assert "total bundle size limit" in result["last_skipped_oversized"][0]["reason"]


def test_delete_bundle_cleans_up_s3_objects() -> None:
    store = _make_store()
    bundle = store.create(org_id="test")
    store.add_object_reference(bundle["bundle_id"], storage_key="draft-uploads/test/x/big.pdf", filename="big.pdf", size_bytes=999, org_id="test")

    with patch("insureflow.storage.object_storage.delete_object") as mock_delete:
        assert store.delete(bundle["bundle_id"], org_id="test") is True
        mock_delete.assert_called_once_with("draft-uploads/test/x/big.pdf")
    assert store.get(bundle["bundle_id"], org_id="test") is None


def test_delete_bundle_without_s3_docs_never_touches_object_storage() -> None:
    store = _make_store()
    bundle = store.create(org_id="test")
    store.add_documents(bundle["bundle_id"], [{"filename": "small.txt", "content": "hi", "encoding": "utf-8"}], org_id="test")

    with patch("insureflow.storage.object_storage.delete_object") as mock_delete:
        assert store.delete(bundle["bundle_id"], org_id="test") is True
        mock_delete.assert_not_called()


def test_remove_document_cleans_up_its_own_s3_object_only() -> None:
    store = _make_store()
    bundle = store.create(org_id="test")
    store.add_object_reference(bundle["bundle_id"], storage_key="k1", filename="a.pdf", size_bytes=10, org_id="test")
    result = store.add_object_reference(bundle["bundle_id"], storage_key="k2", filename="b.pdf", size_bytes=10, org_id="test")
    assert result is not None
    doc_a_id = result["documents"][0]["doc_id"]

    with patch("insureflow.storage.object_storage.delete_object") as mock_delete:
        store.remove_document(bundle["bundle_id"], doc_a_id, org_id="test")
        mock_delete.assert_called_once_with("k1")


def test_concurrent_add_documents_does_not_lose_writes() -> None:
    """Reproduces the read-modify-write race this store used to have: two
    'underwriters' both read the bundle, both append, whoever wrote last used
    to silently discard the other's document. The lock in _bundle_lock must
    prevent that."""
    store = _make_store()
    bundle = store.create(org_id="test")
    bundle_id = bundle["bundle_id"]

    orig_get = store.get

    def slow_get(bundle_id: str, org_id: str = "default") -> dict | None:  # type: ignore[type-arg]
        result = orig_get(bundle_id, org_id=org_id)
        time.sleep(0.02)
        return result

    store.get = slow_get  # type: ignore[method-assign]

    def worker(name: str) -> None:
        store.add_documents(bundle_id, [{"filename": f"{name}.pdf", "content": name, "encoding": "utf-8"}], org_id="test")

    threads = [threading.Thread(target=worker, args=(f"uw{i}",)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    final = orig_get(bundle_id, org_id="test")
    assert final is not None
    assert len(final["documents"]) == 5
