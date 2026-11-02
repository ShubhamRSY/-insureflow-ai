# P-075 build check — @model-risk (D-133)

- Date: 2026-10-26. Worktree `insureflow-fix-t117`, branch `p075`, uncommitted vs `ec48f66`.
- Read: proposal-P-075.md, P-075-as-built.md, the `prepare.py` / `workbench.py` diff, tests, dev SUB-299–303, UI check, screenshots. Author messages not read.
- No model call. LLM_* unset; the probes below stub only `llm_extract._post` and use a temp cache in my scratchpad. Nothing was written in the worktree except this file.
- A build check is not a production approval. The T-027 veto stands.

## Re-run evidence

| Check | Result |
|---|---|
| `pytest tests/pipeline` | 91 passed |
| `prepare.py` / `workbench.py` self-checks | `prepare ok`, `workbench ok`; worktree status unchanged after the run |
| 128 probes as tests (fixture is byte-identical to `deliverables/model-risk/P-075-probes.json`) | hold 107/107; no_hold 15/21 (false holds BEN-05, 11, 12, 13, 14, 15: fail safe) |
| Requests | `llm_extract.py`, `sources.py` unchanged vs ec48f66; baseline test 0 of 143 changed. SYSTEM / request_for not touched |
| Frozen files | none in the diff or untracked (eval_holdout_*, lint_holdout, hold-out gold, simulation/inbox/, cache/, P-073-v12) |
| Route | `_route_value` removes the copied line before routing; self-check passes for every none body. Replay in as-built: only senior_referral→hold and complete→review pending |
| reply.md | runs before the cooking rule, so a reply cannot settle a cooking conflict (my probe: SUB-299 + "use the application" stays unresolved) |
| OCR | an application with any OCR words is never copied from |
| ReDoS | no nested quantifiers in the new patterns; the 10,000-space test passes |
| UI | the SUB-299 screenshot shows the email sentence first (UI check H1 closed); What's new line present |

## High

**H1. The copied-line note claims more than the rule knows.** On a clean scan the row reason says "cooking line copied from the application (P-075); **no other document states cooking**". The scan is a word list, so this sentence turns the list finding nothing into a stated fact. My end-to-end probes on a temp copy of SUB-301 (stubbed host) used emails with a cooking sentence the list misses: "The insured heats up food for staff in the back.", "A frialator was added.", "We do food prepping for events." Each one copied the line, opened no conflict, and showed the underwriter "no other document states cooking". That is the T-118 H1 failure (silence read as "no cooking"), now in the review note, and it breaks criterion 1 ("never infer cooking status from missing words"). The file stays in review, so the harm is bounded, but the note points the underwriter the wrong way.
Remediation: the note makes no claim about the other documents, e.g. "cooking line copied by a rule from the application (P-075); check the other documents for cooking". Add a self-check that the reason does not contain "no other document".

**H2. The approved word list is not fully built.** Proposal B (approved as D-133) lists "heat(s/ed/ing) up soup/food/meal/water" and "food prep*". The build matches only `heat (up|food|soup|meal|water)` and `food (prep|preparation|…)` as whole words. These sentences miss: "heats up food", "heated up food", "heats up water", "heating water", "food prepping", "food prepped". `_COOK_TOKENS` also lists "ul300", but the tokenizer `[^\W\d_]+` drops digits, so that entry can never match ("UL300" was held only by "hood"). The 128 probes do not cover these forms, so 107/107 does not show them.
Remediation: match heat/heats/heated/heating (+ optional "up") + soup/food/meal/water, and food prep\w*. Fix or remove the "ul300" token (match `ul ?300` as a phrase). Add each sentence above as a hold test.

## Medium / Low (backlog, one line each)

- M1: false holds are real: 6/21 no_hold probes, and 19 dev folders gain a conflict (5 go senior_referral→hold). Fail safe, but count them before the pilot.
- M2: the build reads the insured's name; the proposal said to blank it (`_without_name`). This is more conservative, and the as-built records it. Note it in DECISIONS when this is recorded.
- M3: resolving the cooking conflict does not update operations or clear its note (already in the as-built backlog).
- L1: words outside the list are missed: frialator, flattop (one word), culinary, stockpot, cantina, concession, commissary, crepe, empanada, tamale, pupusa, fondue, "warm up food". No list is complete, and the review note (once H1 is fixed) is the backstop.
- L2: quick-15 was replayed for only 5 of 15 files (no model call allowed), so the dev evidence is thin.
- L3: the status label "complete — review pending" next to an open conflict reads oddly (from before this change; the card does say "Not complete until checked").

## Verdict

**BLOCK** until H1 and H2 are closed. Both are small text and pattern fixes plus tests. One look-again after that, High only. Everything else checked holds: rule only, 0/143 requests changed, no frozen file touched, effects only toward held/review, probes 107/107, tests green.
