# Backlog — T-021 review (@model-risk, 2026-10-11)

Medium and Low findings only (D-030). The High finding is in the REVIEW message in team/DISCUSSION.md. Recomputed with a scratch log outside the repo; no model call, no queue run.

- Medium: `correction_counts` counts log rows, not submissions, and has no denominator. One file with edit, edit, approve shows "Corrections: 2" and one approval. The "% of submissions with no corrections" metric needs the last decision per submission over the submissions decided.
- Medium: the submission id is not checked. A row with no submission, or with SUB-999, is stored and counted as an approval.
- Medium: the actor is free text with no login and no roster check. `@ai-engineer-assistant` is accepted as the underwriter id. This becomes High the day the D-033 send gate reads this log.
- Medium: an edit stores only a free-text reason. No field, old value, new value, or copy of what the AI showed (points, codes, carrier match). Nobody can tell what was corrected. Overlaps D-031 item 5 (P-015).
- Medium: every decline is counted as a correction. Declining a correctly prepared file is not an AI error. The metric definition needs a ruling from @pm and @head-of-underwriting.
- Medium: a decision is accepted on a file whose status is `extraction_failed` or `all_values_rejected`, and an approve there counts as "no correction".
- Medium: the row stores a date and no time. "Approve with no later decline" (D-033) would rest on line order alone.
- Medium: one malformed line makes `correction_counts` raise JSONDecodeError and stops `serve()` at start. The append has no lock under ThreadingHTTPServer.
- Low: the page is rendered once at server start. After a POST the counts shown are stale until restart, though feedback-loop.md says the page shows them.
- Low: approve may have an empty reason. The criterion says every decision has a reason. The memo discloses this.
- Low: rows are not labeled synthetic. The log is written by the app into `deliverables/software-engineer/`, is not in `.gitignore`, and has no tamper check.
- Low: the self-check tests only the `+rules-d015` suffix of `ai_version`, never a decline count, and never two decisions on one file.
- Low: no `decisions.jsonl` exists, and the POST handler has no test. The memo gives no metric formula, no monitoring owner, and no limits section.
- Low: the POST has no origin check, and the 400 reply has no content type. The server binds to 127.0.0.1 only.
