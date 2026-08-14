# AWS Bank Landing Zone

Terraform under `infra/aws/` provisions a production-style bank sandbox for Rytera.

Rytera is the **decision maker**, not the system of record. Source files (bank
statements, ACORD XML, W-2s) stay in the customer's PAS / object store. In
`BANK_MODE` we drop raw document text after the job, encrypt the decision
bundle at rest in *their* VPC, and keep pattern memory as feature bands
(line, NAICS, TIV band, state, outcome) — never named insureds or account
numbers.

| What | Where it lives |
|------|----------------|
| Source documents | Customer PAS / S3 / file share (not copied to Rytera) |
| Decision (memo, scores, routing) | Encrypted audit in the landing zone (`ENCRYPTION_KEY`) |
| Memory | `audit_logs/decision_memory.jsonl` — PII-free patterns in the same VPC |
| LLM prompts | Redacted tokens only (`[REDACTED SSN]`, no last-4) |
| Photos to GPT-4V / Claude | **Blocked** unless `ALLOW_VISION_EGRESS=true` |
| Cloud embeddings (OpenAI/Cohere) | **Blocked** unless `ALLOW_EMBEDDING_EGRESS=true` — local hashed 1536-d vectors otherwise |
| LangSmith traces | **Blocked** unless `LANGSMITH_ALLOW_IN_BANK=true` |

Set `RETAIN_SOURCE_DOCS=true` only if the bank's examiner explicitly wants the
raw file in the WORM audit bucket.

## Stack

| Layer | Service |
|-------|---------|
| Network | VPC, public/private subnets, NAT, IGW |
| Edge | ALB (TLS/ACM, HTTP→HTTPS redirect, drop invalid headers) + WAFv2 |
| DDoS | AWS Shield Standard (included with ALB — do not buy Shield Advanced unless the bank already has it) |
| Compute | ECS Fargate (API + Celery worker) |
| Data | RDS Postgres + pgvector (OLTP + guideline vectors), ElastiCache Redis (jobs/cache) |
| Object storage | S3 Object Lock WORM for examiner audits — source files stay in the bank's PAS |
| Secrets | Secrets Manager + KMS key rotation |
| Observability | CloudWatch Logs (ECS awslogs) + CloudTrail |
| AI tracing | LangSmith (key injected via Secrets Manager) |
| Identity | Bank IdP via OIDC (Okta/Cognito) — PKCE; `SSO_REQUIRED` at cutover |

Do **not** add Kong, Apigee, Auth0, Nginx, or Cloudflare WAF. TLS, WAF, SSO to
**their** IdP, and a private VPC are the landing-zone edge.

Do **not** add Pinecone, Weaviate, Qdrant, Neo4j, Elasticsearch, or MySQL.
Guideline vectors are Postgres+pgvector; the UW graph is in-process; jobs are Redis;
blob retention is the WORM bucket.

Do **not** add EC2, GKE, Azure VMs, Lambda, ArgoCD, Consul, Vault, LaunchDarkly,
Datadog, New Relic, Helicone, Portkey, Langfuse, GraphQL, Kafka, or RabbitMQ.
Compute is **ECS Fargate** (Docker locally). CI is **GitHub Actions**. Identity is
**app RBAC + bank OIDC + ECS IAM roles**. Secrets are **Secrets Manager**. Flags are
**env vars**. Metrics are **CloudWatch + Prometheus**. Cost is **`GET /billing/usage`**.
Evals are the optional `[eval]` extra (Ragas / DeepEval) plus HITL sign-off.

```
Internet → WAF → ALB:443 (80 redirects) → ECS API:8000 (private)
                                              ↓
                                    ECS Celery worker (private)
                                              ↓
                                    RDS + Redis (private)
                                              ↓
                                 Secrets Manager / KMS
```

### Edge rules already in Terraform

- HTTP:80 → HTTPS:443 (301)
- WAF: rate limit (`waf_rate_limit`, default 2000/5min/IP), Amazon IP reputation, Core rule set, Known bad inputs, SQLi
- Optional Route 53 A-alias when `domain_name` + `route53_zone_id` are set
- App headers: HSTS, nosniff, DENY, Referrer-Policy, Permissions-Policy (`SecurityHeadersMiddleware` + Caddy)

## Apply

```bash
cd infra/aws
cp terraform.tfvars.example terraform.tfvars   # set ACM ARN + image
terraform init
terraform plan
terraform apply
```

Set ECS task env `AWS_SECRETS_ARN` (already in task def). On boot the API loads JSON secrets into the process environment.

## Local bank simulation (no AWS account)

```bash
./deploy/caddy/gen-certs.sh
export SECRET_KEY="$(openssl rand -hex 32)"
export ENCRYPTION_KEY="$(python -c 'from insureflow.storage.encryption import EnvelopeEncryption; print(EnvelopeEncryption.generate_key())')"
export POSTGRES_PASSWORD="$(openssl rand -hex 16)"
export BANK_MODE=true ENVIRONMENT=production
docker compose -f docker-compose.yml -f deploy/docker-compose.bank.yml up --build
# https://localhost:8443/dashboard
```

## Observability split

- **LangSmith** — LLM/agent traces + eval metrics (precision/recall/Ragas)
- **CloudWatch** — infra JSON logs + optional custom metrics (`Rytera/InsureFlow`)
- **Prometheus + Grafana** — `/metrics` scrape + UW dashboards (compose; internal-only under bank overlay)
- **OpenObserve** — log + trace ingest (`OPENOBSERVE_URL`); optional Prometheus remote_write

LangSmith + CloudWatch remain the bank AIOps pair; Prom/Grafana/OO cover self-hosted ops. See [OBSERVABILITY.md](./OBSERVABILITY.md).
