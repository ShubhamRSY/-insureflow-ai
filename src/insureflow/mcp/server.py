from __future__ import annotations

import json
import logging
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from insureflow.agents.tools import UnderwritingTools
from insureflow.models.submissions import ClaimRecord
from insureflow.models.mortgage import ProductLine
from insureflow.pipeline import UnderwritingPipeline
from insureflow.rag.guidelines import GuidelineCategory, builtin_guidelines
from insureflow.rag.rag_agent import RAGAgent

logger = logging.getLogger(__name__)

_rag_agent: Optional[RAGAgent] = None
_pipeline: Optional[UnderwritingPipeline] = None


def _get_rag() -> RAGAgent:
    global _rag_agent
    if _rag_agent is None:
        _rag_agent = RAGAgent()
        _rag_agent.ensure_indexed()
    return _rag_agent


def _get_pipeline() -> UnderwritingPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = UnderwritingPipeline()
    return _pipeline


def _parse_claims(claims_json: str) -> list[ClaimRecord]:
    data = json.loads(claims_json)
    if isinstance(data, list):
        return [ClaimRecord(**c) for c in data]
    return []


def run_server(host: str = "127.0.0.1", port: int = 8010) -> None:
    """Start the InsureFlow MCP server via SSE transport.

    Can connect via any MCP client (Claude Desktop, VS Code, Cursor, etc.).
    """
    logger.info("Starting InsureFlow MCP server on %s:%d", host, port)
    from mcp.server.fastmcp import FastMCP

    server = FastMCP(
        "InsureFlow Underwriting",
        instructions="Multi-agent AI underwriting system for commercial property and casualty insurance",
        host=host,
        port=port,
    )
    _register_all(server)
    server.run(transport="sse")


