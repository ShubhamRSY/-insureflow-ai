"""Real Databricks SQL warehouse fetch (when workspace credentials are present).

Uses the official `databricks-sql-connector` (a lightweight SQL client over
the Databricks SQL warehouse REST protocol) — not PySpark. Nothing in this
per-submission ingestion pipeline needs distributed compute; this only ever
runs one bounded SELECT to pull a book's exposure / loss-triangle snapshot,
so a thin SQL client is the right tool, not a Spark cluster.

The query result is packaged as a single JSON document and handed to the same
ingestion path every other source uses (`load_from_documents`), rather than
inventing a parallel structured-data pipeline.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

MAX_ROWS_DEFAULT = 500


def databricks_configured(host: str | None = None) -> bool:
    h = (host or os.getenv("DATABRICKS_HOST") or os.getenv("DATABRICKS_SERVER_HOSTNAME") or "").strip()
    http_path = os.getenv("DATABRICKS_HTTP_PATH", "").strip()
    token = os.getenv("DATABRICKS_TOKEN", "").strip()
    return bool(h and http_path and token)


def pull_databricks_submissions(
    *,
    host: str | None = None,
    catalog: str | None = None,
    schema: str | None = None,
    table: str | None = None,
    max_rows: int = MAX_ROWS_DEFAULT,
) -> dict[str, Any]:
    """Query a Unity Catalog table (exposure / loss-triangle data) and return
    it as one JSON "document", the same shape every other connector returns.

    ``catalog``/``schema``/``table`` default to the ``DATABRICKS_CATALOG`` /
    ``DATABRICKS_SCHEMA`` / ``DATABRICKS_LOSS_TRIANGLE_TABLE`` env vars so an
    admin can wire a fixed lakehouse table without the caller specifying one
    per pull.
    """
    try:
        from databricks import sql as databricks_sql
    except ImportError as exc:
        raise ConnectionError("databricks-sql-connector not installed — pip install 'insureflow[databricks]' for lakehouse intake") from exc

    hostname = (host or os.getenv("DATABRICKS_HOST") or os.getenv("DATABRICKS_SERVER_HOSTNAME") or "").strip()
    http_path = os.getenv("DATABRICKS_HTTP_PATH", "").strip()
    token = os.getenv("DATABRICKS_TOKEN", "").strip()
    if not hostname or not http_path or not token:
        raise ConnectionError("Databricks not configured — set DATABRICKS_HOST, DATABRICKS_HTTP_PATH, and DATABRICKS_TOKEN")

    cat = (catalog or os.getenv("DATABRICKS_CATALOG") or "").strip()
    sch = (schema or os.getenv("DATABRICKS_SCHEMA") or "").strip()
    tbl = (table or os.getenv("DATABRICKS_LOSS_TRIANGLE_TABLE") or "").strip()
    if not (cat and sch and tbl):
        raise ConnectionError("Databricks table not configured — set catalog/schema/table on the request or DATABRICKS_CATALOG/DATABRICKS_SCHEMA/DATABRICKS_LOSS_TRIANGLE_TABLE")

    qualified = f"`{cat}`.`{sch}`.`{tbl}`"
    limit = max(1, min(int(max_rows or MAX_ROWS_DEFAULT), MAX_ROWS_DEFAULT))

    with databricks_sql.connect(server_hostname=hostname, http_path=http_path, access_token=token) as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {qualified} LIMIT {limit}")
            columns = [col[0] for col in cursor.description or []]
            rows = [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]

    payload = {
        "source": "databricks",
        "catalog": cat,
        "schema": sch,
        "table": tbl,
        "row_count": len(rows),
        "rows": rows,
    }
    filename = f"databricks_{sch}_{tbl}.json"
    documents = [
        {
            "filename": filename,
            "content": json.dumps(payload, default=str),
            "encoding": "utf-8",
        }
    ]

    return {
        "host": hostname,
        "catalog": cat,
        "schema": sch,
        "table": tbl,
        "documents": documents,
        "documents_found": len(documents),
        "rows_fetched": len(rows),
        "simulated": False,
    }
