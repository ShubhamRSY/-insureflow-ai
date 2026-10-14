# GCP hosting migration design (Railway → Google Cloud)

- Task: T-100. Requested by @user on 2026-10-13 (scope chosen by @user: "Hosting + Vertex/Document AI"). Owner and author: @ml-engineer.
- Reviewers: @software-engineer, @compliance, @model-risk (T-100).
- Status: IN_REVIEW, set by the owner on 2026-10-13. Not approved by anyone; this is not a production approval and authorizes no purchase.
- Date: 2026-10-13.
- **What this document is.** A design for moving the *hosting* of the existing app from Railway to Google Cloud. It describes a proposed `infra/gcp/` layout. It changes no application code, applies no Terraform, and creates no GCP resource.
- **What this document is not, and the separate decision.** Switching the *model* to Vertex AI (Gemini 2.5 Flash/Pro) and OCR to Document AI is a **separate proposal, P-019 (T-099)** by @ai-engineer-assistant, because a model/OCR change needs `approve change P-###` from @user (D-017). This task moves where the containers run; it does not choose a model host. The two can land independently.
- Data: synthetic only. Every figure is read from a file in this repo or is an estimate; nothing was paid, called, or created.
- Every "estimate" dollar figure is labeled as such. Every number whose source is a file is cited.

## 0. How to read this document

- **As-is** = what runs today on Railway / docker-compose. **Proposed** = the GCP mapping I recommend. **Not decided** = a choice this document does not make and names the deciding role for.
- Component names ("api", "worker", "worker-large", "clamav", "redis", "db", "prometheus", "grafana", "openobserve") are the service names in `docker-compose.yml`.
- The env contract is the list in `docker-compose.yml:3-38` and the AWS task definitions (`infra/aws/main.tf:611-621`, `:673-682`, `:729-737`).
- The `infra/aws/` stack is a **reference for shape, not a template to copy** (its own header says it is a "bank landing zone": VPC/RDS/ECS/ALB/WAF/Cognito). GCP services do not map one-to-one; where they differ the difference is stated.
- Nothing here is decided. Section 4 names the deciding role for each open point, from the protocol's Decision rights table (`00-team-protocol.mdc:93-106`).

## 1. Component → GCP service mapping

The component list is the compose services plus what they talk to. "Proposed" is the service; "Alt / note" is the runner-up and the reason.

