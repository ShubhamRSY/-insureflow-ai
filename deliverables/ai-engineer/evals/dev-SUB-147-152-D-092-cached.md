# DEVELOPMENT CHECK — P-044/P-045 accept/reject cases SUB-147 to SUB-152 (dev-SUB-147-152-D-092-cached), not a hold-out

- Commit 7a5eb4cdc350bd1dc3fa7fc858cb4b571d71dbbc, model qwen/qwen3.8-27b, paced 0.0 s, python /Users/disastershubz/INSURANCE FLOW AI/-insureflow-ai-1/.venv/bin/python, {"pdfplumber": "0.11.10", "openpyxl": "3.1.5", "pytesseract": "0.3.13", "pdf2image": "1.17.0", "pillow": "12.3.0"}.
- Model calls: {"model_calls": 0, "from_cache": 6, "tokens": 0, "tokens_per_call": 0}; failed attempts: {"rate_limit_429": 0, "timeout": 0, "other": 0, "reply_not_usable": 0}.
- Plain "complete": SUB-147, SUB-149. False completes: **0** (none).
- Loss run as gold: 5 of 6. Pipeline status as gold: 5 of 6.

| File | Loss run | Reason | Status | Gold loss run | Gold pipeline status | Other values to review |
|---|---|---|---|---|---|---|
| SUB-147 | accepted 2026-09-30 | — | complete | 2026-09-30 accepted | complete | none |
| SUB-148 | missing | — | incomplete | 2026-09-30 accepted | complete | none |
| SUB-149 | accepted 2026-09-30 | — | complete | 2026-09-30 accepted | complete | none |
| SUB-150 | missing | loss run found but no valued-as-of date; ask the producer for a dated carrier loss run (loss-runs.md) | incomplete | loss run found but no valued-as-of date; ask the producer for a dated carrier loss run | incomplete | none |
| SUB-151 | missing | loss run found but no valued-as-of date; ask the producer for a dated carrier loss run (loss-runs.md) | incomplete | loss run found but no valued-as-of date; ask the producer for a dated carrier loss run | incomplete | none |
| SUB-152 | review 2026-09-30 | not a recognised carrier loss run (loss-runs.md); check it or ask the producer for the carrier's loss run | complete — review pending | needs review — not a recognised carrier loss run | complete — review pending | none |
