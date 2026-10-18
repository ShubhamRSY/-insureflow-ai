# @model-risk check — T-104b (D-108): P-057 scorer v6 and P-058 detector scope-v3

- Date: 2026-10-17. Reviewer: @model-risk (independent). High findings in detail; Medium and Low one line each for the backlog.
- Scope: uncommitted change on branch ai-team: `underwriting_pipeline/ai/eval_holdout_v6.py` (new), `underwriting_pipeline/ai/scope.py`, `underwriting_pipeline/app/workbench.py`, `deliverables/ai-engineer/p-057-p-058-as-built.md`, `deliverables/model-risk/model-inventory.md`. `regression_dev.py` is unchanged and works with `--holdout eval_holdout_v6`.
- No T-104 inbox file or gold file was opened. Only `--check-gold` (Scope-line parse) was run on SUB-174-205.
- This is not a production approval. The T-027 veto stands. Approved proposals P-057 and P-058 are not production approvals.

## Verdict: BLOCK the re-freeze until H1 is closed

- **P-057 (scorer v6): no High.** It may be used for T-104 as built.
- **P-058 (scope-v3): one High (H1).** Under D-108 item 4, do not re-freeze or run T-104 until H1 is closed.

## What I re-ran (0 model calls in every check below; temp copies only)

