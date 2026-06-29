"""End-to-end integration tests for all InsureFlow services."""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass
class E2EResult:
    name: str
    passed: bool
    detail: str = ""
    duration_ms: float = 0.0


@dataclass
class E2ERunner:
    base_url: str = "http://127.0.0.1:8002"
    use_llm: bool = False
    job_timeout: int = 180
    test_connectors: bool = True
    test_browser: bool = True
    test_celery: bool = True
    browser_headless: bool = True
    username: str = "e2e-admin"
    password: str = "E2eTestPass123!"
    org_id: str = "e2e-org"
    _token: str = field(default="", init=False)
    _insurance_decision: str = field(default="", init=False)
    _insurance_bundle_id: str = field(default="", init=False)
    _insurance_job_id: str = field(default="", init=False)
    _mortgage_bundle_id: str = field(default="", init=False)
    _mortgage_job_id: str = field(default="", init=False)
    _celery_job_id: str = field(default="", init=False)
    _bound_policy_number: str = field(default="", init=False)
    results: list[E2EResult] = field(default_factory=list)
    _client: Any = field(default=None, init=False)

    def run_all(self) -> dict[str, Any]:
        self.results = []
        suites: list[tuple[str, Callable[[], None]]] = [
            ("Platform", self._test_platform),
            ("Auth", self._test_auth),
            ("Diagnostics deep", self._test_diagnostics_deep),
            ("Insurance connectors", self._test_insurance_connectors),
            ("Insurance pipeline", self._test_insurance_pipeline),
            ("Insurance audit & workflow", self._test_insurance_workflow),
            ("Insurance production (sign-off/bind/loss)", self._test_insurance_production),
            ("Mortgage products", self._test_mortgage_products),
            ("Mortgage pipeline", self._test_mortgage_pipeline),
            ("Mortgage audit", self._test_mortgage_audit),
            ("Mortgage Celery worker", self._test_mortgage_celery),
            ("Job store APIs", self._test_job_stores),
            ("Dashboard overview", self._test_dashboard_overview),
            ("Mortgage webhooks", self._test_mortgage_webhooks),
            ("Direct pipeline (sync)", self._test_direct_pipelines),
            ("Browser UI", self._test_browser_ui),
        ]
        for suite_name, fn in suites:
            try:
                fn()
            except Exception as exc:
                self._record(f"{suite_name} (suite error)", False, str(exc))

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        return {
            "passed": passed,
            "failed": failed,
            "total": len(self.results),
            "success": failed == 0,
            "results": [
                {"name": r.name, "passed": r.passed, "detail": r.detail, "duration_ms": round(r.duration_ms, 1)}
                for r in self.results
            ],
        }

    # ── HTTP helpers ─────────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
        auth: bool = False,
        expected: int | tuple[int, ...] = 200,
    ) -> Any:
        if self._client is not None:
            return self._request_testclient(method, path, json_body=json_body, auth=auth, expected=expected)

        url = f"{self.base_url.rstrip('/')}{path}"
        headers = {"Accept": "application/json"}
        data = None
        if json_body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(json_body).encode()
        if auth:
            if not self._token:
                raise RuntimeError("Not authenticated")
            headers["Authorization"] = f"Bearer {self._token}"

        req = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=120) as resp:
                status = resp.status
                raw = resp.read().decode()
        except HTTPError as exc:
            status = exc.code
            raw = exc.read().decode() if exc.fp else ""
            if isinstance(expected, int):
                expected = (expected,)
            if status not in expected:
                raise RuntimeError(f"{method} {path} → {status}: {raw[:300]}") from exc
            return json.loads(raw) if raw else None

        if isinstance(expected, int):
            expected = (expected,)
        if status not in expected:
            raise RuntimeError(f"{method} {path} → {status}: {raw[:300]}")
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    def _request_testclient(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
        auth: bool = False,
        expected: int | tuple[int, ...] = 200,
    ) -> Any:
        headers = {}
        if auth:
            headers["Authorization"] = f"Bearer {self._token}"
        if method == "GET":
            resp = self._client.get(path, headers=headers)
        elif method == "POST":
            resp = self._client.post(path, json=json_body or {}, headers=headers)
        elif method == "DELETE":
            resp = self._client.delete(path, headers=headers)
        else:
            raise ValueError(method)

        if isinstance(expected, int):
            expected = (expected,)
        if resp.status_code not in expected:
            raise RuntimeError(f"{method} {path} → {resp.status_code}: {resp.text[:300]}")
        if resp.status_code == 204:
            return None
        try:
            return resp.json()
        except Exception:
            return resp.text

    def _record(self, name: str, passed: bool, detail: str = "") -> None:
        self.results.append(E2EResult(name=name, passed=passed, detail=detail))

    def _step(self, name: str, fn: Callable[[], str | None]) -> None:
        t0 = time.perf_counter()
        try:
            detail = fn() or "ok"
            self.results.append(
                E2EResult(name=name, passed=True, detail=detail, duration_ms=(time.perf_counter() - t0) * 1000)
            )
        except Exception as exc:
            self.results.append(
                E2EResult(name=name, passed=False, detail=str(exc), duration_ms=(time.perf_counter() - t0) * 1000)
            )

    def _wait_job(self, path: str, job_id: str) -> dict[str, Any]:
        deadline = time.time() + self.job_timeout
        last: dict[str, Any] = {}
        while time.time() < deadline:
            last = self._request("GET", f"{path}/{job_id}", auth=True)
            status = last.get("status")
            if status in ("completed", "failed"):
                return last
            time.sleep(2)
        raise TimeoutError(f"Job {job_id} not finished after {self.job_timeout}s (last={last.get('status')})")

    def _auth_headers_setup(self) -> None:
        """Ensure token is set (setup new org user or login with existing credentials)."""
        status = self._request("GET", "/auth/status")
        setup_required = status.get("setup_required", False)

        def _try_login(user: str, pwd: str) -> bool:
            try:
                login = self._request(
                    "POST",
                    "/auth/login",
                    json_body={"username": user, "password": pwd},
                )
                self._token = login["access_token"]
                self.username = user
                return True
            except RuntimeError:
                return False

        if _try_login(self.username, self.password):
            return

        if setup_required:
            self._request(
                "POST",
                "/auth/setup",
                json_body={
                    "username": self.username,
                    "password": self.password,
                    "full_name": "E2E Admin",
                    "org_id": self.org_id,
                    "role": "admin",
                },
                expected=201,
            )
            if _try_login(self.username, self.password):
                return

        fallback_user = os.getenv("E2E_USERNAME", "admin")
        fallback_pass = os.getenv("E2E_PASSWORD", "Admin123!")
        if _try_login(fallback_user, fallback_pass):
            return

        raise RuntimeError(
            "Could not authenticate. Set E2E_USERNAME/E2E_PASSWORD or run auth-reset + setup."
        )

    # ── Test suites ──────────────────────────────────────────────

    def _test_platform(self) -> None:
        def health() -> str:
            data = self._request("GET", "/health")
            assert data.get("status") == "ok"
            return f"version={data.get('version')}"

        def root() -> str:
            data = self._request("GET", "/")
            assert "/dashboard" in data.get("dashboard", "")
            return "dashboard link ok"

        def dashboard_html() -> str:
            html = self._request("GET", "/dashboard")
            assert isinstance(html, str) and "InsureFlow" in html
            return "SPA shell served"

        def dashboard_spa_route() -> str:
            html = self._request("GET", "/dashboard/insurance")
            assert isinstance(html, str) and "InsureFlow" in html
            return "client route ok"

        self._step("GET /health", health)
        self._step("GET / (API root)", root)
        self._step("GET /dashboard", dashboard_html)
        self._step("GET /dashboard/insurance (SPA)", dashboard_spa_route)

    def _test_auth(self) -> None:
        def setup_login() -> str:
            if self._token:
                return f"token preset user={self.username}"
            self._auth_headers_setup()
            return f"user={self.username} org={self.org_id}"

        def me() -> str:
            me_data = self._request("GET", "/auth/me", auth=True)
            assert me_data["username"] == self.username
            self.org_id = me_data["org_id"]
            return f"role={me_data['role']} org={self.org_id}"

        self._step("Auth setup + login", setup_login)
        self._step("GET /auth/me", me)

    def _test_diagnostics_deep(self) -> None:
        def diag() -> str:
            data = self._request("GET", "/system/diagnostics")
            summary = data.get("summary", {})
            checks = {c["component"]: c["status"] for c in data.get("checks", [])}
            required = ["llm_api_key", "redis", "job_store", "ocr", "insurance_examples", "postgres_pgvector"]
            missing = [k for k in required if k not in checks]
            if missing:
                raise AssertionError(f"Missing checks: {missing}")
            return f"overall={data['overall']} ok={summary.get('ok')}/{summary.get('total')}"

        def doctor_inprocess() -> str:
            from insureflow.health.diagnostics import SystemDiagnostics

            report = SystemDiagnostics(project_root=PROJECT_ROOT).run_all()
            assert report["summary"]["total"] >= 10
            return f"doctor={report['overall']}"

        self._step("GET /system/diagnostics", diag)
        self._step("SystemDiagnostics.run_all()", doctor_inprocess)

    def _test_insurance_connectors(self) -> None:
        if not self.test_connectors:
            self._record("Insurance connectors (skipped)", True, "test_connectors=False")
            return

        sources = self._request("GET", "/api/insurance/sources")
        ids = [s["id"] for s in sources.get("sources", [])]
        assert len(ids) >= 20, f"Expected 20+ connectors, got {len(ids)}"

        ok_count = 0
        for sid in ids:
            try:
                pull = self._request(
                    "POST",
                    f"/api/insurance/sources/{sid}/pull",
                    json_body={},
                    auth=True,
                    expected=200,
                )
                assert pull.get("file_count", 0) > 0, f"{sid}: no documents"
                ok_count += 1
            except Exception as exc:
                self._record(f"Connector pull: {sid}", False, str(exc))

        self._record("Insurance connector catalog", True, f"{len(ids)} sources listed")
        self._record("Insurance connector pulls", ok_count == len(ids), f"{ok_count}/{len(ids)} ok")

    def _test_insurance_pipeline(self) -> None:
        def presets() -> str:
            data = self._request("GET", "/api/demo/presets")
            assert data.get("insurance"), "No insurance presets"
            return f"insurance={len(data['insurance'])} mortgage={len(data.get('mortgage', []))}"

        def demo_run() -> str:
            resp = self._request(
                "POST",
                "/api/demo/insurance/pacific-coast",
                auth=True,
                expected=202,
            )
            job_id = resp["job_id"]
            job = self._wait_job("/pipeline/jobs", job_id)
            if job.get("status") == "failed":
                raise AssertionError(job.get("error", "insurance job failed"))
            results = job.get("results") or {}
            decision = results.get("ai_decision")
            assert decision in ("accept", "refer", "decline"), f"bad decision: {decision}"
            premium = (results.get("quote") or {}).get("adjusted_premium")
            self._insurance_job_id = job_id
            self._insurance_bundle_id = results.get("bundle_id", job_id)
            self._insurance_decision = decision
            return f"decision={decision} premium={premium}"

        self._step("GET /api/demo/presets", presets)
        self._step("Insurance demo pipeline (Pacific Coast)", demo_run)

    def _test_insurance_workflow(self) -> None:
        bundle_id = getattr(self, "_insurance_bundle_id", None)
        if not bundle_id:
            self._record("Insurance workflow (skipped)", True, "no bundle from pipeline")
            return

        def audit() -> str:
            data = self._request("GET", f"/pipeline/audit/{bundle_id}", auth=True)
            assert data.get("bundle_id") == bundle_id
            return "audit trail loaded"

        def workflow() -> str:
            try:
                wf = self._request("GET", f"/pipeline/workflow/{bundle_id}", auth=True)
                return f"state={wf.get('state')}"
            except RuntimeError as exc:
                if "404" in str(exc):
                    return "no workflow record (ok for some decisions)"
                raise

        def rating() -> str:
            products = self._request("GET", "/pipeline/rating/products", auth=True)
            lines = products.get("lines", products.get("products", []))
            assert lines
            return f"{len(lines)} product lines"

        def calibration() -> str:
            cal = self._request("GET", "/pipeline/outcomes/calibration", auth=True)
            return f"sample_size={cal.get('sample_size', 0)}"

        self._step("GET /pipeline/audit/{bundle}", audit)
        self._step("GET /pipeline/workflow/{bundle}", workflow)
        self._step("GET /pipeline/rating/products", rating)
        self._step("GET /pipeline/outcomes/calibration", calibration)

    def _test_insurance_production(self) -> None:
        """Licensed UW sign-off, bind, regulatory package, and loss feedback loop."""
        bundle_id = getattr(self, "_insurance_bundle_id", None)
        if not bundle_id:
            self._record("Insurance production (skipped)", True, "no bundle from pipeline")
            return

        decision = getattr(self, "_insurance_decision", "")
        if decision == "decline":
            self._record("Insurance production (skipped)", True, "decision=decline, no workflow to sign off")
            return

        def pending_queue() -> str:
            data = self._request("GET", "/pipeline/workflow/pending", auth=True)
            pending = data.get("pending", [])
            ids = pending if not pending or isinstance(pending[0], str) else [p.get("bundle_id") for p in pending]
            if bundle_id not in ids and not ids:
                raise AssertionError(f"Expected pending queue entries, bundle={bundle_id}")
            return f"{len(ids)} pending"

        def sign_off() -> str:
            wf = self._request(
                "POST",
                f"/pipeline/workflow/{bundle_id}/sign-off",
                json_body={
                    "action": "approve",
                    "license_number": "UW-CA-E2E-001",
                    "notes": "E2E licensed UW approval",
                },
                auth=True,
            )
            assert wf.get("state") == "approved", f"unexpected state: {wf.get('state')}"
            return f"state={wf['state']} final={wf.get('final_decision')}"

        def bind_policy() -> str:
            resp = self._request(
                "POST",
                f"/pipeline/workflow/{bundle_id}/bind",
                json_body={"policy_number": "", "bound_premium": 0.0},
                auth=True,
            )
            bind = resp.get("bind") or {}
            outcome = resp.get("outcome") or {}
            policy_number = outcome.get("policy_number") or bind.get("policy_number")
            assert policy_number, f"no policy_number in bind response: {resp}"
            assert bind.get("status") == "bound", f"bind status: {bind}"
            self._bound_policy_number = policy_number
            wf = self._request("GET", f"/pipeline/workflow/{bundle_id}", auth=True)
            assert wf.get("state") == "bound", f"workflow state after bind: {wf.get('state')}"
            return f"policy={policy_number} premium={outcome.get('bound_premium')}"

        def audit_package() -> str:
            pkg = self._request("GET", f"/pipeline/audit/{bundle_id}/package", auth=True)
            assert pkg.get("artifact_count", 0) >= 1, "regulatory package empty"
            assert pkg.get("bundle_id") == bundle_id
            return f"artifacts={pkg['artifact_count']} path={Path(pkg.get('package_path', '')).name}"

        def loss_experience() -> str:
            policy = getattr(self, "_bound_policy_number", f"POL-E2E-{bundle_id[:8]}")
            exp = self._request(
                "POST",
                "/pipeline/outcomes/loss-experience",
                json_body={
                    "policy_number": policy,
                    "policy_year": 2025,
                    "earned_premium": 100_000.0,
                    "incurred_losses": 18_000.0,
                    "paid_losses": 14_000.0,
                    "claim_count": 2,
                    "bundle_id": bundle_id,
                },
                auth=True,
                expected=201,
            )
            return f"loss_ratio={exp.get('loss_ratio')}"

        def calibration_updated() -> str:
            cal = self._request("GET", "/pipeline/outcomes/calibration", auth=True)
            assert cal.get("sample_size", 0) >= 1, "expected loss experience in calibration"
            return f"sample_size={cal['sample_size']} avg_lr={cal.get('avg_loss_ratio')}"

        self._step("GET /pipeline/workflow/pending", pending_queue)
        self._step("POST /pipeline/workflow/{bundle}/sign-off", sign_off)
        self._step("POST /pipeline/workflow/{bundle}/bind", bind_policy)
        self._step("GET /pipeline/audit/{bundle}/package", audit_package)
        self._step("POST /pipeline/outcomes/loss-experience", loss_experience)
        self._step("GET /pipeline/outcomes/calibration (after loss)", calibration_updated)

    def _test_mortgage_products(self) -> None:
        def products() -> str:
            data = self._request("GET", "/mortgage/products", auth=True)
            prods = data.get("products", [])
            assert len(prods) >= 5
            return f"{len(prods)} loan products"

        self._step("GET /mortgage/products", products)

    def _test_mortgage_pipeline(self) -> None:
        def demo_run() -> str:
            resp = self._request(
                "POST",
                "/api/demo/mortgage/johnson-residential",
                auth=True,
                expected=202,
            )
            job_id = resp["job_id"]
            job = self._wait_job("/mortgage/pipeline/jobs", job_id)
            if job.get("status") == "failed":
                raise AssertionError(job.get("error", "mortgage job failed"))
            results = job.get("results") or {}
            decision = results.get("decision")
            assert decision in ("approve", "refer", "suspend", "deny"), f"bad decision: {decision}"
            rq = results.get("rate_quote") or {}
            self._mortgage_job_id = job_id
            self._mortgage_bundle_id = results.get("bundle_id", job_id)
            return f"decision={decision} rate={rq.get('adjusted_rate')} dti={results.get('dti_ratio')}"

        self._step("Mortgage demo pipeline (Johnson)", demo_run)

    def _test_mortgage_audit(self) -> None:
        bundle_id = getattr(self, "_mortgage_bundle_id", None)
        if not bundle_id:
            self._record("Mortgage audit (skipped)", True, "no bundle")
            return

        def audit() -> str:
            data = self._request("GET", f"/mortgage/audit/{bundle_id}", auth=True)
            assert data.get("bundle_id") == bundle_id
            return "mortgage audit ok"

        self._step("GET /mortgage/audit/{bundle}", audit)

    def _celery_worker_alive(self) -> bool:
        try:
            from insureflow.tasks.celery_app import celery_app

            ping = celery_app.control.inspect(timeout=3).ping()
            return bool(ping)
        except Exception:
            return False

    def _test_mortgage_celery(self) -> None:
        if not self.test_celery:
            self._record("Mortgage Celery (skipped)", True, "test_celery=False")
            return
        if self._client is not None:
            self._record("Mortgage Celery (skipped)", True, "requires live server + worker")
            return
        if not self._celery_worker_alive():
            self._record(
                "Mortgage Celery worker",
                False,
                "No Celery worker responding — start: python -m celery -A insureflow.tasks.celery_app worker -Q agents,pipeline,mortgage",
            )
            return

        directory = str(PROJECT_ROOT / "simulated_documents/home_mortgage/johnson_marcus_imani")

        def submit_celery_job() -> str:
            resp = self._request(
                "POST",
                "/mortgage/pipeline/run",
                json_body={
                    "directory": directory,
                    "product_line": "residential_mortgage",
                    "use_llm": False,
                    "use_celery": True,
                    "bundle_id": f"celery-e2e-{uuid.uuid4().hex[:8]}",
                },
                auth=True,
                expected=202,
            )
            assert resp.get("use_celery") is True
            self._celery_job_id = resp["job_id"]
            return f"job_id={resp['job_id']} backend=celery"

        def wait_celery_job() -> str:
            job_id = getattr(self, "_celery_job_id", None)
            if not job_id:
                raise RuntimeError("no celery job_id")
            job = self._wait_job("/mortgage/pipeline/jobs", job_id)
            if job.get("status") == "failed":
                raise AssertionError(job.get("error", "celery job failed"))
            assert job.get("backend") == "celery"
            results = job.get("results") or {}
            decision = results.get("decision")
            assert decision in ("approve", "refer", "suspend", "deny"), f"bad decision: {decision}"
            assert job.get("celery_task_id"), "missing celery_task_id"
            return f"decision={decision} dti={results.get('dti_ratio')} task={job['celery_task_id'][:8]}"

        self._step("POST /mortgage/pipeline/run (use_celery=true)", submit_celery_job)
        self._step("Mortgage Celery job completion", wait_celery_job)

    def _test_job_stores(self) -> None:
        def insurance_jobs() -> str:
            data = self._request("GET", "/pipeline/jobs", auth=True)
            jobs = data.get("jobs", [])
            assert isinstance(jobs, list)
            return f"{len(jobs)} insurance job(s)"

        def mortgage_jobs() -> str:
            data = self._request("GET", "/mortgage/pipeline/jobs", auth=True)
            jobs = data.get("jobs", [])
            assert isinstance(jobs, list)
            return f"{len(jobs)} mortgage job(s)"

        self._step("GET /pipeline/jobs", insurance_jobs)
        self._step("GET /mortgage/pipeline/jobs", mortgage_jobs)

    def _test_dashboard_overview(self) -> None:
        def overview() -> str:
            data = self._request("GET", "/api/dashboard/overview", auth=True)
            assert "insurance" in data and "mortgage" in data
            return (
                f"ins={data['insurance'].get('total', 0)} "
                f"mort={data['mortgage'].get('total', 0)} "
                f"pending={len(data.get('pending', []))}"
            )

        self._step("GET /api/dashboard/overview", overview)

    def _test_mortgage_webhooks(self) -> None:
        sub_id = None

        def register() -> str:
            nonlocal sub_id
            data = self._request(
                "POST",
                "/mortgage/webhooks",
                json_body={"url": "https://example.com/e2e-hook", "events": ["mortgage.completed"]},
                auth=True,
                expected=201,
            )
            sub_id = data["subscription_id"]
            return f"sub={sub_id}"

        def list_hooks() -> str:
            data = self._request("GET", "/mortgage/webhooks", auth=True)
            subs = data.get("subscriptions", data.get("webhooks", []))
            if isinstance(data, list):
                subs = data
            return f"{len(subs)} subscription(s)"

        def delete_hook() -> str:
            if not sub_id:
                return "skipped"
            self._request("DELETE", f"/mortgage/webhooks/{sub_id}", auth=True, expected=204)
            return "deleted"

        self._step("POST /mortgage/webhooks", register)
        self._step("GET /mortgage/webhooks", list_hooks)
        self._step("DELETE /mortgage/webhooks/{id}", delete_hook)

    def _test_direct_pipelines(self) -> None:
        """Run pipelines synchronously in-process (no HTTP job queue wait)."""

        def insurance_sync() -> str:
            from insureflow.insurance.pipeline import InsurancePipeline

            examples = PROJECT_ROOT / "examples"
            acord = (examples / "pacific_coast_acord.xml").read_text(encoding="utf-8")
            inspection = (examples / "pacific_coast_inspection_report.md").read_text(encoding="utf-8")
            loss = (examples / "pacific_coast_loss_run.md").read_text(encoding="utf-8")
            result = InsurancePipeline(org_id=self.org_id, use_llm=self.use_llm).run(
                acord_xml=acord,
                inspection_reports=[inspection],
                loss_run=loss,
                bundle_id=f"e2e-ins-{uuid.uuid4().hex[:8]}",
            )
            assert result["status"] == "completed"
            assert result.get("ai_decision") in ("accept", "refer", "decline")
            return f"sync decision={result['ai_decision']}"

        def mortgage_sync() -> str:
            from insureflow.mortgage.pipeline import MortgagePipeline

            directory = PROJECT_ROOT / "simulated_documents/home_mortgage/johnson_marcus_imani"
            if not directory.is_dir():
                raise FileNotFoundError(directory)
            result = MortgagePipeline(use_llm=self.use_llm, org_id=self.org_id).run_from_directory(
                str(directory),
                bundle_id=f"e2e-mort-{uuid.uuid4().hex[:8]}",
            )
            assert result["status"] == "completed"
            assert result.get("decision") in ("approve", "refer", "suspend", "deny")
            return f"sync decision={result['decision']} dti={result.get('dti_ratio')}"

        self._step("InsurancePipeline.run() sync", insurance_sync)
        self._step("MortgagePipeline.run_from_directory() sync", mortgage_sync)

    def _test_browser_ui(self) -> None:
        if not self.test_browser:
            self._record("Browser UI (skipped)", True, "test_browser=False")
            return
        if self._client is not None:
            self._record("Browser UI (skipped)", True, "requires live server")
            return

        from insureflow.e2e.browser import run_browser_tests

        report = run_browser_tests(
            self.base_url,
            username=self.username,
            password=self.password,
            headless=self.browser_headless,
        )
        for row in report["results"]:
            self._record(row["name"], row["passed"], row["detail"])


def run_inprocess(**kwargs: Any) -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from insureflow.api import app
    from insureflow.auth import Role
    from insureflow.auth.jwt import create_access_token
    from insureflow.auth.models import User
    from insureflow.auth.store import clear_user_store, get_user_store

    runner = E2ERunner(**kwargs)
    runner._client = TestClient(app)
    clear_user_store()
    get_user_store()[runner.username] = User(
        username=runner.username,
        hashed_password="unused",
        role=Role.ADMIN,
        full_name="E2E Admin",
        org_id=runner.org_id,
    )
    runner._token = create_access_token(
        {"sub": runner.username, "role": "admin", "org_id": runner.org_id}
    )
    return runner.run_all()


def run_live(base_url: str = "http://127.0.0.1:8002", **kwargs: Any) -> dict[str, Any]:
    runner = E2ERunner(base_url=base_url, **kwargs)
    try:
        urlopen(f"{base_url.rstrip('/')}/health", timeout=5)
    except URLError as exc:
        raise SystemExit(f"Cannot reach API at {base_url}: {exc}") from exc
    return runner.run_all()
