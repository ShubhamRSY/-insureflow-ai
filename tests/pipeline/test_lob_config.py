"""Engine step 1: the baseline pack, its loader, and the no-call equality replay."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

import llm_extract
import lob_config
import lob_config_snapshot
import prepare
import sources

ROOT = Path(__file__).resolve().parents[2]
BASELINE_FINGERPRINT = "1b56945510707f63f6e24fc01b702bf95ea717d9ebb79bf1a4b33602338ef6ce"  # scope-v8 (P-084, D-165)


def test_load_baseline_and_raw_equality():
    config = lob_config.load("small_commercial")
    assert config.id == "small_commercial"
    assert config.raw == lob_config_snapshot.snapshot()
    assert config.prompt_system == lob_config_snapshot.snapshot()["prompt"]["system"]
    assert config.prompt["version"] == "392b9ce3c1af"  # P-077 part B (D-145); was 759b3e6bc9b2
    assert [field["id"] for field in config.fields] == list(prepare.FIELDS)


def test_fingerprint_is_stable():
    assert lob_config.load("small_commercial").fingerprint() == BASELINE_FINGERPRINT


def test_unknown_key_fails_closed():
    raw = lob_config_snapshot.snapshot()
    raw["unexpected"] = True
    with pytest.raises(ValueError, match="unknown key"):
        lob_config.LobConfig(raw)


def test_unknown_lob_fails_closed_when_engine_on(monkeypatch):
    monkeypatch.setenv("LOB_ENGINE", "on")
    with pytest.raises(ValueError, match="unknown LOB"):
        lob_config.load("not_a_lob")
    with pytest.raises(ValueError, match="unknown LOB"):
        lob_config.pack_for({"lob": "not_a_lob"})


def test_engine_off_is_the_default_and_returns_baseline(monkeypatch):
    monkeypatch.delenv("LOB_ENGINE", raising=False)
    assert not lob_config.engine_enabled()
    assert lob_config.load().id == "small_commercial"
    with pytest.raises(ValueError, match="unknown LOB"):
        lob_config.load("not_a_lob")
    with pytest.raises(ValueError, match="unknown LOB"):
        lob_config.pack_for({"lob": "not_a_lob"})


def test_missing_lob_is_baseline_when_engine_on(monkeypatch):
    monkeypatch.setenv("LOB_ENGINE", "on")
    assert lob_config.pack_for(None).id == "small_commercial"
    assert lob_config.pack_for({}).id == "small_commercial"


def _cache_files(source: Path) -> dict[str, Path]:
    return {path.stem: path for path in source.rglob("*.json")}


def _saved_runs() -> list[Path]:
    return sorted(path for path in (ROOT / "simulation" / "inbox").glob("SUB-*") if path.is_dir())


def _normalise(report: dict) -> dict:
    return json.loads(json.dumps(report, sort_keys=True, default=str))


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "replay"


def test_no_call_replay_on_and_off_are_identical(monkeypatch, tmp_path):
    """Replay saved replies: the temporary fixture by default, or LOB_BASELINE_CACHE when set."""
    monkeypatch.setenv("LLM_MODEL", "qwen/qwen3.8-27b")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("LLM_API_KEY", "fixture-not-sent")
    cache = tmp_path / "cache"
    (cache / "extractions").mkdir(parents=True)

    source = os.environ.get("LOB_BASELINE_CACHE")
    if source:
        files = _cache_files(Path(source))
        if not files:
            pytest.fail(f"no cached replies under {source}")
        folders = [folder for folder in _saved_runs() if 127 <= int(folder.name.removeprefix("SUB-")) <= 269]
        for path in files.values():
            shutil.copy(path, cache / "extractions" / path.name)
        keys = set(files)
    else:
        replies = json.loads((FIXTURE / "replies.json").read_text(encoding="utf-8"))
        folders = [FIXTURE / "submissions" / name for name in replies]
        keys = set()
        for folder in folders:
            docs = sources.read_folder(folder)
            key = llm_extract.key_for(docs)
            assert key
            parsed = replies[folder.name]
            if "location_count" not in parsed:  # P-077 part B: replies recorded before the count; give each a count of 1 quoting its own address
                name, m = next((d["name"], m) for d in docs for m in [prepare.scope.STREET_WORDS.search(d.get("text") or "")] if m)
                parsed = {**parsed, "location_count": {"value": 1, "quote": m.group(0), "source": name}}
            saved = {"model": os.environ["LLM_MODEL"], "prompt_version": llm_extract.PROMPT_VERSION, "files": [doc["name"] for doc in docs], "usage": {}, "parsed": parsed}
            (cache / "extractions" / f"{key}.json").write_text(json.dumps(saved, indent=2) + "\n", encoding="utf-8")
            keys.add(key)

    monkeypatch.setattr(llm_extract, "CACHE", cache)
    monkeypatch.setattr(llm_extract, "_post", lambda *args, **kwargs: pytest.fail("model call during replay"))

    compared = extracted = 0
    for folder in folders:
        key = llm_extract.key_for(sources.read_folder(folder))
        if key not in keys:
            continue
        monkeypatch.setenv("LOB_ENGINE", "off")
        off = _normalise(prepare.process_submission(folder))
        monkeypatch.setenv("LOB_ENGINE", "on")
        on = _normalise(prepare.process_submission(folder))
        assert on == off, folder.name
        compared += 1
        extracted += off["status"] != prepare.MANUAL_INTAKE
    assert compared, "no saved run matched a cached reply"
    assert extracted, "code review 2026-11-02: the replay must compare extracted runs, not only manual-intake reports"
