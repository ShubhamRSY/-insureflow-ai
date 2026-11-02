"""Security review of P-074 (ReDoS): the amount patterns must stay fast on long runs of spaces.

Before the fix, "about" followed by 100 spaces and a letter never finished in SALES_AFTER.
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "underwriting_pipeline" / "ai"))

import llm_extract  # noqa: E402
import prepare  # noqa: E402

PATTERNS = {
    "AMOUNT_TOKEN": re.compile(prepare.AMOUNT_TOKEN, re.I),
    "SALES_BEFORE": prepare.SALES_BEFORE,
    "SALES_AFTER": prepare.SALES_AFTER,
    "_HEDGE_BEFORE": llm_extract._HEDGE_BEFORE,
    "_NUM": llm_extract._NUM,
    "_AMOUNT": llm_extract._AMOUNT,
}
SPACES = " " * 10_000
INPUTS = [
    "about" + SPACES + "x",
    SPACES + "x",
    "sales" + SPACES + "x",
    "1200" + SPACES + "x",
    "sales :" + SPACES + "US$" + SPACES + "x",
    "about :" + SPACES + "1200" + SPACES + "x",
]


def test_amount_patterns_fast_on_long_space_runs():
    for name, pattern in PATTERNS.items():
        for text in INPUTS:
            start = time.perf_counter()
            list(pattern.finditer(text))
            assert time.perf_counter() - start < 1.0, name


def test_amount_patterns_still_read_hedged_amounts():
    assert prepare._sales_figures("Last year sales were about US$1.2 million.") == [(1_200_000, "Last year sales were about US$1.2 million.")]
    assert llm_extract.amount_value("about: $1.2m") == 1_200_000
    assert llm_extract._quote_amounts("we did about $1.42 million") == [(1_420_000, True)]
