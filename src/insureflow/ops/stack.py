"""What Rytera actually runs — not the generic cloud shopping list."""

from __future__ import annotations

import os
from typing import Any


def platform_stack() -> dict[str, Any]:
    from insureflow.auth import ROLE_HIERARCHY, Role
    from insureflow.flags import current_flags
    from insureflow.security.posture import resolve_security_posture
    from insureflow.storage.encryption import EnvelopeEncryption

    posture = resolve_security_posture()
    flags = current_flags()
    encryption_on = EnvelopeEncryption().enabled
    secrets_arn = bool((os.getenv("AWS_SECRETS_ARN") or os.getenv("AWS_SECRET_ID") or "").strip())
    worm = bool((os.getenv("WORM_AUDIT_PATH") or "./audit_logs/worm").strip())
    retention_bucket = bool((os.getenv("RETENTION_S3_BUCKET") or "").strip())

    return {
        "compute": {
            "bank": "ecs_fargate",
            "local": "docker_compose",
            "ci_image": "ghcr.io",
            "not_required": ["ec2", "gke", "aks", "azure_vm", "lambda", "argocd", "kubernetes"],
        },
        "ci_cd": {
            "github_actions": True,
            "workflows": [".github/workflows/ci.yml", ".github/workflows/scheduled_evals.yml"],
            "not_required": ["argocd", "github_actions_runners_as_lambda"],
        },
        "identity": {
            "app_rbac": [r.value for r in Role],
            "role_bands": {r.value: n for r, n in ROLE_HIERARCHY.items()},
            "sso": "oidc_okta_or_cognito",
            "cloud_iam": "ecs_task_and_execution_roles",
            "not_required": ["auth0"],
        },
        "security": {
            "encryption_at_rest": encryption_on,
            "pii_redaction": True,
            "audit_logs": True,
            "worm_path": worm,
            "examiner_s3": retention_bucket,
            "policy_checks": ["appetite", "bind_gates", "bank_mode", "zta"],
            "hardened": posture.is_hardened,
        },
        "communication": {
            "sync": "rest_fastapi",
            "async": "celery_redis",
            "events": "https_webhooks",
            "not_required": ["graphql", "kafka", "rabbitmq"],
        },
        "supporting": {
            "service_discovery": "alb_target_groups",
            "config": "env_and_dotenv",
            "secrets": "aws_secrets_manager" if secrets_arn else "env",
            "secrets_arn_set": secrets_arn,
            "feature_flags": "in_process_env",
            "metrics": "prometheus_/metrics",
            "logs": "cloudwatch_json",
            "optional_logs": "openobserve",
            "not_required": ["consul", "spring_config", "doppler", "vault", "launchdarkly", "elk", "opensearch"],
        },
        "observability": {
            "tracing": "langsmith",
            "app_monitoring": "cloudwatch",
            "scrape": "prometheus_grafana",
            "llm_eval": "ragas_deepeval_extras",
            "feedback": "hitl_signoff",
            "cost": "GET /billing/usage",
            "not_required": ["langfuse", "datadog", "new_relic", "helicone", "portkey"],
        },
        "flags": flags,
    }
