# Rytera™ — SOC 2 Readiness Questionnaire Pack (Draft)

Use this as the internal control narrative while a formal SOC 2 Type I/II engagement is planned.

## Trust service criteria mapping (summary)

| Criterion | Control in product / ops | Evidence |
|-----------|--------------------------|----------|
| **CC6 Security** | JWT RBAC, BANK_MODE lockdown, TLS (ALB/Caddy), WAF, Secrets Manager/KMS | `/security/status`, Terraform, CI |
| **CC7 Change mgmt** | GitHub Actions lint/type/test; GHCR image tags | `.github/workflows/ci.yml` |
| **CC8 Risk** | Model registry + override analytics; licensed UW gate | API underwriting + registry modules |
| **CC9 Monitoring** | CloudWatch Logs JSON + CloudTrail; LangSmith AI traces | `observability/cloudwatch.py`, LangSmith |
| **A1 Availability** | ECS desired count, RDS multi-AZ optional, health checks | ALB `/health`, compose diagnostics |
| **C1 Confidentiality** | Encryption at rest required in BANK_MODE; org-scoped jobs | `ENCRYPTION_KEY`, audit packages |
| **PI1 Privacy** | DPA template; PII redaction module; retention/WORM | `legal/DPA_TEMPLATE.md`, `audit/worm.py` |

## Access control

- Roles: viewer → underwriter → licensed_uw → admin → cuo
- Open registration **off** in BANK_MODE
- Auth reset **off** in BANK_MODE (break-glass via `ALLOW_AUTH_RESET`)
- Optional Cognito/Okta SSO (`/auth/sso/*`)

## Logging & audit

- Application audit trails + regulatory ZIP (SHA-256)
- WORM seal path with 7-year default retention
- Immutable CloudTrail for AWS API activity

## Gaps to close before Type II

- [ ] Formal access reviews (quarterly)
- [ ] Penetration test + remediations
- [ ] Vendor risk reviews for LLM providers
- [ ] Documented incident response runbook drills
- [ ] Production SSO JWKS validation (beyond stub)
- [ ] Multi-AZ RDS + tested restore drill

## Contact

Security questionnaires: security@rytera.ai (placeholder)
