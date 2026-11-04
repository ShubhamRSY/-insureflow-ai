# check-T-130-2: @model-risk look-again on T-130 (P-082, D-161)

- Reviewed: pilot-integration 3a637c1c (fix a94c3468..3a637c1c; full diff f7539497..3a637c1c). Temp copies via git archive; no model calls; no repo file edited.
- **Verdict: APPROVE.** H1 (O-T130-1) closed; no High open. Stricter-only scope change. **Not a production approval; the T-027 veto stands.**

## What I re-ran
- scope.py self-check `scope ok scope-v7`, incl. the H1 self-check (4400 FM 1960 Rd, 12 State Highway 6, 77 County Road 12, 800 I-35 Frontage Rd stay manual intake through detect()).
- tests/pipeline 94 passed.
- `_place_words` diff v6 vs v7: every match listed again, same order as v6 (cell, then pattern; SPUR last); a hidden offset only drops a match where v6 skipped the whole sentence.
- Author's differential (`evals/T-130/model-risk-diff.py`): 60,200 cases, v6 fires and v7 not: 0.
- My own differential (other seed, 80,000 texts of 1–3 addresses; added Spur 5 Rd, Hwy 6 Spur, SPUR … Loop, US Hwy 59 N, Farm Road, Ranch Road; prefixes "Carrier A Loss Run Attached:", "Agent's home office:", "Location 2\t"): v6 fires and v7 not: 0.
- Sweep (`__pycache__` excluded): 380 folders, 380 identical, 0 newly in scope, 0 newly manual intake; dev 12 unchanged.
- Quick-17 (run 20261104T155036-25797; 17 live calls, 0 failed): bands identical to T-129; ran at a94c3468, carries over (scope-only fix, no scope result changed). M1 closed.

## Medium / Low
- M2 (new, backlog): stricter-only keeps the v6 false positive; a single FM, State Highway, County Road or I-35 Frontage premises still goes to manual intake. A fix is a loosening and needs its own P-### for @user.
- L1 closed (380 folders). L2 closed (fingerprint comment).
- L3 (backlog): `with_resolutions` reads `package.DECISIONS_LOG`, not `log_path`, and reads outside `_LOG_LOCK`.

## Acceptance criteria
All met: stricter only (140,200 differential cases, 0 loosened); Spur in the second-address check; approve records include values entered on resolve; dev 12 and sweep 0 newly in scope; quick set identical; tests/pipeline 94 passed.
