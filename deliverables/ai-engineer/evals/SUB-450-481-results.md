# T-120 results — hold-out SUB-450 to SUB-481, scored once with v11 (D-137)

- Run `20261027T124020-83695`, 2026-10-27, once; scored once with `eval_holdout_v11 --write` and `count_ops_gate.py`. Frozen inputs verified (run record). Gate rulings fixed before the run: D-134 (operations gate C1–C7), D-136 (SUB-461/463 cooking-conflict marks excluded; recall on the 7 figure conflicts; C2 counter rules). Synthetic. Not a production approval; the T-027 veto stands until @model-risk rules.
- Score files as the scorer wrote them: `SUB-450-481-holdout-v11.md/.json`. Operations gate output: `SUB-450-481-ops-gate.txt`. Mismatches: `SUB-450-481-holdout-v11-mismatches.md`. Fix nothing (D-137).

## Gates

| Gate | Result | Target | Verdict |
|---|---|---|---|
| Leakage (out-of-scope file treated as in scope) | **1** (SUB-475) | 0 | **FAIL** |
| Detection recall, overall | **11/12** (crit 1: 3/3, 2: **2/3**, 3: 3/3, 4: 3/3) | 100% | **FAIL** |
| Wrong manual intake (in-scope sent to manual) | 0/20 | ≤ 2/20 | met |
| Reasons on detected out-of-scope cards | 11/11 | all | met |
| False completes | 0 | 0 | met |
| Unsafe routes | 0 | 0 | met |
| Route accuracy | 18/20 (misses SUB-451, SUB-458, both toward a person) | ≥ 18/20 | met |
| Direct Carrier A files (450–453) | **3/4** (SUB-451 routed senior_referral) | — (reported) | 3 of 4 |
| Planted-conflict recall (7 figure conflicts, D-136) | **7/7** (454, 455, 458, 459, 460, 462, 469 all held open) | 100% on ≥ 5 | met |
| False conflicts on gold-none files | 0/11 | — | met |
| Cooking conflicts SUB-461/463 (excluded, D-136) | both raised and held open (`cooking: the documents disagree`); v11 marks "miss" (unmeasurable) | reported apart | — |
| C2 operations silent errors | **0** | 0 | met |
| C3 understated hazards | **0** (every file with cooking, fryer, hood, pub/lounge or contractor in gold is an operations hit; the one miss, SUB-458, is an office lessor) | 0 | met |
| C4 operations present / hits | 19/20 / **19/20** | ≥ 18/20 / ≥ 15/20 | met |
| Silent error rate (all fields) | 0/180 = 0.000 | — | — |

## Fields vs floor (in scope, 20)

| Field | Hit | Miss | Flagged (correctly, conflict) | Floor | Verdict |
|---|---|---|---|---|---|
| named_insured | 20 | 0 | 0 | 18/20 | met |
| premises | 20 | 0 | 0 | 18/20 | met |
| effective_date | 20 | 0 | 0 | 18/20 | met |
| operations | 19 | 1 (SUB-458) | 0 | C4 (≥ 15/20) | met |
| sales | 18 | 0 | 2 (455, 462) | 18/20 | met |
| tiv | 19 | 0 | 1 (460) | 18/20 | met |
| construction | 20 | 0 | 0 | 18/20 | met |
| year_built | 20 | 0 | 0 | 18/20 | met |
| loss_runs | 20 | 0 | 0 | 18/20 | met |

## Automation and cost

- Field automation 155/180 = 0.861 (T-119 0.90). Operations automation 0/20 by design (P-076, D-134). Status automation 0/9 gold-complete files by design (all 9 read "complete — review pending"; the scorer marks these 9 as status misses).
- Cost: 21 model calls (20 in-scope + retried call), 0 from cache, 37,085 tokens (1,766 per call); `qwen/qwen3.8-27b` on Groq on-demand, no paid API (D-011). 2 rate-limit retries on SUB-450, logged; 0 failed calls. Wall time 28 min (55 s pacing).

## Verdict summary

Every field, route, conflict and operations gate is met. **Two safety gates fail on one file: SUB-475** (criterion 2, multi-location) was not detected and was extracted as an in-scope file. Its application lists one address and says "two stores"; the email names the second store (Rockport). Nothing was fixed.
