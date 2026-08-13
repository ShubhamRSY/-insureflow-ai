from __future__ import annotations

import logging
from typing import Any

from insureflow.integration.base_adapter import BasePolicyAdminAdapter, PolicySubmissionPayload
from insureflow.integration.britecore_adapter import BriteCoreAdapter
from insureflow.integration.guidewire_adapter import GuidewireAdapter
from insureflow.models.agents import UnderwritingMemo
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import QuoteResult

logger = logging.getLogger(__name__)


class PolicyAdminService:
    """Orchestrates pushing parsed data to core systems (BriteCore, Guidewire, custom).

    Eliminates the copy-paste bottleneck by automating API handoffs.
    """

    def __init__(
        self,
        primary_adapter: BasePolicyAdminAdapter | None = None,
        fallback_adapter: BasePolicyAdminAdapter | None = None,
    ):
        self.primary = primary_adapter or BriteCoreAdapter()
        self.fallback = fallback_adapter or GuidewireAdapter()
        self._adapters: list[BasePolicyAdminAdapter] = [self.primary, self.fallback]

    def submit_to_core_systems(
        self,
        bundle: SubmissionBundle,
        memo: UnderwritingMemo,
        quote: QuoteResult,
        org_id: str = "default",
    ) -> list[dict[str, Any]]:
        """Submit to all configured core systems. Returns results from each."""
        payload = self._build_payload(bundle, memo, quote, org_id)
        try:
            quote.metadata = dict(quote.metadata or {})
            quote.metadata["pas_bind_payload"] = payload.to_dict()
        except Exception:
            pass
        results: list[dict[str, Any]] = []

        for adapter in self._adapters:
            try:
                result = adapter.submit_quote(payload)
                results.append(
                    {
                        "system": adapter.get_system_name(),
                        "success": result.success,
                        "external_reference": result.external_reference,
                        "error": result.error,
                        "response": result.response_payload,
                    }
                )
                logger.info(
                    "Core integration %s: %s (%s)",
                    "SUCCESS" if result.success else "FAILED",
                    adapter.get_system_name(),
                    result.external_reference or result.error,
                )
            except Exception as exc:
                logger.exception("Core integration failed for %s", adapter.get_system_name())
                results.append(
                    {
                        "system": adapter.get_system_name(),
                        "success": False,
                        "error": str(exc),
                        "external_reference": "",
                        "response": {},
                    }
                )

        return results

    def bind_on_core_systems(
        self,
        bundle: SubmissionBundle,
        memo: UnderwritingMemo,
        quote: QuoteResult,
        org_id: str = "default",
    ) -> list[dict[str, Any]]:
        """Bind the policy on all configured core systems."""
        payload = self._build_payload(bundle, memo, quote, org_id)
        results: list[dict[str, Any]] = []

        for adapter in self._adapters:
            try:
                ref = getattr(adapter, "last_quote_reference", "")
                result = adapter.bind_policy(payload, ref)
                results.append(
                    {
                        "system": adapter.get_system_name(),
                        "success": result.success,
                        "policy_number": result.policy_number,
                        "external_reference": result.external_reference,
                        "error": result.error,
                        "response": result.response_payload,
                    }
                )
            except Exception as exc:
                logger.exception("Policy bind failed for %s", adapter.get_system_name())
                results.append(
                    {
                        "system": adapter.get_system_name(),
                        "success": False,
                        "error": str(exc),
                        "policy_number": "",
                        "response": {},
                    }
                )

        return results

    def status(self) -> dict[str, Any]:
        return {
            "primary": self.primary.status() if hasattr(self.primary, "status") else {},
            "fallback": self.fallback.status() if hasattr(self.fallback, "status") else {},
        }

    def _build_payload(
        self,
        bundle: SubmissionBundle,
        memo: UnderwritingMemo,
        quote: QuoteResult,
        org_id: str,
    ) -> PolicySubmissionPayload:
        locations: list[dict[str, Any]] = []
        if bundle.structured:
            for loc in bundle.structured.locations:
                locations.append(
                    {
                        "address": loc.address,
                        "city": loc.city,
                        "state": loc.state,
                        "zip_code": loc.zip_code,
                        "building_value": loc.building_value,
                        "contents_value": loc.contents_value,
                    }
                )

        coverages: list[dict[str, Any]] = []
        if bundle.structured:
            for cov in bundle.structured.coverages:
                coverages.append(
                    {
                        "coverage_type": cov.coverage_type,
                        "limit_amount": cov.limit_amount,
                        "deductible": cov.deductible,
                        "premium": cov.premium,
                    }
                )

        naics = ""
        if bundle.structured and bundle.structured.risk_profile:
            naics = bundle.structured.risk_profile.naics_code or ""

        total_tiv = 0.0
        state = ""
        if bundle.structured and bundle.structured.locations:
            state = bundle.structured.locations[0].state or ""
            total_tiv = sum((loc.building_value or 0) + (loc.contents_value or 0) for loc in bundle.structured.locations)

        period: dict[str, Any] = {}
        if bundle.structured and bundle.structured.policy_period:
            pp = bundle.structured.policy_period
            period = {
                "effective_date": str(getattr(pp, "effective_date", "") or ""),
                "expiration_date": str(getattr(pp, "expiration_date", "") or ""),
            }

        meta = dict(quote.metadata or {})
        components = []
        for c in quote.schedule_modifications or []:
            components.append(
                {
                    "name": getattr(c, "name", ""),
                    "amount": getattr(c, "amount", 0),
                    "basis": getattr(c, "basis", ""),
                    "modifier_pct": getattr(c, "modifier_pct", 0),
                }
            )

        return PolicySubmissionPayload(
            bundle_id=bundle.bundle_id,
            org_id=org_id,
            insured_name=memo.insured_name,
            naics_code=naics,
            state=state,
            tiv=total_tiv,
            base_premium=quote.base_premium,
            adjusted_premium=quote.adjusted_premium,
            uw_decision=memo.decision.value,
            coverages=coverages,
            locations=locations,
            risk_profile=bundle.structured.risk_profile.model_dump() if bundle.structured and bundle.structured.risk_profile else {},
            memo_summary=memo.summary,
            key_findings=[{"title": f.title, "severity": f.severity.value, "description": f.description} for f in memo.key_findings[:10]],
            raw_json=bundle.model_dump(),
            policy_period=period,
            rating={
                "engine": meta.get("rating_engine"),
                "filing_id": meta.get("filing_id"),
                "serff_tracking": meta.get("serff_tracking") or meta.get("filing_id"),
                "carrier_book_id": meta.get("carrier_book_id"),
                "insurance_line": meta.get("insurance_line") or getattr(quote.line, "value", str(quote.line)),
                "rate_per_100_tiv": quote.rate_per_100_tiv,
                "components": components,
                "eligible": quote.eligible,
                "iso_forms": list(meta.get("iso_forms") or []),
                "surplus_lines": dict(meta.get("surplus_lines") or {}),
                "ofac_cleared": meta.get("ofac_cleared"),
                "experience_mod": meta.get("experience_mod"),
                "pas_is_policycenter": False,
            },
            commercial_product_id=str(meta.get("product_id") or ""),
            insurance_line=str(meta.get("insurance_line") or getattr(quote.line, "value", "") or ""),
        )

    def bind_from_summary(self, summary: dict[str, Any], quote_reference: str, org_id: str = "default") -> list[dict[str, Any]]:
        """Bind using the payload captured at quote time — no re-key in PAS."""
        payload_dict = dict(summary.get("pas_bind_payload") or {})
        if not payload_dict:
            quote = summary.get("quote") or {}
            payload_dict = {
                "bundle_id": summary.get("bundle_id") or "",
                "org_id": org_id,
                "insured_name": summary.get("insured_name") or "",
                "state": summary.get("primary_state") or "",
                "tiv": summary.get("tiv") or quote.get("tiv") or 0,
                "base_premium": quote.get("base_premium") or 0,
                "adjusted_premium": quote.get("adjusted_premium") or 0,
                "uw_decision": summary.get("ai_decision") or "",
                "rating": {
                    "filing_id": quote.get("filing_id"),
                    "engine": quote.get("rating_engine"),
                    "serff_tracking": quote.get("serff_tracking"),
                    "insurance_line": quote.get("insurance_line") or summary.get("insurance_line"),
                },
                "subjectivities": list(summary.get("subjectivities") or []),
                "validated_terms": dict(summary.get("validated_terms") or {}),
                "commercial_product_id": summary.get("commercial_product_id") or "",
                "insurance_line": summary.get("insurance_line") or "",
            }
        else:
            payload_dict["subjectivities"] = list(summary.get("subjectivities") or payload_dict.get("subjectivities") or [])
            payload_dict["validated_terms"] = dict(summary.get("validated_terms") or payload_dict.get("validated_terms") or {})
        payload = PolicySubmissionPayload.from_dict(payload_dict)
        results: list[dict[str, Any]] = []
        for adapter in self._adapters:
            try:
                ref = quote_reference or getattr(adapter, "last_quote_reference", "")
                result = adapter.bind_policy(payload, ref)
                results.append(
                    {
                        "system": adapter.get_system_name(),
                        "success": result.success,
                        "policy_number": result.policy_number,
                        "external_reference": result.external_reference,
                        "error": result.error,
                        "response": result.response_payload,
                    }
                )
            except Exception as exc:
                logger.exception("Policy bind failed for %s", adapter.get_system_name())
                results.append(
                    {
                        "system": adapter.get_system_name(),
                        "success": False,
                        "error": str(exc),
                        "policy_number": "",
                        "response": {},
                    }
                )
        return results
