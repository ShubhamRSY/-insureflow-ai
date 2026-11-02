# P-075 look-again — @model-risk (D-129 one look-again, D-133)

- Date: 2026-10-26. Worktree `insureflow-fix-t117`, branch `p075`, uncommitted vs `ec48f66`.
- Scope: H1 and H2 from `P-075-check.md`, plus a re-check that the P-075 criteria still hold. Author messages not read.
- No model call. LLM_* unset. The end-to-end probes stubbed only `llm_extract._post`, used a temp copy of SUB-301 and a temp cache in my scratchpad, and are kept at `scratchpad/p075_recheck_probe.py`. `git status` was the same before and after every run. Nothing was written in the worktree except this file.
- This look-again is not a production approval. The T-027 veto stands.

## H1: the copied line's note claimed no other document states cooking. CLOSED

- `REASON_COOKING_COPIED` now reads "cooking line copied from the application (P-075); check the other documents for cooking". It makes no claim of absence.
- Test `test_copied_note_never_claims_absence`, and a self-check assert on the SUB-301 reason in `prepare.py`.
- `grep "no other document"` over `underwriting_pipeline/`: the only hit is that assert.
- End to end, clean SUB-301: the line is copied, there is no conflict, the row reason is the new note, and the status is "complete — review pending".
- `P-075-copied.png` shows the new note together with "not read by the model".

## H2: the word list was not fully built. CLOSED

- `_COOK_PHRASES` now matches `heat(?:s|ed|ing)? (?:up|food|soup|meals?|water)`, `food prep\w*` and `ul ?300` (hyphens are folded to a space first). It also catches "frial" as a word start.
- Test `test_p075_check_sentences_hold` covers 13 sentences, including every form named in the check.
- I re-ran my own earlier sentences end to end on SUB-301, plus three new variants. Each one opened a `cooking` conflict, copied nothing and gave `ready_to_route` False:
  - "The insured heats up food for staff in the back."
  - "A frialator was added."
  - "We do food prepping for events."
  - "Staff heated up soup at noon."
  - "Hood is UL-300 listed."
  - "Heating meals for the crew."

## P-075 criteria re-check

| Criterion | Result |
|---|---|
| tests/pipeline | 93 passed (91 before, plus the 2 new tests) |
| Self-checks | `prepare ok`, `workbench ok`; worktree unchanged after the run |
| Probes | fixture byte-identical to `P-075-probes.json`; every hold probe held (test passes) |
| Requests | `llm_extract.py` and `sources.py` unchanged vs ec48f66; the baseline test passes (0 of 143 changed) |
| Frozen files | none in the diff or untracked (eval_holdout_*, lint_holdout, hold-out gold, simulation/inbox/, cache/, P-073 v12) |
| Copy / infer / conflict | copies only the typed none-line; any cooking word elsewhere opens a conflict and holds; the copied row stays NEEDS REVIEW and never makes the file complete |
| ReDoS | the new pieces have no nested quantifiers; the 10,000-space test passes |
| Effects | only toward held or review (no copied file loosens; see the as-built replay) |

## Medium / Low (backlog, one line each)

- L1: `"ul300"` in `_COOK_TOKENS` is still dead code, because the tokenizer drops digits. The phrase covers it. Remove it when next touched.
- L2: the card's "Cooking: not scored — no cooking equipment stated in the file" (points.py, from before P-075) sits next to a copied none-line. It is accurate, but it reads close to an absence claim.
- These items from the earlier check remain open on the backlog: M1 false holds, M2 name not blanked, M3 resolving a conflict does not update operations, L1 words outside the list, L2 quick-15 replayed for only 5 of 15 files, L3 status label.

## Verdict

**APPROVE.** H1 and H2 are closed, each with a test, and every P-075 criterion I re-checked still holds. There are no High findings. This is a build approval under D-133, not a production approval: the T-027 veto stands.
