# @model-risk check: P-055 (revision 2), P-056 (built), scorer v5 (D-103)

- Author: @model-risk (independent). 2026-10-16. Worktree `insureflow-ai-team`, branch `ai-team`, pipeline diff uncommitted on top of 3557e4a.
- Read: `deliverables/pm/proposal-P-055.md`, my `scope-P-055.md`, `git diff -- underwriting_pipeline/`, `deliverables/ai-engineer/p-056-as-built.md`, the four JSON files in `evals/P-056-dev/`, `eval_holdout_v5.py` against `eval_holdout_v4.py`, `operations-gold-rule.md` ("Operations checklist"), the T-103 root-cause rows that P-056 targets, D-099 to D-103.
- Recomputed: before/after marks per file from the dev JSON (they match the as-built table: SUB-140 conflict, SUB-142 date, SUB-144 premises up; SUB-134 status down; 0 false completes and 0 unsafe routes both sides). Offline probes of `_quote_dates`, `parse_day`, `accept_field`, `location_sides` and `ops_items_hit` (no model call, no score file). v4 and v5 `--self-check` pass; v4 is unchanged against HEAD. My own read-only cache re-score of SUB-127–146 into a temp folder was blocked by the session permission check, so the dev counts are checked from the JSON, not re-run.
- Nothing in the repo written except this file and the two team logs. Synthetic data. **Not a production approval. An approved P-055 or P-056 is not a production approval. The T-027 veto stands.**

## Verdicts

| Item | Verdict | What resolves it |
|---|---|---|
| P-055 rev 2 | **APPROVE WITH CHANGES**. My H1 and H2 are closed in the text. It can go to @user for `approve change P-055`. Settle M1 to M3 in the text before any gold is written | M1 to M3 below, in the proposal text |
| P-056 | **OBJECTION** (H1) | Close H1 and re-run the dev check (SUB-127–153) |
| Scorer v5 | **OBJECTION** (H2). It must be fixed before any gold uses it, because D-020 freezes it after that | Close H2 and add the self-checks |

## High findings

### H1 — P-056 (b): a scanned number whose own digits read under 0.50 is now kept and can drive a route (owner @ai-engineer-assistant; @user rules on scope)

- `cited_ocr_floor` averages the scores of the cited tokens. For number and date fields the cited tokens are the value's own digit groups (`_cited_scores` keeps only the quote tokens that are in the value). So a number with several digit groups survives when one group scores very low. A one-group number with the same score is dropped.
- Reproduced with `accept_field`. On a scan, TIV "$1,040,000" with the token "000" at 0.05 is now **kept**: value 1040000, confidence 0.05, reason "Low-confidence scan read". Before P-056 it was dropped. "Year built: 2004" with "2004" at 0.30 is still dropped. `prepare._set_cited` behaves the same way.
- Why this is High: a file with a review flag routes as complete (`workbench.match`, P-041). So a TIV whose digits OCR scored 0.05 now feeds the appetite and TIV checks and can produce a carrier or provisional route, where before the file was held "TIV missing or unreadable" (D-061). This is the SUB-170 kind of input ("$1,040,000" read "51,040,009"; sales "000" at 0.27). The user's words were "don't drop a whole field because one word in its quote is low-confidence". The root cause behind that is a label or context word ("takeout:", "TX"). A low digit group is not that: it means the value itself is in doubt. The dev check cannot show this risk because it found only 2 low-scan flags on dev.
- Remediation: for NUMBER_FIELDS and DATE_FIELDS, keep the drop test on the lowest score of the value's own tokens, as before. Use the average only for text fields (operations, construction, named_insured, premises_address). Add two self-checks: the TIV "000" at 0.05 case is dropped, and the operations "takeout" at 0.29 case is still kept and flagged. Re-run SUB-127–153 and report the counts. If @user rules this is inside P-056 (b), no new P-### is needed. Otherwise raise one. I do not decide that.

### H2 — Scorer v5: a checklist item matches word by word anywhere in the answer, so negated and counted items credit wrong answers (owner @ai-engineer-assistant)

- `ops_items_hit` only checks that each word of an item appears somewhere in the answer. Order and closeness are ignored. All five of these wrong answers score as **hits** today:
  - "full bar, alcohol served, no patio" against the item "no alcohol"
  - "48 seats, 4 fryers, 2-burner range" against "2 fryers"
  - "2 seats ... 48 fryers" against "48 seats; 2 fryers"
  - "no live music on weekdays; music Fridays" against "no live music"
  - "no gas, electric ranges only" against "electric ranges only" (this one is correct; it shows only that the matcher cannot tell the cases apart)
