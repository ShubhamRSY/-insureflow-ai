"""MCP server tools: each returns valid JSON; read-only tools don't mutate state.

Every org-scoped tool resolves its tenant from the authenticated principal
(``insureflow.mcp.auth``) rather than a caller-supplied ``org_id``. The
tests below bind a principal per case and assert the org actually reaching
the store — that is the whole regression surface for the cross-tenant read
that used to be possible via ``org_id="someone-else"``.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from insureflow.auth import Role
from insureflow.auth.models import TokenData
from insureflow.mcp.auth import bound_principal
from insureflow.mcp.server import create_mcp_server

DEFAULT_TOKEN = "no-token-headers-set-on-this-test-client"


@pytest.fixture()
def mcp_server() -> Any:
    server = create_mcp_server("test-rytera")
    if server is None:
        pytest.skip("mcp package not available")
    return server


@pytest.fixture()
def principal() -> TokenData:
    return TokenData(username="uw@example.com", role=Role.UNDERWRITER, org_id="acme")


def _call(mcp_server: Any, tool_name: str, arguments: dict[str, Any], *, as_user: TokenData | None = None) -> dict[str, Any]:
    """Call an MCP tool and return the parsed JSON payload.

    ``as_user=None`` simulates a transport that authenticated nobody —
    org-scoped tools must refuse rather than fall back to a default org.
    """
    if as_user is None:
        blocks, _ = asyncio.run(mcp_server.call_tool(tool_name, arguments))
    else:
        with bound_principal(as_user):
            blocks, _ = asyncio.run(mcp_server.call_tool(tool_name, arguments))
    loaded: dict[str, Any] = json.loads(blocks[0].text)
    return loaded


def _as(role: Role, org_id: str = "acme") -> TokenData:
    return TokenData(username="u@example.com", role=role, org_id=org_id)


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

    def test_no_tool_accepts_org_id(self, mcp_server) -> None:
        """org_id is a tenant identifier, never a caller-supplied argument."""
        offenders = [name for name, tool in mcp_server._tool_manager._tools.items() if "org_id" in (getattr(tool, "parameters", None) or {}).get("properties", {})]
        assert offenders == []

    def test_list_jobs_empty(self, mcp_server, principal) -> None:
        mock_store = MagicMock()
        mock_store.list_ids.return_value = []
        with patch("insureflow.mcp.server._get_job_store", return_value=mock_store):
            result = _call(mcp_server, "list_jobs", {}, as_user=principal)
        assert result["count"] == 0
        assert result["jobs"] == []

    def test_list_jobs_with_entries(self, mcp_server, principal) -> None:
        mock_store = MagicMock()
        mock_store.list_ids.return_value = ["j1", "j2"]
        mock_store.get.side_effect = [
            {"status": "completed", "org_id": "acme", "updated_at": "2026-01-01"},
            {"status": "running", "org_id": "acme", "updated_at": "2026-01-02"},
        ]
        with patch("insureflow.mcp.server._get_job_store", return_value=mock_store):
            result = _call(mcp_server, "list_jobs", {"limit": 10}, as_user=principal)
        assert result["count"] == 2
        assert result["jobs"][0]["id"] == "j1"
        assert result["jobs"][0]["status"] == "completed"

    def test_list_jobs_scopes_to_caller_org(self, mcp_server) -> None:
        """The org reaching the store is the caller's, not a chosen one."""
        mock_store = MagicMock()
        mock_store.list_ids.return_value = []
        with patch("insureflow.mcp.server._get_job_store", return_value=mock_store):
            _call(mcp_server, "list_jobs", {"limit": 5}, as_user=_as(Role.VIEWER, "tenant-42"))
        assert mock_store.list_ids.call_args.kwargs["org_id"] == "tenant-42"

    def test_list_jobs_unauthenticated_refused(self, mcp_server) -> None:
        mock_store = MagicMock()
        with patch("insureflow.mcp.server._get_job_store", return_value=mock_store):
            result = _call(mcp_server, "list_jobs", {}, as_user=None)
        assert result["status"] == 401
        mock_store.list_ids.assert_not_called()

    def test_get_job_not_found(self, mcp_server, principal) -> None:
        mock_store = MagicMock()
        mock_store.get.return_value = None
        with (
            patch("insureflow.mcp.server._get_job_store", return_value=mock_store),
            patch("insureflow.mcp.server._get_audit_store"),
        ):
            result = _call(mcp_server, "get_job", {"job_id": "no-such"}, as_user=principal)
        assert "error" in result

    def test_get_job_found(self, mcp_server, principal) -> None:
        mock_store = MagicMock()
        mock_store.get.return_value = {
            "status": "completed",
            "results": {"memo": {"decision": "approved", "confidence": 0.95}},
        }
        with patch("insureflow.mcp.server._get_job_store", return_value=mock_store):
            result = _call(mcp_server, "get_job", {"job_id": "j1"}, as_user=principal)
        assert result["status"] == "completed"
        assert result["results"]["memo_summary"]["decision"] == "approved"

    def test_get_job_scopes_to_caller_org(self, mcp_server) -> None:
        mock_store = MagicMock()
        mock_store.get.return_value = {"status": "completed"}
        with patch("insureflow.mcp.server._get_job_store", return_value=mock_store):
            _call(mcp_server, "get_job", {"job_id": "j1"}, as_user=_as(Role.VIEWER, "other-tenant"))
        assert mock_store.get.call_args.kwargs["org_id"] == "other-tenant"

    def test_get_job_memo_scopes_audit_read_to_caller_org(self, mcp_server) -> None:
        mock_audit = MagicMock()
        mock_audit.load_json.return_value = {"decision": "approved"}
        with patch("insureflow.mcp.server._get_audit_store", return_value=mock_audit):
            _call(mcp_server, "get_job_memo", {"job_id": "j1"}, as_user=_as(Role.VIEWER, "tenant-7"))
        assert mock_audit.load_json.call_args.kwargs["org_id"] == "tenant-7"

    def test_get_job_memo_not_found(self, mcp_server, principal) -> None:
        mock_audit = MagicMock()
        mock_audit.load_json.return_value = None
        mock_store = MagicMock()
        mock_store.get.return_value = None
        with (
            patch("insureflow.mcp.server._get_audit_store", return_value=mock_audit),
            patch("insureflow.mcp.server._get_job_store", return_value=mock_store),
        ):
            result = _call(mcp_server, "get_job_memo", {"job_id": "j1"}, as_user=principal)
        assert "error" in result

    def test_detect_life_product(self, mcp_server) -> None:
        with patch("insureflow.insurance.life_lobs.detect_life_product", return_value="term-life-10"):
            result = _call(mcp_server, "detect_life_product", {"text_blob": "10 year term life"})
        assert result["detected_product"] == "term-life-10"

    def test_add_company_invalid_name(self, mcp_server, principal) -> None:
        with patch("insureflow.insurance.companies.add_company", side_effect=ValueError("bad name")):
            result = _call(mcp_server, "add_company", {"name": "@bad#"}, as_user=principal)
        assert "error" in result

    def test_add_company_valid(self, mcp_server, principal) -> None:
        fake = {"id": "c1", "name": "Acme Corp", "kind": "org", "naic": "", "notes": "", "origin": "org"}
        with patch("insureflow.insurance.companies.add_company", return_value=fake) as mock_add:
            result = _call(mcp_server, "add_company", {"name": "Acme Corp"}, as_user=principal)
        assert result["name"] == "Acme Corp"
        assert mock_add.call_args.args[0] == "acme"

    def test_add_company_viewer_forbidden(self, mcp_server) -> None:
        """Writes need the same role as the REST endpoint, not just a token."""
        with patch("insureflow.insurance.companies.add_company") as mock_add:
            result = _call(mcp_server, "add_company", {"name": "Acme Corp"}, as_user=_as(Role.VIEWER))
        assert result["status"] == 403
        mock_add.assert_not_called()

    def test_delete_company_not_found(self, mcp_server, principal) -> None:
        with patch("insureflow.insurance.companies.delete_company", side_effect=ValueError("not found")):
            result = _call(mcp_server, "delete_company", {"company_id": "no-such"}, as_user=principal)
        assert "error" in result

    def test_list_companies_scopes_to_caller_org(self, mcp_server) -> None:
        with patch("insureflow.insurance.companies.list_companies", return_value=[]) as mock_list:
            _call(mcp_server, "list_companies", {}, as_user=_as(Role.VIEWER, "tenant-9"))
        assert mock_list.call_args.kwargs["org_id"] == "tenant-9"

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
