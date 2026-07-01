from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class CheckStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    MISSING = "missing"
    ERROR = "error"


@dataclass
class ComponentCheck:
    component: str
    status: CheckStatus
    message: str
    category: str = "core"
    details: dict[str, Any] = field(default_factory=dict)


def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"


class SystemDiagnostics:
    """Run environment and dependency checks — never exposes full API keys."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path.cwd()

    def run_all(self) -> dict[str, Any]:
        checks = [
            self._check_llm(),
            self._check_llm_mode(),
            self._check_redis(),
            self._check_job_store(),
            self._check_encryption(),
            self._check_ocr(),
            self._check_audit_storage(),
            self._check_example_data(),
            self._check_mortgage_fixtures(),
            self._check_postgres(),
        ]
        ok = sum(1 for c in checks if c.status == CheckStatus.OK)
        degraded = sum(1 for c in checks if c.status == CheckStatus.DEGRADED)
        missing = sum(1 for c in checks if c.status == CheckStatus.MISSING)
        errors = sum(1 for c in checks if c.status == CheckStatus.ERROR)

        if errors > 0:
            overall = "error"
        elif missing > 0:
            overall = "missing"
        elif degraded > 0:
            overall = "degraded"
        else:
            overall = "healthy"

        return {
            "overall": overall,
            "summary": {
                "ok": ok,
                "degraded": degraded,
                "missing": missing,
                "error": errors,
                "total": len(checks),
            },
            "llm_mode": self._llm_mode_label(),
            "checks": [self._check_to_dict(c) for c in checks],
        }

    def _llm_mode_label(self) -> str:
        from insureflow.config import settings

        if settings.llm_api_key or settings.llm_cheap_api_key or settings.claude_api_key:
            return "llm_enhanced"
        return "deterministic_fallback"

    @staticmethod
    def _check_to_dict(c: ComponentCheck) -> dict[str, Any]:
        return {
            "component": c.component,
            "status": c.status.value,
            "message": c.message,
            "category": c.category,
            "details": c.details,
        }

    def _check_llm(self) -> ComponentCheck:
        from insureflow.config import settings

        has_openai = bool(settings.llm_api_key or settings.llm_cheap_api_key or settings.llm_expensive_api_key)
        has_claude = bool(settings.claude_api_key)

        if has_openai or has_claude:
            provider = settings.llm_cheap_provider or settings.llm_provider
            return ComponentCheck(
                component="llm_api_key",
                status=CheckStatus.OK,
                message="LLM API key configured — ReAct agents and LLM extraction enabled",
                category="llm",
                details={
                    "provider": provider,
                    "cheap_model": settings.llm_cheap_model,
                    "expensive_model": settings.llm_expensive_model,
                    "key_hint": _mask_key(settings.llm_api_key or settings.llm_cheap_api_key or settings.claude_api_key),
                    "openai": has_openai,
                    "claude": has_claude,
                },
            )

        return ComponentCheck(
            component="llm_api_key",
            status=CheckStatus.DEGRADED,
            message="No LLM API key — running deterministic rule-based agents only",
            category="llm",
            details={
                "fix": "Set LLM_API_KEY in .env (see .env.example)",
                "cheap_model": settings.llm_cheap_model,
                "expensive_model": settings.llm_expensive_model,
            },
        )

    def _check_llm_mode(self) -> ComponentCheck:
        mode = self._llm_mode_label()
        if mode == "llm_enhanced":
            return ComponentCheck(
                component="llm_pipeline_mode",
                status=CheckStatus.OK,
                message="Insurance: ReAct + extraction | Mortgage: LLM extraction + agent narrative",
                category="llm",
                details={"mode": mode},
            )
        return ComponentCheck(
            component="llm_pipeline_mode",
            status=CheckStatus.DEGRADED,
            message="Insurance: regex/rules only | Mortgage: regex/rules (--no-llm not required)",
            category="llm",
            details={
                "mode": mode,
                "insurance_agents": "deterministic _analyze()",
                "mortgage_extraction": "regex only",
                "mortgage_agents": "rules only (LLM calls skipped)",
            },
        )

    def _check_redis(self) -> ComponentCheck:
        import os

        from insureflow.config import settings

        url = settings.redis_url or os.getenv("CELERY_BROKER_URL", "")
        if not url or not url.startswith("redis"):
            return ComponentCheck(
                component="redis",
                status=CheckStatus.DEGRADED,
                message="Redis not configured — using in-memory job store (jobs lost on restart)",
                category="storage",
                details={"fix": "Set REDIS_URL in .env and JOB_STORE_BACKEND=redis"},
            )
        try:
            import redis

            client = redis.from_url(url)
            client.ping()
            return ComponentCheck(
                component="redis",
                status=CheckStatus.OK,
                message="Redis reachable — persistent job store available",
                category="storage",
                details={"url": url.split("@")[-1] if "@" in url else url},
            )
        except Exception as exc:
            return ComponentCheck(
                component="redis",
                status=CheckStatus.ERROR,
                message=f"Redis configured but unreachable: {exc}",
                category="storage",
                details={"url": url.split("@")[-1] if "@" in url else url},
            )

    def _check_job_store(self) -> ComponentCheck:
        import os

        from insureflow.storage.job_store import get_job_store

        backend = os.getenv("JOB_STORE_BACKEND", "auto")
        store = get_job_store()
        store_type = type(store).__name__
        if store_type == "RedisJobStore":
            return ComponentCheck(
                component="job_store",
                status=CheckStatus.OK,
                message="Using RedisJobStore (persistent, org-scoped)",
                category="storage",
                details={"backend": backend, "implementation": store_type},
            )
        return ComponentCheck(
            component="job_store",
            status=CheckStatus.DEGRADED,
            message="Using MemoryJobStore (in-process, not persistent)",
            category="storage",
            details={"backend": backend, "implementation": store_type},
        )

    def _check_encryption(self) -> ComponentCheck:
        from insureflow.storage.encryption import EnvelopeEncryption

        enc = EnvelopeEncryption()
        if enc.enabled:
            return ComponentCheck(
                component="encryption_at_rest",
                status=CheckStatus.OK,
                message="Audit bundles encrypted at rest (Fernet)",
                category="security",
                details={"enabled": True},
            )
        return ComponentCheck(
            component="encryption_at_rest",
            status=CheckStatus.DEGRADED,
            message="ENCRYPTION_KEY not set — audit bundles stored as plaintext JSON",
            category="security",
            details={
                "enabled": False,
                "fix": 'python -c "from insureflow.storage.encryption import EnvelopeEncryption; print(EnvelopeEncryption.generate_key())"',
            },
        )

    def _check_ocr(self) -> ComponentCheck:
        details: dict[str, Any] = {}
        pdfminer_ok = False
        tesseract_py_ok = False
        pdf2image_ok = False
        tesseract_bin = False

        try:
            import pdfminer  # noqa: F401

            pdfminer_ok = True
        except ImportError:
            pass

        try:
            import pytesseract  # noqa: F401
            from PIL import Image  # noqa: F401

            tesseract_py_ok = True
        except ImportError:
            pass

        try:
            import pdf2image  # noqa: F401

            pdf2image_ok = True
        except ImportError:
            pass

        import shutil

        tesseract_bin = shutil.which("tesseract") is not None
        details = {
            "pdfminer": pdfminer_ok,
            "pytesseract": tesseract_py_ok,
            "pdf2image": pdf2image_ok,
            "tesseract_binary": tesseract_bin,
        }

        if pdfminer_ok and tesseract_py_ok and pdf2image_ok and tesseract_bin:
            return ComponentCheck(
                component="ocr",
                status=CheckStatus.OK,
                message="Full OCR stack ready (text PDFs + scanned PDFs + images)",
                category="ingestion",
                details=details,
            )
        if pdfminer_ok:
            return ComponentCheck(
                component="ocr",
                status=CheckStatus.DEGRADED,
                message="Text PDF OCR only — install pip install insureflow-ai[ocr] + system Tesseract for scans",
                category="ingestion",
                details={
                    **details,
                    "fix": 'pip install -e ".[ocr]" && brew install tesseract (macOS)',
                },
            )
        return ComponentCheck(
            component="ocr",
            status=CheckStatus.MISSING,
            message="OCR dependencies missing",
            category="ingestion",
            details=details,
        )

    def _check_audit_storage(self) -> ComponentCheck:
        from insureflow.config import settings

        path = settings.audit_log_path
        try:
            path.mkdir(parents=True, exist_ok=True)
            test = path / ".write_test"
            test.write_text("ok")
            test.unlink()
            return ComponentCheck(
                component="audit_storage",
                status=CheckStatus.OK,
                message=f"Audit path writable: {path}",
                category="storage",
                details={"path": str(path)},
            )
        except OSError as exc:
            return ComponentCheck(
                component="audit_storage",
                status=CheckStatus.ERROR,
                message=f"Cannot write to audit path: {exc}",
                category="storage",
                details={"path": str(path)},
            )

    def _check_example_data(self) -> ComponentCheck:
        examples = self.project_root / "examples"
        required = [
            "pacific_coast_acord.xml",
            "pacific_coast_inspection_report.md",
        ]
        missing = [f for f in required if not (examples / f).exists()]
        if not missing:
            return ComponentCheck(
                component="insurance_examples",
                status=CheckStatus.OK,
                message=f"Insurance example data present ({len(list(examples.glob('*')))} files)",
                category="data",
                details={"path": str(examples)},
            )
        return ComponentCheck(
            component="insurance_examples",
            status=CheckStatus.MISSING,
            message=f"Missing example files: {', '.join(missing)}",
            category="data",
            details={"path": str(examples)},
        )

    def _check_mortgage_fixtures(self) -> ComponentCheck:
        home = self.project_root / "simulated_documents" / "home_mortgage"
        if home.exists() and any(home.rglob("*.txt")):
            count = len(list(home.rglob("*.txt")))
            return ComponentCheck(
                component="mortgage_fixtures",
                status=CheckStatus.OK,
                message=f"Mortgage simulated documents present ({count} files)",
                category="data",
                details={"path": str(home)},
            )
        return ComponentCheck(
            component="mortgage_fixtures",
            status=CheckStatus.MISSING,
            message="simulated_documents/home_mortgage not found",
            category="data",
            details={"path": str(home)},
        )

    def _check_postgres(self) -> ComponentCheck:
        import os

        url = os.getenv("DATABASE_URL", "")
        if not url:
            return ComponentCheck(
                component="postgres_pgvector",
                status=CheckStatus.DEGRADED,
                message="DATABASE_URL not set — using in-memory RAG (no pgvector)",
                category="rag",
                details={"fix": "Set DATABASE_URL for production RAG"},
            )
        try:
            import psycopg2

            conn = psycopg2.connect(url)
            conn.close()
            return ComponentCheck(
                component="postgres_pgvector",
                status=CheckStatus.OK,
                message="PostgreSQL reachable — pgvector RAG available",
                category="rag",
                details={"host": url.split("@")[-1] if "@" in url else "configured"},
            )
        except ImportError:
            return ComponentCheck(
                component="postgres_pgvector",
                status=CheckStatus.DEGRADED,
                message="DATABASE_URL set but psycopg2 not installed",
                category="rag",
                details={"fix": 'pip install -e ".[pgvector]"'},
            )
        except Exception as exc:
            return ComponentCheck(
                component="postgres_pgvector",
                status=CheckStatus.ERROR,
                message=f"PostgreSQL unreachable: {exc}",
                category="rag",
                details={},
            )
