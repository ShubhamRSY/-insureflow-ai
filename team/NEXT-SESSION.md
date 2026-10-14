# Next session

Written 2026-10-14 by the orchestrator at wrap-up. Wrap-up commit: `984fa0f` on `ai-team`, pushed to `origin/ai-team` (private). Read CLAUDE.md "Usage budget rules" first: demo blockers only, sessions of 2–3 hours, one-line estimate at the start.

## Where we stopped

- D-059 (carrier match, re-raised by @head-of-underwriting) is approved with the user's changes as D-060. The hash basis is confirmed as built. P-018 stays parked.
- D-060 also asks for a sha256 manifest of the input documents in each saved run, with the send gate refusing on a mismatch. That is a change in `underwriting_pipeline/ai/prepare.py`, so it is numbered **P-020** and is built only after the user types "approve change P-020". Not built.
- T-083 is built in `underwriting_pipeline/app/workbench.py` (`match()`, `route()`) and `package.py` (same function; the D-057 override only on overridable no_match). Status IN_REVIEW.
- @senior-underwriter: **APPROVE WITH CHANGES**, not DONE until High-1 is fixed. High-1, caps fail open: `_tiv` takes the first number, so "$8M" reads as 8 and the $8M office routes to carrier_a; a blank or "TBD" TIV counts as 0. Fix, as written: read M/MM/million/K suffixes; return hold with "TIV missing or unreadable" when absent or unparseable; self-checks for "$8M" and a blank TIV. Medium/Low: B-199 to B-202 (Medium: "bar" matches "bar-b-q", "salad bar"; TIV is `tiv_building` only).
- Builder's choices to confirm: over-$10M no_match is not overridable; the loss-run gate is not built (no loss-run field).
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

1. P-020 (input-document manifest in each saved run; send refuses on mismatch): waits on "approve change P-020".
2. Over $10M as no_match: overridable or not (built as not overridable; D-060 does not say).
3. P-018 (parked). P-019/T-099 and T-100: parked.
4. OCR price basis in the cost model: $10.00 or $1.50 per 1,000 pages.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-017 | @model-risk, @responsible-ai | P-015 built and looked at again |
| T-027 | @model-risk (production) | P-016 built, then the new 20-file hold-out scored once (T-091 to T-093) |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. @software-engineer fixes T-083 High-1 exactly as @senior-underwriter wrote it, then @senior-underwriter re-checks.
2. If the user types "approve change P-020": the input manifest (@ai-engineer-assistant for `prepare.py`, @software-engineer for the send gate), then its reviewers.
3. The remaining reviewers of T-079, T-083, T-085, T-086, T-087; then @pm closes what is approved.

## For the AI Engineer

- Pending proposals: P-020 waits on your approve line; P-018 and P-019 parked.
- Latest eval scores: no new run. Baseline SUB-077 to 086: 2 of 8 scored fields at the D-013 pilot floor of 9/10.
- Top failure to fix next: the carrier caps fail open on "$8M" and blank TIV (T-083 High-1).
