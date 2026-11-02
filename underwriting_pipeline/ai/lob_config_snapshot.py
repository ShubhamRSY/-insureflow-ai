"""Generate the small_commercial baseline pack from the current constants.

Run by hand from the repository root, then commit the JSON with the code change:

    python underwriting_pipeline/ai/lob_config_snapshot.py
"""

import json
from pathlib import Path

import llm_extract
import prepare
import scope

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "underwriting_pipeline" / "config" / "lobs" / "small_commercial.json"


def _kind(field: str) -> str:
    if field in llm_extract.DATE_FIELDS:
        return "date"
    if field in llm_extract.NUMBER_FIELDS:
        return "number"
    if field in llm_extract.SOFT_FIELDS:
        return "soft"
    if field == "premises_address":
        return "address"
    return "text"


def snapshot() -> dict:
    """The baseline pack as data, built only from module constants."""
    fields = []
    for field in prepare.FIELDS:
        fields.append(
            {
                "id": field,
                "label": prepare.LABELS[field][0].rstrip(":"),
                "plain": prepare.PLAIN[field],
                "kind": _kind(field),
                "required": True,
                "scored": True,
                "prompt_hint": ", ".join(label.rstrip(":") for label in prepare.LABELS[field]),
            }
        )
    return {
        "schema_version": 1,
        "id": "small_commercial",
        "name": "Small commercial",
        "family": "small_commercial",
        "states": ["TX"],
        "fields": fields,
        "prompt": {"system": llm_extract.SYSTEM, "version": llm_extract.PROMPT_VERSION},
        "extraction": {
            "min_confidence": llm_extract.MIN_CONFIDENCE,
            "scan_floor": llm_extract.SCAN_FLOOR,
            "number_fields": list(llm_extract.NUMBER_FIELDS),
            "date_fields": list(llm_extract.DATE_FIELDS),
            "text_fields": list(llm_extract.TEXT_FIELDS),
            "soft_fields": list(llm_extract.SOFT_FIELDS),
        },
        "statuses": {
            "all": list(prepare.STATUSES),
            "review_pending": prepare.REVIEW_PENDING,
            "refused": list(prepare.REFUSED_STATUSES),
            "manual_intake": prepare.MANUAL_INTAKE,
        },
        "scope": {
            "version": scope.VERSION,
            "pilot_states": ["TX"],
            "min_words": scope.MIN_WORDS,
            "unsure_ratio": scope.UNSURE_RATIO,
            "reasons": dict(scope.REASONS),
        },
    }


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
