# @model-risk answer on P-055 pilot scope (D-102 item 3)

- Author: @model-risk (independent). 2026-10-16.
- Read: `deliverables/pm/proposal-P-055.md`, `deliverables/model-risk/T-027-gate-memo-T-103.md`, `deliverables/ai-engineer/analysis/T-103-root-cause.md`, `deliverables/ai-engineer/evals/SUB-154-173-holdout-v4.json`, `deliverables/model-risk/validation-standards.md`, D-102. Row counts of the T-103 `schedule.csv` files.
- Recomputed from the score JSON `checks` (no model call, nothing rescored, no file other than this one and the two team logs written).
- Synthetic data. Not a production approval. An approved P-055 would not be a production approval either. The T-027 veto stands.

## Verdict: ACCEPT WITH CONDITIONS

The scope is sound in kind: sending a whole file to a human when the pipeline is known to fail on it is the right failure behaviour for a Tier 2 component, and it does not touch extraction, prompts, OCR or scorers. I accept it as the boundary for a scoped T-027 gate if H1 and H2 below are met before the new gold is written. Scope alone does not lift the veto (see H1).

## What the gate needs for a scoped production lift

**Detection measures** (the detector is a new Tier 2 component; inventory entry, version id, deterministic rules preferred):

| Measure | Definition | Target |
|---|---|---|
| Leakage (hard gate) | Out-of-scope files that show any field as complete, status complete or complete — review pending, any carrier or provisional route, any carrier suggested, or a send action enabled ÷ out-of-scope files | 0. Any leak fails the gate |
| Detection recall | Out-of-scope files sent to manual intake ÷ out-of-scope files, per criterion and overall | 100% overall; every criterion detected on every file of that criterion |
| Reason accuracy | Manual-intake cards whose listed reasons equal the gold scope labels | 100% of matched reasons listed (extra reasons allowed, a missing one is a miss) |
| False manual intake | In-scope files sent to manual intake ÷ in-scope files | Ceiling set by @user before the gold is written; reported always. A file sent to manual intake by mistake is removed from the in-scope gate denominator only if the ceiling is met |
| Fail closed | Detector error, unknown language, unknown text layer | Manual intake, never in scope. `extraction_failed` keeps precedence (D-021) and is counted apart |

**Hold-out mix:** one new frozen set, gold first, scope label in gold for every file, scored once, no code change after the gold exists:

- **20 in-scope files**, so the unchanged gate (9/10 per field, route 18/20, 0 false completes, 0 unsafe routes) keeps its 20-file denominator. At least 6 of the 20 are boundary cases that must stay in scope: scanned or image-only carrier loss run with a typed application; English email with an application attached; English application with a Spanish email or a Spanish business name; one-row schedule; application that mentions a second address that is not a location (mailing address, prior address).
- **12 out-of-scope files**: 3 per criterion (scanned application, email-only, non-English, multi-location), of which at least 3 match two criteria. Include each criterion in a near-pass form (scanned application with a good OCR score, multi-location only in a schedule file, Spanish application with English email).
- 32 files total. D-020 says new hold-outs are 20 submissions; the 12-file detection set is either a separate frozen set or needs @user's word to extend this one. Either is acceptable to me.
- With 12 out-of-scope files, 0 leaks gives an upper bound near 22% (95%), so leakage stays a monitored metric in shadow on every file (M2).

**T-103 under the scope:** published scores are never rewritten, and T-103 cannot count toward the scoped gate (H1). A post-hoc re-read may be written as a new, separate file labelled "post-hoc, not gate evidence". My recompute of that re-read, for the record:

| Field | All 20 (published) | 15 in scope (excl. 163, 168, 169, 170, 172) |
|---|---|---|
| named_insured, premises, effective_date, sales, tiv, construction, year_built | 80–95% | 15/15 each |
| operations | 7/20 | 6/15 (40%) |
| loss_runs | 5/9 | 5/9 (scanned loss runs 159–161 stay in scope) |
| route | 16/20 | 14/15 (SUB-167 "hold" gold) |

Even post hoc it fails: 7 of 9 fields at the floor. The five excluded files carry 30 of the 49 non-hit marks. On T-103 those five were already held "incomplete" with no carrier route, so leakage would have read 0 of 5 with no detector at all: leakage by itself proves nothing about detection.

## High findings

### H1 — The scope was drawn from the hold-out it would be judged on (owner @pm, @user)

- Each criterion is taken from a T-103 failure (170 scanned; 168, 169 email-only; 163, 169 Spanish; 172 multi-location). Removing them lifts 7 fields to 15/15 by construction. That is selection after seeing the results, not evidence the pipeline works on in-scope files.
- In scope, operations (6/15, mostly scorer and gold wording per the root-cause table) and loss_runs (5/9, scanned carrier loss runs) still fail. The H1/H2 items of the T-027 memo that are not out-of-scope criteria remain open: 2-digit-year dates, OCR word floor on loss runs, reword flag on a trailing period, extras rule on "kitchen"/"restaurant", SUB-169 laundry route.
- Remediation: (1) T-103 is not re-scored and not used as gate evidence; any re-read is a new file labelled post-hoc. (2) The four criteria, the two open questions (scanned loss runs, schedule-only multi-location) and the false-manual-intake ceiling are fixed in writing by @user before the new gold is written, and do not change after. (3) The in-scope gate is met on the new set only.

### H2 — The detection measure as drafted cannot show the detector works (owner @pm, build owner)

- P-055 measures leakage only, and defines it as "shown as complete or routed to a carrier". On T-103 that reads 0/5 with no detector (see above), and it does not count a provisional route with "Carrier A suggested" (SUB-169 today), a "complete — review pending" status, or an enabled send.
- No recall per criterion, no reason accuracy, no fail-closed rule, no minimum count of out-of-scope files, no false-positive ceiling.
- Remediation: adopt the measure table and the 20 + 12 mix above, in P-055, before the gold. Add the detector to `model-inventory.md` as Tier 2 with version id; any change to its rules is a change under D-017 and needs revalidation.

## Medium and Low (backlog, one line each)

- M1: "non-English" needs a rule for mixed files (English application, Spanish email; Spanish business name) and a stated detector; set it before gold, include in the boundary cases.
- M2: report the manual-intake rate on every file in shadow and in the pilot; if it is large the automation metric shrinks and @head-of-underwriting must see that number.
- M3: "scanned application" must say what counts (image file, image-only PDF, PDF with a poor OCR text layer) and whether a scanned ACORD page in an otherwise typed file triggers it.
- M4: the operations scorer/gold-wording gap (12 of 13 operations misses are scorer or gold convention) needs a forward decision before the new gold, or operations fails any scope.
- L1: SUB-145 (dev, 3-location csv) and T-103 schedules: only 170 (2 rows) and 172 (3 rows) have more than one row, so a schedule rule would not over-trigger on T-103; recheck on dev before gold.
- L2: the workbench card wording in P-055 is fine; the build must show the same reason on the blocked send (D-065).
