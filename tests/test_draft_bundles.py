from __future__ import annotations

from insureflow.storage.draft_bundle_store import DraftBundleStore
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
    store.add_documents(bundle["bundle_id"], [{"filename": "a.xml", "content": "", "encoding": "utf-8"}], org_id="test")
    store.add_documents(
        bundle["bundle_id"],
        [{"filename": "b.md", "content": "", "encoding": "utf-8"}],
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
        [{"filename": "a.xml", "content": "", "encoding": "utf-8"}, {"filename": "b.md", "content": "", "encoding": "utf-8"}],
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
