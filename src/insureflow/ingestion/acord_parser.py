from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from typing import Optional

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


class ACORDParser(BaseParser):
    NAMESPACES = {
        "acord": "http://www.acord.org/standards/PC_Surety/ACORD",
        "xsd": "http://www.w3.org/2001/XMLSchema",
    }

    def parse(self, raw_xml: str, submission_id: str) -> StructuredSubmission:
        root = ET.fromstring(raw_xml)
        submission = StructuredSubmission(
            submission_id=submission_id,
            source="broker_acord_xml",
            raw_xml=raw_xml,
            parsed_at=datetime.now(timezone.utc),
        )

        submission.named_insured = self._parse_named_insured(root)
        submission.broker = self._parse_broker(root)
        submission.policy_period = self._parse_policy_period(root)
        submission.coverages = self._parse_coverages(root)
        submission.locations = self._parse_locations(root)
        submission.financial = self._parse_financial(root)
        submission.risk_profile = self._parse_risk_profile(root)

        return submission

    def _find_text(self, root: ET.Element, xpath: str) -> Optional[str]:
        try:
            elem = root.find(xpath, self.NAMESPACES)
            if elem is not None and elem.text:
                return elem.text.strip()
        except Exception:
            pass
        return None

    def _find_float(self, root: ET.Element, xpath: str) -> Optional[float]:
        val = self._find_text(root, xpath)
        if val is not None:
            try:
                return float(val.replace(",", "").replace("$", ""))
            except (ValueError, TypeError):
                pass
        return None

    def _find_int(self, root: ET.Element, xpath: str) -> Optional[int]:
        val = self._find_text(root, xpath)
        if val is not None:
            try:
                return int(val.replace(",", ""))
            except (ValueError, TypeError):
                pass
        return None

    def _find_bool(self, root: ET.Element, xpath: str) -> Optional[bool]:
        val = self._find_text(root, xpath)
        if val is not None:
            return val.lower() in ("yes", "true", "1", "y", "full", "fully")
        return None

    def _find_date(self, root: ET.Element, xpath: str) -> Optional[date]:
        val = self._find_text(root, xpath)
        if val:
            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y%m%d"):
                try:
                    return datetime.strptime(val, fmt).date()
                except ValueError:
                    continue
        return None

    def _parse_named_insured(self, root: ET.Element) -> Optional[NamedInsured]:
        name = self._find_text(
            root,
            ".//acord:NamedInsured/acord:GeneralPartyInfo/acord:NameInfo/acord:CommercialName/acord:Name",
        )
        if not name:
            return None
        return NamedInsured(
            legal_name=name,
            dba=self._find_text(
                root,
                ".//acord:NamedInsured/acord:GeneralPartyInfo/acord:NameInfo/acord:CommercialName/acord:DBA",
            ),
            tax_id=self._find_text(
                root, ".//acord:NamedInsured/acord:GeneralPartyInfo/acord:TaxIdentity/acord:TaxID"
            ),
            entity_type=self._find_text(
                root, ".//acord:NamedInsured/acord:GeneralPartyInfo/acord:BusinessType"
            ),
            address=self._find_text(
                root, ".//acord:NamedInsured/acord:GeneralPartyInfo/acord:Addr1"
            ),
        )

    def _parse_broker(self, root: ET.Element) -> Optional[BrokerInfo]:
        name = self._find_text(
            root,
            ".//acord:Broker/acord:GeneralPartyInfo/acord:NameInfo/acord:CommercialName/acord:Name",
        )
        if not name:
            return None
        return BrokerInfo(
            broker_name=name,
            broker_id=self._find_text(root, ".//acord:Broker/acord:GeneralPartyInfo/acord:ID"),
            contact_name=self._find_text(
                root, ".//acord:Broker/acord:GeneralPartyInfo/acord:ContactName"
            ),
            contact_email=self._find_text(
                root, ".//acord:Broker/acord:GeneralPartyInfo/acord:Email"
            ),
            agency=self._find_text(
                root,
                ".//acord:Broker/acord:GeneralPartyInfo/acord:NameInfo/acord:CommercialName/acord:DBA",
            ),
        )

    def _parse_policy_period(self, root: ET.Element) -> Optional[PolicyPeriod]:
        eff = self._find_date(root, ".//acord:PolicyPeriod/acord:EffectiveDate")
        exp = self._find_date(root, ".//acord:PolicyPeriod/acord:ExpirationDate")
        if not eff or not exp:
            return None
        return PolicyPeriod(effective_date=eff, expiration_date=exp)

    def _parse_coverages(self, root: ET.Element) -> list[CoverageDetail]:
        coverages: list[CoverageDetail] = []
        for cov_elem in root.findall(".//acord:Coverage", self.NAMESPACES):
            cov_type = self._find_text(cov_elem, ".//acord:CoverageType")
            if not cov_type:
                continue
            limit = self._find_float(cov_elem, ".//acord:Limit") or 0.0
            deductible = self._find_float(cov_elem, ".//acord:Deductible") or 0.0
            premium = self._find_float(cov_elem, ".//acord:Premium") or 0.0

            detail = CoverageDetail(
                coverage_type=cov_type,
                limit_amount=limit,
                deductible=deductible,
                premium=premium,
            )

            for sub_elem in cov_elem.findall("acord:CoverageSubLimit", self.NAMESPACES):
                sub_type = self._find_text(sub_elem, ".//acord:SubLimitType")
                sub_amount = self._find_float(sub_elem, ".//acord:SubLimitAmount")
                if sub_type and sub_amount is not None:
                    detail.sublimits[sub_type] = sub_amount

            for end_elem in cov_elem.findall("acord:Endorsement", self.NAMESPACES):
                end_text = end_elem.text
                if end_text and end_text.strip():
                    detail.endorsements.append(end_text.strip())

            coverages.append(detail)
        return coverages

    def _parse_locations(self, root: ET.Element) -> list[LocationData]:
        locations: list[LocationData] = []
        for loc_elem in root.findall(".//acord:Location", self.NAMESPACES):
            addr = self._find_text(loc_elem, ".//acord:Addr1") or ""
            city = self._find_text(loc_elem, ".//acord:City") or ""
            state = self._find_text(loc_elem, ".//acord:StateProvCd") or ""
            zip_code = self._find_text(loc_elem, ".//acord:PostalCode") or ""
            if not addr:
                continue
            locations.append(
                LocationData(
                    address=addr,
                    city=city,
                    state=state,
                    zip_code=zip_code,
                    building_occupancy=self._find_text(loc_elem, ".//acord:Occupancy"),
                    year_built=self._find_int(loc_elem, ".//acord:YearBuilt"),
                    square_footage=self._find_float(loc_elem, ".//acord:SquareFootage"),
                    construction_type=self._find_text(loc_elem, ".//acord:ConstructionType"),
                    protection_class=self._find_int(loc_elem, ".//acord:ProtectionClass"),
                    building_value=self._find_float(loc_elem, ".//acord:EstimatedValue"),
                    contents_value=self._find_float(loc_elem, ".//acord:ContentsValue"),
                    bi_value=self._find_float(loc_elem, ".//acord:BusinessIncomeValue"),
                )
            )
        return locations

    def _parse_financial(self, root: ET.Element) -> Optional[FinancialData]:
        revenue = self._find_float(root, ".//acord:FinancialInfo/acord:AnnualRevenue")
        if revenue is None:
            return None
        return FinancialData(
            annual_revenue=revenue,
            payroll=self._find_float(root, ".//acord:FinancialInfo/acord:Payroll"),
            total_asset_value=self._find_float(root, ".//acord:FinancialInfo/acord:TotalAssets"),
            credit_rating=self._find_text(root, ".//acord:FinancialInfo/acord:CreditRating"),
        )

    def _parse_risk_profile(self, root: ET.Element) -> Optional[RiskProfile]:
        naics = self._find_text(root, ".//acord:Risk/acord:NAICSCode")
        if not naics:
            return None
        return RiskProfile(
            naics_code=naics,
            sic_code=self._find_text(root, ".//acord:Risk/acord:SICCode"),
            business_description=self._find_text(root, ".//acord:Risk/acord:BusinessDescription"),
            occupancy_type=self._find_text(root, ".//acord:Risk/acord:Occupancy"),
            construction_type=self._find_text(root, ".//acord:Risk/acord:ConstructionType"),
            protection_class=self._find_int(root, ".//acord:Risk/acord:ProtectionClass"),
            sprinklered=self._find_bool(root, ".//acord:Risk/acord:Sprinklered"),
            number_of_stories=self._find_int(root, ".//acord:Risk/acord:NumberOfStories"),
            total_square_footage=self._find_float(root, ".//acord:Risk/acord:TotalSquareFootage"),
        )