def _register_all(server: FastMCP) -> None:
    """Register all tools, resources, and prompts on a FastMCP instance."""

    # -----------------------------------------------------------------------
    # Tools
    # -----------------------------------------------------------------------

    @server.tool(
        name="calculate_loss_ratio",
        description="Calculate the loss ratio (incurred losses / earned premium). A ratio >0.7 indicates unprofitable risk.",
    )
    def calculate_loss_ratio(incurred: float, premium: float) -> float:
        return UnderwritingTools.loss_ratio(incurred, premium)

    @server.tool(
        name="calculate_claim_frequency",
        description="Calculate average number of claims per year over a given period.",
    )
    def calculate_claim_frequency(
        claims_json: str,
        years: float = 5.0,
    ) -> float:
        claims = _parse_claims(claims_json)
        return UnderwritingTools.claim_frequency(claims, years)

    @server.tool(
        name="calculate_average_severity",
        description="Calculate the average dollar amount per claim.",
    )
    def calculate_average_severity(claims_json: str) -> float:
        claims = _parse_claims(claims_json)
        return UnderwritingTools.average_severity(claims)

    @server.tool(
        name="calculate_large_loss_ratio",
        description="Calculate the proportion of claims exceeding a given threshold (default $100k).",
    )
    def calculate_large_loss_ratio(claims_json: str, threshold: float = 100_000.0) -> float:
        claims = _parse_claims(claims_json)
        return UnderwritingTools.large_loss_ratio(claims, threshold)

    @server.tool(
        name="calculate_litigation_ratio",
        description="Calculate the proportion of claims that are in litigation.",
    )
    def calculate_litigation_ratio(claims_json: str) -> float:
        claims = _parse_claims(claims_json)
        return UnderwritingTools.litigation_ratio(claims)

    @server.tool(
        name="query_underwriting_guidelines",
        description="Search the underwriting guideline knowledge base for rules relevant to a given risk profile.",
    )
    def query_underwriting_guidelines(query: str, top_k: int = 5) -> str:
        agent = _get_rag()
        return agent.format_context(query, top_k=top_k)

    @server.tool(
        name="assess_risk_profile",
        description="Evaluate a commercial risk profile against underwriting guidelines and return structured findings.",
    )
    def assess_risk_profile(
        occupancy_type: str = "",
        construction_type: str = "",
        year_built: Optional[int] = None,
        sprinklered: Optional[bool] = None,
        protection_class: Optional[int] = None,
        square_footage: Optional[float] = None,
        naics: Optional[str] = None,
    ) -> str:
        findings: list[str] = []

        if construction_type:
            findings.append(f"Construction: {construction_type}")

        if year_built is not None:
            yr = UnderwritingTools.year_built_risk(year_built)
            findings.append(f"Year built {year_built}: {yr.value} risk")

        if sprinklered is not None:
            sr = UnderwritingTools.sprinkler_risk(sprinklered)
            findings.append(f"Sprinklered: {sprinklered} → {sr.value} risk")

        if protection_class is not None:
            pcr = UnderwritingTools.protection_class_risk(protection_class)
            findings.append(f"Protection class {protection_class}: {pcr.value} risk")

        query_parts = [
            p
            for p in [occupancy_type, construction_type]
            if p
        ]
        if query_parts:
            agent = _get_rag()
            guidelines = agent.format_context(" ".join(query_parts), top_k=3)
            if guidelines:
                findings.append(f"\nRelevant guidelines:\n{guidelines}")

        if not findings:
            return "No risk profile data provided."

        return "\n".join(findings)

    @server.tool(
        name="run_underwriting_pipeline",
        description="Execute the full multi-agent underwriting pipeline on an ACORD XML submission.",
    )
    def run_underwriting_pipeline(
        acord_xml: str,
        bundle_id: Optional[str] = None,
    ) -> str:
        pipeline = _get_pipeline()
        result = pipeline.run(
            acord_xml=acord_xml,
            bundle_id=bundle_id,
        )
        summary = {
            "bundle_id": result.get("bundle_id"),
            "status": result.get("status"),
            "human_review_needed": result.get("human_review_needed"),
            "synthesis_decision": result.get("synthesis", {}).get("underwriting_decision"),
            "reconciliation_match_rate": result.get("reconciliation", {}).get("match_rate"),
            "discrepancies": result.get("reconciliation", {}).get("discrepancies", 0),
        }
        return json.dumps(summary, indent=2)

    @server.tool(
        name="run_pipeline_from_file",
        description="Execute the underwriting pipeline from an ACORD XML file path on the server.",
    )
    def run_pipeline_from_file(acord_xml_path: str, bundle_id: Optional[str] = None) -> str:
        pipeline = _get_pipeline()
        result = pipeline.run_from_files(
            acord_xml_path=acord_xml_path,
            bundle_id=bundle_id,
        )
        summary = {
            "bundle_id": result.get("bundle_id"),
            "status": result.get("status"),
            "human_review_needed": result.get("human_review_needed"),
            "synthesis_decision": result.get("synthesis", {}).get("underwriting_decision"),
        }
        return json.dumps(summary, indent=2)

    @server.tool(
        name="assess_mortgage_risk",
        description="Evaluate a mortgage risk profile against standard underwriting guidelines.",
    )
    def assess_mortgage_risk(
        credit_score: Optional[int] = None,
        dti_ratio: Optional[float] = None,
        ltv_ratio: Optional[float] = None,
        loan_amount: Optional[float] = None,
        property_value: Optional[float] = None,
        reserves: Optional[float] = None,
        self_employed: Optional[bool] = None,
        loan_purpose: Optional[str] = None,
        occupancy_type: Optional[str] = None,
    ) -> str:
        findings: list[str] = []

        if credit_score is not None:
            if credit_score >= 740:
                findings.append(f"Credit score {credit_score}: LOW risk")
            elif credit_score >= 680:
                findings.append(f"Credit score {credit_score}: MODERATE risk")
            elif credit_score >= 620:
                findings.append(f"Credit score {credit_score}: HIGH risk")
            else:
                findings.append(f"Credit score {credit_score}: CRITICAL risk")

        if dti_ratio is not None:
            if dti_ratio <= 0.36:
                findings.append(f"DTI ratio {dti_ratio:.1%}: LOW risk")
            elif dti_ratio <= 0.43:
                findings.append(f"DTI ratio {dti_ratio:.1%}: MODERATE risk")
            elif dti_ratio <= 0.50:
                findings.append(f"DTI ratio {dti_ratio:.1%}: HIGH risk")
            else:
                findings.append(f"DTI ratio {dti_ratio:.1%}: CRITICAL risk")

        if ltv_ratio is not None:
            if ltv_ratio <= 0.60:
                findings.append(f"LTV ratio {ltv_ratio:.1%}: LOW risk")
            elif ltv_ratio <= 0.75:
                findings.append(f"LTV ratio {ltv_ratio:.1%}: MODERATE risk")
            elif ltv_ratio <= 0.85:
                findings.append(f"LTV ratio {ltv_ratio:.1%}: HIGH risk")
            else:
                findings.append(f"LTV ratio {ltv_ratio:.1%}: CRITICAL risk")

        if loan_amount is not None and property_value is not None and property_value > 0:
            computed_ltv = loan_amount / property_value
            if computed_ltv <= 0.60:
                findings.append(f"Loan-to-value ({computed_ltv:.1%}): LOW risk")
            elif computed_ltv <= 0.75:
                findings.append(f"Loan-to-value ({computed_ltv:.1%}): MODERATE risk")
            elif computed_ltv <= 0.85:
                findings.append(f"Loan-to-value ({computed_ltv:.1%}): HIGH risk")
            else:
                findings.append(f"Loan-to-value ({computed_ltv:.1%}): CRITICAL risk")

        if reserves is not None and loan_amount is not None and loan_amount > 0:
            reserve_months = reserves / (loan_amount * 0.007)
            if reserve_months >= 6:
                findings.append(f"Reserves ({reserve_months:.0f} months): LOW risk")
            elif reserve_months >= 3:
                findings.append(f"Reserves ({reserve_months:.0f} months): MODERATE risk")
            else:
                findings.append(f"Reserves ({reserve_months:.0f} months): HIGH risk")

        if self_employed is not None:
            if self_employed:
                findings.append("Self-employed: additional income documentation required")
            else:
                findings.append("Employed: standard employment verification applies")

        if loan_purpose:
            purpose_lower = loan_purpose.lower()
            if purpose_lower in ("purchase", "refinance"):
                findings.append(f"Loan purpose '{loan_purpose}': standard risk")
            elif purpose_lower == "cash-out":
                findings.append(f"Loan purpose '{loan_purpose}': elevated risk — verify equity retention")
            else:
                findings.append(f"Loan purpose '{loan_purpose}': review required")

        if occupancy_type:
            occ_lower = occupancy_type.lower()
            if occ_lower == "primary":
                findings.append(f"Occupancy '{occupancy_type}': LOW risk")
            elif occ_lower == "secondary":
                findings.append(f"Occupancy '{occupancy_type}': MODERATE risk")
            elif occ_lower == "investment":
                findings.append(f"Occupancy '{occupancy_type}': HIGH risk")
            else:
                findings.append(f"Occupancy '{occupancy_type}': review required")

        if not findings:
            return "No mortgage risk data provided."

        return "\n".join(findings)

    @server.tool(
        name="query_mortgage_guidelines",
        description="Search mortgage underwriting guideline knowledge base.",
    )
    def query_mortgage_guidelines(query: str, top_k: int = 5) -> str:
        agent = _get_rag()
        return agent.format_context(query, top_k=top_k)

    @server.tool(
        name="run_mortgage_pipeline",
        description="Execute the full mortgage underwriting pipeline on a set of mortgage documents.",
    )
    def run_mortgage_pipeline(
        documents_json: str,
        bundle_id: Optional[str] = None,
        use_llm: bool = True,
    ) -> str:
        from uuid import uuid4
        from insureflow.mortgage.pipeline import MortgagePipeline

        documents = json.loads(documents_json)
        pipeline = MortgagePipeline(use_llm=use_llm)
        bid = bundle_id or f"mortgage-{uuid4().hex[:12]}"
        result = pipeline.run_from_texts(
            documents,
            bundle_id=bid,
            product_line=ProductLine.RESIDENTIAL_MORTGAGE,
        )
        summary = {
            "document_count": result.get("document_count", len(documents)),
            "decision": result.get("decision", "refer"),
            "risk_score": result.get("risk_score", 0.0),
            "dti_ratio": result.get("dti_ratio"),
            "ltv_ratio": result.get("ltv_ratio"),
            "bundle_id": result.get("bundle_id", bid),
        }
        return json.dumps(summary, indent=2)

    @server.tool(
        name="calculate_mortgage_metrics",
        description="Calculate monthly mortgage payment, total interest, and affordability metrics.",
    )
    def calculate_mortgage_metrics(
        loan_amount: float,
        interest_rate: float,
        loan_term_years: int = 30,
        property_tax_rate: float = 0.0,
        insurance: float = 0.0,
        hoa: float = 0.0,
    ) -> str:
        monthly_rate = interest_rate / 100 / 12
        num_payments = loan_term_years * 12

        if monthly_rate > 0:
            monthly_pi = loan_amount * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
        else:
            monthly_pi = loan_amount / num_payments

        monthly_tax = (loan_amount * property_tax_rate / 100) / 12 if property_tax_rate > 0 else 0.0
        total_monthly = monthly_pi + monthly_tax + insurance + hoa
        total_paid = total_monthly * num_payments
        total_interest = (monthly_pi * num_payments) - loan_amount
        total_cost = total_paid

        lines = [
            f"Monthly P&I: ${monthly_pi:,.2f}",
            f"Monthly tax: ${monthly_tax:,.2f}",
            f"Monthly insurance: ${insurance:,.2f}",
            f"Monthly HOA: ${hoa:,.2f}",
            f"Total monthly payment: ${total_monthly:,.2f}",
            f"Total interest over {loan_term_years} years: ${total_interest:,.2f}",
            f"Total cost (interest + principal + tax + insurance + HOA): ${total_cost:,.2f}",
        ]
        return "\n".join(lines)

    # -----------------------------------------------------------------------
    # Resources
    # -----------------------------------------------------------------------

    @server.resource(
        "insureflow://guidelines",
        description="All built-in underwriting guidelines across all categories.",
    )
    def get_all_guidelines() -> str:
        guidelines = builtin_guidelines()
        lines: list[str] = []
        for g in guidelines.guidelines:
            lines.append(f"[{g.id}] ({g.category.value.upper()}, {g.source.value}) {g.title}")
            lines.append(f"    Impact: {g.risk_impact}")
            lines.append(f"    {g.content}")
            lines.append("")
        return "\n".join(lines) if lines else "No guidelines loaded."

    @server.resource(
        "insureflow://guidelines/{category}",
        description="Underwriting guidelines filtered by category (e.g. building, occupancy, protection, location, financial, management, operations, company).",
    )
    def get_guidelines_by_category(category: str) -> str:
        try:
            cat = GuidelineCategory(category.lower())
        except ValueError:
            valid = [c.value for c in GuidelineCategory]
            return f"Invalid category. Valid options: {', '.join(valid)}"

        guidelines = builtin_guidelines()
        matched = guidelines.by_category(cat)
        if not matched:
            return f"No guidelines found for category: {category}"

        lines: list[str] = []
        for g in matched:
            lines.append(f"[{g.id}] ({g.source.value}) {g.title}")
            lines.append(f"    Impact: {g.risk_impact}")
            lines.append(f"    {g.content}")
            lines.append("")
        return "\n".join(lines)

    @server.resource(
        "insureflow://guidelines/search/{query}",
        description="Search underwriting guidelines by keyword. Returns top 5 most relevant matches.",
    )
    def search_guidelines(query: str) -> str:
        agent = _get_rag()
        return agent.format_context(query, top_k=5) or "No matching guidelines found."

    # -----------------------------------------------------------------------
    # Prompts
    # -----------------------------------------------------------------------

    @server.prompt(
        name="underwriting_review",
        description="Generate a structured underwriting review prompt for a commercial risk submission.",
    )
    def underwriting_review_prompt(
        insured_name: str = "",
        occupancy_type: str = "",
        construction_type: str = "",
        year_built: Optional[int] = None,
        sprinklered: Optional[bool] = None,
        protection_class: Optional[int] = None,
        total_insurable_value: Optional[float] = None,
        prior_claims_count: Optional[int] = None,
    ) -> str:
        parts = [
            "You are a senior commercial property underwriter. Review the following risk submission and provide a detailed underwriting analysis.",
            "",
            f"Insured: {insured_name or 'Unknown'}" if insured_name else "",
            f"Occupancy: {occupancy_type}" if occupancy_type else "",
            f"Construction: {construction_type}" if construction_type else "",
            f"Year Built: {year_built}" if year_built else "",
            f"Sprinklered: {sprinklered}" if sprinklered is not None else "",
            f"Protection Class: {protection_class}" if protection_class else "",
            f"Total Insurable Value: ${total_insurable_value:,.2f}" if total_insurable_value else "",
            f"Prior Claims (5yr): {prior_claims_count}" if prior_claims_count is not None else "",
            "",
            "Analyze the following dimensions:",
            "1. Physical risk (construction, age, protection class, sprinklers)",
            "2. Occupancy hazard (what does this business do?)",
            "3. Loss history (frequency, severity, large loss ratio)",
            "4. Coverage adequacy (is the limit enough for the TIV?)",
            "5. Overall recommendation (ACCEPT / REFER / DECLINE)",
            "",
            "Cite specific underwriting guidelines that support your assessment.",
        ]
        return "\n".join(p for p in parts if p)
