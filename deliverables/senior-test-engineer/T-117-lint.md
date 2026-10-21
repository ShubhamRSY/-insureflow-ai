# T-117 lint (scorer v11) - @senior-test-engineer, 2026-10-21
- Command: `.venv/bin/python deliverables/senior-test-engineer/lint_holdout.py deliverables/senior-test-engineer/T-117-plan.json --run-date 2026-10-21` -> `T-117-lint.txt`. Result at first run: FAIL (3 failures, 3 info, 32 files). **After gold fixes (2026-10-21, re-run after T-117 check H1/H2): PASS (0 failures, 3 info, 32 files); see `T-117-lint.txt`.** Not run for scoring (D-020).
- sha256 checked before run: lint `01147a75...ea653` ok; v11 `7ddcfb50...fcbb` ok. Neither edited.
- Plan: ids 238-269, in 20/out 12, criteria 4/5/4/2, two_criteria 3, criterion_4 2, routes carrier_a 0 / senior_referral 16 / no_match 4 (updated after H1), undated 241, 242, 254 (all confirmed by lint INFO).
## FAIL lines (all gold cards, owner @senior-underwriter; plan is clean)
1. SUB-239/gold: "closes midnight" fits no slot; move to `- Operations notes (unscored):`.
2. SUB-247/scorer: business_type near-miss ['restaurant'] -> "no restaurant" marked hit; gold item set needs adjusting (e.g. "no liquor"/"catering" items let the wrong text match).
3. SUB-252/scorer: near-miss ['bar_pub','office'] -> "office" marked hit; same kind of gold fix (item wording).
No inbox-file (@producer) failures.
## Mix vs gold (gold wins; plan follows gold)
- Routes: mix gave none; routes file/gold: carrier_a 2, senior_referral 14, no_match 4.
- SUB-239 loss run not a recognised Carrier B layout (mix: Carrier B, valued 2026-07-02); SUB-251 one class not two-operation; SUB-243/257 referral not allow-list; SUB-255 R8 no_match not referral; SUB-252 R1 no_match. None change plan counts (criteria counts match the mix).
- undated_loss_runs: mix and gold agree (241, 242, 254); 244 no loss run, 248 dated letter, 239 unrecognised are not "undated" in the plan.
