"""Rytera MCP Server — exposes core Rytera capabilities as MCP tools.

Usage:
    # stdio (for Claude Desktop / local clients)
    python -m insureflow.mcp.server

    # SSE (for remote access, mounted on FastAPI at /mcp/)
    from insureflow.mcp import create_mcp_server
    mcp = create_mcp_server()
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None  # type: ignore[assignment,misc]

logger = logging.getLogger("insureflow.mcp")

_INSURANCE_NS = "insurance"
_EXAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "examples" / "insurance"


def _get_job_store():
    from insureflow.storage.job_store import get_job_store

    return get_job_store()


def _get_audit_store():
    from insureflow.audit.store import AuditStore

    return AuditStore()


def _parse_claims(raw: Any) -> list[dict[str, Any]]:
    """Parse claims JSON string into a list of claim dicts. Returns [] on failure."""
    if not raw:
        return []
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return []
    if isinstance(parsed, list):
        return [c for c in parsed if isinstance(c, dict)]
    return []


def _register_all(server: Any) -> None:
    """Register all Rytera MCP tools on a FastMCP server instance."""
    if FastMCP is None or not hasattr(server, "tool"):
        return

    @server.tool()
    def list_jobs(org_id: str = "default", limit: int = 50) -> str:
        """List recent insurance pipeline jobs."""
        js = _get_job_store()
        ids = js.list_ids(_INSURANCE_NS, org_id=org_id)
        jobs: list[dict[str, Any]] = []
        for jid in ids[-limit:]:
            job = js.get(_INSURANCE_NS, jid, org_id=org_id)
            if job:
                jobs.append(_json_safe({"id": jid, "status": job.get("status")}))
        return json.dumps({"count": len(jobs), "jobs": jobs}, indent=2)

    @server.tool()
    def get_job(job_id: str, org_id: str = "default") -> str:
        """Get full details of a specific pipeline job."""
        js = _get_job_store()
        job = js.get(_INSURANCE_NS, job_id, org_id=org_id)
        if not job:
            return json.dumps({"error": f"Job {job_id} not found"})
        return json.dumps(_json_safe(job), indent=2)

    @server.tool()
    def calculate_mortgage_metrics(loan_amount: float, interest_rate: float, term_years: int) -> str:
        """Calculate basic mortgage metrics."""
        if term_years <= 0 or loan_amount <= 0 or interest_rate < 0:
            return json.dumps({"error": "Invalid inputs"})
        monthly_rate = interest_rate / 100.0 / 12.0
        n_payments = term_years * 12
        if monthly_rate == 0:
            monthly_payment = loan_amount / n_payments
        else:
            monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** n_payments) / ((1 + monthly_rate) ** n_payments - 1)
        return json.dumps({"monthly_payment": round(monthly_payment, 2)})

    @server.tool()
    def get_health() -> str:
        """Check system health."""
        return json.dumps({"status": "ok", "version": "0.3.1"})


def _json_safe(obj: Any) -> Any:
    """Best-effort conversion for MCP tool return values."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(i) for i in obj]
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    return str(obj)


