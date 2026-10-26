# @model-risk check — D-097: P-049 build and scorer v4

- Date: 2026-10-16. Reviewer: @model-risk (independent). Scope: commits 96deed8, a6cebb3, 3fe3e00, 213d884 (added by the orchestrator: wet chemical exemption narrowed).
- Evidence read: carrier-match.md, appetite-guide.md, carrier-appetite.md, workbench.py `_match` and self-checks, eval_holdout_v4.py (diffed against v3), dev gold SUB-127–146 diffs, P-049-dev score files, RUN-RULES.md, screenshot, DECISIONS D-095–D-097.
- Synthetic data. An approved proposal is not a production approval; the T-027 veto stands.

## Verdict: OBJECTION (production and gate use of P-049 routing), one High. Scorer v4: APPROVE.

## Recomputed

- Dev re-score SUB-127–146 at HEAD 213d884, scorer v4, from a temp copy of the cache (`LLM_CACHE_DIR` temp, `HOLDOUT_RESCORE=1`, `LLM_PACE_SECONDS=0`, no `--write`): 0 model calls, 20/20 from cache, repo `git status` unchanged before/after.
- Route gate **PASS**: 0 unsafe, route 18/20 (exactly the floor). Misses: SUB-135 and SUB-143, gold carrier_a, code no_match (safe direction). False completes 0. Loss runs 8 hit / 0 miss / 12 not credited. Matches the committed 3fe3e00 file.
- `eval_holdout_v4.py --self-check` ok; `workbench.py --self-check` ok. v2 and v3 have no commits after a11ab83 (frozen).
- Conditions: (a) R10 cites AG:39, AG:62 (AG:66 citation dropped), B-377 logged — met. (b) AG:37 and AG:62 quoted correctly; D-059 item 6 replacement recorded in D-097 — met. (c) "suggested market: Carrier B/C, underwriter confirms" on every B/C note and in the screenshot — met. (d) W2 checked before class words; SUB-138 and SUB-144 now senior_referral — met for the listed words; see H1 for W1.
- Dev gold: 8 files changed, each with a dated @senior-underwriter note citing the rule; changes follow the written rules, not the code output.
- 213d884: the exemption is whole-phrase and only with restaurant evidence; "wet chemicals wholesale" stays senior_referral (re-run). Closed.

## High

**H1 — Written prohibited classes reach carrier_a, the only direct route (an unsafe route under v4).** Probed `match()` at 213d884 with TIV $1,000,000:
- "office building with ground-floor pub" → carrier_a; "retail store and cocktail lounge" → carrier_a. AG:46 (edited in 96deed8) lists pubs and lounges as prohibited, but W1 / `PROHIBITED` omit pub, pubs, lounge, lounges, so a bar word without restaurant evidence plus a class A word falls through to R14.
- "office building, no utilities" → carrier_a. AG:51 prohibits buildings with no utilities; `_ops` drops "no <word>", so the phrase is never seen (the same defect P-049 fixed for "no sprinklers").
- "office, unoccupied" → carrier_a (AG:51 vacancy synonym not in W2e).
D-097 1d requires prohibited words to win over appetite words. A gold writer following AG:46/AG:51 would mark these no_match, so a T-103 file like these fails the gate as unsafe.
**Resolution:** (1) a bar word (W1b: pub, pubs, lounge, lounges) with a class A word and no restaurant evidence → senior_referral (or no_match), never carrier_a; written in carrier-match.md to match AG:46; (2) read "no utilities" / "without utilities" / "unoccupied" from the raw cited text before the negation drop (as `unsprinklered`), routed per AG:51 / W2e; (3) self-checks for each probe above. Needs `approve change P-###` from the user; @head-of-underwriting writes the rule lines.

## Medium / Low (backlog, one line each)

- M1: W2 is a closed word list; "wholesale gasoline", "wholesale ammonia", "wholesale lithium batteries", "retail convenience store with gas pumps", "retail paint store" → carrier_a. AG:31 needs a hazardous-goods yes/no field or a wider list (@head-of-underwriting, @senior-underwriter).
- M2: v4 still parses a gold line "hold" as a route and then never counts it unsafe; v4 should make the gate NOT EVALUABLE when any gold route is "hold" (H3 says it is never one).
- M3: v2/v3 route columns call the live `workbench.match`; re-running them now gives different route marks and their self-checks fail (RUN-RULES documents it). Published files are untouched, but frozen scorers are no longer reproducible; pin or snapshot the router for re-runs.
- M4: the dev gate passes at exactly 18/20 and the dev gold changed in the same commit as the code; this is not hold-out evidence. T-103 (SUB-154–173) must be scored once with v4.
- L1: W1 runs before the R5/R6 hold gate, unlike the rules-file order (B-378); safe direction.
- L2: "dry chemical extinguishers" on an office routes to the hazardous-goods referral (safe, wrong note).
- L3: two lines added at AG:63–64 shift later AG line numbers; older citations past AG:62 now point elsewhere.
- L4: SUB-130 card shows "Cooking: not scored — no cooking equipment stated" for a cafe routed by R10 (screenshot).