- Why this is High: liquor, cooking counts and seats are the operations items that change the route and the referral. Operations is the field that failed T-103, so v5 is the instrument the next gate will be judged by. Under D-020 the scorer cannot change once the gold exists, so this must be fixed now. v4 had the same bag-of-words weakness, but v4 needed every gold word, so these flips were less likely to pass.
- Remediation: an item is a hit only when its words, after the stop words are removed, appear **as a contiguous run in the same order** in the answer, also after stop words are removed. "no alcohol" must then be adjacent words, and "2 fryers" must be "2" right before "fryers". Add the five probes above as self-checks (four misses, one hit), keep the existing ones, and commit v5 before any gold. v4 stays frozen.

## Medium and Low (backlog, one line each)

- P-055 M1: "substantial non-English" is written as "mostly". It needs a measurable rule (share of words in the application, or the main document) and a named deterministic detector, fixed before the gold so that gold labels and the detector agree.
- P-055 M2: say what the detector does when it cannot tell which document is the application (for example an image named "scan1.jpg"). A scanned application taken for a scanned loss run would leak. Fail closed, and add that near-pass form to the 12.
- P-055 M3: "4 per criterion, at least 3 match two criteria" is ambiguous. State that each criterion has at least 4 files labelled with it, counting double-criterion files under both.
- P-055 L1: the leakage definition should also count an automated missing-info draft to the producer on a manual-intake file.
- P-056 M1: (a) regression. Hyphen-joined ranges "3/15/2026-3/15/2027" and "03/15/2026-03/15/2027" no longer parse (the new look-arounds reject them, and the old regex read both dates), so an effective date cited from a policy-period line is dropped. None is in `simulation/inbox` today. Add a self-check.
- P-056 M2: (e) `location_sides` searches the whole document for "value (loc N)". It does not tie the label to the field's own line, so "2012 (loc 1)" on a roof line can make a year_built conflict look like per-location values. Match on the line the side's quote cites.
- P-056 M3: (e) a multi-location application now leaves the premises conflict and routes on loc 1 without a premises flag. Build P-055 before any pilot use, so these files go to manual intake.
- P-056 L1: (a) reading month first changes P-016 D2 for every ambiguous 4-digit date, not only 2-digit years. The flag covers it, and the user's own example "3/1/27" needs it. Record that the user accepts it when P-055/P-056 come back to @user.
- P-056 L2: (a) "3/1/202" (a cut-off year) reads as 2020, "12/31/99" as 2099 and "v1.2.25" as a date. Rare; the value must still match.
- P-056 L3: (c) the parts of a " ... " join have no minimum length, so a one-word fragment can be found anywhere in the document. Same exposure as the P-048 (d) newline join.
- P-056 L4: (f) reading the whole document flags negated mentions ("Liquor: none") as missing. Safe direction; watch the automation cost (dev: 1 file, SUB-134).
- P-056 L5: the evidence for (a) to (d) on real files is only the unit self-checks. Dev showed 0 month-first dates and 2 low-scan flags. The next hold-out is the first real test; do not treat the dev counts as evidence the T-103 failures are fixed.
- v5 M1: a new-gold file with no "Operations items:" line (and not "not in documents") silently falls back to the v4 word rule. For gold dated after the v5 commit, refuse or flag it.
- v5 L1: an answer that copies the whole document hits every item. There is no penalty for contradicting extras.

## Look-again, D-103 (2026-10-16): P-056 H1 and v5 H2, High only

- Read: `git diff -- underwriting_pipeline/` (`accept_field`, `cited_ocr_floor`, `prepare._set_cited`, `ops_items_hit`), the v5 and `llm_extract` self-checks, `p-056-as-built.md` (check section), the two `*-after-v4.json` dev files. Re-ran `--self-check` for llm_extract, prepare, v4 and v5 (all ok); v4 unchanged against HEAD. Probes in memory only; nothing written but this section and the two team logs. No model call. I did not re-score the dev files (D-069; the runner writes logs). The after files are dated after the last code edit (23:26:54 vs 23:26:38) and show 0 false completes and 0 unsafe routes on SUB-127–153.

| Item | Verdict now |
|---|---|
| P-056 H1 | **CLOSED** |
| v5 H2 | **OPEN (narrowed), OBJECTION stands** on scorer v5. No gold may be scored with v5 until it closes |
| New High | None |

**H1 closed.** Numbers and dates now use the lowest score of their own tokens (`cited_ocr_score`), in both `accept_field` and `_set_cited`. Only text fields use the average. The self-checks I asked for are present and pass: the TIV with "000" at 0.05 is dropped, and the operations value with "takeout" at 0.29 is kept and flagged. A date check was added too ("27" at 0.2 is dropped). For a date, every word of the quote is scored, label words included. That is the stricter direction and acceptable. Whether this narrowing stays inside P-056 (b) is still for @user; I do not decide that. This is not a production approval, and the T-027 veto stands.

