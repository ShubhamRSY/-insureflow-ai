from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any, Optional

from insureflow.ingestion.base import BaseParser
from insureflow.models.submissions import (
    BrokerInfo,
    CoverageDetail,
    FinancialData,
    LocationData,
    NamedInsured,
    PolicyPeriod,
    RiskProfile,
    StructuredSubmission,
)


class JSONBrokerParser(BaseParser):
    FIELD_MAP = {
        "legal_name": ["legalName", "legal_name", "name", "insuredName", "companyName"],
        "dba": ["dba", "doingBusinessAs", "tradingAs"],
        "tax_id": ["taxId", "taxID", "tax_id", "ein", "fein", "employerId"],
        "entity_type": ["entityType", "entity_type", "businessType", "business_type"],
        "address": ["address", "addr1", "streetAddress", "street", "mailingAddress"],
    }

    COVERAGE_MAP = {
        "type": ["type", "coverageType", "coverage_type", "line", "lineOfBusiness"],
        "limit": ["limit", "limitAmount", "limit_amount", "liabilityLimit", "coverageLimit"],
        "deductible": ["deductible", "deductibleAmount", "deductible_amount", "selfInsuredRetention"],
        "premium": ["premium", "annualPremium", "premium_amount", "totalPremium"],
    }

    LOCATION_MAP = {
        "address": ["address", "addr1", "street", "streetAddress", "siteAddress"],
        "city": ["city", "cityName", "municipality"],
        "state": ["state", "stateProvCd", "stateCode", "region"],
        "zip": ["zip", "zipCode", "postalCode", "postcode"],
    }

    def parse(self, raw_json: str, submission_id: str) -> StructuredSubmission:
        data = json.loads(raw_json)
        submission = StructuredSubmission(
            submission_id=submission_id,
            source="broker_api_json",
            raw_json=raw_json,
            parsed_at=datetime.now(timezone.utc),
        )

        submission.named_insured = self._parse_named_insured(data)
        submission.broker = self._parse_broker(data)
        submission.policy_period = self._parse_policy_period(data)
        submission.coverages = self._parse_coverages(data)
        submission.locations = self._parse_locations(data)
        submission.financial = self._parse_financial(data)
        submission.risk_profile = self._parse_risk_profile(data)
        submission.schedule_of_values = []

        return submission

    @staticmethod
    def _get_nested(data: dict, *keys: str, default: Any = None) -> Any:
        for key in keys:
            if "." in key:
                parts = key.split(".")
                current = data
                for part in parts:
                    if isinstance(current, dict):
                        current = current.get(part)
                    else:
                        return default
                if current is not None:
                    return current
            else:
                if key in data and data[key] is not None:
                    return data[key]
        return default

    @staticmethod
    def _first_match(data: dict, candidates: list[str], default: Any = None) -> Any:
        for key in candidates:
            for dot_key in [key, f"insured.{key}", f"applicant.{key}", f"submission.{key}"]:
                val = JSONBrokerParser._get_nested(data, dot_key)
                if val is not None:
                    return val
        return default

    def _parse_named_insured(self, data: dict) -> Optional[NamedInsured]:
        insured_data = data.get("insured") or data.get("applicant") or data.get("namedInsured") or data

        if isinstance(insured_data, str):
            return NamedInsured(legal_name=insured_data)

        if not isinstance(insured_data, dict):
            return None

        legal_name = self._first_match(insured_data, ["legalName", "legal_name", "name", "companyName", "businessName"])
        if not legal_name:
            for top_key in ["legalName", "legal_name", "name", "companyName", "submissionName"]:
                val = data.get(top_key)
                if val:
                    legal_name = val
                    break

        if not legal_name:
            return None

        return NamedInsured(
            legal_name=str(legal_name),
            dba=str(self._first_match(insured_data, ["dba", "doingBusinessAs"])) if self._first_match(insured_data, ["dba", "doingBusinessAs"]) else None,
            tax_id=str(self._first_match(insured_data, ["taxId", "taxID", "ein", "fein"])) if self._first_match(insured_data, ["taxId", "taxID", "ein", "fein"]) else None,
            entity_type=str(self._first_match(insured_data, ["entityType", "businessType", "entity_type"])) if self._first_match(insured_data, ["entityType", "businessType", "entity_type"]) else None,
            address=str(self._first_match(insured_data, ["address", "streetAddress", "addr1"])) if self._first_match(insured_data, ["address", "streetAddress", "addr1"]) else None,
        )

    def _parse_broker(self, data: dict) -> Optional[BrokerInfo]:
        broker_data = data.get("broker") or data.get("agency") or data.get("producer") or {}

        if not isinstance(broker_data, dict):
            return None

        name = self._first_match(broker_data, ["name", "brokerName", "agencyName", "broker_name"])
        if not name:
            return None

        return BrokerInfo(
            broker_name=str(name),
            broker_id=str(self._first_match(broker_data, ["id", "brokerId", "licenseNumber"])) if self._first_match(broker_data, ["id", "brokerId", "licenseNumber"]) else None,
            contact_name=str(self._first_match(broker_data, ["contactName", "contact", "agentName"])) if self._first_match(broker_data, ["contactName", "contact", "agentName"]) else None,
            contact_email=str(self._first_match(broker_data, ["email", "contactEmail"])) if self._first_match(broker_data, ["email", "contactEmail"]) else None,
        )

    def _parse_policy_period(self, data: dict) -> Optional[PolicyPeriod]:
        policy = data.get("policy") or data.get("policyPeriod") or data

        eff = self._first_match(policy, ["effectiveDate", "effective_date", "inceptionDate", "policyEffective"])
        exp = self._first_match(policy, ["expirationDate", "expiration_date", "expiryDate", "policyExpiration"])

        if not eff or not exp:
            return None

        def parse_date(val: str) -> Optional[date]:
            if isinstance(val, date):
                return val
            if isinstance(val, datetime):
                return val.date()
            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y%m%d", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(str(val)[:10], fmt).date()
                except ValueError:
                    continue
            return None

        eff_date = parse_date(eff)
        exp_date = parse_date(exp)
        if not eff_date or not exp_date:
            return None

        return PolicyPeriod(effective_date=eff_date, expiration_date=exp_date)

    def _parse_coverages(self, data: dict) -> list[CoverageDetail]:
        coverages: list[CoverageDetail] = []
        raw = data.get("coverages") or data.get("coverage") or data.get("lines") or data.get("policyLines") or []

        if isinstance(raw, dict):
            raw = [raw]

        for cov in raw:
            if not isinstance(cov, dict):
                continue
            cov_type = self._first_match(cov, ["type", "coverageType", "coverage_type", "lineOfBusiness"])
            if not cov_type:
                continue

            limit = self._first_match(cov, ["limit", "limitAmount", "liabilityLimit", "coverageLimit"])
            deductible = self._first_match(cov, ["deductible", "deductibleAmount", "selfInsuredRetention"])
            premium = self._first_match(cov, ["premium", "annualPremium", "totalPremium"])

            detail = CoverageDetail(
                coverage_type=str(cov_type),
                limit_amount=float(limit) if limit else 0.0,
                deductible=float(deductible) if deductible else 0.0,
                premium=float(premium) if premium else 0.0,
            )

            sublimits_raw = cov.get("sublimits") or cov.get("subLimits") or {}
            if isinstance(sublimits_raw, dict):
                for k, v in sublimits_raw.items():
                    try:
                        detail.sublimits[str(k)] = float(v)
                    except (ValueError, TypeError):
                        pass

            endorsements_raw = cov.get("endorsements") or cov.get("forms") or []
            if isinstance(endorsements_raw, list):
                detail.endorsements = [str(e) for e in endorsements_raw]

            coverages.append(detail)

        return coverages

    def _parse_locations(self, data: dict) -> list[LocationData]:
        locations: list[LocationData] = []
        raw = data.get("locations") or data.get("location") or data.get("premises") or data.get("sites") or []

        if isinstance(raw, dict):
            raw = [raw]

        for loc in raw:
            if not isinstance(loc, dict):
                continue
            addr = self._first_match(loc, ["address", "addr1", "streetAddress", "street"])
            if not addr:
                continue

            locations.append(
                LocationData(
                    address=str(addr),
                    city=str(self._first_match(loc, ["city"])) if self._first_match(loc, ["city"]) else "",
                    state=str(self._first_match(loc, ["state", "stateProvCd", "stateCode"])) if self._first_match(loc, ["state", "stateProvCd", "stateCode"]) else "",
                    zip_code=str(self._first_match(loc, ["zip", "zipCode", "postalCode"])) if self._first_match(loc, ["zip", "zipCode", "postalCode"]) else "",
                    building_occupancy=str(self._first_match(loc, ["occupancy", "occupancyType", "buildingUse"])) if self._first_match(loc, ["occupancy", "occupancyType", "buildingUse"]) else None,
                    year_built=int(self._first_match(loc, ["yearBuilt", "constructionYear", "year_built"])) if self._first_match(loc, ["yearBuilt", "constructionYear", "year_built"]) else None,
                    square_footage=float(self._first_match(loc, ["squareFootage", "sqft", "totalArea"])) if self._first_match(loc, ["squareFootage", "sqft", "totalArea"]) else None,
                    construction_type=str(self._first_match(loc, ["constructionType", "construction", "frameType"])) if self._first_match(loc, ["constructionType", "construction", "frameType"]) else None,
                )
            )

        return locations

    def _parse_financial(self, data: dict) -> Optional[FinancialData]:
        fin = data.get("financial") or data.get("financialInfo") or data

        revenue = self._first_match(fin, ["annualRevenue", "revenue", "totalRevenue", "grossRevenue"])
        payroll = self._first_match(fin, ["payroll", "annualPayroll", "totalPayroll"])
        assets = self._first_match(fin, ["totalAssets", "assets", "totalAssetValue"])
        rating = self._first_match(fin, ["creditRating", "credit_rating", "rating"])

        if not revenue:
            return None

        return FinancialData(
            annual_revenue=float(revenue) if revenue else None,
            payroll=float(payroll) if payroll else None,
            total_asset_value=float(assets) if assets else None,
            credit_rating=str(rating) if rating else None,
        )

    def _parse_risk_profile(self, data: dict) -> Optional[RiskProfile]:
        risk = data.get("risk") or data.get("riskProfile") or data.get("classification") or data

        naics = self._first_match(risk, ["naicsCode", "naics", "naics_code"])
        if not naics:
            return None

        return RiskProfile(
            naics_code=str(naics),
            sic_code=str(self._first_match(risk, ["sicCode", "sic", "sic_code"])) if self._first_match(risk, ["sicCode", "sic", "sic_code"]) else None,
            business_description=str(self._first_match(risk, ["businessDescription", "description", "businessDesc"])) if self._first_match(risk, ["businessDescription", "description", "businessDesc"]) else None,
            occupancy_type=str(self._first_match(risk, ["occupancy", "occupancyType"])) if self._first_match(risk, ["occupancy", "occupancyType"]) else None,
            construction_type=str(self._first_match(risk, ["constructionType", "construction"])) if self._first_match(risk, ["constructionType", "construction"]) else None,
            protection_class=int(self._first_match(risk, ["protectionClass", "pc", "isoClass"])) if self._first_match(risk, ["protectionClass", "pc", "isoClass"]) else None,
            number_of_stories=int(self._first_match(risk, ["numberOfStories", "stories", "floors"])) if self._first_match(risk, ["numberOfStories", "stories", "floors"]) else None,
            total_square_footage=float(self._first_match(risk, ["totalSquareFootage", "totalSqft", "buildingArea"])) if self._first_match(risk, ["totalSquareFootage", "totalSqft", "buildingArea"]) else None,
        )
