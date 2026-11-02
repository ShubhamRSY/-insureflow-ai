"""LOB configuration packs (engine step 1).

A pack is data only. This module loads and validates it; it contains no business rules.
Unknown LOBs, unknown keys, missing keys and wrong types fail closed with ValueError.
LOB_ENGINE is off by default: every lookup returns the small_commercial baseline pack.
"""

import hashlib
import json
import os
import re
from pathlib import Path
from types import MappingProxyType

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config" / "lobs"
BASELINE = "small_commercial"
KINDS = ("text", "number", "date", "soft", "address")
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
VERSION = re.compile(r"^[0-9a-f]{12}$")
_MISSING = object()


def engine_enabled() -> bool:
    """On only when LOB_ENGINE is exactly 'on'; off is the default and the rollback."""
    return (os.environ.get("LOB_ENGINE") or "").strip().lower() == "on"


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value):
    if isinstance(value, MappingProxyType):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _fail(message: str):
    raise ValueError(f"LOB pack: {message}")


def _exact(mapping: dict, keys: tuple[str, ...], where: str) -> None:
    if not isinstance(mapping, dict):
        _fail(f"{where} must be an object")
    extra = sorted(set(mapping) - set(keys))
    missing = sorted(set(keys) - set(mapping))
    if extra:
        _fail(f"{where} has unknown key(s): {', '.join(extra)}")
    if missing:
        _fail(f"{where} is missing key(s): {', '.join(missing)}")


