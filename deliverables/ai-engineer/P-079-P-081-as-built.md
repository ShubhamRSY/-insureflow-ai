# P-079, P-080, P-081 as built (T-129, D-155–D-157), 2026-11-03

Written by the orchestrator (D-139 tool rule: no role subagents for builds). Branch pilot-integration. Prompt unchanged: PROMPT_VERSION 392b9ce3c1af (no request changes; no re-recording). Scope detector scope-v5 → scope-v6.

## P-079 (D-155; memo T-121 H1, B-518) — `underwriting_pipeline/ai/prepare.py`
- `scope.HIGHWAY` (new, shared): "1906 Hwy 290 W", "100 US-59", "4400 FM 1960", "12 State Route 9", "800 I-35". `CITY_STATE_ZIP` accepts "Brenham TX 77833" (comma before the state optional).
- `_shows_one_address`: exactly one address (street, highway/route or number-city-state-ZIP; overlapping matches are one), not a PO Box, no count phrase.
- `_location_problem`: a count of 1 passes only when its quote is found in its file, holds no count phrase, and either the count quote shows one address or `_premises_shows_one`: every premises row agrees and each premises quote is found in its cited file and shows one address. Everything else fails closed as before. Part A (`scope.detect`) runs before the call and any hit wins.

| Condition | Evidence |
|---|---|
| (a) count 1 only with one address found in the documents | prepare self-check: quotes not in file, quotes with no address, two addresses, disagreeing premises rows → unclear |
| (b) rule checks still run; any hit wins | unchanged order (scope.detect before the call); dev re-check DEV-06–12 all stopped by Part A |
| (c) any second address in any document → manual intake | scope-v6 also reads highway addresses (DEV-12 "300 FM 2222"); self-check positives |
| (d) SUB-475, SUB-533–537 shapes still manual intake | dev re-check DEV-06–DEV-11: 6/6 manual intake, words quoted |
| (e) "two floors", "2nd floor", "two entrances" stay in scope | DEV-03, DEV-05, DEV-04 in scope; scope self-check negatives |
| (f) SUB-510/513/527/529 shapes now in scope | DEV-01, 02, 03, 04: old code manual intake ("number of locations not clear"), new code in scope |

## P-080 (D-156; memo T-121 H2, B-519) — `underwriting_pipeline/ai/scope.py`, stricter only
- A3 reads each sentence of a line: a role word (carrier, agent, mailing…) skips only its own sentence. `label_above` applies only to a bare label line ("Mailing address:" or a name with no colon); "Mailing address: same as premises" no longer hides the next line. Highway addresses count.
- Over all 365 folders in simulation/inbox and inbox-dev, scope-v5 vs scope-v6: 0 moved to in scope; 2 moved to manual intake (SUB-533 as intended; SUB-219: application 2701 Memorial Blvd vs schedule 4810 Twin City Hwy, a real second address the filled mailing line had hidden; SUB-219 is published T-108 data whose pre-D-149 gold says in scope; published scores unchanged, D-020); SUB-129 (already manual intake, scan) gains the multiple-locations reason (schedule 3115 S 31st St).

## P-081 (D-157; B-522) — `underwriting_pipeline/app/package.py`, `workbench.py`, `prepare.py`
- `with_resolutions` recomputes Missing from the resolved values. `resolved_to_review`: an "incomplete" run becomes "complete — review pending" (never "complete") only if every conflict open in the saved run was resolved by a listed underwriter's logged resolve on this run hash, no field is empty, `extra` is recorded and empty (runs saved before P-081 never qualify), no unread file or page, no file for a human read, and the scope result is in scope. Approve with every acknowledgment (incl. the operations C1 ack), the senior market confirm (P-052) and every send gate are unchanged.
- The saved run now records `extra`. Card: the status line names the P-081 reason; the producer draft is shown as withdrawn and `/approve-draft` refuses it with a plain reason.
- package self-check: promoted case plus 11 fail-closed cases (another run's resolve, extra asked, saved before P-081, unread page, human read, out of scope, no scope, another empty field, an unresolved third conflict, already review pending, manual intake) and one conflict left.
- Demo SUB-133 (temp copy, new code, 0 live calls): resolve → senior confirm → send refused (not approved) → approve with both acks → account-manager send → quote. Screenshots `deliverables/software-engineer/screenshots/T-129-P-081-SUB-133-resolved-review-pending.png`, `T-129-P-081-SUB-133-sent.png`.

## Checks
- Self-checks (temp copy): scope ok scope-v6, prepare ok, package ok, workbench ok, sources ok, regression_dev ok. tests/pipeline 94 passed (LOB config fingerprint re-pinned for scope-v6, as P-077 did).
- pyright on the 4 changed files: 43 → 43. code-review plugin: no findings.
- Quick set 17 (temp copy; 15 saved replies + 2 paced live calls for SUB-026/036 on the baseline): baseline silent 0.188 (26/138), automation 0.565; after: identical, 0 differences in any field or status.
- Dev re-check (12 dev files, `deliverables/ai-engineer/evals/T-129/devcheck-inbox`, 5 paced live calls): before/after in `devcheck-before-scope-v5.txt` / `devcheck-after-scope-v6.txt`.
- Not a production approval; the T-027 veto stands.

## Fixes after @model-risk REJECT (check-T-129.md), 2026-11-03 (D-159)
- **H1:** `package.needs_review_ids` reads the run after the logged resolutions on this run (`with_resolutions`), so the operations value entered at a resolve is a C1 review row. One function serves the approve list (workbench) and the send-gate `ack_problem`, so both are the same list. Self-check: the send-gate ack check refuses until operations is acknowledged on this run hash; an acknowledgment of another field, or on another run, does not count.
- **H2:** `workbench.saved_report` passes the saved `extra` through (None for a run saved before P-081) instead of `[]`; the Missing line reads `extra or []`. Self-check with real saved runs on disk: `extra: ["hours"]` and a pre-P-081 run stay "incomplete" on the card, exactly as the send gate reads them; `extra: []` reads review pending in both.
- **H3:** `scope._bare_label`: a label is a line ending in ":" or a name-only line (no colon, no sentence punctuation, every word capitalised; "of", "and", "&", "the", "de", "y" allowed). A sentence on the line above never hides the next line. Self-check: four two-line SUB-533 shapes (carrier, agent, prior carrier, loss-run line above) fire; "Mailing address:", "ABC Insurance Agency" are labels.
- M3 closed: the dev re-check replies are saved in `deliverables/ai-engineer/evals/T-129/devcheck-replies/` (5 files).
- Re-run after the fixes (temp copies): self-checks scope, prepare, sources, regression_dev, package, workbench ok; tests/pipeline 94 passed; pyright 43 → 43; code review no findings; dev re-check identical to the first build (`devcheck-after-fixes.txt`); scope-v5 vs v6 over 365 folders: 0 loosened, stricter SUB-219 (D-160) and SUB-533; quick-17 vs baseline 0 differences (`quick17-after-fixes.json`); SUB-133 demo (0 live calls): resolve → confirm → refused before approve → approve with the operations and scan acknowledgments → sent → quote. Demo guide Demo A and the SUB-133 screenshots updated.
