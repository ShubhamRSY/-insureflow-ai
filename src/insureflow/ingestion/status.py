"""Intake surface for the desk — not Airbyte, Airflow, or Kafka."""

from __future__ import annotations

from typing import Any


def ingestion_status() -> dict[str, Any]:
    from insureflow.ingestion.insurance.email_connector import ImapConnection
    from insureflow.ingestion.insurance.s3_connector import s3_configured
    from insureflow.ingestion.insurance.sftp_connector import sftp_configured
    from insureflow.tasks.dispatch import broker_configured, broker_reachable

    imap = ImapConnection()
    unstructured_ok = False
    try:
        import unstructured  # noqa: F401

        unstructured_ok = True
    except ImportError:
        pass
    tesseract_ok = False
    try:
        import pytesseract  # noqa: F401

        tesseract_ok = True
    except ImportError:
        pass
    celery = broker_configured()
    return {
        "connectors": {
            "imap": {"configured": imap.is_configured, "live": True},
            "s3": {"configured": s3_configured(), "live": True},
            "sftp": {"configured": sftp_configured(), "live": True},
            "folder": {"configured": True, "live": True},
        },
        "parsers": [
            "acord_xml",
            "broker_json",
            "loss_run",
            "sov",
            "inspection",
            "financials",
            "excel",
            "ocr_pdf_image",
        ],
        "ocr": {
            "pdfminer": True,
            "tesseract": tesseract_ok,
            "unstructured_optional": unstructured_ok,
        },
        "workflow": "celery" if celery else "in_process",
        "broker_reachable": broker_reachable() if celery else False,
        "events": "https_webhooks",
        "not_required": ["airbyte", "fivetran", "airflow", "dbt", "kafka", "debezium", "docling"],
    }
