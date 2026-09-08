# Gap fill status (verified 2026-09-08)

| Gap | Severity | Status | Evidence |
|-----|----------|--------|----------|
| In-memory state | High | **FILLED** (Redis jobs + file fallback; audit on disk + Redis dual-write; portfolio JSON) | `storage/job_store.py`, `storage/file_job_store.py`, `audit/store.py`, `portfolio/store.py` — Postgres PAS sync still optional/future |
| Synthetic ML only | High | **FILLED** (real CSV path + export from audit outcomes) | `ml/training.py`, `ml/export_training.py`, `POST /ml/export-training`, `ml_data/README.md` |
| Lending ingestion | High | **FILLED** (regex + OCR + LLM extraction) | `ingestion/lending/loader.py`, `lending/llm_extractor.py`, `/lending/pipeline/run` accepts `documents`/`directory` |
| Simulated oracles | Medium | **CODE-READY / blocked on keys** | Enriched gateway CLUE/A-PLUS scenarios in `gateway/payloads.py`; live HTTP in `oracles/*` + `docs/ops/ORACLE_LIVE_WIRING.md` — needs LexisNexis/Verisk sandbox credentials |
| No Celery for insurance | Medium | **FILLED** | `tasks/pipeline_tasks.py`; `/pipeline/run` honors `use_celery` or `INSURANCE_USE_CELERY=true` |
| Pricing calibration | Medium | **FILLED** (file/URL rate curves) | `rating/calibration.py`, `data/rate_curves.json`, `RATE_CURVES_URL` / `RATE_CURVES_PATH` |
| Stub connectors | Medium | **PARTIAL** | Live when configured: folder / IMAP / Outlook-IMAP / S3 / SFTP. Drive / SharePoint / IVANS / PAS adapters remain catalog stubs |
| Mortgage progress/errors | Low | **FILLED** | Stage progress via `PipelineProgressTracker` → job_store; fail-closed empty/error → refer |
| Life filings beyond term | Medium | **PARTIAL** | Pilot exhibits: all term + traditional/limited-pay/participating WL + immediate annuity. UL/VUL/other annuities stay illustrative |
| Carrier book cutover | High | **PROCESS** | Checklist + CLI `cutover-check`; template `data/rating/carrier_book_import_template.csv`. Pilot synthetic book must stay non-customer |

## Still external (not a code gap)

1. Oracle / Guidewire **vendor sandbox API keys** (not the synthetic gateway)
2. Customer **filed rate book** import (`posture=carrier_imported` / SERFF) — see `data/rating/README_CARRIER_BOOK.md`
3. Carrier **claims warehouse** feed for large-scale ML
4. Full **PostgreSQL** policy-admin sync
5. Infra/legal: apply Terraform, domain/TLS/SPF, counsel-signed DPA/privacy, trademark filing — `docs/ops/LAUNCH_CHECKLIST.md`

## Ops commands

```bash
PYTHONPATH=src python cli.py sandbox-status
PYTHONPATH=src python cli.py cutover-check
PYTHONPATH=src python cli.py oracle-verify --ping
PYTHONPATH=src python scripts/ops/import_carrier_filings.py --csv data/rating/carrier_book_import_template.csv --carrier "Your Carrier"
```
