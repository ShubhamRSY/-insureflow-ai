# P-074 look-again (D-129, the one look-again) — @model-risk

Scope: branch `p074` in `insureflow-fix-t117`, uncommitted diff vs pilot-integration 3c50cd5, after the fixes for `P-074-check.md`. LLM_* unset; no model call; stubbed probes only. **Not a production approval; the T-027 veto stands.** An approved proposal (D-132) is not a production approval.

## Re-run (by me, 2026-10-26)

| Check | Result |
|---|---|
| `llm_extract.py` self-check | `llm gate ok` |
| `prepare.py` self-check | `prepare ok` |
| `workbench.py` self-check | `workbench ok` |
| `pytest tests/pipeline` | 86 passed (incl. `test_request_equality`) |
| PROMPT_VERSION | `759b3e6bc9b2`; `SYSTEM`, `request_for` not in diff |
| Dev manifest | 38/38 `shasum -c` OK |
| Frozen files | none in diff or untracked |
| D-065 | What's new line (2026-10-24, P-074, D-132), `side_note` on list and resolve form, P-074.png present, UI check: no High |
| Worktree after my runs | `git status` hash identical before and after |

## Earlier findings

- **M1 — NOT fixed on the path it named. Now High (H1).**
- **M2 — fixed.** Probes: "about US$1.2 million", "about USD 1.2 million", "Approximately: $1,200,000", "around: US$ 1.2 million", "nearly US$1,200,000", "~ USD 1.2m" all approximate. Leftover gaps are in the Low list.
- **M3 — fixed.** Probe: a labelled two-location file keeps the premises conflict that has an unverified side and drops the plain one.
- **M4 — corrected.** The as-built now says B can verify a side that was rejected before. It finds no such case in the 69 dev replays.

## High findings

- **H1 — `_carry_flag` still drops the per-location review flag (loosening vs HEAD; the M1 fix only works when the notes are in the other order).**
  - **The reason text.** In `llm_extract.llm_extract`, the P-056(e) per-location row is built as `f"{first['reason']}; {note}"`. `first` comes from `accept_field`, which already put `approximate figure: …` at the end of its reason. So on a hedged row the reason reads `approximate figure: <quote>; values differ by location: …`.
  - **What the fix does to it.** In `prepare._carry_flag`, the regex `(?:^|; )approximate figure: .*$` (re.S) removes everything from the note to the end. That includes the per-location note. `rest` is then empty, so the function returns and the flag is not carried.
  - **Probe.** cur is exact and clean. other is `{approximate, needs_review, reason: "approximate figure: about $1.2 million; values differ by location: loc 1 1200000; loc 2 900000"}`. Result: cur `needs_review False`, `reason None`. Before P-074 this flag was carried.
  - **How it is reached.** An agreeing merge in `process_submission` (`fuller` then `_carry_flag`, prepare.py ~1236–1239) between the hedged location-1 row and an exact figure from another document. The "values differ by location" review is then lost, and the file can go toward complete.
  - **Why the self-check missed it.** It only tests the opposite order (`values differ by location…; approximate figure…`). The docstring comment "the note is always last" is wrong for this path.
  - **Resolution (small; no further @model-risk look needed if the self-check line passes):**
    1. Remove only the note itself, not everything after it. Option (a): rebuild the exact note string from `other["quote"]` the same way `accept_field` builds it, and `str.replace` it. Option (b): store the note in its own key and leave `reason` untouched.
    2. Add a self-check line with the per-location order shown above, asserting `needs_review` is True and the location note is kept.

## Medium

- None new.

## Low (backlog, one line each)

- L6: hedge still not seen across "US $" (with a space), "CA$", "€", or "circa." with a period. Each verifies as exact.
- L7: a hedge that is not directly before the amount is not seen ("approx. annual sales of $1.2M" verifies as exact). This is by design ("directly before") but it is a gap.
- L8: the M3 self-check accepts `keep74 == []`, which is the failure case. Assert `len(keep74) == 1` and that the kept conflict has the unverified side.
- L1–L5 from the earlier check stand as recorded in the as-built.

## Verdict

**BLOCK** (production/merge of P-074 as built). Resolved when H1 is fixed as above and `prepare.py` self-check passes with the new per-location-order line. Everything else in the criteria holds: D1–D5, units, the hedge list, equal-amount merge, stricter only, PROMPT_VERSION and 0 request changes, tests green, no frozen file, and the D-065 items. Not a production approval; the T-027 veto stands.
