"""Tests for DecisionMemoryStore's semantic (embedding-based) recall.

Mirrors the categorical similar()/similar_to_bundle() tests this module
already had none of — similar_semantic() is new this session: it ranks by
cosine similarity over embedded decision text instead of exact/substring
field matching, and is the mechanism the recall_similar_past_decisions
ReAct tool (tests/test_agents.py) is actually built on.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from insureflow.privacy.decision_memory import DecisionMemoryRecord, DecisionMemoryStore


@pytest.fixture(autouse=True)
def _local_embeddings(monkeypatch: pytest.MonkeyPatch) -> None:
    # Force the offline hashed-embedding path regardless of the ambient
    # environment's EMBEDDING_BACKEND/API-key/egress config — these tests
    # must be deterministic and network-free, not just "usually" fast.
    monkeypatch.setenv("EMBEDDING_BACKEND", "local")


@pytest.fixture
def store(tmp_path: Path) -> DecisionMemoryStore:
    return DecisionMemoryStore(persist_path=tmp_path / "decision_memory.jsonl")


def _record(**overrides: object) -> DecisionMemoryRecord:
    base: dict[str, object] = dict(
        org_id="org-a",
        bundle_id="b1",
        line="commercial_property",
        decision="refer",
        naics="236220",
        state="CA",
        tiv_band="1m-5m",
        construction="wood frame",
        occupancy="habitational",
        loss_count_band="2-3",
        reasons=["three prior losses", "wood frame construction in wildfire zone"],
    )
    base.update(overrides)
    return DecisionMemoryRecord(**base)  # type: ignore[arg-type]


def test_remember_computes_an_embedding_automatically(store: DecisionMemoryStore) -> None:
    rec = store.remember(_record())
    assert rec.embedding is not None
    assert len(rec.embedding) > 0


def test_similar_semantic_ranks_closer_matches_first(store: DecisionMemoryStore) -> None:
    store.remember(_record(bundle_id="close-1"))  # near-identical risk profile
    store.remember(
        _record(
            bundle_id="close-2",
            decision="accept",
            loss_count_band="0",
            reasons=["clean loss history", "sprinklered"],
        )
    )
    store.remember(
        _record(
            bundle_id="distant-1",
            line="workers_comp",
            naics="811111",
            state="TX",
            tiv_band="0-250k",
            construction="",
            occupancy="auto repair shop",
            loss_count_band="4-6",
            reasons=["high claim frequency in an unrelated trade"],
        )
    )

    query = "line=commercial_property state=CA naics=236220 tiv_band=1m-5m construction=wood frame occupancy=habitational"
    hits = store.similar_semantic(query, "org-a", limit=5, min_score=0.0)

    assert [rec.bundle_id for rec, _score in hits[:2]] == ["close-1", "close-2"]
    assert hits[0][1] > hits[-1][1]  # the property-line hits outrank the unrelated workers_comp one
    assert hits[-1][0].bundle_id == "distant-1"


def test_similar_semantic_never_crosses_org_boundary(store: DecisionMemoryStore) -> None:
    store.remember(_record(org_id="org-a", bundle_id="a1"))
    store.remember(_record(org_id="org-b", bundle_id="b1"))

    query = "line=commercial_property state=CA naics=236220 tiv_band=1m-5m construction=wood frame occupancy=habitational"
    hits_a = store.similar_semantic(query, "org-a", limit=10, min_score=0.0)
    hits_b = store.similar_semantic(query, "org-b", limit=10, min_score=0.0)

    assert {rec.bundle_id for rec, _ in hits_a} == {"a1"}
    assert {rec.bundle_id for rec, _ in hits_b} == {"b1"}


def test_similar_semantic_skips_records_without_an_embedding(store: DecisionMemoryStore) -> None:
    # Simulates data written before the embedding field existed.
    legacy = _record(bundle_id="legacy-1")
    store.remember(legacy)
    # Overwrite on disk with embedding stripped, bypassing remember()'s
    # auto-embed so this genuinely represents pre-existing data.
    stripped = store.get("org-a", "legacy-1")
    assert stripped is not None
    with store._lock:
        records = store._load_unlocked()
        records = [r for r in records if r.bundle_id != "legacy-1"]
        records.append(stripped.model_copy(update={"embedding": None}))
        store._write_unlocked(records)

    query = "line=commercial_property state=CA naics=236220 tiv_band=1m-5m construction=wood frame occupancy=habitational"
    hits = store.similar_semantic(query, "org-a", limit=5, min_score=0.0)
    assert hits == []


def test_similar_semantic_empty_probe_or_org_returns_empty(store: DecisionMemoryStore) -> None:
    store.remember(_record())
    assert store.similar_semantic("", "org-a") == []
    assert store.similar_semantic("line=commercial_property", "") == []


def test_categorical_similar_still_works_unchanged(store: DecisionMemoryStore) -> None:
    # Regression guard: adding semantic recall must not touch the existing
    # categorical matching path at all.
    store.remember(_record(bundle_id="p1"))
    probe = _record(bundle_id="probe", decision="")
    hits = store.similar(probe, limit=5)
    assert [rec.bundle_id for rec, _ in hits] == ["p1"]