**H2 still open.** Contiguous in-order matching is built as I asked, and three of my probes now miss correctly. But the run of words can cross a sentence or label boundary, and nothing checks for a negator just before the run. So these wrong answers are still credited, all on route-relevant items:
- "Alcohol: no. Live music Fridays" is a **hit** for "no live music".
- "Beer and wine: no. Liquor license" is a **hit** for "beer and wine".
- "not 2 fryers, 4 fryers" is a **hit** for "2 fryers".

I also correct my own probe. "no live music on weekdays; music Fridays" is still a hit, and the contiguous rule I wrote could never make it a miss, because a qualifier after the item needs a different rule. I withdraw it from the H2 acceptance and log it below as M2. That part was my error, not the author's.

What closes H2 (owner @ai-engineer-assistant; change v5 before any gold is scored with it, v4 stays frozen):
1. An item counts only inside one clause. Split the answer on `. ; : ,` and newline, and do not let a run cross a split.
2. A run directly preceded by no / not / non / without / zero is not a hit, unless the item itself starts with that word.
3. A run is not a hit if the clause right after it is only "no", "none", "n" or "0" (the "Label: no" form).
4. Add the three probes above as self-check misses. Keep all the current self-checks, and add "Beer and wine only, no liquor" as a hit for "beer and wine only; no liquor".

I checked in memory, without touching the repo, that a rule written this way passes every current v5 self-check plus the new probes.

Medium and Low (backlog, one line each):
- v5 M2: a qualifier after an item ("no live music on weekdays") is still credited. The gold reviewer should write qualified items in full ("no live music on weekdays") so that a bare answer misses.
- v5 L2: clause splitting on commas means an item that itself contains a comma can never hit. The gold rule should say "no commas inside an item".

## Second look-again, D-103 (2026-10-16): v5 H2 only, High only

- Read: `ops_items_hit`, `_clauses`, `NEGATION`, `NO_CLAUSE` and the self-checks in `eval_holdout_v5.py` (mtime 23:30:05). Re-ran `--self-check` for v5 and v4 (both ok); `git diff HEAD -- eval_holdout_v4.py` is empty, so v4 is still frozen. Probes in memory only, no model call, nothing written but this section and the two team logs.

| Item | Verdict now |
|---|---|
| v5 H2 | **CLOSED.** All four parts of my resolution are built and behave as written |
| New High | **H3 (v5), OBJECTION** on scorer v5. No gold may be scored with v5 until it closes |

**H2 closed.** Clause split on `. ; : ,` newline: yes. A run right after no/not/non/without/zero is a miss unless the item starts with that word: yes ("not 2 fryers, 4 fryers", "Without 2 fryers" miss; "No alcohol" hits "no alcohol"). A run whose next clause is only no/none/n/0 is a miss: yes ("Live music: No", "Live music, none", "live music: 0" miss). The three look-again probes are self-check misses. The positive "Beer and wine only, no liquor" for "beer and wine only; no liquor" returns a hit, but it is not in the self-checks (L3 below). My original H2 probes still miss, and "no gas, electric ranges only" still hits.

**H3 — a "no" in the same clause, right after the item, is still credited (owner @ai-engineer-assistant).** My rule 3 only looked at the *next* clause, and I listed only `. ; : ,` as separators. Answers that copy a Y/N form with other punctuation slip through. These all score as **hits** for a positive, route-relevant item: "Live music - no", "Live music? No", "Live music (no)", "Live music no", "Live music – none", "Beer and wine (none)". Liquor and live music decide the route and the referral, and under D-020 the scorer cannot change once gold exists, so this is High for the same reason H2 was. This gap is in my own resolution, not a deviation by the author.

What closes H3 (v5 only, before any gold; v4 stays frozen):
1. A run is also a miss when the rest of its own clause after the run is non-empty and is only no / none / n / 0.
2. Add the six probes above as self-check misses, and add "Beer and wine only, no liquor" as a hit for "beer and wine only; no liquor" (closes L3).

I checked in memory that this one extra condition passes every current v5 self-check plus all seven new probes. That is the whole change I will accept; I will not add new conditions at the next look unless a probe shows a wrong answer credited.

Backlog (one line each):
- v5 L3: the positive self-check from H2 item 4 is missing (behaviour is right). Folded into H3 item 2.
- v5 L4: "Live music: no live music" and "No: live music" still hit "live music". Contrived; gold reviewer to watch.

This is a scorer check, not a production approval. The T-027 veto and the P-056 scope question for @user are unchanged.
