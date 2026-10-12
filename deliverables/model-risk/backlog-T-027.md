# Backlog — T-027 review, Medium and Low findings

- Author: @model-risk
- Date: 2026-10-11
- Scope: `underwriting_pipeline/ai/llm_extract.py`, `underwriting_pipeline/ai/sources.py`. Tested with the model call stubbed. Synthetic data.
- High findings are in the review message in `team/DISCUSSION.md`, not here (D-030).

- Medium: the model's reply is not checked against the nine field ids. A duplicate id and an unknown id pass through `llm_extract`, and an id the model leaves out gets no row.
- Medium: a conflict with one side under the gate, or uncited, disappears with no trace. The field has no value and no conflict record.
- Medium: a kept conflict stores value and source only. The quote position and the confidence of each side are dropped, so a conflict has no citation.
- Medium: a reply whose only value is 0 or false is treated as "no fields" and becomes `extraction_failed`.
- Medium: confidence is not range-checked. NaN and 95 both pass the 0.75 gate.
- Medium: a text file that is not UTF-8, or a damaged or locked PDF or image, raises out of `read_folder`. The whole submission fails with no per-file status.
- Medium: OCR of a scanned PDF needs `pdftoppm` (poppler). It is not installed on this machine, the error is swallowed with no reason given, and that path has no self-check. Only image scans were OCR-tested here.
- Medium: a multi-page scanned PDF gets one mean OCR score. Two unreadable pages pulled a readable page to 0.357, so every field from the readable page would be dropped.
- Medium: the prompt holds rules written for development files (taqueria, mamposteria, bar and night club). Nothing shows they generalize.
- Low: the whitespace-tolerant quote match can join a label on one line to a value on another.
- Low: the "no known loss" guard is English only and looks only at the cited span.
- Low: Excel dates are read as timestamp strings, a formula with no saved value is blank, and hidden sheets are read.
- Low: `prepare.py` line 4 and the task criterion still say OPENAI_API_KEY. The code reads LLM_API_KEY (D-011, D-012).
- Low: the Tesseract version and language pack are not in `OCR_SETTINGS`, which is kept by hand and is part of the cache key.
- Low: the unreadable-page cut-offs (mean 40, 4 words, OSD confidence 1) have no evidence behind them.
- Low: the request header says the caller is curl.
