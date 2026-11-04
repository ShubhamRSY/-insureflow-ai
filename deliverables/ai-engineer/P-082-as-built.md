# P-082 as built (T-130, D-161) — B-523 M1, B-524 M4/L4, B-523 L1

Stricter only. Scope detector scope-v6 → **scope-v7**. PROMPT_VERSION unchanged (`llm_extract.py` not touched).

## Rules (underwriting_pipeline/ai/scope.py `_place_words`, `_bare_label`, `_role_label`)
- A role word (mailing, prior, agent, carrier, landlord, …) hides an address only when it sits in a short label right before that address: label ≤ 30 characters and ≤ 4 words (brackets not counted), then ":" or a schedule tab, then only names / a PO Box, then the address. One label hides one address. In prose a role word hides nothing (M1).
- A label with the word "home" never hides anything (M1).
- A line above hides the next line's address only if it is a bare label ending in ":" with a role word, and only an address that starts that next line. A Title Case or name line ("Carrier A Loss Run Attached", "ABC Insurance Agency") is never a label (M4).
- "Spur 191" (any case) counts as a highway address in the second-address check only. `prepare._shows_one_address` still uses `scope.HIGHWAY`, so a Spur premises is not newly accepted as one address (no loosening) (L1). Lowercase "highway" not added (not in P-082).
- workbench.py: the approve record's `approved_values` and the confirm record's `confirmed_values` read `package.with_resolutions(saved)`, so they include values entered on resolve, the same values the card shows and `needs_review_ids` reads (L4).
- What's new line (2026-11-04, P-082, D-161). No screenshot: no layout change; the manual-intake card is the P-077 card with a new quote.

## Evidence
- Self-checks: scope ok scope-v7 (8 old negatives moved to positives as P-082 asks; 13 new positives; code-review shapes added), prepare, package, sources, workbench, regression_dev ok.
- Scope sweep scope-v6 vs v7, 381 folders (simulation/inbox, inbox-dev, T-129 devcheck-inbox): 381 identical; **0 newly in scope, 0 newly manual intake** (`evals/T-130/scope-v6-vs-v7-sweep.json`, script `sweep.py`). Dev 12: DEV-01–05 in scope, DEV-06–12 manual intake, as before.
- tests/pipeline 94 passed (LOB config scope version and fingerprint re-pinned for scope-v7, as P-077/P-079 did). pyright 31 → 31.
- Code review (plugin) 2026-11-04: 3 loosening shapes in the first draft (label above hiding a later sentence, prose before a colon as a label, prose next line starting with a number) and SPUR case fixed, each with a self-check; confirm record aligned; What's new added.
- Residual (Low): `with_resolutions` reads `package.DECISIONS_LOG`, not the `log_path` given to `record_decision` (same as `needs_review_ids` and the send gate); resolutions read outside `_LOG_LOCK`.
