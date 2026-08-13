"""Pull marketplace sources into draft bundles for multi-file UW runs.

Simulated vendor feeds (honest) plus an optional submission package so a
marketplace-only intake can still execute ``POST /pipeline/bundles/{id}/run``.
Subsequent pulls into the same bundle add only the source artifact — they do
not duplicate the submission package.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from insureflow.ingestion.insurance.sources import load_directory, load_package
from insureflow.insurance.relevance import validate_documents_relevance
from insureflow.integrations.connections import get_connection
from insureflow.marketplace.catalog import get_source
from insureflow.marketplace.registry import connect_source
from insureflow.storage.draft_bundle_store import get_draft_bundle_store

_PKG_ROOT = Path(__file__).resolve().parent.parent  # src/insureflow
PROJECT_ROOT = _PKG_ROOT.parent.parent
EXAMPLES_DIR = PROJECT_ROOT / "examples" / "insurance"
SIM_DOCS_DIR = PROJECT_ROOT / "simulated_documents"

_VERTICAL_PACKAGES: dict[str, dict[str, Path]] = {
    "mortgage": {
        "johnson-residential": SIM_DOCS_DIR / "home_mortgage" / "johnson_marcus_imani",
        "midwest-commercial": SIM_DOCS_DIR / "commercial_mortgage" / "midwest_medical_plaza",
    },
    "lending": {
        "keller-logistics": SIM_DOCS_DIR / "lending" / "keller_logistics",
        "blue-harbor-bakery": SIM_DOCS_DIR / "lending" / "blue_harbor_bakery",
    },
}
_DEFAULT_PACKAGE = {
    "insurance": "pacific-coast",
    "mortgage": "johnson-residential",
    "lending": "keller-logistics",
}


def _submission_documents(vertical: str, package_id: str | None) -> tuple[list[dict[str, str]], str]:
    vert = (vertical or "insurance").lower()
    pid = (package_id or _DEFAULT_PACKAGE.get(vert, "pacific-coast")).strip()
    if vert == "insurance":
        return load_package(EXAMPLES_DIR, pid), pid
    paths = _VERTICAL_PACKAGES.get(vert, {})
    directory = paths.get(pid)
    if directory is None:
        raise FileNotFoundError(f"Unknown {vert} package: {pid}")
    return load_directory(directory), pid


def _artifact_document(source_id: str, meta: dict[str, Any], config: dict[str, Any]) -> dict[str, str]:
    kind = str(meta.get("type") or "")
    payload: dict[str, Any] = {
        "source_id": source_id,
        "name": meta.get("name"),
        "type": kind,
        "category": meta.get("category"),
        "pulled_at": datetime.now(tz=timezone.utc).isoformat(),
        "simulated": True,
        "config_keys": sorted(config.keys()),
        "note": (f"Underwriting marketplace pull from {meta.get('name')}. Live vendor API not configured — demo feed attached."),
    }
    if kind == "oracle" or source_id in {"clue", "a-plus", "ncci", "cat-model", "bureau-credit", "osha", "mib-life"}:
        payload["loss_history"] = {
            "description": "CLUE / A-PLUS loss run summary (simulated)",
            "claims_count": 0,
            "open_claims": 0,
            "undisclosed_hint": False,
            "experience_mod": 0.92 if source_id == "ncci" else None,
        }
    if kind == "kyc" or source_id in {"ofac-sdn", "world-check", "lexisnexis-bridger", "dow-jones-watchlist"}:
        payload["sanctions"] = {"cleared": True, "hits": [], "list": "OFAC-SDN", "underwriting_use": "named insured KYC"}
    if kind == "banking" or source_id in {"plaid", "yodlee", "finicity", "ocrolus", "mx-banking"}:
        payload["cashflow"] = {
            "ending_balance": 48_250.0,
            "transaction_count": 12,
            "ach_pulls_30d": 2,
            "loan_application_support": True,
        }
    if kind == "mortgage" or source_id in {"fannie-mae", "freddie-mac", "mers", "black-knight", "credit-plus"}:
        payload["mortgage"] = {"product": "residential mortgage", "borrower_credit_report": "simulated"}
    filename = f"{source_id}_marketplace_pull.json"
    return {
        "filename": filename,
        "path": f"{source_id}/{filename}",
        "directory": source_id,
        "content": json.dumps(payload, indent=2),
        "encoding": "utf-8",
    }


def pull_marketplace_source(
    source_id: str,
    *,
    org_id: str = "default",
    bundle_id: str | None = None,
    vertical: str = "insurance",
    package_id: str | None = None,
    config: dict[str, Any] | None = None,
    label: str = "",
    include_submission: bool | None = None,
) -> dict[str, Any]:
    meta = get_source(source_id)
    if meta is None:
        raise ValueError(f"Unknown marketplace source: {source_id}")

    saved = get_connection(source_id, org_id=org_id) or {}
    saved_cfg = saved.get("config") if isinstance(saved, dict) else {}
    merged_cfg = {**(saved_cfg or {}), **(config or {})}
    display = label or (saved.get("label") if isinstance(saved, dict) else "") or str(meta["name"])
    connect_source(source_id, config=merged_cfg, label=display, org_id=org_id)

    store = get_draft_bundle_store()
    existing_docs = 0
    if bundle_id:
        bundle = store.get(bundle_id, org_id=org_id)
        if not bundle:
            raise FileNotFoundError(f"Draft bundle not found: {bundle_id}")
        existing_docs = len(bundle.get("documents") or [])

    add_package = include_submission if include_submission is not None else existing_docs == 0
    documents: list[dict[str, str]] = []
    used_package = ""
    if add_package:
        documents, used_package = _submission_documents(vertical, package_id)
    documents.append(_artifact_document(source_id, meta, merged_cfg))

    accumulated: dict[str, Any] | None = None
    if bundle_id:
        updated = store.add_documents(
            bundle_id,
            documents,
            source_id=source_id,
            connection_label=display,
            org_id=org_id,
        )
        if not updated:
            raise FileNotFoundError(f"Draft bundle not found: {bundle_id}")
        accumulated = {
            "bundle_id": updated["bundle_id"],
            "document_count": len(updated.get("documents") or []),
            "added": len(documents),
            "sources": sorted({str(d.get("source_id") or "") for d in updated.get("documents") or [] if d.get("source_id")}),
        }

    vert = (vertical or "insurance").lower()
    relevance_docs = documents
    if bundle_id:
        full = store.get(bundle_id, org_id=org_id) or {}
        relevance_docs = [{"filename": d.get("filename", ""), "content": d.get("content", ""), "encoding": d.get("encoding", "utf-8")} for d in (full.get("documents") or [])]
    relevance = validate_documents_relevance(relevance_docs, vertical=vert, strict=False)

    return {
        "source_id": source_id,
        "simulated": True,
        "connection_label": display,
        "vertical": vert,
        "package_id": used_package or package_id or "",
        "included_submission_package": add_package,
        "documents": documents,
        "file_count": len(documents),
        "accumulated": accumulated,
        "relevance": relevance,
        "warnings": list(relevance.get("warnings") or []),
        "message": relevance.get("message") or "",
    }


def pull_marketplace_sources(
    source_ids: list[str],
    *,
    org_id: str = "default",
    bundle_id: str | None = None,
    create_bundle: bool = True,
    bundle_name: str = "",
    vertical: str = "insurance",
    package_id: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ids = [s.strip() for s in source_ids if s and s.strip()]
    if not ids:
        raise ValueError("source_ids is required")

    store = get_draft_bundle_store()
    created = False
    if not bundle_id:
        if not create_bundle:
            raise ValueError("bundle_id is required when create_bundle is false")
        bundle = store.create(org_id=org_id, name=bundle_name or "Marketplace intake")
        bundle_id = str(bundle["bundle_id"])
        created = True
    elif not store.get(bundle_id, org_id=org_id):
        raise FileNotFoundError(f"Draft bundle not found: {bundle_id}")

    pulls: list[dict[str, Any]] = []
    for i, sid in enumerate(ids):
        pulls.append(
            pull_marketplace_source(
                sid,
                org_id=org_id,
                bundle_id=bundle_id,
                vertical=vertical,
                package_id=package_id,
                config=config,
                include_submission=(i == 0),
            )
        )

    final = store.get(bundle_id, org_id=org_id) or {}
    docs = final.get("documents") or []
    vert = (vertical or "insurance").lower()
    relevance = validate_documents_relevance(
        [{"filename": d.get("filename", ""), "content": d.get("content", ""), "encoding": d.get("encoding", "utf-8")} for d in docs],
        vertical=vert,
        strict=False,
    )
    return {
        "bundle_id": bundle_id,
        "created_bundle": created,
        "vertical": vert,
        "document_count": len(docs),
        "sources": sorted({str(d.get("source_id") or "") for d in docs if d.get("source_id")}),
        "pulls": [{k: v for k, v in p.items() if k != "documents"} for p in pulls],
        "relevance": relevance,
        "warnings": list(relevance.get("warnings") or []),
        "message": relevance.get("message") or "",
        "run": {"method": "POST", "path": f"/pipeline/bundles/{bundle_id}/run", "query": {"vertical": vert, "use_llm": False}},
    }
