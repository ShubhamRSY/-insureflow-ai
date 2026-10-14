# Next session

Written 2026-10-14 by the orchestrator at wrap-up. Wrap-up commit: `832fd90` on `ai-team`, pushed to `origin/ai-team` (private). Read CLAUDE.md "Usage budget rules" first: demo blockers only, sessions of 2–3 hours, one-line estimate at the start.

## Where we stopped

- D-062: P-020 built (each saved run stores `input_manifest`, covered by `saved_hash`; `package.send_to_carrier` calls `prepare.manifest_problem()` after the P-010 status gate, every actor; a document added after extraction refuses the send). P-021 approved and built (`amount_value()` reads "MM": "$1.2MM" = 1,200,000). B-203 fixed (TIV 0 or negative holds). Memo: `deliverables/ai-engineer/p-020-p-021-as-built.md`.
- @compliance on P-020: **APPROVE**, no High. Medium: B-205 (manifest built after extraction; build it before) and B-206 (dotfiles skipped by the manifest, read by `sources.read_folder`); both are `ai/` changes and need their own approve line. Low: B-207, B-208.
- @senior-underwriter on the TIV cases: **APPROVE**, no High. Medium: B-209 ("50,000 sq ft" in the TIV field reads as $50,000). Low: B-210.
- **Before any demo send (B-208):** all 16 saved runs SUB-001 to SUB-016 have no manifest (they are old-format and G2 already refused them), so every send is refused until they are re-saved by `write_drafts()`. That makes no model call only if every submission hits the cache (coverage not checked).
- The quick set of 15 owed after P-021 (D-020/D-022) was not run: no model host in the shell.
- Stubbed test: 24 pass, 9 known-gap, 1 error (B-191), 1 fail (token log).
- T-083 carrier match: @senior-underwriter APPROVE; other reviewers pending.
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

1. B-205 and B-206 (manifest timing, dotfiles): each needs a P-number and "approve change P-###" before a build.
2. Re-saving SUB-001 to SUB-016 with a manifest (B-208): needs the cache coverage checked, or a model host.
3. P-018 (parked). P-019/T-099 and T-100: parked.
4. OCR price basis in the cost model: $10.00 or $1.50 per 1,000 pages.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-017 | @model-risk, @responsible-ai | P-015 built and looked at again |
| T-027 | @model-risk (production) | P-016 built, then the new 20-file hold-out scored once (T-091 to T-093) |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. @ai-engineer-assistant checks cache coverage for the demo submissions and, if covered, re-saves them with a manifest (B-208); otherwise reports what needs a model host.
2. B-209 in `workbench.py` (a TIV with "sq ft" must hold), small.
3. The remaining reviewers of T-079, T-083, T-085, T-086, T-087; then @pm closes what is approved. Run the quick set of 15 once a model host is set.

## For the AI Engineer

- Pending proposals: none awaiting your line; B-205/B-206 need numbering. P-018 and P-019 parked. P-020 and P-021 built.
- Latest eval scores: no new run; the quick set of 15 is owed after P-021. Baseline SUB-077 to 086: 2 of 8 scored fields at the D-013 pilot floor of 9/10.
- Top failure to fix next: no saved run has a manifest, so every send is refused until they are re-saved (B-208).
