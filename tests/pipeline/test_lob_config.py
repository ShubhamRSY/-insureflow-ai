"""Engine step 1: the baseline pack, its loader, and the no-call equality replay."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

import llm_extract
import lob_config
import lob_config_snapshot
import prepare
import sources

ROOT = Path(__file__).resolve().parents[2]
BASELINE_FINGERPRINT = "7833137958df1e3761aabfc25b16fa80722c54dc5d9f0662cbde590a0f78a14b"


def test_load_baseline_and_raw_equality():
    config = lob_config.load("small_commercial")
    assert config.id == "small_commercial"
    assert config.raw == lob_config_snapshot.snapshot()
    assert config.prompt_system == lob_config_snapshot.snapshot()["prompt"]["system"]
    assert config.prompt["version"] == "759b3e6bc9b2"
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


def test_no_call_replay_on_and_off_are_identical(monkeypatch, tmp_path):
    """Set LOB_BASELINE_CACHE to the saved cache to replay SUB-127–269 with no model calls."""
    source = os.environ.get("LOB_BASELINE_CACHE")
    if not source:
        pytest.skip("set LOB_BASELINE_CACHE to a saved extraction cache to run the replay")
    files = _cache_files(Path(source))
    if not files:
        pytest.skip(f"no cached replies under {source}")

    cache = tmp_path / "cache"
    (cache / "extractions").mkdir(parents=True)
    for path in files.values():
        shutil.copy(path, cache / "extractions" / path.name)
    monkeypatch.setattr(llm_extract, "CACHE", cache)
    monkeypatch.setenv("LLM_MODEL", "qwen/qwen3.8-27b")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setattr(llm_extract, "_post", lambda *args, **kwargs: pytest.fail("model call during replay"))

    compared = 0
    for folder in _saved_runs():
        if not 127 <= int(folder.name.removeprefix("SUB-")) <= 269:
            continue
        key = llm_extract.key_for(sources.read_folder(folder))
        if key not in files:
            continue
        monkeypatch.setenv("LOB_ENGINE", "off")
        off = _normalise(prepare.process_submission(folder))
        monkeypatch.setenv("LOB_ENGINE", "on")
        on = _normalise(prepare.process_submission(folder))
        assert on == off, folder.name
        compared += 1
    assert compared, "no saved run in SUB-127–269 matched a cached reply"
