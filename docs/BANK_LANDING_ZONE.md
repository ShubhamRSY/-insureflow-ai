# AWS Bank Landing Zone

Terraform under `infra/aws/` provisions a production-style bank sandbox for Rytera.

## Stack

| Layer | Service |
|-------|---------|
| Network | VPC, public/private subnets, NAT, IGW |
| Edge | ALB (TLS/ACM) + WAFv2 |
| Compute | ECS Fargate (API) |
| Data | RDS Postgres (encrypted/KMS), ElastiCache Redis (private) |
| Secrets | Secrets Manager + KMS key rotation |
| Observability | CloudWatch Logs (ECS awslogs) + CloudTrail |
| AI tracing | LangSmith (key injected via Secrets Manager) |
| Retention | S3 Object Lock WORM bucket for examiner audits |
| Identity | Optional Cognito user pool (MFA-capable) |

```
Internet → WAF → ALB:443 → ECS:8000 (private)
                    ↓
            RDS + Redis (private)
                    ↓
         Secrets Manager / KMS
```

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
docker compose -f docker-compose.yml -f docker-compose.bank.yml up --build
# https://localhost:8443/dashboard
```

## Observability split

- **LangSmith** — LLM/agent traces + eval metrics (precision/recall/Ragas)
- **CloudWatch** — infra JSON logs + optional custom metrics (`Rytera/InsureFlow`)

Both are required for a credible bank AIOps story; neither replaces the other.
