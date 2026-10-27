# T-108 corrected gold copy (B-437, P-065)

A **copy** of `../gold-set` SUB-206 to SUB-237, made so the lint and the v9 re-score can read a set the scorer accepts. The real gold folder and the published T-108 scores are never rewritten (D-020, D-115).

What is different, and nothing else:

- The 13 in-scope cards whose loss run has a date now carry their own line `- Loss runs valued as of: <YYYY-MM-DD>` — the date each card already states in its `- Loss runs:` line: SUB-206 2026-08-15, 207 2026-07-31, 209 2026-06-15, 210 2026-06-30, 211 2026-07-20, 213 2026-04-30, 215 2026-07-15, 217 2026-08-05, 218 2026-08-31, 221 2026-08-20, 222 2026-05-27, 224 2026-07-06, 225 2026-06-01.
- The 7 review cards carry no such line: SUB-208, 212, 214, 216, 219, 220, 223 (SUB-216 and SUB-219 name the review in the middle of `Expected loss run`; scorer v9 reads it, v8 did not).
- The 12 out-of-scope cards (SUB-226–237) are byte-for-byte copies.

The other two T-109c findings needed no gold change: `Conflict: none (…)` and an hour written `11 p.m.` / `2:00 a.m.` inside an `Operations items` item are reads the scorer got wrong, fixed in v9 (F1, F2).

How to read it:

```bash
HOLDOUT_GOLD=deliverables/senior-underwriter/gold-set-T-108-corrected \
  .venv/bin/python underwriting_pipeline/ai/eval_holdout_v9.py --check-gold
HOLDOUT_GOLD=deliverables/senior-underwriter/gold-set-T-108-corrected \
  .venv/bin/python deliverables/senior-test-engineer/lint_holdout.py deliverables/senior-test-engineer/T-108-plan.json --run-date 2026-10-19
```

Author: orchestrator session for @senior-underwriter, 2026-10-19, from the T-109c lint findings F1–F3. The scorer change is P-065 (`eval_holdout_v9.py`); the gold convention is written in `../operations-gold-rule.md`.
