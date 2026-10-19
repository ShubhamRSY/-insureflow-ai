# P-063 and P-064 as built — T-109a, T-109b, D-116

Author: orchestrator session for @ai-engineer-assistant, 2026-10-19. Approved by the user in this session: `approve change P-063` (pasted message) and `approve change P-064` (answer to the scorer question). Not a production approval; the T-027 veto stands. No model call. Dev data only (SUB-206–237 is dev since D-115).

## P-063 (B-432, T-027 memo H1) — scope detector and send gate

- (a) `scope.py` → `scope-v4`. The P-058 numbered-label pattern is shared as `_LABEL`. `NUMBERED` (line start, list item, schedule cell) is unchanged. The new `NUMBERED_ANY` finds the same label anywhere in an application line, so "Loc 1: …; Loc #2: …" inside the `Premises address:` value (SUB-233), "Location 2" in body text and "Bldg 2" anywhere now give `multiple_locations`. Kept as not-a-location: mailing/prior/former lines, "Number of buildings: 2" and "1 of 2 buildings" (no label after "of"), "Building 2 stories" and its other lookahead words, "Building 2020", "Premises 12 Main St" (a street number). One added rule: a number followed by on/at/in/is/near/behind/by is a label, not a house number ("Location 2 on Bell St").
- (b) `prepare.scope_problem()` is the send-gate re-check, independent of status. It refuses when the saved run recorded the file out of scope, or when the current detector, run at send time on the folder, puts it out of scope. It fails closed when there is no saved run or the folder cannot be read. It is called by `package.send_to_carrier` (every actor, after the manifest check) and `prepare.approve` (producer requests, every actor). The workbench card shows "No send: out of pilot scope at send time (multiple locations, scope-v4); a person reads this file." in both the carrier-send panel and in place of the producer-draft approve button. "What's new" line added (T-109a, D-116).
- Behaviour change, fail-closed direction: three P-058 negatives are now manual intake: "Premises address: 500 Oak Park Dr, Building 2, Austin, TX", "Premises: 500 Oak Park Dr, Bldg 2, Austin" and "The shop is in Building 2 of the plaza". P-063 (a) names "Bldg 2" anywhere, so the self-check now expects these three to be multiple locations. Risk: more false manual intake (ceiling 2 of 20 per hold-out). Backlog B-439.

## Self-checks (dev)

- `scope.py`: ok scope-v4. Real SUB-233 → `["multiple_locations"]`. Seven anywhere-forms are positive; two new negatives ("we lease 1 of 2 buildings", a single "Loc 1:" premises).
- Dev sweep, scope-v3 vs scope-v4 on all 237 folders in `simulation/inbox/` (read-only): **one change, SUB-233 → multiple_locations. No other file changes.**
- `prepare.py` ok: a SUB-233-shaped file saved in scope under the leaky detector has an ordinary status and a draft, unchanged documents, and `scope_problem` refuses it; `approve` by the user is refused with the reason and nothing is written to to-producer; no saved run fails closed.
- `package.py` ok: the same shape is refused for user and account manager; nothing sent. The stub application is now a real one-location application, so the re-check sees an in-scope file.
- `workbench.py` ok: `/send` gives "Send refused: out of pilot scope at send time (multiple locations, scope-v4)…"; the card shows "No send:" and has no send form and no approve-draft form; `/approve-draft` is refused too.
- `intake.py`, `llm_extract.py` ok. pyright 1.1.390 on the 4 changed files: 49 errors before and 49 after, identical (0 new).
- @senior-underwriter UI check H1 (fixed in the same task): an out-of-scope card now opens with "Send blocked — out of pilot scope at send time (…). Nothing on this file can be sent. Do not chase the missing items. Next step: re-run extraction on this file; …", and shows "Carrier match: none — out of pilot scope at send time" instead of the route and hold lines. Self-check asserts both.
- Screenshot (sandbox copy, stubbed values, D-069): `deliverables/software-engineer/screenshots/T-109a-scope-send-refused.png`.

## P-064 (B-435) — scorer v8

- `eval_holdout_v8.py` is a copy of v7 (v7 frozen, not edited) with one scoring change: the loss-run date comes only from the gold line `- Loss runs valued as of: <YYYY-MM-DD>`, never from the `- Loss runs:` line (v7 took its first date, the policy-period start). A card that expects a date with no such line, or with not exactly one date, stops the run before any call (`gold_problems`, also shown by `--check-gold`). Where gold expects no date, the line is absent or `none`. `score_one` is split into `score_one` + `score_report` (same marks), so the lint can score answers built from gold.
- Self-check ok (`--self-check`): SUB-206 shape hits under v8 and misses under v7's rule; malformed lines stop. v7 self-check still ok.
- `HOLDOUT_IDS=206-237 --check-gold`: 15 in-scope T-108 cards fail (no valued-as-of line), as expected: T-108 gold was written before D-116. Published v7 scores stay as published.
