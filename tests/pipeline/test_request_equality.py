"""Every SUB-127–269 builds a byte-identical model request with LOB_ENGINE off and on."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import llm_extract
import sources

ROOT = Path(__file__).resolve().parents[2]
FIRST, LAST = 127, 269


def _submissions() -> list[Path]:
    folders = []
    for number in range(FIRST, LAST + 1):
        folder = ROOT / "simulation" / "inbox" / f"SUB-{number:03d}"
        if folder.is_dir():
            folders.append(folder)
    return folders


def _request_bytes(docs: list[dict]) -> bytes:
    request = llm_extract.request_for(docs)
    body = {key: request[key] for key in ("payload", "key", "files", "not_sent")}
    return json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def test_request_and_cache_key_are_identical_off_and_on(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "qwen/qwen3.8-27b")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("LLM_API_KEY", "fixture-not-sent")
    monkeypatch.setattr(llm_extract, "_post", lambda *args, **kwargs: pytest.fail("model call while building a request"))

    total = identical = different = 0
    failed = []
    for folder in _submissions():
        total += 1
        try:
            docs = sources.read_folder(folder)
        except Exception as exc:
            failed.append((folder.name, f"{type(exc).__name__}: {exc}"))
            continue
        monkeypatch.setenv("LOB_ENGINE", "off")
        off = _request_bytes(docs)
        monkeypatch.setenv("LOB_ENGINE", "on")
        on = _request_bytes(docs)
        if off == on:
            identical += 1
        else:
            different += 1

    print(f"request equality: total={total} identical={identical} different={different} failed={len(failed)}")
    for name, reason in failed:
        print(f"  could not prepare {name}: {reason}")
    assert different == 0
    assert not failed, failed
    assert total == LAST - FIRST + 1


def test_requests_equal_the_recorded_head_baseline(monkeypatch):
    """P-075 (D-133): 0 of 143 request bodies changed against the SHA-256s recorded from HEAD before the build."""
    import hashlib

    baseline = json.loads((Path(__file__).parent / "fixtures" / "request_baseline.json").read_text())
    monkeypatch.setenv("LLM_MODEL", "qwen/qwen3.8-27b")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("LLM_API_KEY", "fixture-not-sent")
    monkeypatch.setenv("LOB_ENGINE", "off")
    changed = [f.name for f in _submissions() if hashlib.sha256(_request_bytes(sources.read_folder(f))).hexdigest() != baseline.get(f.name)]
    print(f"request baseline: {len(baseline)} recorded, {len(changed)} changed")
    assert len(baseline) == LAST - FIRST + 1 and not changed, changed
