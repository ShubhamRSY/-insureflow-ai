from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from insureflow.agents.tools import UnderwritingTools
from insureflow.models.submissions import ClaimRecord, SubmissionBundle


@dataclass
class ToolDef:
    name: str
    description: str
    parameters: dict[str, str] = field(default_factory=dict)
    fn: Callable[..., Any] | None = None


class ToolRegistry:
    # Tools that expose or reason about P&C-only concepts — physical insured
    # locations, coverage limits/deductibles/sublimits, and claims loss-run
    # history. Never registered for a line in NON_PROPERTY_LINES (life,
    # health, general, and the face/limit-rated commercial specialty lines):
    # an LLM-driven ReAct agent that cannot call these tools cannot fabricate
    # a "missing locations/coverages/loss run/schedule of values" finding
    # from their (structurally-always-empty, for those lines) output.
    _PROPERTY_ONLY_TOOLS = frozenset(
        {
            "get_risk_profile",
            "get_locations",
            "get_coverages",
            "get_loss_run",
            "get_sovs",
            "compute_claim_frequency",
            "compute_average_severity",
            "compute_large_loss_ratio",
            "compute_open_claim_ratio",
            "compute_litigation_ratio",
            "assess_protection_class",
            "assess_year_built_risk",
            "check_non_disclosed_claims",
            "check_sov_vs_location_valuation",
            "check_coverage_adequacy",
        }
    )

    def __init__(self, bundle: SubmissionBundle, insurance_line: str | None = None, org_id: str | None = None) -> None:
        self.bundle = bundle
        self.uw = UnderwritingTools()
        self.insurance_line = insurance_line
        self.org_id = org_id
        self._tools: dict[str, ToolDef] = {}
        from insureflow.rating.models import is_non_property_line

        self._include_property_tools = not is_non_property_line(insurance_line)
        self._register_all()

    def _register_all(self) -> None:
        self._register(
            "get_named_insured",
            "Returns the legal name of the named insured.",
            {},
            lambda: self.uw.get_named_insured(self.bundle),
        )
        self._register(
            "get_risk_profile",
            "Returns the risk profile including construction type, sprinklered status, protection class, occupancy, year built, square footage.",
            {},
            lambda: self._serialize(self.uw.get_risk_profile(self.bundle)),
        )
        self._register(
            "get_locations",
            "Returns all insured locations with address, year built, building value, contents value, square footage.",
            {},
            lambda: self._serialize(self.uw.get_locations(self.bundle)),
        )
        self._register(
            "get_coverages",
            "Returns all coverages with type, limit, deductible, premium, sublimits, endorsements.",
            {},
            lambda: self._serialize(self.uw.get_coverages(self.bundle)),
        )
        self._register(
            "get_loss_run",
            "Returns the loss run data with all claims, totals, and loss ratios.",
            {},
            lambda: self._serialize(self.uw.get_loss_run(self.bundle)),
        )
        self._register(
            "get_sovs",
            "Returns schedule of values with items and totals.",
            {},
            lambda: self._serialize(self.uw.get_sovs(self.bundle)),
        )
        self._register(
            "compute_claim_frequency",
            "Calculates claims per year over a given period.",
            {"years": "number of years to average over (default 5)"},
            lambda years=5: self._serialize(
                {
                    "frequency": self.uw.claim_frequency(self._claims(), float(years)),
                    "total_claims": len(self._claims()),
                    "years": float(years),
                }
            ),
        )
        self._register(
            "compute_average_severity",
            "Calculates average incurred amount per claim.",
            {},
            lambda: {"average_severity": self.uw.average_severity(self._claims())},
        )
        self._register(
            "compute_large_loss_ratio",
            "Calculates percentage of claims over a threshold.",
            {"threshold": "minimum incurred amount for large loss (default 100000)"},
            lambda threshold=100000: {
                "large_loss_ratio": self.uw.large_loss_ratio(self._claims(), float(threshold)),
                "threshold": float(threshold),
            },
        )
        self._register(
            "compute_open_claim_ratio",
            "Returns ratio of open claims and total open reserves.",
            {},
            lambda: self._serialize(
                {
                    "open_ratio": self.uw.open_claim_ratio(self._claims()),
                    "open_reserves": sum(c.open_reserve for c in self._claims() if c.claim_status.value == "open"),
                }
            ),
        )
        self._register(
            "compute_litigation_ratio",
            "Returns ratio of claims in litigation.",
            {},
            lambda: {"litigation_ratio": self.uw.litigation_ratio(self._claims())},
        )
        self._register(
            "assess_protection_class",
            "Assesses risk level of a given protection class (1-10).",
            {"pclass": "protection class number"},
            lambda pclass: {
                "risk": self.uw.protection_class_risk(int(pclass)).value,
            },
        )
        self._register(
            "assess_year_built_risk",
            "Assesses risk level based on building age.",
            {"year": "year the building was constructed"},
            lambda year: {
                "risk": self.uw.year_built_risk(int(year)).value,
                "age": 2026 - int(year),
            },
        )
        self._register(
            "check_non_disclosed_claims",
            "Compares loss run claims against structured submission to find claims not disclosed in the application.",
            {},
            lambda: self._serialize(
                {
                    "non_disclosed_count": len(self._non_disclosed()),
                    "non_disclosed": [
                        {
                            "claim_id": c.claim_id,
                            "incurred": c.incurred_amount,
                            "date": str(c.date_of_loss),
                            "cause": c.cause,
                        }
                        for c in self._non_disclosed()
                    ],
                }
            ),
        )
        self._register(
            "check_sov_vs_location_valuation",
            "Compares total SOV values against location building/contents values to detect mismatches.",
            {},
            lambda: self._serialize(self._sov_vs_location()),
        )
        self._register(
            "check_coverage_adequacy",
            "Checks if a coverage limit is adequate relative to total insurable value.",
            {"coverage_type": "the coverage type to check (e.g. 'Property')"},
            lambda coverage_type: self._serialize(self._check_coverage_adequacy(coverage_type)),
        )
        self._register(
            "get_all_structured_data",
            "Returns the complete structured submission data as a single JSON object.",
            {},
            lambda: self._serialize(self.bundle.structured),
        )
        self._register(
            "recall_similar_past_decisions",
            "Finds past submissions from this same organization with similar risk characteristics "
            "(line, state, industry, size band, construction, occupancy) and reports what decision "
            "was made and why. Use this to check for precedent before making a judgment call — this "
            "line is agnostic and applies to every insurance line, not just property.",
            {"limit": "max number of similar past cases to return (default 5)"},
            lambda limit=5: self._recall_similar_past_decisions(int(limit)),
        )

    def _register(
        self,
        name: str,
        description: str,
        parameters: dict[str, str],
        fn: Callable[..., Any],
    ) -> None:
        if name in self._PROPERTY_ONLY_TOOLS and not self._include_property_tools:
            return
        self._tools[name] = ToolDef(name=name, description=description, parameters=parameters, fn=fn)

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            }
            for t in self._tools.values()
        ]

    def call(self, name: str, **kwargs: Any) -> Any:
        tool = self._tools.get(name)
        if not tool:
            return {"error": f"Unknown tool: {name}"}
        try:
            assert tool.fn is not None
            result = tool.fn(**kwargs)
            return result
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}"}

    def tool_descriptions(self) -> str:
        lines = ["Available tools:"]
        for t in self._tools.values():
            params = ", ".join(f"{k}: {v}" for k, v in t.parameters.items())
            lines.append(f"  - {t.name}({params}): {t.description}")
        return "\n".join(lines)

    def _serialize(self, obj: Any) -> Any:
        if obj is None:
            return {"data": None}
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if isinstance(obj, list):
            return [self._serialize(item) for item in obj]
        if isinstance(obj, dict):
            return {k: self._serialize(v) for k, v in obj.items()}
        if hasattr(obj, "__dict__"):
            return {k: self._serialize(v) for k, v in obj.__dict__.items()}
        return obj

    def _claims(self) -> list[ClaimRecord]:
        lr = self.uw.get_loss_run(self.bundle)
        return lr.claims if lr else []

    def _non_disclosed(self) -> list[ClaimRecord]:
        claims = self._claims()
        structured_claims = []
        if self.bundle.structured and self.bundle.structured.financial:
            structured_claims = self.bundle.structured.financial.prior_losses
        return self.uw.find_non_disclosed_losses(claims, structured_claims)

    def _sov_vs_location(self) -> dict[str, Any]:
        locations = self.uw.get_locations(self.bundle)
        sovs = self.uw.get_sovs(self.bundle)
        if not locations or not sovs:
            return {"message": "Missing SOV or location data for comparison"}
        sov_total = sum(s.total_value for s in sovs)
        loc_total = self.uw.total_insurable_value(locations)
        return {
            "sov_total": sov_total,
            "location_total": loc_total,
            "ratio": round(sov_total / loc_total, 4) if loc_total else 0,
        }

    def _recall_query_text(self) -> str:
        """Best-effort description of the CURRENT submission's own risk
        characteristics — built from whatever fields this line actually has,
        not the eventual decision/reasons (those don't exist yet; that's
        what the agent calling this tool is still reasoning toward).
        """
        from insureflow.privacy.decision_memory import tiv_band

        structured = self.bundle.structured
        risk = structured.risk_profile if structured else None
        insured = structured.named_insured if structured else None
        locations = self.uw.get_locations(self.bundle) if self._include_property_tools else []

        state = (locations[0].state if locations else None) or (insured.state_of_residence if insured else None) or ""
        naics = risk.naics_code if risk else ""
        construction = risk.construction_type if risk else ""
        occupancy = risk.occupancy_type if risk else ""
        tiv = self.uw.total_insurable_value(locations) if locations else 0.0

        parts = [f"line={self.insurance_line or ''}", f"state={state or ''}", f"naics={naics or ''}", f"tiv_band={tiv_band(tiv)}", f"construction={construction or ''}", f"occupancy={occupancy or ''}"]
        return " ".join(parts)

    def _recall_similar_past_decisions(self, limit: int) -> dict[str, Any]:
        if not self.org_id:
            return {"available": False, "reason": "org_id not available for this run — cannot look up organization-scoped decision history"}
        from insureflow.privacy.decision_memory import get_decision_memory

        try:
            hits = get_decision_memory().similar_semantic(self._recall_query_text(), self.org_id, limit=max(1, min(limit, 20)))
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}"}
        return {
            "available": True,
            "count": len(hits),
            "similar_cases": [
                {
                    "bundle_id": rec.bundle_id,
                    "score": round(score, 3),
                    "decision": rec.decision,
                    "line": rec.line,
                    "state": rec.state,
                    "tiv_band": rec.tiv_band,
                    "reasons": rec.reasons,
                }
                for rec, score in hits
            ],
        }

    def _check_coverage_adequacy(self, coverage_type: str) -> dict[str, Any]:
        coverages = self.uw.get_coverages(self.bundle)
        locations = self.uw.get_locations(self.bundle)
        tiv = self.uw.total_insurable_value(locations)
        for c in coverages:
            if coverage_type.lower() in c.coverage_type.lower():
                ratio, status = self.uw.coverage_adequacy(c, tiv)
                return {
                    "coverage_type": c.coverage_type,
                    "limit": c.limit_amount,
                    "total_insurable_value": tiv,
                    "ratio": ratio,
                    "status": status,
                }
        return {"error": f"No coverage found matching: {coverage_type}"}
