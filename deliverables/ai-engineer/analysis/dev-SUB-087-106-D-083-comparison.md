# Development check SUB-087–106 after P-035 and P-036 (D-083 item 3)

- Development data since D-082; not a hold-out score. Code: working tree after commit 0bf3cf2 with P-036 (as approved by @model-risk, fourth check). Python .venv 3.14.6.
- Uncached: a new empty cache; every reply was fetched in this session (Groq openai/gpt-oss-120b, 20 calls, 0 failed), then scored with the final code from that cache (0 calls). Scored by the frozen eval_holdout_087.py into dev file names (`deliverables/ai-engineer/evals/dev-SUB-087-106-D-083.*`); the published SUB-087-106 files are untouched.
- The hold-out rerun had 19 scored files (SUB-101 call failed); this check has 20 (SUB-101 now reads).

| Field | Hold-out rerun (9e725e3) hit / needs review / miss | Dev D-083 hit / needs review / miss | Other dev marks |
|---|---|---|---|
| named_insured | 17 / 0 / 2 | 17 / 0 / 3 | — |
| premises | 7 / 0 / 12 | 11 / 0 / 9 | — |
| effective_date | 14 / 0 / 5 | 13 / 0 / 7 | — |
| operations | 12 / 0 / 7 | 11 / 0 / 9 | — |
| sales | 12 / 0 / 6 | 10 / 1 / 9 | — |
| tiv | 13 / 0 / 6 | 14 / 0 / 6 | — |
| construction | 13 / 0 / 6 | 16 / 0 / 4 | — |
| year_built | 11 / 0 / 7 | 12 / 0 / 7 | flagged 1 |
| loss_runs | 13 / 0 / 0 | 13 / 0 / 1 | not_credited 6 |
| conflict | 10 / 0 / 7 | 10 / 0 / 6 | not_credited 3, flagged 1 |
| status | 10 / 0 / 9 | 9 / 0 / 9 | not_credited 2 |

## What moved (orchestrator's reading)

- P-036: premises +4 (SUB-092, 095, 099, 103), SUB-098 name and conflict now hits, SUB-103 status and operations hits.
- P-035: the three scans now read, but the OCR text is noisy (B-301). On SUB-088 and SUB-097 the scan competes with the email, and the fields the email gave are now misses or empty; SUB-101 reads but most fields miss.
- Typed files with no P-036 field involved changed on fresh calls (SUB-087 sales, SUB-100 sales/TIV, SUB-102 operations, SUB-105 sales/status): run-to-run model variation at temperature 0, about ±1–2 per field on 20 files.
