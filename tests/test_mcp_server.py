"""MCP server tools: each returns valid JSON; read-only tools don't mutate state."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from insureflow.mcp.server import create_mcp_server


@pytest.fixture()
def mcp_server() -> Any:
    server = create_mcp_server("test-rytera")
    if server is None:
        pytest.skip("mcp package not available")
    return server


def _call(mcp_server: Any, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Call an MCP tool and return the parsed JSON payload."""
    blocks, _ = asyncio.run(mcp_server.call_tool(tool_name, arguments))
    loaded: dict[str, Any] = json.loads(blocks[0].text)
    return loaded


class TestMCPServerTools:
    def test_list_tools_registered(self, mcp_server) -> None:
        tools = mcp_server._tool_manager._tools
        names = sorted(tools.keys())
        assert names == [
            "add_company",
            "calculate_mortgage_metrics",
            "delete_company",
            "detect_life_product",
            "get_health",
            "get_job",
            "get_job_memo",
            "get_life_line",
            "list_companies",
            "list_jobs",
            "list_life_categories",
            "list_life_lines",
            "list_sources",
        ]

    def test_list_jobs_empty(self, mcp_server) -> None:
        mock_store = MagicMock()
        mock_store.list_ids.return_value = []
        with patch("insureflow.mcp.server._get_job_store", return_value=mock_store):
            result = _call(mcp_server, "list_jobs", {})
        assert result["count"] == 0
        assert result["jobs"] == []

    def test_list_jobs_with_entries(self, mcp_server) -> None:
        mock_store = MagicMock()
        mock_store.list_ids.return_value = ["j1", "j2"]
        mock_store.get.side_effect = [
            {"status": "completed", "org_id": "default", "updated_at": "2026-01-01"},
            {"status": "running", "org_id": "default", "updated_at": "2026-01-02"},
        ]
        with patch("insureflow.mcp.server._get_job_store", return_value=mock_store):
            result = _call(mcp_server, "list_jobs", {"limit": 10})
        assert result["count"] == 2
        assert result["jobs"][0]["id"] == "j1"
        assert result["jobs"][0]["status"] == "completed"

    def test_get_job_not_found(self, mcp_server) -> None:
        mock_store = MagicMock()
        mock_store.get.return_value = None
        with (
            patch("insureflow.mcp.server._get_job_store", return_value=mock_store),
            patch("insureflow.mcp.server._get_audit_store"),
        ):
            result = _call(mcp_server, "get_job", {"job_id": "no-such"})
        assert "error" in result

    def test_get_job_found(self, mcp_server) -> None:
        mock_store = MagicMock()
        mock_store.get.return_value = {
            "status": "completed",
            "results": {"memo": {"decision": "approved", "confidence": 0.95}},
        }
        with patch("insureflow.mcp.server._get_job_store", return_value=mock_store):
            result = _call(mcp_server, "get_job", {"job_id": "j1"})
        assert result["status"] == "completed"
        assert result["results"]["memo_summary"]["decision"] == "approved"

    def test_get_job_memo_not_found(self, mcp_server) -> None:
        mock_audit = MagicMock()
        mock_audit.load_json.return_value = None
        mock_store = MagicMock()
        mock_store.get.return_value = None
        with (
            patch("insureflow.mcp.server._get_audit_store", return_value=mock_audit),
            patch("insureflow.mcp.server._get_job_store", return_value=mock_store),
        ):
            result = _call(mcp_server, "get_job_memo", {"job_id": "j1"})
        assert "error" in result

    def test_detect_life_product(self, mcp_server) -> None:
        with patch("insureflow.insurance.life_lobs.detect_life_product", return_value="term-life-10"):
            result = _call(mcp_server, "detect_life_product", {"text_blob": "10 year term life"})
        assert result["detected_product"] == "term-life-10"

    def test_add_company_invalid_name(self, mcp_server) -> None:
        with patch("insureflow.insurance.companies.add_company", side_effect=ValueError("bad name")):
            result = _call(mcp_server, "add_company", {"name": "@bad#"})
        assert "error" in result

    def test_add_company_valid(self, mcp_server) -> None:
        fake = {"id": "c1", "name": "Acme Corp", "kind": "org", "naic": "", "notes": "", "origin": "org"}
        with patch("insureflow.insurance.companies.add_company", return_value=fake):
            result = _call(mcp_server, "add_company", {"name": "Acme Corp"})
        assert result["name"] == "Acme Corp"

    def test_delete_company_not_found(self, mcp_server) -> None:
        with patch("insureflow.insurance.companies.delete_company", side_effect=ValueError("not found")):
            result = _call(mcp_server, "delete_company", {"company_id": "no-such"})
        assert "error" in result

    def test_get_health_ok(self, mcp_server) -> None:
        mock_store = MagicMock()
        mock_store.client = MagicMock()
        mock_store.client.ping.return_value = True
        with patch("insureflow.mcp.server._get_job_store", return_value=mock_store):
            result = _call(mcp_server, "get_health", {})
        assert result["status"] == "ok"
        assert result["job_store"] == "ok"

    def test_get_health_degraded(self, mcp_server) -> None:
        mock_store = MagicMock()
        mock_store.client = MagicMock()
        mock_store.client.ping.side_effect = Exception("connection refused")
        with patch("insureflow.mcp.server._get_job_store", return_value=mock_store):
            result = _call(mcp_server, "get_health", {})
        assert result["status"] == "degraded"