def _text(value, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{where} must be a non-empty string")
    return value


def _strings(value, where: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty) or not all(isinstance(item, str) and item for item in value):
        _fail(f"{where} must be a {'non-empty ' if not allow_empty else ''}list of strings")
    if len(set(value)) != len(value):
        _fail(f"{where} has duplicate values")
    return value


def _ratio(value, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        _fail(f"{where} must be a number from 0 to 1")
    return float(value)


def _validate(raw: dict) -> dict:
    top = ("schema_version", "id", "name", "family", "states", "fields", "prompt", "extraction", "statuses", "scope")
    _exact(raw, top, "the pack")
    if raw["schema_version"] != 1 or isinstance(raw["schema_version"], bool):
        _fail("schema_version must be 1")
    lob_id = _text(raw["id"], "id")
    if not IDENTIFIER.fullmatch(lob_id):
        _fail(f"id {lob_id!r} must match {IDENTIFIER.pattern}")
    _text(raw["name"], "name")
    _text(raw["family"], "family")
    states = _strings(raw["states"], "states", allow_empty=False)
    if not all(re.fullmatch(r"[A-Z]{2}", state) for state in states):
        _fail("states must be two-letter uppercase codes")

    fields = raw["fields"]
    if not isinstance(fields, list) or not fields:
        _fail("fields must be a non-empty list")
    ids = []
    for index, field in enumerate(fields):
        where = f"fields[{index}]"
        _exact(field, ("id", "label", "plain", "kind", "required", "scored", "prompt_hint"), where)
        field_id = _text(field["id"], f"{where}.id")
        if not IDENTIFIER.fullmatch(field_id):
            _fail(f"{where}.id {field_id!r} is not an identifier")
        if field_id in ids:
            _fail(f"duplicate field id {field_id}")
        ids.append(field_id)
        _text(field["label"], f"{where}.label")
        _text(field["plain"], f"{where}.plain")
        if field["kind"] not in KINDS:
            _fail(f"{where}.kind must be one of {', '.join(KINDS)}")
        if not isinstance(field["required"], bool) or not isinstance(field["scored"], bool):
            _fail(f"{where}.required and .scored must be booleans")
        if field["prompt_hint"] is not None:
            _text(field["prompt_hint"], f"{where}.prompt_hint")

    prompt = raw["prompt"]
    _exact(prompt, ("system", "version"), "prompt")
    system = _text(prompt["system"], "prompt.system")
    version = _text(prompt["version"], "prompt.version")
    if not VERSION.fullmatch(version):
        _fail("prompt.version must be 12 lowercase hex characters")
    if hashlib.sha256(system.encode("utf-8")).hexdigest()[:12] != version:
        _fail("prompt.version does not match the prompt text")

    extraction = raw["extraction"]
    _exact(extraction, ("min_confidence", "scan_floor", "number_fields", "date_fields", "text_fields", "soft_fields"), "extraction")
    low = _ratio(extraction["min_confidence"], "extraction.min_confidence")
    scan = _ratio(extraction["scan_floor"], "extraction.scan_floor")
    if scan > low:
        _fail("extraction.scan_floor must not exceed min_confidence")
    for key in ("number_fields", "date_fields", "text_fields", "soft_fields"):
        values = _strings(extraction[key], f"extraction.{key}")
        bad = [value for value in values if not IDENTIFIER.fullmatch(value)]
        if bad:
            _fail(f"extraction.{key} has invalid field id(s): {', '.join(bad)}")

    statuses = raw["statuses"]
    _exact(statuses, ("all", "review_pending", "refused", "manual_intake"), "statuses")
    all_statuses = _strings(statuses["all"], "statuses.all", allow_empty=False)
    review = _text(statuses["review_pending"], "statuses.review_pending")
    refused = _strings(statuses["refused"], "statuses.refused", allow_empty=False)
    manual = _text(statuses["manual_intake"], "statuses.manual_intake")
    if review not in all_statuses:
        _fail("statuses.review_pending is not in statuses.all")
    if manual not in all_statuses:
        _fail("statuses.manual_intake is not in statuses.all")
    unknown = sorted(set(refused) - set(all_statuses))
    if unknown:
        _fail(f"statuses.refused has unknown status(es): {', '.join(unknown)}")

    scope = raw["scope"]
    _exact(scope, ("version", "pilot_states", "min_words", "unsure_ratio", "reasons"), "scope")
    _text(scope["version"], "scope.version")
    pilot = _strings(scope["pilot_states"], "scope.pilot_states", allow_empty=False)
    if sorted(pilot) != sorted(states):
        _fail("scope.pilot_states must equal states")
    if not isinstance(scope["min_words"], int) or isinstance(scope["min_words"], bool) or scope["min_words"] < 1:
        _fail("scope.min_words must be a positive integer")
    _ratio(scope["unsure_ratio"], "scope.unsure_ratio")
    reasons = scope["reasons"]
    if not isinstance(reasons, dict) or not reasons:
        _fail("scope.reasons must be a non-empty object")
    for key, text in reasons.items():
        _text(key, "scope.reasons key")
        _text(text, f"scope.reasons.{key}")
    return raw


class LobConfig:
    """An immutable, validated pack."""

    def __init__(self, raw: dict):
        self._raw = _freeze(_validate(raw))
        self.id = self._raw["id"]
        self.name = self._raw["name"]
        self.family = self._raw["family"]
        self.fields = tuple(self._raw["fields"])
        self.prompt = self._raw["prompt"]
        self.extraction = self._raw["extraction"]
        self.statuses = self._raw["statuses"]
        self.scope = self._raw["scope"]

    @property
    def raw(self) -> dict:
        return _thaw(self._raw)

    @property
    def prompt_system(self) -> str:
        return self._raw["prompt"]["system"]

    def get(self, path: str, default=_MISSING):
        if not isinstance(path, str) or not path:
            _fail("path must be a non-empty dotted key")
        value = self._raw
        for part in path.split("."):
            if not isinstance(value, MappingProxyType) or part not in value:
                if default is _MISSING:
                    _fail(f"unknown key {path!r}")
                return default
            value = value[part]
        return _thaw(value)

    def fingerprint(self) -> str:
        blob = json.dumps(self.raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def load(lob_id: str = BASELINE) -> LobConfig:
    """Load one named pack. Off (the default) resolves a known LOB to the baseline pack."""
    if not isinstance(lob_id, str) or not IDENTIFIER.fullmatch(lob_id):
        _fail(f"invalid LOB id {lob_id!r}")
    requested = CONFIG_DIR / f"{lob_id}.json"
    if not requested.is_file():
        _fail(f"unknown LOB {lob_id!r}")
    name = lob_id if engine_enabled() else BASELINE
    path = CONFIG_DIR / f"{name}.json"
    if not path.is_file():
        _fail(f"unknown LOB {name!r}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(f"cannot read {path.name}: {exc}")
    return LobConfig(raw)


def pack_for(submission: dict | None = None) -> LobConfig:
    """Resolve a submission's pack. A missing lob is the baseline; unknown LOBs fail closed."""
    if not submission:
        return load(BASELINE)
    lob_id = submission.get("lob") or BASELINE
    return load(lob_id)


def baseline_prompt() -> str:
    return load(BASELINE).prompt_system
