# P-074 — A conflict the pipeline cannot verify stays open and holds the file; "million" is read; approximate amounts never verify an exact figure

- Author: @ai-engineer-assistant, 2026-10-24. **Not approved, not built.** Draft for @user to read (D-131). Development data only. Not a production approval; the T-027 veto stands.
- Raised by @model-risk T-027 memo after T-119, High H2 (`deliverables/model-risk/T-027-memo-T-119.md`, backlog B-469). Scope is the user's own, D-131. H1 (cooking) is P-075, later.

## Problem (SUB-345, from the stored reply, read from a temp copy; nothing run)

The model did the right thing: `sales_or_payroll` 1,240,000 (application, "Annual sales: $1,240,000") against 1,420,000 (email, "Last year we did about $1.42 million"). The pipeline turned it into one flagged figure and no conflict:

1. The quote check (`llm_extract.value_in_span` → `_quote_numbers`, regex `_NUM`) knows `k`, `m`, `mm`, `b`, **not** the word "million". So 1,420,000 is "not inside the cited text" and that side is rejected.
2. One side kept, one rejected: the P-038(c) branch (`llm_extract.py` ~929) keeps the application figure flagged "conflict with rejected value" and **appends no conflict**.
3. The P-070 backstop `apply_sales_conflicts` misses the email (no sales word in "we did about $1.42 million", and `AMOUNT_TOKEN` has no "million" either).
4. Result: "complete — review pending", no open conflict, so `ready_to_route` (`prepare.py` 662–667) passes. Gold says "incomplete — hold: open conflict (sales)".

## Where a model-raised conflict is dropped today (every path)

All in the conflict loop of `llm_extract.llm_extract` (`for item in parsed["conflicts"]`, ~908–958). A "rejected" side is one `accept_field` empties (quote not found, value not in quote, confidence under the line, scan floor). Today each of these ends with no conflict:

| # | Shape | Today | Line |
|---|---|---|---|
| D1 | 1 side kept, ≥1 rejected (not premises) | keeps the kept value, flagged; conflict dropped (SUB-345) | ~929 |
| D2 | every side rejected | falls through every branch: nothing is stored, nothing is raised | end of loop |
| D3 | ≥2 sides kept with the **same** value, one rejected with another | the `elif` needs two different values: dropped | ~955 |
| D4 | premises with a schedule: kept sides agree with a schedule row, a rejected side exists | kept side stored; rejected side dropped | ~946 |
| D5 | ≥2 kept with different values, plus a rejected third side | conflict opens (held) but the rejected side is not on it | ~955 |

Checked and **not** changed, because the side is verified, not unverifiable: sides that agree once normalized (`agrees`, H3 every-pair, `prepare.py` ~1253); P-037 typed-vs-scan (a scan side never opens a conflict, the field is flagged); P-056(e) and P-005 labelled locations; the P-036 schedule split; a producer reply (`_apply_reply`).

Also: with D2 fixed, a reply whose only content is that conflict is no longer an "all-empty reply" (`prepare.py` ~1208, `rejected = True`); it is an answer with an open conflict.

## Change

**A. Unverified side keeps the conflict open (D1–D5), `llm_extract.py` conflict loop.**
- A rejected side is kept as a conflict side with the model's stated value, its source and quote, `"unverified": true`, and the reason `accept_field` already computed ("quote not found in email.md", "value not inside the cited text", "confidence 0.xx is under …").
- If at least two sides (kept or unverified) are present and they are not all the same verified value, a conflict is appended. The existing downstream code (`prepare.py` ~1246–1270) then empties the field, marks it NEEDS REVIEW and holds the file. A side with an empty model value is still no disagreement (as today).
- P-038(c)'s "keep the valid side, flagged" branch is removed for sides the model raised as a conflict. A rejected value is never promoted to a number (no change to that rule).
- Nobody can drop it later: an unverified side is only cleared by an underwriter's resolve (B-324) or a producer reply, as for any open conflict.

**B. "million", "thousand", "k" are read.** `_NUM`, `_AMOUNT` and `AMOUNT_TOKEN` (the P-070 sales rule) accept "1.42 million", "$1.2 million", "250 thousand", "250k", "1.2m", "1.2mm" (units as whole words, case-insensitive). So SUB-345's 1,420,000 verifies as a number. The P-070 sales rule can now read such amounts when a sales word is beside them.

**C. Approximate amounts are kept as approximate.** Words that make an amount approximate when they sit directly before it (or "or so" / "give or take" after it): **about, around, approximately, approx., roughly, nearly, almost, close to, circa, ~** (found in code: `_AMOUNT`, `AMOUNT_TOKEN`; in dev data: about 43, around 23, approximately 2, roughly 1, "close to" 1; no "over/under/at least" found). Not on the list: the label "Estimated annual sales:" (a form label, not a hedge in the sentence); the build reports any further hedge word it finds in dev data before it is added.
- Today `amount_value` silently drops these words, so "about $1.42 million" verifies as an exact figure. After P-074 a number whose quote hedges it **does not verify an exact value**: the value is kept with NEEDS REVIEW and the reason "approximate figure: <quote>". It is never dropped and never counted as the exact figure.
- In a conflict, an approximate side is a conflict side (flag `approximate`), so SUB-345 opens: 1,240,000 vs about 1,420,000.
- Equal numbers still merge (1,240,000 and "about $1.24 million" are one number, as today); the exact side wins and the approximate quote is kept as `also_quoted`. Different numbers conflict (held).

