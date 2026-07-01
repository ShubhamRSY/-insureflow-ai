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

# Simulated cloud / enterprise connectors — pull maps to curated demo packages.
DEMO_CONNECTORS: dict[str, dict[str, Any]] = {
    "google-drive": {
        "name": "Google Drive",
        "type": "cloud",
        "category": "Document Storage",
        "description": "Broker shared drive / MGA submission folder",
        "config_fields": [{"key": "folder_id", "label": "Folder ID or URL", "placeholder": "1BxiMVs0XRA5..."}],
        "label": lambda req: f"Google Drive › {req.folder_id or 'Broker Submissions'}",
    },
    "sharepoint": {
        "name": "SharePoint / OneDrive",
        "type": "cloud",
        "category": "Document Storage",
        "description": "Carrier or MGA document library (Microsoft 365)",
        "config_fields": [
            {
                "key": "site_url",
                "label": "Site URL",
                "placeholder": "https://contoso.sharepoint.com/sites/uw-intake",
            }
        ],
        "label": lambda req: f"SharePoint › {req.site_url or 'UW Intake Library'}",
    },
    "s3-bucket": {
        "name": "AWS S3",
        "type": "cloud",
        "category": "Document Storage",
        "description": "Submission drop bucket (s3://carrier-submissions/)",
        "config_fields": [
            {"key": "bucket", "label": "Bucket", "placeholder": "carrier-submissions"},
            {"key": "prefix", "label": "Prefix", "placeholder": "brokers/golden-gate/"},
        ],
        "label": lambda req: f"s3://{req.bucket or 'carrier-submissions'}/{req.prefix or 'inbound/'}",
    },
    "azure-blob": {
        "name": "Azure Blob Storage",
        "type": "cloud",
        "category": "Document Storage",
        "description": "Carrier intake container (Azure Storage Account)",
        "config_fields": [
            {"key": "bucket", "label": "Container", "placeholder": "submissions"},
            {"key": "prefix", "label": "Path prefix", "placeholder": "brokers/inbound/"},
        ],
        "label": lambda req: f"azure://{req.bucket or 'submissions'}/{req.prefix or 'inbound/'}",
    },
    "box": {
        "name": "Box Enterprise",
        "type": "cloud",
        "category": "Document Storage",
        "description": "Enterprise content cloud for broker submissions",
        "config_fields": [{"key": "folder_id", "label": "Folder ID", "placeholder": "123456789"}],
        "label": lambda req: f"Box › Folder {req.folder_id or 'UW Intake'}",
    },
    "email-inbox": {
        "name": "Email Inbox",
        "type": "email",
        "category": "Submission Intake",
        "description": "Poll submissions@yourmga.com for broker attachments",
        "config_fields": [{"key": "mailbox", "label": "Mailbox", "placeholder": "submissions@insureflow.demo"}],
        "label": lambda req: req.mailbox or "submissions@insureflow.demo",
    },
    "sftp": {
        "name": "SFTP / Broker Portal",
        "type": "sftp",
        "category": "Submission Intake",
        "description": "Wholesale broker automated feed (ACORD XML + PDFs)",
        "config_fields": [{"key": "host", "label": "Host", "placeholder": "sftp.broker.com"}],
        "label": lambda req: req.host or "sftp.wholesale-broker.com",
    },
    "ivans-download": {
        "name": "IVANS Download",
        "type": "data",
        "category": "Industry Exchange",
        "description": "Download carrier/broker transactions via IVANS (Applied, Vertafore)",
        "config_fields": [
            {"key": "host", "label": "IVANS mailbox / account", "placeholder": "carrier-12345"},
            {"key": "environment", "label": "Environment", "placeholder": "production"},
        ],
        "label": lambda req: f"IVANS › {req.host or 'carrier-mailbox'} ({req.environment or 'prod'})",
    },
    "acord-al3": {
        "name": "ACORD AL3 / XML Hub",
        "type": "data",
        "category": "Industry Exchange",
        "description": "Automated ACORD 125/126/140 XML and AL3 message intake",
        "config_fields": [
            {"key": "host", "label": "Endpoint / queue", "placeholder": "acord-intake.carrier.com"},
            {"key": "environment", "label": "Environment", "placeholder": "sandbox"},
        ],
        "label": lambda req: f"ACORD Hub › {req.host or 'intake.carrier.com'}",
    },
    "guidewire-policycenter": {
        "name": "Guidewire PolicyCenter",
        "type": "policy",
        "category": "Policy Admin",
        "description": "Pull submission attachments from Guidewire PolicyCenter",
        "config_fields": [
            {
                "key": "site_url",
                "label": "PolicyCenter URL",
                "placeholder": "https://pc.carrier.com",
            },
            {"key": "environment", "label": "Environment", "placeholder": "prod"},
        ],
        "label": lambda req: f"Guidewire PC › {req.site_url or 'pc.carrier.com'}",
    },
    "duck-creek": {
        "name": "Duck Creek Policy",
        "type": "policy",
        "category": "Policy Admin",
        "description": "Submission documents from Duck Creek Policy admin",
        "config_fields": [
            {
                "key": "site_url",
                "label": "Duck Creek URL",
                "placeholder": "https://policy.carrier.com",
            },
            {"key": "environment", "label": "Environment", "placeholder": "prod"},
        ],
        "label": lambda req: f"Duck Creek › {req.site_url or 'policy.carrier.com'}",
    },
    "majesco-policy": {
        "name": "Majesco Policy",
        "type": "policy",
        "category": "Policy Admin",
        "description": "P&C policy admin — submission bundle export",
        "config_fields": [
            {
                "key": "site_url",
                "label": "Majesco tenant URL",
                "placeholder": "https://tenant.majesco.com",
            }
        ],
        "label": lambda req: f"Majesco › {req.site_url or 'tenant.majesco.com'}",
    },
    "applied-epic": {
        "name": "Applied Epic (Vertafore)",
        "type": "agency",
        "category": "Agency Management",
        "description": "Agency management system — broker submission export",
        "config_fields": [
            {"key": "host", "label": "Epic server / tenant", "placeholder": "epic.agency.com"},
            {"key": "environment", "label": "Environment", "placeholder": "production"},
        ],
        "label": lambda req: f"Applied Epic › {req.host or 'epic.agency.com'}",
    },
    "hawksoft": {
        "name": "HawkSoft AMS",
        "type": "agency",
        "category": "Agency Management",
        "description": "Independent agency management — new business submissions",
        "config_fields": [{"key": "host", "label": "Agency ID / API host", "placeholder": "agency-12345"}],
        "label": lambda req: f"HawkSoft › {req.host or 'agency-12345'}",
    },
    "salesforce-crm": {
        "name": "Salesforce",
        "type": "crm",
        "category": "CRM / Distribution",
        "description": "Broker opportunity files from Salesforce Opportunity / Case",
        "config_fields": [
            {
                "key": "site_url",
                "label": "Salesforce org URL",
                "placeholder": "https://carrier.my.salesforce.com",
            },
            {
                "key": "folder_id",
                "label": "Record type / queue",
                "placeholder": "Commercial_Submissions",
            },
        ],
        "label": lambda req: f"Salesforce › {req.folder_id or 'Commercial Submissions'}",
    },
    "verisk-iso": {
        "name": "Verisk / ISO",
        "type": "data",
        "category": "Rating & Loss Data",
        "description": "ISO loss costs, PPC, and property analytics feed",
        "config_fields": [
            {
                "key": "site_url",
                "label": "Verisk account / endpoint",
                "placeholder": "https://api.verisk.com",
            },
            {"key": "environment", "label": "Environment", "placeholder": "production"},
        ],
        "label": lambda req: f"Verisk ISO › {req.site_url or 'api.verisk.com'}",
    },
    "corelogic": {
        "name": "CoreLogic / Cotality",
        "type": "data",
        "category": "Rating & Loss Data",
        "description": "Property risk, replacement cost, and catastrophe models",
        "config_fields": [{"key": "site_url", "label": "API endpoint", "placeholder": "https://api.corelogic.com"}],
        "label": lambda req: f"CoreLogic › {req.site_url or 'property-risk-api'}",
    },
    "imageright": {
        "name": "ImageRight (Vertafore)",
        "type": "document",
        "category": "Document Storage",
        "description": "Document management for small carriers — policy forms, applications, inspection reports",
        "config_fields": [
            {
                "key": "host",
                "label": "ImageRight server / tenant",
                "placeholder": "imageright.carrier.com",
            },
            {"key": "folder_id", "label": "Document queue / folder", "placeholder": "UW-Intake"},
        ],
        "label": lambda req: f"ImageRight › {req.host or 'imageright.carrier.com'}/{req.folder_id or 'UW-Intake'}",
    },
    "bold-penguin": {
        "name": "Bold Penguin",
        "type": "marketplace",
        "category": "Submission Intake",
        "description": "Small commercial marketplace — route applications from agents directly to carrier appetite",
        "config_fields": [
            {
                "key": "host",
                "label": "Bold Penguin API endpoint",
                "placeholder": "https://api.boldpenguin.com",
            },
            {"key": "environment", "label": "Environment", "placeholder": "production"},
        ],
        "label": lambda req: f"Bold Penguin › {req.host or 'api.boldpenguin.com'} ({req.environment or 'prod'})",
    },
    "docusign": {
        "name": "DocuSign",
        "type": "signature",
        "category": "eSignature",
        "description": "Signed application packets and broker attestations",
        "config_fields": [
            {
                "key": "site_url",
                "label": "DocuSign account",
                "placeholder": "https://account.docusign.com",
            },
            {
                "key": "folder_id",
                "label": "Envelope folder / template",
                "placeholder": "UW-Applications",
            },
        ],
        "label": lambda req: f"DocuSign › {req.folder_id or 'UW Applications'}",
    },
    "microsoft-teams": {
        "name": "Microsoft Teams",
        "type": "messaging",
        "category": "Collaboration",
        "description": "UW intake channel file drops and @mention submissions",
        "config_fields": [
            {
                "key": "site_url",
                "label": "Team channel webhook / URL",
                "placeholder": "https://teams.microsoft.com/...",
            }
        ],
        "label": lambda req: "Teams › UW Intake Channel",
    },
    "slack-intake": {
        "name": "Slack",
        "type": "messaging",
        "category": "Collaboration",
        "description": "#submissions channel — broker file uploads via workflow",
        "config_fields": [{"key": "mailbox", "label": "Channel / workflow ID", "placeholder": "#submissions"}],
        "label": lambda req: f"Slack › {req.mailbox or '#submissions'}",
    },
    "snowflake": {
        "name": "Snowflake",
        "type": "data",
        "category": "Data Warehouse",
        "description": "Historical loss and exposure data from carrier warehouse",
        "config_fields": [
            {
                "key": "host",
                "label": "Account / warehouse",
                "placeholder": "carrier.snowflakecomputing.com",
            },
            {"key": "prefix", "label": "Schema.table", "placeholder": "UW.SUBMISSIONS_STAGING"},
        ],
        "label": lambda req: f"Snowflake › {req.prefix or 'UW.SUBMISSIONS_STAGING'}",
    },
}


def _encode_file(path: Path) -> dict[str, str]:
    ext = path.suffix.lower()
    if ext in SUPPORTED_BINARY:
        return {
            "filename": path.name,
            "content": base64.b64encode(path.read_bytes()).decode("ascii"),
            "encoding": "base64",
        }
    return {
        "filename": path.name,
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
            docs.append(_encode_file(path))
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
        docs.append(_encode_file(path))
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


def list_sources(examples_dir: Path) -> list[dict[str, object]]:
    packages = [
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
    return (
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