| Check | Result |
|---|---|
| `scope.py` self-check | `scope ok scope-v3` |
| `eval_holdout_v6.py --self-check`, `regression_dev.py --self-check` | ok, ok |
| v4 and v5 scorers | unchanged (`git status`: only scope.py and workbench.py modified; v6 new) |
| `--check-gold` on SUB-174-205 | 32/32 Scope lines parse. 20 in scope, 12 out. Per criterion: 1: 4, 2: 5, 3: 4, 4: 2. Two-criteria files: 3. This matches the P-055 design (≥4 each for criteria 1-3, ≥3 two-criteria files) and the gold commit 3678c0f message. |
| Inbox SUB-001-173, scope-v2 (HEAD) vs scope-v3 | identical: in scope 95, not_identified 30, non_english 17, scanned_application 31, multiple_locations 13. 0 files changed. |
| v6 on dev SUB-127-146 (temp gold copies with the as-built Scope labels, temp cache, `HOLDOUT_RESCORE=1`) | leak 0/6, recall 6/6 (per criterion 2/2, 3/3, 1/1, 2/2), reasons 6/6, false manual intake 0/14, P-055 gate PASS. Route gate FAIL (dev data). This reproduces the as-built numbers. |
| v6 with labels deliberately wrong (SUB-127 marked out of scope, criterion 2; SUB-129 marked in scope) | SUB-127: leak (field shown, complete status, suggested market, send enabled) and a recall miss; criterion 2 3/4; false manual intake 1 (SUB-129); P-055 gate **FAIL**. The scorer catches both kinds of error. |
| Pyright | scope.py: 0 errors. eval_holdout_v6.py: 1 error, the same `workbench` import-resolution error as v5. workbench.py: 31 errors that predate this change (the diff adds one What's new tuple). |

## High

### H1 — scope-v3 narrows the existing criterion-2 rule. P-058 does not cover that.

- What changed: the new `_is_loss_sheet` (scope.py) is called from `_is_sheet` and `_kind`. It removes a csv or xlsx from **all** schedule reading, including the scope-v2 address-row count, not only from the new numbered-label check. A sheet is removed when its name matches LOSS_RUN, or when its text has two or more loss terms ("incurred", "reserve", "claim number", "valued as of", "valuation date", "paid loss", ...) and fewer than 3 application labels.
- Evidence (synthetic probes, application with one premises, plus one sheet):

| Sheet | scope-v2 | scope-v3 |
|---|---|---|
| `sov.csv`: Location / Address / TIV / Paid loss reserve / Claim number, two addresses | multiple_locations | **in scope** |
| `property-schedule.xlsx`: Loc / Address / TIV / Valued as of / Incurred losses, two addresses | multiple_locations | **in scope** |
| `sov.xlsx`: Loc / Address / TIV / Reserve / Incurred, two addresses | multiple_locations | **in scope** |

- Why it is High: criterion 2 is under a hard leakage gate (0 leaks, 100% recall). This change lowers detection on the existing rule. D-108 approved P-058 as an addition ("the detector **also** catches numbered locations"). Any other rule change to a Tier 2 component needs its own `approve change P-###` (D-017; model-inventory C-4: "any rule change ... is revalidated"). The as-built note calls it a precision choice. It also cuts recall, and nothing in the note measures that cost. The dev inbox shows no difference, so no dev file tests it either way.
- What resolves it (either one):
  1. Apply the loss-sheet exclusion to the new numbered check only. `_codes` keeps scope-v2's `_is_sheet` and `_addresses` behaviour for address rows. Add one self-check that the three sheets above still give multiple_locations. Re-run the scope self-check and the inbox 1-173 comparison. Then re-freeze. **Or:**
  2. @user approves the narrowing explicitly in this session as part of P-058 or a new P-###, with its recall cost stated.

## Medium (backlog, one line each)

- M1: scope-v3 misses numbered labels that are not at the start of a plain line: markdown table rows (`| Location 2 | 200 Oak Ave |`), markdown headings (`### Location 2`), and a two-row address table in an application `.md`. The guard against "stories" also drops "Bldg 2 - storage" (the lookahead matches `stor`). No dev application uses tables (0 of 173), so this is a format-coverage risk, not a dev regression. Owner @ai-engineer-assistant, after T-104 under D-017.
- M2: when 1 or 2 in-scope files go to manual intake by mistake, they are left out of the route denominator, so the route gate passes at 17/18. That is 17 correct routes of 20 in-scope files, below the user's literal "≥ 18/20". This follows the P-055 text. The T-104 report should also print hits over all 20 in-scope files. Owner @ai-engineer-assistant / @pm.

## Low (backlog, one line each)

- L1: "Loc 1 / Loc 2" (slash), "Site 2", "Store #2", "Building B", "Location Two" are not caught. They are outside the approved word list.
- L2: v6 returns NOT EVALUABLE when criterion 4 has no gold file, though P-055 makes criterion-4 files optional. This does not matter for T-104, which has 2.
- L3: v6 self-check: `GOLD = _OUT = Path(tmp) / "x"` is followed by `GOLD = Path(tmp)`. The first assignment to GOLD does nothing. Cosmetic.
- L4: the gold author (@senior-underwriter) should check the per-file `--check-gold` output against T-104-gold-summary.md before the single run. The totals already match.
- L5: the rest of B-398 is still open: "second store at ...", two addresses on one premises line (both still in scope), and "Additional premises: N/A" (still multiple_locations, a false manual intake).

## Reviewer process note (disclosure)

- While running self-checks, I started `regression_dev.py` with no argument. That runs the dev regression SUB-017-076 live, not a self-check. It made **7 model calls (8,111 tokens, Groq, qwen/qwen3.8-27b, run 20261017T185139-17415)** before I stopped it.
- Where it wrote: the worktree's git-ignored `underwriting_pipeline/cache/` (6 new extraction files and token-log rows) and a temp output folder. It wrote no tracked file, no T-104 file, no outbox and no workbench page. I did not touch or "restore" the cache (D-069).
- This is the reviewer's error, not the author's. It does not affect the T-104 hold-out, because the cache keys are for dev files.

## Look-again (2026-10-17, same paths, still uncommitted)

**Verdict: BLOCK the re-freeze. H1 is closed. One new High (H2) of the same kind.** P-057 (scorer v6) still has no High.

Re-run with 0 calls, no key, temp cache:
- Self-checks: scope ok scope-v3; eval_holdout_v6 ok; regression_dev ok.
- Pyright: 0 new errors (only the known `workbench` import error).
- Inbox SUB-001-173, scope-v2 vs scope-v3: identical, 0 files changed.

### H1: closed

- The loss-sheet exclusion now gates only the numbered-label check.
- All my H1 sheets give multiple_locations again, as in scope-v2: the loss-like SOV, the SOV with Valued as of / Incurred columns, sov.xlsx with Reserve / Incurred, and loss-runs.xlsx with two addresses.

### H2 (new, High): the schedule address reader now chooses a mailing or prior-address column

- What changed: in `_addresses`, the scope-v2 substring filter `mail|prior|previous|former` was replaced by the narrower label regex `NOT_A_LOCATION`. This applies to both the header choice and line skipping.
- Effect: a schedule header such as "Address (mailing)", "Prior-address" or "Address - previous" no longer matches the filter. When it is the first address column, it becomes the column that is read. Its repeated mailing address counts as one place, and the premises column is ignored.
- Evidence: a schedule.csv with header `Loc | <header> | Premises address`, the same mailing address on every row, and two different premises.

| Header | scope-v2 | scope-v3 |
|---|---|---|
| Address (mailing) | multiple_locations | **in scope** |
| Prior-address | multiple_locations | **in scope** |
| Address - previous | multiple_locations | **in scope** |
| Owner mailing addr address | multiple_locations | **in scope** |

- Why it is High: same reason as H1. It cuts recall on hard-gated criterion 2 through an existing rule. The additive P-058 approval does not cover that (D-017).
- On the line-skip side, the narrower filter only adds detections (stricter). That part is not a High.
- Resolve by either:
  1. Restoring scope-v2's substring test for the **header choice** in `_addresses` (keeping the label regex for line skipping is acceptable, because it only adds detections). Add one self-check with the four headers above, re-run the inbox 1-173 comparison, then re-freeze. **Or:**
  2. @user approves the narrowing explicitly.

### Backlog

- L6: `p-057-p-058-as-built.md` "After code review" still says loss-run sheets are "never read for numbered or address rows". The later "After @model-risk H1" section supersedes it. Mark the old line as replaced.
- M1, M2 and L1-L5 are unchanged. M2 is partly addressed: the report now prints hits over all in-scope files. L3 is fixed.

### Second look-again (2026-10-17, scope.py changed again)

**Verdict: APPROVE for the re-freeze and the single T-104 run. H1 and H2 are closed and there is no new High.** P-057 still has no High. This is not a production approval; the T-027 veto stands.

- H2 closed: `_addresses` uses scope-v2's `mail|prior|previous|former` substring test again for the header choice, and a self-check covers the three headers. My probes all give multiple_locations, as in scope-v2: "Address (mailing)", "Prior-address", "Address - previous", "Mail Address", "Former Address", "Owner mailing addr address".
- H1 still closed: the four loss-like SOV and loss-run sheets with two addresses give multiple_locations.
- Structure: scope-v3 now differs from scope-v2 on criterion 2 only by additions (the numbered check, OR'd in) and a narrower line-skip filter. Both can only add detections, so no remaining change lowers criterion-2 recall below scope-v2.
- Re-run (0 calls, no key, temp cache): scope and eval_holdout_v6 self-checks ok; pyright on scope.py 0 errors; inbox SUB-001-173 scope-v2 vs scope-v3 identical (0 files changed).
- Backlog is unchanged: M1 (markdown tables and headings, "Bldg 2 - storage"), M2 (partly addressed), L1, L2, L4, L5, L6.
