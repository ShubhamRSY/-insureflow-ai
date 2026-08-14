# Gap fill status (verified 2026-07-30)

| Gap | Severity | Status | Evidence |
|-----|----------|--------|----------|
| In-memory state | High | **FILLED** (Redis jobs + file fallback; audit on disk + Redis dual-write; portfolio JSON) | `storage/job_store.py`, `storage/file_job_store.py`, `audit/store.py`, `portfolio/store.py` — Postgres PAS sync still optional/future |
| Synthetic ML only | High | **FILLED** (real CSV path + export from audit outcomes) | `ml/training.py`, `ml/export_training.py`, `POST /ml/export-training`, `ml_data/README.md` |
| Lending ingestion | High | **FILLED** (regex + OCR + LLM extraction) | `ingestion/lending/loader.py`, `lending/llm_extractor.py`, `/lending/pipeline/run` accepts `documents`/`directory` |
| Simulated oracles | Medium | **CODE-READY / blocked on keys** | Live HTTP in `oracles/*` + `docs/ops/ORACLE_LIVE_WIRING.md` — needs LexisNexis/Verisk sandbox credentials |
| No Celery for insurance | Medium | **FILLED** | `tasks/pipeline_tasks.py`; `/pipeline/run` honors `use_celery` or `INSURANCE_USE_CELERY=true` |
| Pricing calibration | Medium | **FILLED** (file/URL rate curves) | `rating/calibration.py`, `data/rate_curves.json`, `RATE_CURVES_URL` / `RATE_CURVES_PATH` |
| Stub connectors | Medium | **FILLED** (3 live fetches) | **Email IMAP** + **AWS S3** + **SFTP**; other catalog rows stay demo stubs until vendor creds. No Airbyte/Fivetran/Airflow/Kafka. |
| Mortgage progress/errors | Low | **FILLED** | Stage progress via `PipelineProgressTracker` → job_store; fail-closed empty/error → refer |

## Still external (not a code gap)

1. Oracle / Guidewire **vendor sandbox API keys**
2. Carrier **claims warehouse** feed for large-scale ML (export path works; volume needs partner data)
3. Full **PostgreSQL** policy-admin sync (Redis+filesystem durable today; PG used for pgvector RAG when configured)
