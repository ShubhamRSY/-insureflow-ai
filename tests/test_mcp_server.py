from __future__ import annotations

import json
from unittest.mock import patch

from insureflow.mcp.server import _parse_claims, _register_all, run_server
from insureflow.rag.guidelines import GuidelineCategory


class TestMCPServerModule:
    def test_import(self) -> None:
        from insureflow.mcp import run_server as rs

        assert rs is run_server

    def test_parse_claims_empty(self) -> None:
        assert _parse_claims("[]") == []

    def test_parse_claims_valid(self) -> None:
        data = json.dumps(
            [
                {
                    "claim_id": "C001",
                    "date_of_loss": "2024-03-15",
                    "line_of_business": "Property",
                    "cause": "Fire",
                    "incurred_amount": 50000,
                    "claim_status": "closed",
                },
            ]
        )
        claims = _parse_claims(data)
        assert len(claims) == 1
        assert claims[0].claim_id == "C001"
        assert claims[0].incurred_amount == 50000

    def test_guideline_categories_exist(self) -> None:
        cats = list(GuidelineCategory)
        assert len(cats) >= 6

    @patch("insureflow.mcp.server.FastMCP")
    def test_register_all_tools(self, mock_fastmcp) -> None:
        mock_instance = mock_fastmcp.return_value
        _register_all(mock_instance)
        tool_calls = [call for call in mock_instance.tool.call_args_list]
        resource_calls = [call for call in mock_instance.resource.call_args_list]
        prompt_calls = [call for call in mock_instance.prompt.call_args_list]
        assert len(tool_calls) == 9
        assert len(resource_calls) == 3
        assert len(prompt_calls) == 1


class TestMCPToolLogic:
    def test_loss_ratio_zero_premium(self) -> None:
        from insureflow.agents.tools import UnderwritingTools

        assert UnderwritingTools.loss_ratio(1000, 0) == 0.0

    def test_guideline_search(self) -> None:
        from insureflow.rag.rag_agent import RAGAgent

        agent = RAGAgent()
        agent.ensure_indexed()
        result = agent.format_context("masonry construction", top_k=2)
        assert "=== RELEVANT UNDERWRITING GUIDELINES ===" in result
