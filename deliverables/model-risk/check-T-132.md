# check-T-132 — @model-risk independent check of P-084 (scope-v8, D-165)

- Date: 2026-11-05 · Reviewer: @model-risk · Component: C-4 pilot scope detector, `scope-v8`
- Verdict: **APPROVE** (no High). This clears the D-165 "no High" condition for merge. It is **not a production approval** of the scope detector.

## What I re-ran (temp copy, D-069; real tree unchanged after)
| Check | Result | Matches author? |
|---|---|---|
| Structure: v8 A3 = `_second_address(docs, ()) or _second_address(docs, EXTRA_ADDRESS)`; the `extra=()` path is line-for-line the v7 body; `detect` only adds a reason from `_place_words` | stricter by construction | yes |
| `python scope.py` self-check | `scope ok scope-v8` | yes |
| `sweep.py` vs `git show HEAD:…/scope.py` (380 folders) | 380 same; newly in scope 0; newly manual intake 0; DEV-01–05 in scope, DEV-06–12 manual intake | byte-identical JSON |
| `diff-v7-v8.py` (seed 11) | 200,924 cases; v7 fires and v8 not: 0; v8 adds: 37,753 | yes |
| `pytest tests/pipeline` | 94 passed | yes |
| quick17-p084.json vs T-130 quick17-p082.json | `counted` and `metrics` identical (silent 26/138 = 0.188, automation 0.565); rows differ only in retry record; 17 calls, 0 failed, 0 cache | yes |
| What's new line + screenshot | present, D-165, T-132 | yes |
| pyright / code-review | not re-run by me; as-built reports 31 → 31 and two review passes | evidence accepted |

## High findings
None.

## Medium
- **M1 — owner @ai-engineer-assistant / @software-engineer: "any letter case" is overclaimed to underwriters.** The new any-case and Spanish forms fire only when a comma and a city follow on the same line. My probes (A3 `_place_words`, premises 100 Main St, Austin) missed: `1200 ELM DR WACO TX 76701` (no comma), `Ship stock to\n1200 ELM DR\nWACO TX 76701` (USPS line format), `9 oak st waco tx`, `Warehouse 1200 ELM DR WACO TX`, `Calle Roble 12 Laredo`. The as-built states the comma rule; the What's new line does not. Not a loosening (v7 missed these too; the model location count is still the backstop). Remediation: add "when a comma and a city follow" to the What's new line, record the limit in the as-built's known limits; backlog the comma-less / line-break capitals form with its own near-miss set.

## Low (backlog, one line each)
- L1: lower-case route codes (`12 ih 35, waco`) and mixed case (`1200 Elm DR, Waco`) not caught.
- L2: `STATE HWY 6`, `BUS 287`, `PR 4012` (all capitals) not caught.
- L3: lower-case `general delivery`, `Av` without a dot, `Blvd. Colosio 300` (Spanish) not caught.
- L4: false manual intake on `Policy 2024 TX-71, issued` and `5 FM 1960 deliveries, daily` (stricter; 0 in the 380 corpus; watch in pilot).
- L5: version id `scope-v8` was first given to the dropped P-083 build (D-164, P-083-as-built.md); note in the inventory that `scope-v8` = P-084 only.
- L6 (@model-risk, own item): model-inventory.md C-4 still says `scope-v4`; update to `scope-v8` with v5–v8 history.
- L7: second pass re-reads documents (2–3× A3 time on long lines); acceptable, monitor.
