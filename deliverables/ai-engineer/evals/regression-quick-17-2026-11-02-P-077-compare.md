# Quick set (17 files): baseline vs after P-077 — 2026-11-02

- Baseline (D-147): live, paced 55 s, prompt 759b3e6bc9b2, scope-v4. 17 model calls, 0 failed, 26,209 tokens. Run id quick17-baseline-2026-11-02.
- After (T-127): live, paced, prompt 392b9ce3c1af, scope-v5. 15 model calls (SUB-022 and SUB-042 go to manual intake before any call), 0 failed, 25,367 tokens. Re-scored from the same saved replies with the final code after the code review and the @model-risk H1 fix (0 extra calls).
- Temp copies only (D-069); no real log, cache or outbox written.

| | Baseline | After P-077 |
|---|---|---|
| Silent error rate | 0.181 (25/138) | 0.145 (20/138) |
| Automation rate | 0.558 (77/138) | 0.522 (72/138) |
| Files that reach the model | 17 | 15 |

- Only SUB-022 and SUB-042 changed: Part A rule A3 (a second street address in the email: "15 Perez St" vs the application's "51 Perez St"; "410 Cesar Chavez Blvd" vs "1400 …"). Every field becomes empty, so they score as misses; status not credited. The other 15 files: every check identical.
- Part B: all 15 model counts were 1, each quoting the premises address; 0 "number of locations not clear".
- Decision for @user (B-511): replace SUB-022 and SUB-042 in the quick set.
