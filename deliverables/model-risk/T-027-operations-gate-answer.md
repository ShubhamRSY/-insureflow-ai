# T-027: answer to @user on the operations gate (D-133)

- Author: @model-risk (independent). Date: 2026-10-26. Answer only. No rule, gate, code, scorer or score changed. No model call, no pipeline run.
- Question (D-133, verbatim): "would it accept, for T-027, "operations is never auto-accepted; the operations gate is 0 silent errors instead of the 18/20 hit floor"? Conditions and reasons."
- Read: TASKS.md T-027 (resolution conditions after T-108, T-117, T-119); `T-027-memo.md`, `T-027-memo-T-117.md`, `T-027-memo-T-119.md`; `SUB-340-371-results.md`, `SUB-340-371-holdout-v11.md`; D-084, D-127, D-128, D-131, D-132, D-133; `ai/prepare.py` (`ready_to_route` 661, status 1310–1316, `check_operations` 1079); `app/package.py` (acknowledgment list 402–417, send refusal 927–958); `proposal-P-075.md`.
- Synthetic data. This is not a production approval. An approved P-### is not a production approval. The T-027 veto stands until a hold-out meets the gate set below.

## Answer: ACCEPT WITH CONDITIONS

As worded, I would **not** accept it. With the seven conditions below, I would accept that operations stops being judged on the 18/20 hit floor.

## Reasons

**For it.**
1. Operations is a summary of the business written in free text. The safety risk is a reviewer who misses the error, not the wrong text itself. The send gate already makes the underwriter acknowledge every needs-review value. That acknowledgment is tied to the saved run's hash (D-039, D-068, P-026; `package.py` 402–417, refusal tested at 927–958). If operations is always a needs-review value, no wrong operations value can be sent unless a named underwriter has acknowledged it.
2. Every T-119 operations miss came to the underwriter as a flagged value except one (10 of 11 flagged; `SUB-340-371-results.md` line 49). The fail-safe direction already works for most misses.
3. P-075 as approved (D-133, review note kept) already chose "never complete from this change". The question pushes that choice to the whole field.

**Against it as worded.**
1. **"0 silent errors" means nothing once review is forced.** D-084 defines a silent error as "value wrong AND not flagged needs-review". If operations is flagged on every file, the count is 0 by construction, even when every answer is wrong. A gate that cannot fail is not a gate.
2. **A flag with no reason does not point the reviewer anywhere.** A generic "always review" note on a value that left out "Cooking operations: None", or that understates a fryer, invites a one-click acknowledgment (automation bias). What protects the file is a flag that names what is missing or in dispute, not the flag itself.
3. **Without a floor, a broken extractor would pass.** An extractor that gets operations wrong every time, or returns nothing, would still show 0 silent errors. A null operations value makes the file incomplete and drafts a missing-info request to the producer for facts that are already in the file. That costs the producer relationship, and it is not caught by any safety gate.
4. **Operations is read before anyone acknowledges it.** `ready_to_route` lets a "complete — review pending" file go to carrier match. Carrier match and referral read the operations context lines (`check_operations`, P-047 (c)). Forcing review on the operations field does not make routing safe.

## Conditions (each testable on a hold-out)

**C1 — "Never auto-accepted" is enforced in code, as the last step, and shown on the card.**
- What changes: in `prepare.py`, after every rule and merge (after P-074/P-075, conflicts and `check_operations`), any operations row that has a value gets `needs_review = True` with a fixed policy reason, e.g. "operations is always checked by the underwriter (D-###)".
- Effects: operations is always on the acknowledgment list. No file is ever plain "complete"; the best status is "complete — review pending". The send is refused until an approve on the current run hash acknowledges operations.
- The card shows the policy note, plus any specific reason, next to the value. One "What's new" line (D-065). Playwright screenshot on a temp copy.
- Tests: a self-check that no path leaves operations with a value and `needs_review` False (model-carried line, rule-copied line, agreeing merge P-024, scan path P-037); and a send-refusal test with operations not acknowledged.
- Approval: this is a code change under `underwriting_pipeline/ai/`, so it needs a P-### and the user's `approve change P-###` (D-017). The gate change itself is the user's decision, recorded in DECISIONS.md.

**C2 — "Silent error" for operations is redefined so the policy flag does not count.**
- Definition: an operations value scored a miss by the frozen scorer, and with no *specific* review reason, counts as a silent error. A specific reason is one that names the missing or disagreeing item: P-059/P-075 "operations may be missing: …", a `cooking` conflict, or a scan/low-confidence reason. The C1 policy reason never counts.
- To make it countable, the report stores the specific reasons apart from the policy flag (e.g. `review_reasons` vs `policy_review`).
- Counting: a small counting script, frozen and hashed **before T-120 gold**. v11 is not edited (D-127, D-020). Scorer-reading misses (M class, e.g. SUB-350 "plumbing supplies") count against the gate. They are not reclassified after the score.
- Target: 0 silent errors.

**C3 — No understated hazard, whether flagged or not.**
- Target: 0 files where gold has cooking or another rated hazard item (fryer, hood, bar/pub, contractor class) and the system shows operations without it, unless the file is held with an open conflict that names it.
- Reason: a flag does not make an understatement safe, because of acknowledgment bias.

