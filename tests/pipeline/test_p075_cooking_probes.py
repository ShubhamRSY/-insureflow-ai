"""P-075 (D-133): the @model-risk probe set (128 sentences). Every "hold" probe must open the cooking conflict. A false hold on a
"no_hold" probe fails safe and is only counted. Also: the cooking patterns stay fast on long runs of spaces (P-074 ReDoS review)."""
import json
import time
from pathlib import Path

import prepare

PROBES = json.loads((Path(__file__).parent / "fixtures" / "p075_probes.json").read_text())


def held(text: str, pid: str = "") -> bool:  # the insured's name is read (code review 2): BEN-05 is now a false hold, by design
    return bool(prepare.cooking_hits({"email.md": text}))


def test_every_hold_probe_is_held():
    holds = [p for p in PROBES if p["expect"] == "hold"]
    missed = [(p["id"], p["text"]) for p in holds if not held(p["text"], p["id"])]
    false = [p["id"] for p in PROBES if p["expect"] == "no_hold" and held(p["text"], p["id"])]
    print(f"hold probes held {len(holds) - len(missed)}/{len(holds)}; no_hold probes not held {sum(p['expect'] == 'no_hold' for p in PROBES) - len(false)}/{sum(p['expect'] == 'no_hold' for p in PROBES)}; false holds {false}")
    assert len(PROBES) == 128 and not missed, missed


def test_cooking_patterns_fast_on_long_space_runs():
    spaces = " " * 10_000
    texts = {
        "application.md": "Cooking operations:" + spaces + "x",
        "email.md": spaces + "x" + spaces,
        "schedule.csv": "cooking" + spaces + "\tx\n" + spaces,
        "b.md": "heated" + spaces + "display, hot" + spaces + "food",
    }
    for pattern in (prepare.COOKING_LINE, prepare._COOK_PHRASES, prepare._CLAUSE, prepare._COOK_RANGE_SKIP):
        for text in texts.values():
            start = time.perf_counter()
            list(pattern.finditer(text))
            assert time.perf_counter() - start < 1.0
    start = time.perf_counter()
    prepare.cooking_hits(texts)
    prepare.cooking_none_line(texts)
    assert time.perf_counter() - start < 2.0


MODEL_RISK_CHECK = ("The staff heats up food for staff.", "A frialator was added.", "There is food prepping on site.", "She heats up food.", "They heated up food.",
                    "Staff heats up water.", "Staff are heating water.", "Food prepping every day.", "Food prepped daily.", "A fryolator is used.", "UL 300 system over the line.", "UL300 system.", "ul-300 hood")


def test_p075_check_sentences_hold():
    assert [t for t in MODEL_RISK_CHECK if not held(t)] == []


def test_copied_note_never_claims_absence():
    note = prepare.REASON_COOKING_COPIED.lower()
    assert "no other document" not in note and "no other" not in note and "check the other documents" in note
