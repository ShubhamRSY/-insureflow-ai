# Observability — Prometheus, Grafana, OpenObserve

Rytera already ships CloudWatch JSON logs, LangSmith LLM traces, and `/ops/snapshot`.
This stack adds **metrics + dashboards + log/trace ingest** for local compose and
self-hosted ops. It does **not** invent a live vendor feed.

| Layer | What | Where |
|-------|------|--------|
| Metrics | `prometheus_client` counters/histograms | `GET /metrics` |
| Dashboards | Grafana (provisioned) | http://localhost:3000 |
| Logs + traces | OpenObserve HTTP `_json` ingest | http://localhost:5080 |
| Snapshot | Job counts + sandbox alerts | `GET /ops/snapshot` (auth) |
| CloudWatch | Optional AWS landing zone | `CLOUDWATCH_LOGS=true` |
| LangSmith | LLM/agent eval traces | `LANGSMITH_API_KEY` |

## Quick start

```bash
docker compose up -d prometheus grafana openobserve api redis db
```

| UI | URL | Default login |
|----|-----|----------------|
| Grafana | http://localhost:3000 | `admin` / `rytera` (anonymous Viewer also on) |
| Prometheus | http://localhost:9090 | — |
| OpenObserve | http://localhost:5080 | `root@example.com` / `Complexpass#123` |
| Metrics | http://localhost:8000/metrics | optional `METRICS_BEARER` |

Dashboard folder **Rytera → Rytera UW Platform** (`uid: rytera-uw`).

## Metrics

| Name | Type | Labels |
|------|------|--------|
| `rytera_http_requests_total` | counter | `method`, `path`, `status` |
| `rytera_http_request_duration_seconds` | histogram | `method`, `path` |
| `rytera_pipeline_runs_total` | counter | `line`, `decision`, `status` |
| `rytera_quotes_total` | counter | `eligible`, `line` |
| `rytera_binds_total` | counter | `result` |
| `rytera_oracle_findings_total` | counter | `severity` |
| `rytera_jobs` | gauge (scrape-time) | `namespace`, `status` |

Paths are normalized (`{id}`, `{n}`) so UUID/demo ids do not explode cardinality.
`/metrics` itself is not recorded.

Multi-worker uvicorn (compose `WEB_CONCURRENCY`) uses `PROMETHEUS_MULTIPROC_DIR`
(set in `entrypoint.sh`).

Optional scrape auth:

```
METRICS_BEARER=a-long-token
# Prometheus scrape Authorization: Bearer a-long-token
```

## OpenObserve

Disabled unless `OPENOBSERVE_URL` is set. Compose sets it to `http://openobserve:5080`.
Local `insureflow serve` leaves it off (`.env.example`).

Ingest:

- Logs: `POST {url}/api/{org}/{OPENOBSERVE_LOGS_STREAM}/_json`
- Traces: `POST {url}/api/{org}/{OPENOBSERVE_TRACES_STREAM}/_json`
- Prometheus remote_write (compose): `/api/default/prometheus/api/v1/write`

Auth: Basic (`OPENOBSERVE_USER` / `OPENOBSERVE_PASSWORD`) or `OPENOBSERVE_TOKEN`.
Shipper is best-effort and never fails a UW request.

## Railway / production

Do **not** assume Grafana/OO run on Railway by default. Point scrape at the public
API `/metrics` (prefer `METRICS_BEARER` + private network). Host Grafana + OpenObserve
beside the bank landing zone, or keep CloudWatch as the AWS sink.

Bank overlay (`deploy/docker-compose.bank.yml`) un-publishes Prom/Grafana/OO host
ports so they stay on the internal compose network.

## Files

- `src/insureflow/observability/prometheus_metrics.py`
- `src/insureflow/observability/openobserve.py`
- `src/insureflow/observability/http_middleware.py`
- `deploy/observability/prometheus.yml`
- `deploy/observability/grafana/`