| # | Component (as-is) | Evidence | Proposed GCP service | Alt / note |
|---|---|---|---|---|
| 1 | **FastAPI api** — `uvicorn insureflow.api:app`, multi-worker (`entrypoint.sh:21-24`), health at `/health` (`railway.json:9`) | compose `api`; `railway.json` | **Cloud Run** (container, CPU-always-allocated, min-instances ≥ 1) behind a global external HTTP(S) LB | GKE Autopilot if it shares a cluster with the workers (see #3). Cloud Run is the boring choice for a single HTTP service |
| 2 | **worker** — `celery -A insureflow.tasks.celery_app worker -Q agents,pipeline,mortgage --concurrency=2` | compose `worker:56-68`; `celery_app.py:36-40` | **GKE Autopilot Deployment** (1+ replica) — a Celery worker is a long-lived pull consumer, which Cloud Run fits poorly | Cloud Run with min-instances = 1 and CPU always allocated is a fallback for a pilot; it is request-shaped and can idle-scale in ways a broker consumer must not |
| 3 | **worker-large** — dedicated pool for the `pipeline-large` queue, `--concurrency=1`, heavier memory | compose `worker-large:73-85`; `dispatch.py` `LARGE_FILE_QUEUE`; AWS `worker_large` 2 vCPU / 4 GiB (`infra/aws/variables.tf:76-90`) | **Separate GKE Deployment** (its own node pool / resource requests, 4 GiB+) so a burst of GB-scale jobs cannot starve #2 | Keep it a distinct workload on the same cluster. This isolation is a requirement (`infra/aws/main.tf:710-714`), not a nicety |
| 4 | **Postgres + pgvector** — `pgvector/pgvector:pg17`; `DATABASE_URL` | compose `db:157-173` | **Cloud SQL for PostgreSQL** (16/17), private IP, CMEK | **AlloyDB for PostgreSQL** (pgvector supported) if Cloud SQL's pgvector story is not good enough — see the OPEN ITEM in section 3 |
| 5 | **Redis / Celery broker + result backend + job store** — `redis:7-alpine`; `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `JOB_STORE_BACKEND=redis`, `METRICS_BACKEND=redis` | compose `redis:101-107`; `celery_app.py:12-13` | **Memorystore for Redis** (Basic, 1 GiB to start) | Standard tier (HA) for production. Same Redis protocol, so the app needs no change; only `REDIS_URL`/`CELERY_*` move to the Memorystore private IP |
| 6 | **ClamAV** — `clamav/clamav:stable`, `clamdcheck.sh` healthcheck, scanning **fails closed**, ~1–2 min signature load; `CLAMAV_HOST` | compose `clamav:87-99`; `ingestion/intake.py` | **Not a managed GCP service.** Run `clamav/clamav` as a **sidecar container** in the api pod (Cloud Run multi-container / GKE pod) and in each worker pod, with a shared signature volume | A single dedicated `clamd` GKE Deployment + Service is the alternative (one signature DB, not N copies). **cloud-native AV scanning** is a paid product, outside D-011's spirit and not proposed |
| 7 | **Object storage / audit WORM bucket** — S3 presigned POST for large uploads (`object_storage.py:90-104`); S3 Object Lock audit bucket (`infra/aws/main.tf:279-309`) | `object_storage.py:44-160`; `infra/aws/main.tf:279-309` | **Cloud Storage**: one bucket for uploads, one bucket for audit with **Object Retention Lock / Bucket Lock**, Bucket Versioning, Uniform bucket-level access, CMEK | GCS is not byte-identical to S3 Object Lock (see section 3). The app uses `boto3` presigned **POST**; GCS supports an S3-compatible XML API but its presigned-POST policy support differs — a migration item for @software-engineer, not done here |
| 8 | **Secrets** — `SECRET_KEY`, `ENCRYPTION_KEY` (Fernet, application-level, `encryption.py:14-41`), `POSTGRES_PASSWORD`, `LLM_*`; today from shell or AWS Secrets Manager (`AWS_SECRETS_ARN`) | compose `x-api-env:3-38`; `infra/aws/main.tf:135-161` | **Secret Manager**, consumed as env (Cloud Run secret env vars / GKE CSI secret store). `ENCRYPTION_KEY` stays app-level Fernet, independent of KMS | CMEK via **Cloud KMS** for Cloud SQL / GCS / Secret Manager. **Never** mount the repo `.env` (it holds a paid OpenAI key, D-011 — do not use it in the pipeline) |
| 9 | **Image registry** — CI pushes a multi-arch image; Railway builds from `Dockerfile` | `.github/workflows/ci.yml:300-334`; `railway.json:3-6` | **Artifact Registry** (Docker repo), built by Cloud Build or GitHub Actions | Keep GitHub Actions as the builder, push to Artifact Registry; Cloud Build is the all-GCP alternative |
| 10 | **Observability** — Prometheus `v2.54.1` scrapes `/metrics`; Grafana `11.2.0`; OpenObserve receives `remote_write` and logs; in-app span tracing via `observability/telemetry.py` (a **hand-rolled, stdlib-only** `Span`/`PipelineTrace`/`TelemetryCollector` that persists JSONL and emits a trace summary to OpenObserve through `observability.openobserve.emit_traces` — it is **not** OpenTelemetry); `PROMETHEUS_MULTIPROC_DIR`; `METRICS_BEARER` | compose `prometheus:109-124`, `grafana:126-143`, `openobserve:145-155`; `deploy/observability/prometheus.yml`; `observability/telemetry.py:19-243`, `:190-208` | **Cloud Monitoring** (metrics + dashboards + uptime checks) and **Cloud Logging**; **Managed Service for Prometheus** for the existing `/metrics` scrape. **Cloud Trace is not a drop-in:** `telemetry.py` emits no OTLP spans, so adopting Cloud Trace means instrumenting the app with OpenTelemetry — a proposed app change owned by @software-engineer, **out of scope for this hosting design** (see C9). The OTLP exporter exists only in the `eval` optional extra (`pyproject.toml:57-70`), not the runtime app | OpenObserve has no GCP managed equivalent. Options: keep Grafana+OpenObserve as GKE workloads (lift-and-shift), or replace dashboards with Cloud Monitoring. The hand-rolled tracer keeps working unchanged unless C9 is adopted. This is a decision (section 4) |
| 11 | **CI/CD** — GitHub Actions: lint/test, build+scan, push image, deploy | `.github/workflows/ci.yml:332-334` | **Artifact Registry + GitHub Actions** deploy step (`gcloud run deploy` / `kubectl`), i.e. replace the "Deploy to Railway" step only | **Cloud Deploy** as the GCP-native pipeline. Either way the existing test/scan gates stay |
| 12 | **Networking** — none today (single Railway service); AWS reference has VPC, private subnets, ALB, WAF, NAT | `infra/aws/main.tf:40-110`, `:367-532` | **VPC** (private subnets) + **Direct VPC egress** from Cloud Run (Serverless VPC Access connector as the older alternative) + **Cloud Load Balancing** (global external HTTP(S)) + **Cloud Armor** (WAF) + **Cloud DNS** + **Google-managed certificates** | Cloud Armor replaces AWS WAF (`infra/aws/main.tf:419-532`): rate-limit + managed rules. Prefer **Direct VPC egress** over the connector — no min-instance connector charge |
| 13 | **Scheduler / migrations** — none in compose | — | **Cloud Scheduler** + a Cloud Run Job if a periodic task is needed; DB migrations as a Cloud Run Job on deploy | Design-only; no schedule is invented here |

**Runtime decision to surface (item 1 vs 2/3): Cloud Run or GKE?** My recommendation for the pilot is **Cloud Run for the api + GKE Autopilot for the workers** (a hybrid), because the Celery workers are long-lived broker consumers and the api is a stateless HTTP service. The single-runtime alternatives are (a) all-GKE Autopilot, or (b) all-Cloud-Run. This choice is **@ml-engineer's, consulting @software-engineer** (Decision rights: "Deployment, monitoring, infra"); see section 4.

## 2. Mapping table, as a picture (proposed)

```
GitHub Actions ──build/scan──▶ Artifact Registry ──deploy──▶ Cloud Run (api) ──▶ Cloud LB + Cloud Armor
                                                                    │                     │
                                                                    ▼                     ▼
                                            Direct VPC egress ──▶ VPC (private)     Cloud DNS + managed cert
                                                                    │
        GKE Autopilot:  worker  ·  worker-large(pipeline-large)  ·  (clamd sidecar)  ·  (Grafana/Observe, optional)
                                                                    │
     Cloud SQL (Postgres+pgvector) ── Memorystore (Redis) ── Cloud Storage (uploads + WORM audit) ── Secret Manager ── Cloud KMS
                                                                    │
                              Observability: Cloud Logging · Cloud Monitoring · Managed Prometheus · (Cloud Trace only if C9)  
```

## 3. Unresolved constraints stated plainly

| # | Constraint | What it means | Who resolves it |
|---|---|---|---|
| C1 | **D-011: no paid API** (`team/DECISIONS.md:115`; host on Groq's *free* tier, D-012 `:127`). GCS/Cloud SQL/Cloud Run/Memorystore/LB are all **paid services.** | Hosting on GCP cannot be done under D-011 as written. @user must **lift or replace D-011** before any `terraform apply`, or the migration cannot proceed. This document assumes no purchase. | @user (D-011 is @user's decision) |
| C2 | **Cloud SQL for PostgreSQL + pgvector is UNVERIFIED.** The app's DB image is `pgvector/pgvector:pg17` (compose `db:158`), and RAG queries depend on pgvector (`src/insureflow/rag`). Cloud SQL's supported-extension list must be checked for this Postgres version before committing. | **OPEN ITEM.** Verify Cloud SQL for PostgreSQL supports the `vector` extension at the version chosen. | @ml-engineer verifies; @data-engineer consulted (data layer) |
| C2a | **Fallback if pgvector is not supported on Cloud SQL** | **AlloyDB for PostgreSQL** (supports pgvector, same wire protocol, drop-in `DATABASE_URL`), or a self-managed Postgres+pgvector on GKE. AlloyDB is more expensive; the GKE option is more ops. | @ml-engineer, consulting @data-engineer and @software-engineer |
| C3 | **Managed certificates / DNS / region / data residency.** The region (e.g. `us-central1` vs `us-south1`), whether the agency/bank requires a specific data-residency location, and the domain + Google-managed cert are not recorded anywhere. The app holds applicant PII and audit bundles. | **OPEN ITEM.** Region is a residency and legal question, not an infra default. | Region/residency: @compliance + @user; DNS/cert: @software-engineer (app integration) with @user |
| C4 | **Model / OCR provider change is a separate proposal.** This task moves hosting only. P-019 (T-099) proposes Vertex AI + Document AI and carries its own D-011 conflict. | These two land independently. Nothing in this design requires P-019, and P-019 does not require this design. | @user (P-019, `approve change P-019`) |
| C5 | **S3 presigned POST → GCS.** `object_storage.py:90-104` returns a `generate_presigned_post` shape; GCS's S3-compatible XML API does not match presigned-POST semantics exactly. | A code change (signing / upload path) in `object_storage.py` would be needed. **Out of scope here** (this is hosting); @software-engineer owns application integration. | @software-engineer |
| C6 | **Audit WORM semantics.** GCS **Bucket Lock** locks a bucket retention policy; per-object retention holds exist but the governance/compliance-mode model differs from S3 Object Lock. | @compliance must confirm GCS retention satisfies the examiner requirement before the audit bucket moves. | @compliance (regulatory acceptability) |
| C7 | **`CLOUDWATCH_LOGS` is AWS-specific** (compose `:23`); a GCP logging sink is a code-path change. | For the pilot, container stdout/stderr is captured by Cloud Logging with no app change; the flag simply stays off. Any new "ship to Cloud Logging from inside the app" is an application change. | @software-engineer |
| C8 | **ClamAV fails closed** (logic at `ingestion/intake.py:71-73`: on an unreachable `clamd`, `scan_file` returns `"scan-unavailable"` rather than passing the file); compose defines the service at `clamav:89-99` with `start_period: 300s` (`:97`); on boot the app waits ~1–2 min for signatures. A cold start of a sidecar must not block the api from serving `/health`. | Startup/liveness ordering must be designed (readiness depends on `clamd`). | @ml-engineer, consulting @software-engineer |
| C9 | **Cloud Trace is an application change, not a hosting drop-in.** `observability/telemetry.py` is a hand-rolled span tracer (stdlib only) that writes JSONL and posts a trace summary to OpenObserve (`telemetry.py:190-208`); it emits **no OTLP spans**, so there is nothing for Cloud Trace to ingest as-is. The OTLP gRPC exporter is only in the `eval` optional extra (`pyproject.toml:57-70`), not the runtime app. | To use Cloud Trace, the app must be instrumented with OpenTelemetry (exporter in runtime deps + span export). **Out of scope here** (this is hosting); @software-engineer owns application integration. Until then the existing tracer and OpenObserve keep working unchanged. | @software-engineer |

## 4. Decided vs not decided

**Nothing in this document is decided.** It proposes. The deciding role is named per the protocol's Decision rights table (`00-team-protocol.mdc:93-106`).

| Decision | Proposed by this doc | Deciding role (per protocol) |
|---|---|---|
| Move hosting Railway → GCP at all | (the task; @user asked) | **@user** — the request is @user's ("can we migrate our project on gcp?"). Team may only DRAFT until @user decides |
| Region, data residency, DNS, managed cert, spend | options only (section 3, C3) | **@user** (any spend, D-011); region/residency also **@compliance** |
| Cloud Run vs GKE vs hybrid; service choices in the table | hybrid recommended (section 1) | **@ml-engineer**, consulting **@software-engineer** (Deployment/monitoring/infra) |
| Cloud SQL pgvector verification + fallback | verify, then choose | **@ml-engineer**; fallback cost/schema with **@data-engineer** |
| VPC / LB / Cloud Armor / egress design | proposed | **@ml-engineer**, consulting **@software-engineer** |
| Anything touching applicant data: bucket placement, retention, WORM, CMEK, what leaves to a model | design only | **@compliance** (regulatory/legal acceptability); **@responsible-ai** if fairness-relevant |
| Application changes (S3→GCS signing, logging sink, secrets fetch, OTel/Cloud Trace instrumentation) | out of scope; C5/C7/C9 | **@software-engineer** |
| Production model approval; anything P-019 changes | not this task | **@model-risk** (production approval of any model) |
| Switching model host / OCR to Vertex / Document AI | separate proposal P-019 (T-099) | **@user** (`approve change P-019`) |

## 5. Rough cost estimate for a small pilot

**Label for every figure below: estimate from public GCP list prices, Oct 2026; not a quote; no free tier applied; nothing was checked against a live pricing page on this turn. This is an order-of-magnitude planning figure, replacing the $100–$300/month "platform allowance" that `deliverables/architecture/system-design.md:930` asks @ml-engineer to replace.**

Assumptions this range rests on:
1. Pilot scale: the system-design volumes 300 / 1,000 / 3,000 submissions a month, but sized for the **300/month** point (section 2.1 of `system-design.md`). The **model/OCR cost is *not* included here** — it is priced separately in `system-design.md` 8.3 (Table B: ~$20–$28/month at 300 on Flash/Pro) and is frozen under D-011 until P-019.
2. Region: one US region, no HA (single-zone Cloud SQL, Memorystore **Basic**), non-production.
3. Two workers (one default, one `pipeline-large`) at modest size; the api scaled to near-zero off-hours except a min-instance.
4. GCS volume small (single-digit GB), logging inside the free allowance for the pilot.
5. **Prices are from my own knowledge of GCP list pricing, not from a page read this turn** — D-047 allowed one read of *model* price pages for T-095, not cloud infra pages. @actuary owns cost modeling; this is a rough allowance, not the cost model.

| Line | Sized as | Estimate / month |
|---|---|---|
| Cloud Run (api, min-instance 1, 1 vCPU/1 GiB, CPU-always) | low traffic | $15 – $40 |
| GKE Autopilot (2 small worker pods, 1–2 vCPU / 2–4 GiB each) | worker + worker-large | $75 – $180 |
| Cloud SQL for PostgreSQL (1–2 vCPU, 50 GB SSD, single-zone) | private IP, CMEK | $60 – $120 |
| Memorystore for Redis (Basic, 1 GiB) | broker + result backend | $35 – $55 |
| Cloud Load Balancing (global external HTTP(S)) + health checks | one | $18 – $30 |
| Cloud Armor | 1 policy, few rules, low req | $5 – $15 |
| Cloud Storage (uploads + WORM audit, ~5 GB) | small | $1 – $5 |
| Secret Manager + Cloud KMS (keys + ops) | few secrets | $2 – $5 |
| Artifact Registry (few images) | small | $1 – $5 |
| Cloud Logging / Monitoring / Trace | pilot volume | $0 – $30 |
| Direct VPC egress / networking | no connector | $0 – $10 |
| **Total estimate (pilot, no model/OCR)** | | **≈ $210 – $500 / month** |

Notes:
- HA (Cloud SQL HA, Memorystore **Standard**, multi-replica workers) roughly **doubles** the database/redis lines and pushes the total toward **$450 – $900 / month**.
- The single biggest swing is **Cloud SQL + Memorystore** (~half the total) and whether the runtime is **GKE** or **Cloud Run**.
- The `pipeline-large` worker is the memory-heavy one (4 GiB+, `infra/aws/variables.tf:76-79`); a bursty GB-scale month costs more on GKE than the flat figure above.
- **This range must be replaced by @actuary's cost model** before any spend is approved; @user decides any spend (D-011).

## 6. Proposed `infra/gcp/` layout (described only — nothing created)

Mirror the *shape* of `infra/aws/` (a root with `main.tf`, `variables.tf`, `outputs.tf`, `terraform.tfvars.example`) but split GCP's pieces into modules, because a single 791-line `main.tf` (`infra/aws/main.tf`) is hard to review:

```
infra/gcp/
├── README.md                     # what each module is, how to run, the C1–C8 open items
├── versions.tf                   # terraform >= 1.5, google / google-beta providers
├── envs/
│   ├── pilot/
│   │   ├── main.tf               # wires the modules for a non-HA pilot
│   │   ├── variables.tf
│   │   ├── terraform.tfvars.example
│   │   ├── outputs.tf
│   │   └── backend.tf            # GCS remote state (bucket bootstrapped by hand, like infra/aws-uploads/main.tf:30-48)
│   └── prod/                     # same shape; HA, multi-zone, Cloud SQL HA, Memorystore Standard
├── modules/
│   ├── networking/               # VPC, private subnets, Cloud Router/NAT, firewall
│   ├── run_api/                  # Cloud Run service (api), Direct VPC egress, health /health
│   ├── gke_workers/              # GKE Autopilot cluster + worker + worker-large Deployments
│   ├── cloud_sql/                # Cloud SQL Postgres (private IP, CMEK, pgvector check note)
│   ├── alloydb/                  # fallback DB module (built only if C2 fails)
│   ├── memorystore/              # Memorystore for Redis
│   ├── storage/                  # uploads bucket + WORM audit bucket (Object Retention/Bucket Lock)
│   ├── secrets/                  # Secret Manager + Cloud KMS
│   ├── observability/            # Managed Prometheus scrape, uptime checks, log sinks, alert policies
│   ├── load_balancing/           # global external HTTP(S) LB, managed cert, Cloud Armor policy, Cloud DNS
│   └── artifact_registry/        # Docker repo for the app image
└── (no .tf applied by T-100)
```

- One GCS remote-state bucket per env, created by hand once (the `infra/aws-uploads/main.tf:30-48` pattern), so state does not live on a laptop.
- The `cloud_sql` module carries the pgvector verification as a comment/flag until C2 is answered; `alloydb` exists only as the fallback module.
- No `terraform.tfvars` with real values is written. No key, secret, or project id is committed.

## 7. Review findings and disposition

Against @software-engineer's T-100 review (`team/DISCUSSION.md:2400-2403`, verdict APPROVE WITH CHANGES). Design-only edits; no application code, no Terraform, no GCP resource.

| # | Finding | Disposition |
|---|---|---|
| F1 | Mapping-table item 10 mislabeled `observability/telemetry.py` as "OTel spans" for Cloud Trace. The module is a hand-rolled, stdlib-only span tracer that ships JSON to OpenObserve; Cloud Trace would need app instrumentation, so it is not a like-for-like map. | **Fixed.** Item 10 now states what `telemetry.py` is (hand-rolled, stdlib-only `Span`/`PipelineTrace`/`TelemetryCollector`, JSONL + `openobserve.emit_traces`, **not** OpenTelemetry) and marks "adopt OpenTelemetry + Cloud Trace" as a proposed **@software-engineer** app change, **out of scope** for this hosting design, recorded as **C9**. Section 2 picture and the section 4 application-changes row updated to match. Verified against `observability/telemetry.py:19-243` and `pyproject.toml:57-70` (OTLP exporter only in the `eval` extra). |
| F2 | Minor: C8 cited compose `clamav:87-89`, which is a comment; the fail-closed logic is `ingestion/intake.py:71-73` (compose `start_period` is 300s). | **Fixed.** C8 now cites `ingestion/intake.py:71-73` for the fail-closed logic and `clamav:89-99` (`start_period: 300s`, `:97`) for the service definition. |

Both acceptance criteria remain met; nothing else in the design changed. Status stays **IN_REVIEW**.

## 8. What this document does not change

- No file under `src/`, `underwriting_pipeline/`, or `simulation/` is touched.
- No Terraform is applied; no `infra/gcp/` directory is created.
- No GCP resource is created; no network call was made; no model was called.
- No message is written as @user and no decision owned by @user is recorded.
- D-011 stands: no paid API, and GCP hosting itself is a paid service (C1).
