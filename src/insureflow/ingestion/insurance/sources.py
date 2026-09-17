"""Load insurance submission documents from packages and folders."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

SUPPORTED_TEXT = {".xml", ".json", ".txt", ".md", ".csv"}
SUPPORTED_BINARY = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".tif"}

INSURANCE_PACKAGES: dict[str, dict[str, str | list[str]]] = {
    "pacific-coast": {
        "name": "Pacific Coast Distributors",
        "broker": "Golden Gate Insurance Brokers",
        "files": [
            "pacific_coast_acord.xml",
            "pacific_coast_loss_run.md",
            "pacific_coast_sov.md",
            "pacific_coast_inspection_report.md",
            "pacific_coast_broker_api.json",
        ],
    },
    "northwind": {
        "name": "Northwind Logistics LLC",
        "broker": "Midwest Commercial Brokers",
        "files": [
            "northwind_acord.xml",
            "northwind_loss_run.md",
            "northwind_sov.md",
            "northwind_inspection_report.md",
        ],
    },
}

# Field-type conventions for config_fields, rendered by the Integrations page:
# "text" (default), "password" (masked, show/hide toggle), "number", or
# "select" (needs an "options": [{"value","label"}, ...] list).
_ENV_OPTIONS = [
    {"value": "production", "label": "Production"},
    {"value": "sandbox", "label": "Sandbox"},
]

# Simulated cloud / enterprise connectors — pull maps to curated demo packages.
DEMO_CONNECTORS: dict[str, dict[str, Any]] = {
    "google-drive": {
        "name": "Google Drive",
        "type": "cloud",
        "category": "Document Storage",
        "description": "Broker shared drive / MGA submission folder",
        "config_fields": [
            {"key": "folder_id", "label": "Folder ID or URL", "placeholder": "1BxiMVs0XRA5...", "required": True},
            {"key": "client_id", "label": "OAuth client ID", "placeholder": "1234567890-abc.apps.googleusercontent.com"},
            {"key": "client_secret", "label": "OAuth client secret", "type": "password", "placeholder": "GOCSPX-..."},
        ],
        "label": lambda req: f"Google Drive › {req.folder_id or 'Broker Submissions'}",
    },
    "sharepoint": {
        "name": "SharePoint / OneDrive",
        "type": "cloud",
        "category": "Document Storage",
        "description": "Carrier or MGA document library (Microsoft 365)",
        "config_fields": [
            {"key": "site_url", "label": "Site URL", "placeholder": "https://contoso.sharepoint.com/sites/uw-intake", "required": True},
            {"key": "client_id", "label": "App registration client ID", "placeholder": "00000000-0000-0000-0000-000000000000"},
            {"key": "client_secret", "label": "Client secret", "type": "password", "placeholder": "•••••••••••"},
        ],
        "label": lambda req: f"SharePoint › {req.site_url or 'UW Intake Library'}",
    },
    "s3-bucket": {
        "name": "AWS S3",
        "type": "cloud",
        "category": "Document Storage",
        "description": "Live drop-bucket pull when S3_SUBMISSIONS_BUCKET / AWS creds are set; lab stub otherwise",
        "config_fields": [
            {"key": "bucket", "label": "Bucket", "placeholder": "carrier-submissions", "required": True},
            {"key": "prefix", "label": "Prefix", "placeholder": "brokers/golden-gate/"},
            {
                "key": "region",
                "label": "Region",
                "type": "select",
                "options": [
                    {"value": "us-east-1", "label": "us-east-1"},
                    {"value": "us-east-2", "label": "us-east-2"},
                    {"value": "us-west-1", "label": "us-west-1"},
                    {"value": "us-west-2", "label": "us-west-2"},
                    {"value": "eu-west-1", "label": "eu-west-1"},
                    {"value": "eu-central-1", "label": "eu-central-1"},
                ],
            },
            {"key": "access_key_id", "label": "Access key ID", "placeholder": "AKIAIOSFODNN7EXAMPLE"},
            {"key": "secret_access_key", "label": "Secret access key", "type": "password", "placeholder": "•••••••••••"},
        ],
        "label": lambda req: f"s3://{req.bucket or 'carrier-submissions'}/{req.prefix or 'inbound/'}",
    },
    "azure-blob": {
        "name": "Azure Blob Storage",
        "type": "cloud",
        "category": "Document Storage",
        "description": "Carrier intake container (Azure Storage Account)",
        "config_fields": [
            {"key": "bucket", "label": "Container", "placeholder": "submissions", "required": True},
            {"key": "prefix", "label": "Path prefix", "placeholder": "brokers/inbound/"},
            {"key": "account_id", "label": "Storage account name", "placeholder": "carriersubmissions"},
            {"key": "secret_access_key", "label": "Account key / SAS token", "type": "password", "placeholder": "•••••••••••"},
        ],
        "label": lambda req: f"azure://{req.bucket or 'submissions'}/{req.prefix or 'inbound/'}",
    },
    "box": {
        "name": "Box Enterprise",
        "type": "cloud",
        "category": "Document Storage",
        "description": "Enterprise content cloud for broker submissions",
        "config_fields": [
            {"key": "folder_id", "label": "Folder ID", "placeholder": "123456789", "required": True},
            {"key": "client_id", "label": "App client ID", "placeholder": "abc123..."},
            {"key": "client_secret", "label": "App client secret", "type": "password", "placeholder": "•••••••••••"},
        ],
        "label": lambda req: f"Box › Folder {req.folder_id or 'UW Intake'}",
    },
    "email-inbox": {
        "name": "Email Inbox",
        "type": "email",
        "category": "Submission Intake",
        "description": "Pull broker submission attachments from the configured mailbox",
        "config_fields": [
            {"key": "host", "label": "IMAP host", "placeholder": "imap.mailserver.com", "required": True},
            {"key": "port", "label": "Port", "type": "number", "placeholder": "993"},
            {"key": "username", "label": "Username", "placeholder": "submissions@carrier.com"},
            {"key": "password", "label": "Password", "type": "password", "placeholder": "•••••••••••"},
        ],
        "label": lambda req: "Email Inbox",
    },
    "outlook-inbox": {
        "name": "Outlook / Microsoft 365",
        "type": "email",
        "category": "Submission Intake",
        "description": "Pull broker submissions from Outlook/Microsoft 365 mailbox via Microsoft Graph API",
        "config_fields": [
            {"key": "host", "label": "IMAP host (or Graph tenant)", "placeholder": "outlook.office365.com", "required": True},
            {"key": "username", "label": "Username", "placeholder": "submissions@carrier.onmicrosoft.com"},
            {"key": "password", "label": "Password / app password", "type": "password", "placeholder": "•••••••••••"},
        ],
        "label": lambda req: "Outlook › Inbox",
    },
    "sftp": {
        "name": "SFTP / Broker Portal",
        "type": "sftp",
        "category": "Submission Intake",
        "description": "Live broker drop when SFTP_HOST + credentials are set; lab stub otherwise",
        "config_fields": [
            {"key": "host", "label": "Host", "placeholder": "sftp.broker.com", "required": True},
            {"key": "port", "label": "Port", "type": "number", "placeholder": "22"},
            {"key": "username", "label": "Username", "placeholder": "uw-intake"},
            {"key": "password", "label": "Password", "type": "password", "placeholder": "•••••••••••"},
        ],
        "label": lambda req: req.host or "sftp.wholesale-broker.com",
    },
    "ivans-download": {
        "name": "IVANS Download",
        "type": "data",
        "category": "Industry Exchange",
        "description": "Download carrier/broker transactions via IVANS (Applied, Vertafore)",
        "config_fields": [
            {"key": "host", "label": "IVANS mailbox / account", "placeholder": "carrier-12345", "required": True},
            {"key": "username", "label": "Username", "placeholder": "carrier-12345"},
            {"key": "password", "label": "Password", "type": "password", "placeholder": "•••••••••••"},
            {"key": "environment", "label": "Environment", "type": "select", "options": _ENV_OPTIONS},
        ],
        "label": lambda req: f"IVANS › {req.host or 'carrier-mailbox'} ({req.environment or 'prod'})",
    },
    "acord-al3": {
        "name": "ACORD AL3 / XML Hub",
        "type": "data",
        "category": "Industry Exchange",
        "description": "Automated ACORD 125/126/140 XML and AL3 message intake",
        "config_fields": [
            {"key": "host", "label": "Endpoint / queue", "placeholder": "acord-intake.carrier.com", "required": True},
            {"key": "api_key", "label": "API key", "type": "password", "placeholder": "•••••••••••"},
            {"key": "environment", "label": "Environment", "type": "select", "options": _ENV_OPTIONS},
        ],
        "label": lambda req: f"ACORD Hub › {req.host or 'intake.carrier.com'}",
    },
    "guidewire-policycenter": {
        "name": "Guidewire PolicyCenter",
        "type": "policy",
        "category": "Policy Admin",
        "description": "Pull submission attachments from Guidewire PolicyCenter",
        "config_fields": [
            {"key": "site_url", "label": "PolicyCenter URL", "placeholder": "https://pc.carrier.com", "required": True},
            {"key": "client_id", "label": "API client ID", "placeholder": "gw-integration-uw"},
            {"key": "client_secret", "label": "API client secret", "type": "password", "placeholder": "•••••••••••"},
            {"key": "environment", "label": "Environment", "type": "select", "options": _ENV_OPTIONS},
        ],
        "label": lambda req: f"Guidewire PC › {req.site_url or 'pc.carrier.com'}",
    },
    "duck-creek": {
        "name": "Duck Creek Policy",
        "type": "policy",
        "category": "Policy Admin",
        "description": "Submission documents from Duck Creek Policy admin",
        "config_fields": [
            {"key": "site_url", "label": "Duck Creek URL", "placeholder": "https://policy.carrier.com", "required": True},
            {"key": "api_key", "label": "API key", "type": "password", "placeholder": "•••••••••••"},
            {"key": "environment", "label": "Environment", "type": "select", "options": _ENV_OPTIONS},
        ],
        "label": lambda req: f"Duck Creek › {req.site_url or 'policy.carrier.com'}",
    },
    "majesco-policy": {
        "name": "Majesco Policy",
        "type": "policy",
        "category": "Policy Admin",
        "description": "P&C policy admin — submission bundle export",
        "config_fields": [
            {"key": "site_url", "label": "Majesco tenant URL", "placeholder": "https://tenant.majesco.com", "required": True},
            {"key": "api_key", "label": "API key", "type": "password", "placeholder": "•••••••••••"},
        ],
        "label": lambda req: f"Majesco › {req.site_url or 'tenant.majesco.com'}",
    },
    "applied-epic": {
        "name": "Applied Epic (Vertafore)",
        "type": "agency",
        "category": "Agency Management",
        "description": "Agency management system — broker submission export",
        "config_fields": [
            {"key": "host", "label": "Epic server / tenant", "placeholder": "epic.agency.com", "required": True},
            {"key": "api_key", "label": "API key", "type": "password", "placeholder": "•••••••••••"},
            {"key": "environment", "label": "Environment", "type": "select", "options": _ENV_OPTIONS},
        ],
        "label": lambda req: f"Applied Epic › {req.host or 'epic.agency.com'}",
    },
    "hawksoft": {
        "name": "HawkSoft AMS",
        "type": "agency",
        "category": "Agency Management",
        "description": "Independent agency management — new business submissions",
        "config_fields": [
            {"key": "host", "label": "Agency ID / API host", "placeholder": "agency-12345", "required": True},
            {"key": "api_key", "label": "API key", "type": "password", "placeholder": "•••••••••••"},
        ],
        "label": lambda req: f"HawkSoft › {req.host or 'agency-12345'}",
    },
    "salesforce-crm": {
        "name": "Salesforce",
        "type": "crm",
        "category": "CRM / Distribution",
        "description": "Broker opportunity files from Salesforce Opportunity / Case",
        "config_fields": [
            {"key": "site_url", "label": "Salesforce org URL", "placeholder": "https://carrier.my.salesforce.com", "required": True},
            {"key": "folder_id", "label": "Record type / queue", "placeholder": "Commercial_Submissions"},
            {"key": "client_id", "label": "Connected app client ID", "placeholder": "3MVG9..."},
            {"key": "client_secret", "label": "Connected app client secret", "type": "password", "placeholder": "•••••••••••"},
        ],
        "label": lambda req: f"Salesforce › {req.folder_id or 'Commercial Submissions'}",
    },
    "verisk-iso": {
        "name": "Verisk / ISO",
        "type": "data",
        "category": "Rating & Loss Data",
        "description": "ISO loss costs, PPC, and property analytics feed",
        "config_fields": [
            {"key": "site_url", "label": "Verisk account / endpoint", "placeholder": "https://api.verisk.com", "required": True},
            {"key": "api_key", "label": "API key", "type": "password", "placeholder": "•••••••••••"},
            {"key": "environment", "label": "Environment", "type": "select", "options": _ENV_OPTIONS},
        ],
        "label": lambda req: f"Verisk ISO › {req.site_url or 'api.verisk.com'}",
    },
    "corelogic": {
        "name": "CoreLogic / Cotality",
        "type": "data",
        "category": "Rating & Loss Data",
        "description": "Property risk, replacement cost, and catastrophe models",
        "config_fields": [
            {"key": "site_url", "label": "API endpoint", "placeholder": "https://api.corelogic.com", "required": True},
            {"key": "api_key", "label": "API key", "type": "password", "placeholder": "•••••••••••"},
        ],
        "label": lambda req: f"CoreLogic › {req.site_url or 'property-risk-api'}",
    },
    "bold-penguin": {
        "name": "Bold Penguin",
        "type": "marketplace",
        "category": "Submission Intake",
        "description": "Small commercial marketplace — route applications from agents directly to carrier appetite",
        "config_fields": [
            {"key": "host", "label": "Bold Penguin API endpoint", "placeholder": "https://api.boldpenguin.com", "required": True},
            {"key": "api_key", "label": "API key", "type": "password", "placeholder": "•••••••••••"},
            {"key": "environment", "label": "Environment", "type": "select", "options": _ENV_OPTIONS},
        ],
        "label": lambda req: f"Bold Penguin › {req.host or 'api.boldpenguin.com'} ({req.environment or 'prod'})",
    },
    "docusign": {
        "name": "DocuSign",
        "type": "signature",
        "category": "eSignature",
        "description": "Signed application packets and broker attestations",
        "config_fields": [
            {"key": "site_url", "label": "DocuSign account", "placeholder": "https://account.docusign.com", "required": True},
            {"key": "folder_id", "label": "Envelope folder / template", "placeholder": "UW-Applications"},
            {"key": "client_id", "label": "Integration key", "placeholder": "00000000-0000-0000-0000-000000000000"},
            {"key": "client_secret", "label": "Client secret", "type": "password", "placeholder": "•••••••••••"},
        ],
        "label": lambda req: f"DocuSign › {req.folder_id or 'UW Applications'}",
    },
    "microsoft-teams": {
        "name": "Microsoft Teams",
        "type": "messaging",
        "category": "Collaboration",
        "description": "UW intake channel file drops and @mention submissions",
        "config_fields": [
            {"key": "site_url", "label": "Channel webhook URL", "placeholder": "https://contoso.webhook.office.com/...", "required": True},
            {"key": "client_secret", "label": "Bot / app password", "type": "password", "placeholder": "•••••••••••"},
        ],
        "label": lambda req: "Teams › UW Intake Channel",
    },
    "slack-intake": {
        "name": "Slack",
        "type": "messaging",
        "category": "Collaboration",
        "description": "#submissions channel — broker file uploads via workflow",
        "config_fields": [
            {"key": "mailbox", "label": "Channel / workflow ID", "placeholder": "#submissions", "required": True},
            {"key": "token", "label": "Bot token", "type": "password", "placeholder": "xoxb-•••••••••••"},
        ],
        "label": lambda req: f"Slack › {req.mailbox or '#submissions'}",
    },
    "snowflake": {
        "name": "Snowflake",
        "type": "data",
        "category": "Data Warehouse",
        "description": "Historical loss and exposure data from carrier warehouse",
        "config_fields": [
            {"key": "host", "label": "Account identifier", "placeholder": "carrier.snowflakecomputing.com", "required": True},
            {"key": "username", "label": "Username", "placeholder": "uw_pipeline_svc"},
            {"key": "password", "label": "Password", "type": "password", "placeholder": "•••••••••••"},
            {"key": "prefix", "label": "Database.schema.table", "placeholder": "UW.SUBMISSIONS_STAGING"},
        ],
        "label": lambda req: f"Snowflake › {req.prefix or 'UW.SUBMISSIONS_STAGING'}",
    },
    "databricks": {
        "name": "Databricks",
        "type": "data",
        "category": "Data Warehouse",
        "description": "Lakehouse exposure and loss triangles (Unity Catalog table, via databricks-sql-connector)",
        "config_fields": [
            {"key": "host", "label": "Workspace hostname (optional — else DATABRICKS_HOST)", "placeholder": "adb-1234.5.azuredatabricks.net"},
            {"key": "prefix", "label": "catalog.schema.table", "placeholder": "uw.exposure.loss_triangles", "required": True},
            {"key": "token", "label": "Personal access token", "type": "password", "placeholder": "dapi•••••••••••"},
        ],
        "label": lambda req: f"Databricks › {req.prefix or 'uw.exposure.loss_triangles'}",
    },
}

# Real pull adapters. Everything else in DEMO_CONNECTORS is a lab stub.
# outlook-inbox is live when OUTLOOK_* or IMAP_* credentials are set (IMAP path, not Graph OAuth).
LIVE_CONNECTOR_IDS = frozenset({"email-inbox", "outlook-inbox", "s3-bucket", "sftp", "server-folder", "databricks"})


def _live_connector_configured(source_id: str) -> bool:
    if source_id == "server-folder":
        return True
    if source_id == "email-inbox":
        from insureflow.ingestion.insurance.email_connector import ImapConnection

        return ImapConnection().is_configured
    if source_id == "outlook-inbox":
        import os

        host = (os.getenv("OUTLOOK_HOST") or os.getenv("IMAP_HOST") or "").strip()
        user = (os.getenv("OUTLOOK_USERNAME") or os.getenv("IMAP_USERNAME") or "").strip()
        password = (os.getenv("OUTLOOK_PASSWORD") or os.getenv("IMAP_PASSWORD") or "").strip()
        return bool(host and user and password)
    if source_id == "s3-bucket":
        from insureflow.ingestion.insurance.s3_connector import s3_configured

        return s3_configured()
    if source_id == "sftp":
        from insureflow.ingestion.insurance.sftp_connector import sftp_configured

        return sftp_configured()
    if source_id == "databricks":
        from insureflow.ingestion.insurance.databricks_connector import databricks_configured

        return databricks_configured()
    return False


def annotate_source(entry: dict[str, object]) -> dict[str, object]:
    """Label connectors honestly: live / needs_config / lab_demo / catalog_stub."""
    sid = str(entry.get("id") or "")
    if entry.get("type") == "library" or entry.get("category") == "Demo Packages":
        entry["kind"] = "lab_demo"
        entry["honesty"] = "Lab sample — pre-loaded broker package"
        entry["configured"] = True
        entry["pullable"] = True
        return entry

    _live_honesty = {
        "server-folder": "Live folder on this server",
        "email-inbox": "Live IMAP — pull broker submissions from mailbox",
        "outlook-inbox": "Live Outlook via IMAP — set OUTLOOK_HOST/USERNAME/PASSWORD (or IMAP_*)",
        "s3-bucket": "Live S3 drop — pull submissions from bucket",
        "sftp": "Live SFTP — pull from broker drop folder",
        "databricks": "Live Databricks SQL warehouse — pull exposure/loss-triangle table",
    }
    _stub_honesty = {
        "google-drive": "Not contracted — Google Drive lab stub (maps to demo packages)",
        "sharepoint": "Not contracted — SharePoint lab stub (maps to demo packages)",
        "azure-blob": "Not contracted — Azure Blob lab stub (maps to demo packages)",
        "box": "Not contracted — Box lab stub (maps to demo packages)",
        "ivans-download": "Not contracted — IVANS lab stub (maps to demo packages)",
        "acord-al3": "Not contracted — ACORD Hub lab stub (maps to demo packages)",
        "guidewire-policycenter": "Not contracted — Guidewire attach lab stub (maps to demo packages)",
        "duck-creek": "Not contracted — Duck Creek lab stub (maps to demo packages)",
        "majesco-policy": "Not contracted — Majesco lab stub (maps to demo packages)",
        "applied-epic": "Not contracted — Applied Epic lab stub (maps to demo packages)",
        "hawksoft": "Not contracted — HawkSoft lab stub (maps to demo packages)",
        "salesforce-crm": "Not contracted — Salesforce lab stub (maps to demo packages)",
        "verisk-iso": "Not contracted — Verisk/ISO lab stub (maps to demo packages)",
        "corelogic": "Not contracted — CoreLogic lab stub (maps to demo packages)",
        "bold-penguin": "Not contracted — Bold Penguin lab stub (maps to demo packages)",
        "docusign": "Not contracted — DocuSign lab stub (maps to demo packages)",
        "microsoft-teams": "Not contracted — Teams lab stub (maps to demo packages)",
        "slack-intake": "Not contracted — Slack lab stub (maps to demo packages)",
        "snowflake": "Not contracted — Snowflake lab stub (maps to demo packages)",
    }

    if sid in LIVE_CONNECTOR_IDS:
        configured = _live_connector_configured(sid)
        entry["kind"] = "live" if configured else "needs_config"
        entry["honesty"] = _live_honesty.get(sid, "Live — connected and ready") if configured else f"Live connector available — set credentials to enable ({sid})"
        entry["configured"] = configured
        entry["pullable"] = configured or sid == "server-folder"
        return entry

    entry["kind"] = "catalog_stub"
    entry["honesty"] = _stub_honesty.get(sid, "Not contracted — lab stub maps to demo packages until vendor credentials")
    entry["configured"] = False
    # Still pullable: stubs resolve to curated demo packages for lab runs.
    entry["pullable"] = True
    return entry


def _encode_file(path: Path, root: Path | None = None) -> dict[str, str]:
    ext = path.suffix.lower()
    rel = path.relative_to(root).as_posix() if root is not None else path.name
    parent = str(Path(rel).parent)
    directory = "" if parent in {".", ""} else parent
    if ext in SUPPORTED_BINARY:
        return {
            "filename": path.name,
            "path": rel,
            "directory": directory,
            "content": base64.b64encode(path.read_bytes()).decode("ascii"),
            "encoding": "base64",
        }
    return {
        "filename": path.name,
        "path": rel,
        "directory": directory,
        "content": path.read_text(encoding="utf-8"),
        "encoding": "utf-8",
    }


def load_package(examples_dir: Path, package_id: str) -> list[dict[str, str]]:
    pkg = INSURANCE_PACKAGES.get(package_id)
    if not pkg:
        raise FileNotFoundError(f"Unknown package: {package_id}")
    docs: list[dict[str, str]] = []
    for fname in pkg["files"]:
        path = examples_dir / fname
        if path.is_file():
            encoded = _encode_file(path, root=examples_dir)
            encoded["directory"] = package_id
            encoded["path"] = f"{package_id}/{path.name}"
            docs.append(encoded)
    if not docs:
        raise FileNotFoundError(f"No files found for package {package_id}")
    return docs


def load_directory(directory: Path, max_files: int = 40) -> list[dict[str, str]]:
    if not directory.is_dir():
        raise FileNotFoundError(f"Directory not found: {directory}")
    allowed = SUPPORTED_TEXT | SUPPORTED_BINARY
    docs: list[dict[str, str]] = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in allowed:
            continue
        docs.append(_encode_file(path, root=directory))
        if len(docs) >= max_files:
            break
    if not docs:
        raise FileNotFoundError(f"No supported documents in {directory}")
    return docs


def simulated_connection_label(source_id: str, req: Any) -> str:
    meta = DEMO_CONNECTORS.get(source_id)
    if not meta:
        return source_id
    return str(meta["label"](req))


def list_sources(
    examples_dir: Path,
    extra_packages: list[dict[str, object]] | None = None,
    include_insurance_packages: bool = True,
    hardened: bool = False,
) -> list[dict[str, object]]:
    packages: list[dict[str, object]] = (
        [
            {
                "id": pid,
                "name": meta["name"],
                "type": "library",
                "category": "Demo Packages",
                "description": f"Curated demo package — {meta['broker']}",
                "status": "ready",
                "file_count": len(meta["files"]),
            }
            for pid, meta in INSURANCE_PACKAGES.items()
        ]
        if include_insurance_packages
        else []
    )
    if extra_packages:
        packages = extra_packages + packages
    enterprise = [
        {
            "id": sid,
            "name": meta["name"],
            "type": meta["type"],
            "category": meta["category"],
            "description": meta["description"],
            "status": "ready",
            "config_fields": meta["config_fields"],
        }
        for sid, meta in DEMO_CONNECTORS.items()
    ]
    rows = (
        packages
        + [
            {
                "id": "server-folder",
                "name": "Server Directory",
                "type": "filesystem",
                "category": "Document Storage",
                "description": "Pull from a folder on the API server (e.g. examples/)",
                "status": "ready",
                "config_fields": [{"key": "path", "label": "Folder path", "placeholder": "examples"}],
            },
        ]
        + enterprise
    )
    annotated = [annotate_source(dict(r)) for r in rows]
    if hardened:
        return [r for r in annotated if r.get("kind") in {"live", "needs_config"}]
    return annotated