def create_mcp_server(name: str = "rytera") -> FastMCP:
    mcp = FastMCP(name)

    # ── Jobs ──────────────────────────────────────────────────────

    @mcp.tool()
    def list_jobs(org_id: str = "default", limit: int = 50) -> str:
        """List recent insurance pipeline jobs. Returns job IDs with status and timestamps."""
        js = _get_job_store()
        ids = js.list_ids(_INSURANCE_NS, org_id=org_id)
        jobs: list[dict[str, Any]] = []
        for jid in ids[-limit:]:
            job = js.get(_INSURANCE_NS, jid, org_id=org_id)
            if job:
                jobs.append(
                    _json_safe(
                        {
                            "id": jid,
                            "status": job.get("status"),
                            "org_id": job.get("org_id"),
                            "updated_at": job.get("updated_at"),
                            "created_at": job.get("created_at"),
                            "preset_id": job.get("preset_id"),
                        }
                    )
                )
        return json.dumps({"count": len(jobs), "jobs": jobs}, indent=2)

    @mcp.tool()
    def get_job(job_id: str, org_id: str = "default") -> str:
        """Get full details of a specific pipeline job including results and memo summary."""
        js = _get_job_store()
        job = js.get(_INSURANCE_NS, job_id, org_id=org_id)
        if not job:
            from insureflow.privacy.archive import hydrate_job_from_archive

            job = hydrate_job_from_archive(job_id, org_id=org_id)
        if not job:
            return json.dumps({"error": f"Job {job_id} not found"})

        safe = _json_safe(job)
        memo = safe.get("results", {}).get("memo")
        if memo:
            safe["results"]["memo_summary"] = {k: memo.get(k) for k in ("decision", "confidence", "risk_score", "headline", "summary") if memo.get(k) is not None}
        return json.dumps(safe, indent=2)

    @mcp.tool()
    def get_job_memo(job_id: str, org_id: str = "default") -> str:
        """Retrieve the full underwriting memo for a completed job."""
        store = _get_audit_store()
        memo = store.load_json(job_id, "underwriting_memo.json", org_id=org_id)
        if not memo:
            js = _get_job_store()
            job = js.get(_INSURANCE_NS, job_id, org_id=org_id)
            memo = (job or {}).get("results", {}).get("memo")
        if not memo:
            return json.dumps({"error": f"No memo found for job {job_id}"})
        return json.dumps(_json_safe(memo), indent=2)

    # ── Companies ─────────────────────────────────────────────────

    @mcp.tool()
    def list_companies(org_id: str = "default") -> str:
        """List the writing panel companies available for this organization."""
        from insureflow.insurance.companies import list_companies as _list

        return json.dumps(_json_safe(_list(org_id=org_id)), indent=2)

    @mcp.tool()
    def add_company(name: str, org_id: str = "default", naic: str = "", notes: str = "") -> str:
        """Add a new company to the organization's writing panel. Validates name format."""
        from insureflow.insurance.companies import add_company as _add

        try:
            result = _add(org_id, name=name, naic=naic, notes=notes)
            return json.dumps(_json_safe(result))
        except ValueError as exc:
            return json.dumps({"error": str(exc)})

    @mcp.tool()
    def delete_company(company_id: str, org_id: str = "default") -> str:
        """Remove an org-added company from the writing panel. Demo companies cannot be deleted."""
        from insureflow.insurance.companies import delete_company as _del

        try:
            result = _del(org_id, company_id)
            return json.dumps(_json_safe(result))
        except ValueError as exc:
            return json.dumps({"error": str(exc)})

    # ── Life LOB Taxonomy ────────────────────────────────────────

    @mcp.tool()
    def list_life_lines(category_id: str = "", status: str = "") -> str:
        """List life insurance product lines. Filter by category (term, whole, universal, etc.) or status (live, catalog)."""
        from insureflow.insurance.life_lobs import list_life_lines as _list

        kwargs: dict[str, Any] = {}
        if category_id:
            kwargs["category_id"] = category_id
        if status:
            kwargs["status"] = status
        lines = _list(**kwargs)
        summaries = [
            _json_safe(
                {
                    "id": ln["id"],
                    "slug": ln["slug"],
                    "name": ln["name"],
                    "category_id": ln["category_id"],
                    "status": ln["status"],
                    "coverage_count": ln.get("coverage_count", 0),
                }
            )
            for ln in lines
        ]
        return json.dumps({"count": len(summaries), "lines": summaries}, indent=2)

    @mcp.tool()
    def get_life_line(line_id_or_slug: str) -> str:
        """Get full details of a life product line including coverages and checklist requirements."""
        from insureflow.insurance.life_lobs import get_life_line as _get

        result = _get(line_id_or_slug)
        if not result:
            return json.dumps({"error": f"Life line '{line_id_or_slug}' not found"})
        return json.dumps(_json_safe(result), indent=2)

    @mcp.tool()
    def detect_life_product(text_blob: str) -> str:
        """Detect which life insurance product a submission text maps to."""
        from insureflow.insurance.life_lobs import detect_life_product as _detect

        result = _detect(text_blob)
        return json.dumps({"detected_product": result})

    @mcp.tool()
    def list_life_categories() -> str:
        """List life insurance categories with product counts."""
        from insureflow.insurance.life_lobs import list_life_categories as _list

        return json.dumps(_json_safe(_list()), indent=2)

    # ── Sources ───────────────────────────────────────────────────

    @mcp.tool()
    def list_sources() -> str:
        """List available insurance data sources (demo packages, live connectors)."""
        from insureflow.ingestion.insurance.sources import list_sources as _list

        sources = _list(_EXAMPLES_DIR)
        summaries = [
            _json_safe(
                {
                    "id": s["id"],
                    "name": s["name"],
                    "type": s.get("type"),
                    "category": s.get("category"),
                    "status": s.get("status"),
                    "kind": s.get("kind"),
                }
            )
            for s in sources
        ]
        return json.dumps({"count": len(summaries), "sources": summaries}, indent=2)

    # ── Health ────────────────────────────────────────────────────

    @mcp.tool()
    def get_health() -> str:
        """Check system health: job store connectivity and version."""
        checks: dict[str, Any] = {"version": "0.3.1"}
        try:
            js = _get_job_store()
            redis_client = getattr(js, "client", None)
            if redis_client and hasattr(redis_client, "ping"):
                redis_client.ping()
                checks["job_store"] = "ok"
            else:
                checks["job_store"] = "ok (memory/file)"
        except Exception as exc:
            checks["job_store"] = f"error: {exc}"
            checks["status"] = "degraded"
        if "status" not in checks:
            checks["status"] = "ok"
        return json.dumps(checks, indent=2)

    # ── Mortgage (placeholder — full calculator lives in mortgage vertical) ──

    @mcp.tool()
    def calculate_mortgage_metrics(
        loan_amount: float,
        interest_rate: float,
        term_years: int,
    ) -> str:
        """Calculate basic mortgage metrics: monthly payment, total cost, total interest."""
        if term_years <= 0 or loan_amount <= 0 or interest_rate < 0:
            return json.dumps({"error": "Invalid inputs: loan_amount and term_years must be positive; interest_rate must be non-negative."})
        monthly_rate = interest_rate / 100.0 / 12.0
        n_payments = term_years * 12
        if monthly_rate == 0:
            monthly_payment = loan_amount / n_payments
        else:
            monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** n_payments) / ((1 + monthly_rate) ** n_payments - 1)
        total_cost = monthly_payment * n_payments
        total_interest = total_cost - loan_amount
        return json.dumps(
            {
                "loan_amount": loan_amount,
                "interest_rate_pct": interest_rate,
                "term_years": term_years,
                "monthly_payment": round(monthly_payment, 2),
                "total_cost": round(total_cost, 2),
                "total_interest": round(total_interest, 2),
            },
            indent=2,
        )

    return mcp


# ── stdio entrypoint ──────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    server = create_mcp_server()
    server.run(transport="stdio")
