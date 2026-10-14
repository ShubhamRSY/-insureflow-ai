# Next session

Written 2026-10-14 by the orchestrator at wrap-up. Wrap-up commit: `ff8cf63` on `ai-team`, pushed to `origin/ai-team` (private). Read CLAUDE.md "Usage budget rules" first: demo blockers only, sessions of 2–3 hours, one-line estimate at the start.

## Where we stopped

- D-061: the user typed "approve change P-020" (an input-document sha256 manifest in each saved run; the send refuses on a mismatch). **Approved, not built**; it needs a build task (@ai-engineer-assistant for `prepare.py`, @software-engineer for the send gate). Not a production approval.
- T-083 carrier match (D-059 as amended by D-060 and D-061) is built. The High-1 fix was made in the main session: `_tiv` uses `prepare.amount_value()`; a missing, blank, "TBD" or unreadable TIV holds ("TIV missing or unreadable"; "$1.2MM" holds because the normalizer does not read MM). The over-$10M rule is removed; over $5M per location is senior referral "outside pilot TIV limit (AG:16)".
- @senior-underwriter re-check: **APPROVE**, no High. Medium/Low: B-199 to B-204 (B-203 Medium: "$0" routes to carrier_a, should hold). T-083 stays IN_REVIEW for its other reviewers (@head-of-underwriting, @compliance, @responsible-ai, @model-risk).
- Backlog from D-060: B-197 (Spanish variants review), B-198 (housing proxy review, required before pilot).
- T-087 High-1 is fixed in `underwriting_pipeline/app/quotes.py` and `workbench.py`. The status comes from the reply's first line: QUOTE is quoted, DECLINE is declined by carrier, anything else is "reply needs human reading". A subjectivity is none only for exactly "none." or "none beyond the file as sent.". Per D-058, a carrier's "satisfied" is evidence only, and a listed underwriter closes a subjectivity with a logged one-click action on the workbench (`deliverables/software-engineer/subjectivity_closures.jsonl`). The form was checked in the rendered card only; the server was not run.
- @compliance re-checked T-020 item (e): **APPROVE**. **The T-020 veto is lifted**: all six items, (a) to (f), are met. Medium/Low: B-194 (Medium, before real carrier replies: a QUOTE with no Subjectivities line, or with the header in other capitals, shows "none"), B-195, B-196.
- D-058 recorded: D-043 confirmed; D-041, D-042, D-044 void as unverified.
- The D-057 carrier override is built in `package.py`: no_match only, never hold; the user names the carrier and gives a reason; the label "Outside matched appetite — placed by underwriter override"; logged in `sends.jsonl`. @compliance: no finding.
- D-057 recorded. B-190 (required before real data: authenticated underwriter action) and B-191 (required before pilot: concurrent decision-log writes) are on the backlog.
- T-085 and T-086 are IN_REVIEW. @compliance approved T-020 items (b), (c), (d).
- T-079 has @compliance APPROVE (D-055 build). T-079, T-085, and T-086 still wait on @senior-underwriter and @account-manager (T-079 also @model-risk).
- Stubbed test file, as measured by @software-engineer after T-087: 22 pass, 8 known-gap, 3 skip, 1 error (B-191), 1 fail (token-log count, 28 rows against 13; not touched).
- Self-checks at wrap-up, no model host: llm_extract, prepare, intake, package, workbench, and points all ok.
- Parked until after the demo: P-019, T-100, and P-018.
- Not committed, left alone: `src/insureflow/`, `tests/`, `docs/rag/`, `scripts/`.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-015 score fixes | no build task |
| P-016 citations, confidence, unread content | no build task |
| P-017 commit hash and status in score output | with T-072 |
| D-048 exits from `all_values_rejected` | no build task |
| D-050 producer-request rule | T-098 |

## Pending decisions for the user

1. P-018 (parked). P-019/T-099 and T-100: parked.
2. OCR price basis in the cost model: $10.00 or $1.50 per 1,000 pages.
3. Whether to widen `prepare.amount_value()` to read "MM" (a change under `ai/`, needs its own approve line); today "$1.2MM" holds.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-017 | @model-risk, @responsible-ai | P-015 built and looked at again |
| T-027 | @model-risk (production) | P-016 built, then the new 20-file hold-out scored once (T-091 to T-093) |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. Build P-020 (approved in D-061): @ai-engineer-assistant stores the input manifest in `prepare.write_drafts()`, @software-engineer makes the send refuse on a mismatch; then its reviewers.
2. B-203: a TIV of 0 should hold (small, `workbench.py`).
3. The remaining reviewers of T-079, T-083, T-085, T-086, T-087; then @pm closes what is approved.

## For the AI Engineer

- Pending proposals: P-020 approved (D-061), not built; P-018 and P-019 parked.
- Latest eval scores: no new run. Baseline SUB-077 to 086: 2 of 8 scored fields at the D-013 pilot floor of 9/10.
- Top failure to fix next: the send does not check that the input documents are the ones extracted (P-020, approved, not built).