## Status effects (only toward held or review; no gate is loosened)

| Case | Before | After |
|---|---|---|
| Model conflict, one side unverifiable (D1–D4) | complete — review pending, passes send gate; or no trace | incomplete + open conflict, held, no carrier match, no send |
| Model conflict, every side unverifiable (D2) | nothing stored | open conflict, held |
| "about / roughly / ~ …" quote on a number field, no conflict | stored as exact, not flagged | stored, NEEDS REVIEW "approximate figure" (complete → complete — review pending) |
| "$1.42 million" quote (SUB-345 email side) | side rejected | side verified (approximate: flagged) |
| Everything else | unchanged | unchanged |

- Nothing moves toward complete or sendable. `ready_to_route`, the send gate, `completeness`, carrier match, appetite and routing are not edited. No confidence line, scan floor or quote rule is relaxed: B only reads an amount the quote really holds ("1.42 million" is 1,420,000).
- One watch item: a quote that holds a hedged number now reads as a review flag where before it was clean. That sends more files to a person, never fewer.

## Request equality, prompt, cache

- `SYSTEM` and `request_for` are not touched, so `PROMPT_VERSION` (759b3e6bc9b2) and `cache_key` stay the same, and **zero requests change**. Stored replies stay valid; the rules run on them with no model call.
- `tests/pipeline/test_request_equality.py` (SUB-127–269, byte-identical request with `LOB_ENGINE` off and on) must stay green unchanged. It only compares requests, so it does not cover the new rules; the dev checks below do.

## Dev checks only (no model call, no hold-out file)

- **SUB-345 as a new dev file: SUB-297**, in `simulation/inbox-dev/document_conflicts/`, built by `deliverables/producer/build_document_conflicts_dev.py` (same builder as SUB-293–296) with a dev note and manifest line. New names and figures (application sales 1,180,000; email "about $1.35 million, the application is the budget"), carrier loss run in the published format so the file does not hold on anything else. The model reply is **stubbed** with the SUB-345 stored conflict shape (read, never written, from a temp copy of the cache). Expected: open `sales_or_payroll` conflict, sales empty, status not complete, not routed, card shows the reason.
- **SUB-298**: the same with every side unverifiable (D2) and a "~$1.2m" side (approximate).
- Re-run on dev, expected unchanged status unless a hedge word is in a number quote (list each change): SUB-293–296 (P-070 cases), SUB-348/349-style shapes (cooking conflicts are not raised here; they stay held/flagged as today, H1 is P-075), SUB-350 (operations only, unchanged).
- Rule-level self-checks in `llm_extract.py` and `prepare.py` for D1–D5, "million/thousand/k", each hedge word, "about 1.24 million" vs 1,240,000 (merge), "about 1.2 million" vs 1,240,000 (conflict).
- `python underwriting_pipeline/ai/prepare.py` self-check, `llm_extract` self-check, `workbench ok`; `pytest tests/pipeline` green; `regression_dev.py --quick` after the build (D-022) with any field whose hit count drops reported; pyright shows no new finding.
- @model-risk check, High only, one look-again (D-129, D-131).
- **Frozen, not touched:** every `underwriting_pipeline/ai/eval_holdout_*.py` scorer, hold-out gold (SUB-340–371 and earlier sets), hold-out files under `simulation/inbox/`, every published score file (v11 stays frozen), `underwriting_pipeline/cache/T-119-live`.

## D-065 (the workbench)

Yes, a small change. A conflict side with `unverified` or `approximate` shows its reason on the Conflicts list and in the resolve form (`workbench.py` ~1206 and `resolve_form`):
- "Not verified against the document: <reason>. Check it on the page before you choose it."
- "Approximate figure: 'about $1.42 million'. It does not confirm an exact amount."
- The refusal text for a held file is the existing "OPEN: no send until the underwriter chooses or enters the value"; nothing new to refuse.
- "What's new" line (date, P-074, D-131 or the decision for this change). Playwright screenshot of the SUB-297 card on a temp copy (D-069), saved as `deliverables/software-engineer/screenshots/P-074.png`. @senior-underwriter UI check, High only.

## Risks

- A hedge word in a sales or square-feet quote now adds a review flag. Expected on a few dev files; the build counts them first.
- More conflicts on files where the model raised a disagreement the old code hid. That is the point; each is held for the underwriter, who can resolve it on the card.
- A model-raised conflict whose "unverifiable" side is a model hallucination also holds the file. Cost: one underwriter click. Fails safe.
- Word list is a choice: "nearly/almost/circa" are extra to the user's three words; say so if you want them out.

## Not included

- H1 cooking (copy the stated line, cooking mention elsewhere → conflict, whole-document check): P-075.
- A sales rule for sentences with no sales word ("we did about $1.42 million"); the model raising the conflict is what P-074 protects.
- Any scorer or hold-out change; any gate, route, appetite or send rule; the prompt.
- Medium/Low from the memo (B-470–B-477).

To approve, the user types: `approve change P-074`.