**C4 — A floor stays on usefulness, but it is not 18/20.**
- Operations value present on ≥ 18/20 in-scope files, so no false missing-info drafts.
- Operations hits ≥ 15/20 under frozen v11. I set this now, before T-120 gold, not after a score. Below that, more than a quarter of answers need rewriting by the reviewer.
- Hits are reported every time.

**C5 — Every other field and gate keeps its criterion.**
- named_insured, premises, effective_date, sales, tiv, construction, year_built and loss_runs each stay at ≥ 18/20.
- These also stay unchanged: 0 false completes, 0 unsafe routes, route ≥ 18/20, 0 leaks, detection recall 100%, false manual intake ≤ 2/20, planted-conflict recall 100% on ≥ 5 measurable conflicts (T-119 H2).
- The relaxation applies to operations only. It never applies to a field that feeds rating directly (sales, TIV).

**C6 — Sample size, and what it can show.**
- T-120: 20 in-scope + 12 out-of-scope, gold first, run once, scored once (D-020, D-131).
- Within the 20 in-scope files: at least 12 with a stated "Cooking operations: None"-type line, at least 3 with cooking stated, at least 2 with a planted cooking conflict, and at least 2 with a contractor, wholesale or mixed class.
- Known limit: 0 silent errors out of 20 only bounds the true rate below about 14% at 95% (rule of three). That is enough to lift the veto, not to claim a low rate.
- Production monitoring then counts operations edits at acknowledgment and post-send corrections. That count must reach ≥ 60 reviewed files with 0 silent errors (upper bound below 5%) before anyone proposes relaxing C1.

**C7 — Pre-registration.** The user records C1–C6 in DECISIONS.md as the T-027 operations gate before T-120 gold is written. If the decision comes after any T-120 file exists, I will not accept it (same reason as D-127: no gate change after seeing data).

## What it does to automation and to the T-119 numbers

- Operations automation becomes **0 by design**. T-119 had 0.25 (`results.md` line 78).
- Overall field automation on T-119 would have been at most 157/180 = 0.87 instead of 162/180 = 0.90. That figure assumes T-119's 5 auto-accepted operations values were among the 162.
- Status automation becomes **0**: no file reads plain "complete". T-119 had 2/13 (SUB-351, SUB-356). Every send goes through an acknowledgment. This is the intended cost.
- T-119 cannot be re-scored and is not re-scored (D-020). For reading only: operations hits 9/20 would fail C4. SUB-350 is an unflagged miss and fails C2 and C3's spirit. The 9 dropped "no cooking" lines would have had a specific reason ("operations may be missing: no cooking") and so would not be silent.

## Evidence that already meets a condition, and what does not

| Condition | Already met by | Not yet met |
|---|---|---|
| C1 enforcement | Acknowledgment list and send refusal bound to the run hash (D-039/D-068/P-026, tested in `package.py`). P-075 keeps the review note on copied lines (D-133). | Model-carried operations can still read complete (P-075 status table). No last-step policy flag exists. No P-### or test for it. |
| C2 silent error | D-084 metric exists. T-119 shows 10/11 misses flagged. | Policy and specific reasons are not stored apart. No frozen counting script. T-119 has 1 silent error (SUB-350). |
| C3 hazard | P-075 holds the file on any cooking word elsewhere (when built). P-074 keeps unverifiable sides open (D-132). | P-075 is not built or checked. Hazards other than cooking (contractor class, pub) are not checked. Not measured on a hold-out. |
| C4 floor | — | T-119 operations 9/20. P-075 is expected to give about +7 (not measured). |
| C5 other gates | T-119: 8 fields 20/20, all safety gates pass. | Planted-conflict recall 2/3 on T-119 (H2). P-074 is built but not yet proven on a hold-out. |
| C6/C7 | T-120 plan scope in D-131 matches. | No T-120 gold yet (good: still time to pre-register). |

Even with this gate accepted, the T-119 H2 conditions (P-074 checked, ≥ 5 measurable conflicts, recall 100%) still apply. Lifting the veto is not a production approval.

## Summary (≤10 lines)

**ACCEPT WITH CONDITIONS** (not as worded: under forced review, "0 silent errors" is 0 by construction).
- C1: last-step code forces operations `needs_review` with a policy note; the send stays refused until it is acknowledged on the run hash. Needs a P-###, a self-check and a card note.
- C2: a silent error is a scored miss with no *specific* item-naming reason. The policy flag does not count. Counted by a script frozen before T-120 gold. Target 0.
- C3: 0 understated hazards (cooking, fryer, hood, pub, contractor class), whether flagged or not.
- C4: operations present ≥ 18/20 and hits ≥ 15/20 (usefulness floor, set now).
- C5: the other 8 fields keep ≥ 18/20. Every safety gate, plus conflict recall 100% on ≥ 5, unchanged.
- C6: T-120 has 20 in-scope with ≥ 12 none-lines, ≥ 3 cooking, ≥ 2 cooking conflicts. Production needs ≥ 60 monitored files before any relaxation.
- C7: the user records the gate before T-120 gold.
- Cost: operations and status automation go to 0. T-119 would not have met C2 or C4.
