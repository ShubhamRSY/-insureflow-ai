# @model-risk check — T-126 (B-508, D-148) and T-127 (P-077 A+B, D-145, D-146)

- Date: 2026-11-02 · Reviewer: @model-risk · Scope: uncommitted diff on `pilot-integration` (incl. the post-dispatch `HOUSE_NUMBER` change in `prepare.py`).
- Re-run on a temp copy (D-069), no model call: `scope.py` ok (scope-v5), `prepare.py` ok, `regression_dev` self-check ok, `tests/pipeline` 94 passed (before the HOUSE_NUMBER edit); after it: `prepare.py` ok, test_pilot/test_lob_config/test_request_equality 21 passed. Real worktree unchanged.
- Not a production approval. The T-027 veto stands.

## Verdicts

| Task | Verdict |
|---|---|
| T-126 (B-508) | **APPROVE** |
| T-127 (P-077 A+B) | **APPROVE** (final, after the one look-again; H1 closed). Medium/Low to backlog. |

_First pass: REJECT on H1. See "Look-again" below._

## Recomputed evidence

- (d) PROMPT_VERSION: sha256(system)[:12] = `392b9ce3c1af`, 3,257 bytes; config, `llm_extract.PROMPT_VERSION` and test agree. Request fixture re-recorded; test passes.
- (e) Stricter only, scope-v4 (HEAD) vs scope-v5 over all 333 readable `simulation/inbox` folders: manual intake 137 → 143; 6 move to manual (SUB-014, -022, -032, -042, -052, -475); **0 move back to in scope**. Part A only appends codes; Part B sits in the post-call `else` branch, so a raised call stays `extraction_failed` (D-021, self-check case `failed77`).
- (a) Part A runs before the call; Part B returns whole-file manual intake, no values kept, refused at send via the saved scope.
- (c) Near-miss list in the `scope.py` self-check passes, including D-146 sold/closed wording.

## High findings

### H1 — Part B's "quote holds a premises address" check now accepts almost any number followed by a capital (fail-open against condition (b))
- Where: `prepare.py` `HOUSE_NUMBER = r"\b\d{1,6} +(?:[NSEW]\.? +)?[A-Z0-9][A-Za-z0-9]"`, used in `_location_problem` for `value == 1`. It replaced `scope.STREET_WORDS` after dispatch.
- Evidence (direct calls to `_location_problem`, `value: 1`, quote found in the cited file): these all return **None (in scope)**: `"1 Location"`, `"Seats: 40 Indoor"`, `"Employees: 12 FT"`, `"Effective 2027 TX"`, `"Policy period 12 Months"`, `"Est. 2009 Family owned"`, `"PO Box 9 Waco"` (a mailing address), and `"2 Stores"` (a quote that contradicts the count of 1).
- Why it matters: T-127 criterion (b) and D-145 (b) say that a quote with no street address, or an uncertain count, goes to manual intake. With this regex the quote no longer has to show a premises address. A model count of 1 backed by an unrelated line passes, so the check does not do what the criterion says. Part A catches some of these cases (`"2 Stores"`), but not all, and (a) requires each signal to stand on its own. The only new self-check case, `"Years in business: 9"`, does not exercise the gap.
- Remediation, any one of:
  1. Revert to `scope.STREET_WORDS` (the dispatched version, which met (b)). Bare "500 Broadway"-style addresses then fail closed to manual intake, which is acceptable.
  2. Keep a looser form only if it also needs a city, state or ZIP after the street name (e.g. `500 Broadway, San Antonio, TX`), and it rejects `PO Box`.
  3. Either way, add these as self-check cases that must give `location_count_unclear`: `"1 Location"`, `"Seats: 40 Indoor"`, `"PO Box 9 Waco"`, `"2 Stores"`, `"Est. 2009 Family owned"`.
- Closing evidence: the fixed `prepare.py` self-check, plus `tests/pipeline` re-run. Medium/Low need no new evidence.

## Medium / Low (backlog, one line each)
- M1: A3 (second street address) sends files whose email gives a *different premises address* (SUB-022/032/042/052, SUB-014) to manual intake labelled "multiple locations". These look like address discrepancies, not second places, so the card may mislead. The quick set also loses 2 of 17 model-reaching files. Replacing them is @user's decision.
- M2: a model count of 1 is weak evidence by design: it is checked against a single quote. A second place in an unsent file (past MAX_CHARS), or a non-standard address, depends on Part A. Track the `location_count_unclear` and `multiple_locations` rates on the next quick set.
- L1: B-508 screenshot shows "scope-v4" (taken before v5). Cosmetic; retake when convenient.
- L2: "No other locations." fires A1 (negation not read). Accepted fail-closed, but it adds false manual intake. Count it in M2 monitoring.

## T-126 note
`blocked_reasons` is the single helper behind `status_refusal`, `scope_problem` and the manual-intake card; the extended test asserts the scanner leads in all three. No findings.

## Look-again (the one allowed), 2026-11-02: H1 CLOSED

- Change: `prepare._shows_one_address` = (`scope.STREET_WORDS` or `CITY_STATE_ZIP`) and not `PO_BOX` and not `scope.COUNT_PHRASE`; new self-check cases. `test_lob_config.py` changed only its import.
- Re-probed `_location_problem` directly (count 1, quote in file). These now give `location_count_unclear`: "1 Location", "Number of locations: 1 Location", "Seats: 40 Indoor", "Employees: 12 FT", "Effective 2027 TX", "Policy period 12 Months", "2 Stores", "We have 1 Store", "Est. 2009 Family owned", "PO Box 9 Waco", "P.O. Box 9, Waco, TX 76701", "Years in business: 9", "500 Broadway", "We run two stores at 100 Main St". These stay in scope: "100 Main St, Austin", "500 Broadway, San Antonio, TX 78205", "2801 E 42nd St".
- Re-run on a temp copy: `prepare.py` self-check ok; `tests/pipeline` 94 passed. Real worktree unchanged apart from this review.
- **Final T-127 verdict: APPROVE.** No High open. This is not a production approval; the T-027 veto stands.
- New Medium (backlog): M3: with a count of 1, a quote that holds two street addresses ("100 Main St and 200 Elm St") or a mailing address ("Mailing address: 100 Main St, Austin, TX 78701") still passes Part B. Part A's A3 rule catches the two-address case on the document text. Tighten Part B to need exactly one non-role address when convenient.
