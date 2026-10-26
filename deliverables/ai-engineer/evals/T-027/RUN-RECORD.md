# T-027 official hold-out run record — SUB-127 to SUB-146

- Run by: orchestrator, 2026-10-15 22:14–22:31, on the user's typed instruction in this session. Run once, scored once. No code or gold change before, during or after.
- Score files (written by the frozen scorer): `deliverables/ai-engineer/evals/SUB-127-146-holdout.md` and `.json`.
- Synthetic. Not a production approval.

## Fixed before running (user rules) and how each was checked

| Rule | Check | Result |
|---|---|---|
| Code = frozen `3a77415` | `git diff 3a77415 HEAD -- underwriting_pipeline/` empty; last commit touching `underwriting_pipeline/` = `3a7741506c72` ; no uncommitted paths there | met (HEAD `15265d4`) |
| Gold = `bd9168e` | `git diff bd9168e HEAD` on `simulation/inbox/SUB-127..146` and the gold files: empty; no uncommitted paths | met |
| .venv Python | `.venv/bin/python` 3.14.6; pdfplumber 0.11.10, openpyxl 3.1.5, pytesseract 0.3.13, pdf2image 1.17.0, pillow 12.3.0; tesseract 5.5.2; poppler 26.10.0 | met |
| `smoke_readers.py` first | 8 of 8 file types read (typed PDF, image-only PDF, colour/grey/rotated scan, Excel, email-only, Spanish), "smoke ok" | met |
| No cached replies for SUB-127–146 | cache key computed per file with `llm_extract.key_for` (no call): **none cached** | met |
| qwen, paced | `qwen/qwen3.8-27b` on Groq, `LLM_PACE_SECONDS=55` | met |
| Retry: a 429 or network error once; anything else "call failed" | The frozen code retries more (`_post` up to 6 posts on 429/network, a resend after HTTP 400, `score_retry` 3 attempts on any error). The run used `T-027/t027_run.py`, a driver outside `underwriting_pipeline/` that caps posts at the network call (second post only after a 429/timeout/network failure) and calls each file once. Pipeline files were not edited. Guard self-check passed before the run. | met |

## Calls

- 20 model calls, 0 call failed, 0 from cache. One failed attempt: SUB-145, HTTP 429 per-minute output-token limit ("Requested 1086, limit 1000"); posted again once, reply used.
- Tokens: 35,551 (prompt 21,476, completion 14,075); mean 1,778 per call, max 2,585.
- Cost per file: $0 in money (Groq free tier, D-011/D-012). Estimate at the only list prices captured in the repo (system-design 8.3: $0.30 in / $2.50 out per million): **≈ $0.0021 per file**. Estimate from public list prices, Oct 2026; free tier is development only.

## Route and loss-run readout (read-only, from each run's own report)

`route-lossrun-readout.json`, made by `t027_readout.py` with `workbench.match()` on the saved report and the gold "Expected carrier route" line. Route: **14 / 20**.

| File | Pipeline route | Gold route |
|---|---|---|
| SUB-132 | hold (status incomplete) | carrier_b |
| SUB-133 | hold | carrier_c |
| SUB-134 | no_match | carrier_c |
| SUB-139 | hold | no_match |
| SUB-141 | hold | senior_referral |
| SUB-146 | hold | senior_referral |

The other 14 match (carrier_a ×2, carrier_b ×1, hold ×11). No file routed to carrier_c or senior_referral; gold has carrier_c ×2 and senior_referral ×2.

Loss-run per document: the per-document column re-applies `prepare._run_doc_reason` to each document's text outside the gate, so it lists documents the gate itself may not reach. Accepted: SUB-127, 128, 130, 132, 134 (one typed carrier run each). Review: SUB-129, 131, 133 (scan/image-only run), SUB-135, 136, 138 (not a recognised carrier run), SUB-137, 139, 140 (no valued-as-of date). Also flagged by the re-applied rule: `application.jpg` in SUB-129 and SUB-144 ("loss run from scan/spreadsheet").

## Reports and driver

- `reports/SUB-*.json`: each file's full pipeline report and post count.
- `t027_run.py`, `t027_readout.py`, `t027_run.log`: driver, readout and console log as run. Their paths point at the session scratchpad.
