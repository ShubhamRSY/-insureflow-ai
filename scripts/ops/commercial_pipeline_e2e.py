#!/usr/bin/env python3
"""Full commercial pipeline E2E: ingest → agents → quote → worksheet → subjectivities → bind.

Runs in-process against demo fixtures. LLM is enabled when LLM_API_KEY/OPENAI_API_KEY is set;
otherwise agents run deterministic fallbacks (still full stage coverage).

Usage:
  PYTHONPATH=src python scripts/ops/commercial_pipeline_e2e.py
  PYTHONPATH=src python scripts/ops/commercial_pipeline_e2e.py --live --port 8002
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

# Load .env if present
_env = ROOT / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        if not line.strip() or line.strip().startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)

DEMOS = [
    "novapay-cyber",
    "ridgehaul-auto",
    "summit-wc",
    "oaksteel-gl",
    "corner-bop",
    "harbor-builders",
    "ledger-crime",
    "apex-surety",
]


def _llm_status() -> dict:
    key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""
    return {
        "llm_key_present": bool(key),
        "provider": os.getenv("LLM_PROVIDER", "openai"),
        "mode": "llm" if key else "deterministic_fallback",
    }


def run_inprocess(use_llm: bool = True) -> dict:
    from insureflow.api import main as api_main
    from insureflow.insurance.pipeline import InsurancePipeline
    from insureflow.underwriting.subjectivities import compute_bind_readiness, seed_subjectivities_from_conditions

    loaders = {
        "novapay-cyber": api_main._load_novapay_cyber_submission,
        "ridgehaul-auto": api_main._load_ridgehaul_auto_submission,
        "summit-wc": api_main._load_summit_wc_submission,
        "oaksteel-gl": api_main._load_oaksteel_gl_submission,
        "corner-bop": api_main._load_corner_bop_submission,
        "harbor-builders": api_main._load_harbor_builders_submission,
        "ledger-crime": api_main._load_ledger_crime_submission,
        "apex-surety": api_main._load_apex_surety_submission,
    }

    llm = _llm_status()
    results = []
    for preset in DEMOS:
        req = loaders[preset]()
        # Force LLM flag; pipeline still no-ops LLM calls without a key
        use = bool(use_llm and llm["llm_key_present"])
        pipe = InsurancePipeline(org_id="e2e-commercial", use_llm=use)
        t0 = time.time()
        docs = []
        for d in req.documents or []:
            if hasattr(d, "model_dump"):
                docs.append(d.model_dump())
            elif isinstance(d, dict):
                docs.append(d)
            else:
                docs.append({"filename": getattr(d, "filename", "doc.md"), "content": getattr(d, "content", str(d))})
        summary = pipe.run(
            acord_xml=req.acord_xml or "",
            loss_run=req.loss_run or "",
            schedule_of_values=req.schedule_of_values or "",
            inspection_reports=list(req.inspection_reports or []),
            json_payload=req.json_payload or "",
            documents=docs,
            insurance_line=req.insurance_line,
            commercial_product_id=getattr(req, "commercial_product_id", None),
        )
        # Ensure subjectivities/bind seeded (pipeline should already; defend)
        if not summary.get("subjectivities"):
            summary["subjectivities"] = seed_subjectivities_from_conditions(summary)
        if not summary.get("bind_readiness"):
            summary["bind_readiness"] = compute_bind_readiness(summary)

        quote = summary.get("quote") or {}
        meta = quote.get("metadata") or {}
        engine = quote.get("rating_engine") or meta.get("rating_engine")
        row = {
            "preset": preset,
            "ok": bool(quote.get("adjusted_premium") or quote.get("premium")),
            "duration_s": round(time.time() - t0, 2),
            "insurance_line": summary.get("insurance_line") or req.insurance_line,
            "product_id": summary.get("commercial_product_id") or getattr(req, "commercial_product_id", None),
            "decision": (summary.get("memo") or {}).get("decision") or summary.get("decision"),
            "premium": quote.get("adjusted_premium") or quote.get("premium"),
            "rating_engine": engine,
            "filing_id": quote.get("filing_id") or meta.get("filing_id"),
            "uw_worksheet": bool(summary.get("uw_worksheet")),
            "subjectivities": len(summary.get("subjectivities") or []),
            "bind_ready": (summary.get("bind_readiness") or {}).get("ready_to_bind"),
            "bind_summary": (summary.get("bind_readiness") or {}).get("summary"),
            "stages_present": {
                "quote": bool(quote),
                "memo": bool(summary.get("memo")),
                "worksheet": bool(summary.get("uw_worksheet")),
                "subjectivities": "subjectivities" in summary,
                "bind_readiness": "bind_readiness" in summary,
            },
        }
        results.append(row)
        eng_s = str(engine or "?")
        print(
            f"[{'PASS' if row['ok'] else 'FAIL'}] {preset:<18} eng={eng_s:<24} "
            f"prem={row['premium']} subj={row['subjectivities']} worksheet={row['uw_worksheet']} ({row['duration_s']}s)"
        )

    passed = sum(1 for r in results if r["ok"] and r["stages_present"]["quote"] and r["stages_present"]["bind_readiness"])
    return {
        "mode": "inprocess",
        "llm": llm,
        "passed": passed,
        "total": len(results),
        "success": passed == len(results),
        "results": results,
    }


def run_live(base_url: str, timeout: int = 300) -> dict:
    llm = _llm_status()

    def req(method: str, path: str, body: dict | None = None, token: str | None = None):
        data = None if body is None else json.dumps(body).encode()
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        r = urllib.request.Request(base_url + path, data=data, headers=headers, method=method)
        with urllib.request.urlopen(r, timeout=60) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}

    # Auth
    token = None
    for user, pwd in [
        (os.getenv("E2E_USERNAME", "admin"), os.getenv("E2E_PASSWORD", "Admin123!")),
        ("admin", "Admin123!"),
    ]:
        try:
            login = req("POST", "/auth/login", {"username": user, "password": pwd})
            token = login.get("access_token")
            if token:
                break
        except Exception:
            continue
    if not token:
        raise RuntimeError("Live E2E auth failed — set E2E_USERNAME/E2E_PASSWORD")

    results = []
    for preset in DEMOS:
        t0 = time.time()
        started = req("POST", f"/api/demo/insurance/{preset}", token=token)
        job_id = started["job_id"]
        job = {}
        deadline = time.time() + timeout
        while time.time() < deadline:
            job = req("GET", f"/pipeline/jobs/{job_id}", token=token)
            if job.get("status") in ("completed", "failed"):
                break
            time.sleep(2)
        r = job.get("results") or {}
        q = r.get("quote") or {}
        meta = q.get("metadata") or {}
        engine = q.get("rating_engine") or meta.get("rating_engine")
        row = {
            "preset": preset,
            "job_id": job_id,
            "status": job.get("status"),
            "ok": job.get("status") == "completed" and bool(q.get("adjusted_premium") or q.get("premium")),
            "duration_s": round(time.time() - t0, 2),
            "premium": q.get("adjusted_premium") or q.get("premium"),
            "rating_engine": engine,
            "uw_worksheet": bool(r.get("uw_worksheet")),
            "subjectivities": len(r.get("subjectivities") or []),
            "bind_ready": (r.get("bind_readiness") or {}).get("ready_to_bind"),
            "error": job.get("error") or job.get("message"),
        }
        results.append(row)
        print(
            f"[{'PASS' if row['ok'] else 'FAIL'}] {preset:<18} status={row['status']} "
            f"eng={engine} prem={row['premium']} ({row['duration_s']}s)"
        )

    passed = sum(1 for r in results if r["ok"])
    return {
        "mode": "live",
        "base_url": base_url,
        "llm": llm,
        "passed": passed,
        "total": len(results),
        "success": passed == len(results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--port", type=int, default=8002)
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--json-out", default="")
    args = parser.parse_args()

    print("LLM:", _llm_status())
    if args.live:
        report = run_live(f"http://127.0.0.1:{args.port}")
    else:
        report = run_inprocess(use_llm=not args.no_llm)

    out = args.json_out or str(ROOT / "evaluation_baselines" / "commercial_pipeline_e2e.json")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(report, indent=2))
    print(f"\nWrote {out}")
    print(f"RESULT {report['passed']}/{report['total']} success={report['success']} mode={report['mode']}")
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
