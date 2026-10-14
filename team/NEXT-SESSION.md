# Next session

Written 2026-10-13 by the orchestrator at wrap-up. Wrap-up commit: `6e68f1b` on `ai-team`, pushed to `origin/ai-team` (private). Read CLAUDE.md "Usage budget rules" first: demo blockers only, sessions of 2–3 hours, one-line estimate at the start.

## Where we stopped

- Three architecture documents are written and IN_REVIEW: T-094 `architecture.md`, T-095 `system-design.md`, T-096 `low-level-design.md` (all in `deliverables/architecture/`). They describe `dd45467`; HEAD's `underwriting_pipeline/` is identical to it.
- T-094 was approved twice by @model-risk and @compliance on an earlier version. Since then it was re-cited to `dd45467` and needs a second look. T-095 and T-096 have had no review.
- **Stale in the documents, not fixed** (the turn was cut off by the usage limit):
  - `architecture.md` still shows T-071 as TODO and the T-059 veto as open.
  - Neither document states D-053 (the send rule) or D-054.
- An OpenCode session ran alongside today. It committed an unreviewed T-079 build (`db7cbb1`), which was reverted in `5e0f180`. Both parts are kept as `deliverables/software-engineer/unknown-edit-package*.patch`. Its D-052 is superseded by D-053.
- **Under D-054, the following are the user's to confirm** before anyone relies on them; this session did not write them:
  - D-041 to D-044.
  - P-019 and T-099 (move to Vertex AI and Document AI).
  - T-100 and `deliverables/ml-engineer/gcp-migration.md`.
  - `deliverables/ai-engineer/evals/scratch/`.
- Self-checks at wrap-up, no model host set: llm_extract, prepare, intake, package, workbench and points all ok.
- Not committed, left alone: `src/insureflow/`, `tests/`, `docs/rag/`, `scripts/`.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 (12.6 of low-level-design lists what P-006 leaves unset) |
| P-011 read-only published scores | T-072 |
| P-015 score fixes | no build task |
| P-016 citations, confidence, unread content | no build task |
| P-017 commit hash and status in score output | with T-072 |
| D-048 exits from `all_values_rejected` | no build task |
| D-050 producer-request rule | T-098 |
| D-053 send rule (latest decision approve; written reason if after a decline; full history kept) | T-079 rebuild |

P-010 is built (T-070, T-071 DONE).

## Pending decisions for the user

1. P-018 (error enum): waits on `approve change P-018`.
2. Confirm or reject, per D-054: D-041 to D-044, P-019/T-099, T-100.
3. T-079 points D-053 does not settle: how "last" is ordered (the log has a date, no time) and which ids count as an underwriter.
4. OCR price basis in the cost model: Layout Parser at $10.00 per 1,000 pages (D-038) or Enterprise Document OCR at $1.50.
5. Who updates the stubbed test file to the T-071 signatures (5 cases error at `dd45467`): @software-engineer or @ml-engineer.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-017 | @model-risk, @responsible-ai | P-015 built and looked at again |
| T-020 | @compliance | Items (a) to (f); (b) met by T-071; formal re-check pending |
| T-027 | @model-risk (production) | P-016 built, then the new 20-file hold-out scored once (T-091 to T-093) |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md`; D-042 does not lift it |

T-059 and T-026 were lifted by @model-risk today.

## First 3 tasks next session

1. T-079 rebuild by @software-engineer from the two saved patches, to D-053, then its reviewers (demo blocker 2).
2. The next demo blockers in `team/DEMO-BLOCKERS.md` (T-085, T-086, T-087 for the T-020 veto items).
3. Only after the demo, per budget rule 8: fix the stale lines above in `architecture.md`, then the reviews of T-094 (second look), T-095 and T-096.

## For the AI Engineer

- Pending proposals: P-018 waits on your approve line. P-019 needs your confirmation under D-054.
- Latest eval scores: no new run this session. Baseline SUB-077 to 086: 2 of 8 scored fields at the D-013 pilot floor of 9/10 ("8 of 9 fields scored; loss runs = date only").
- Top failure to fix next: a carrier send does not require a logged underwriter approve (T-079).
