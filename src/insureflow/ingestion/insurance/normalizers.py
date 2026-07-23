"""Normalize raw data from 23 enterprise source systems into StructuredSubmission.

Each source system (Salesforce, Guidewire, Applied Epic, etc.) returns data in its
own format. This module provides source-specific normalizers that map system-proprietary
field names and structures onto the common StructuredSubmission schema used by the
underwriting pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from insureflow.models.submissions import (
    BrokerInfo,
    ClaimRecord,
    ClaimStatus,
    CoverageDetail,
    FinancialData,
    LocationData,
    LossRunData,
    NamedInsured,
    PolicyPeriod,
    RiskProfile,
    StructuredSubmission,
)


def _parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    s = str(value).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).replace(",", "").replace("$", "").replace("%", "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _to_int(value: Any) -> Optional[int]:
    f = _to_float(value)
    return int(f) if f is not None else None


def _nested(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return None
    return current


def _find_claim_status(raw: str) -> ClaimStatus:
    low = raw.lower()
    if "open" in low:
        return ClaimStatus.OPEN
    if "subrog" in low:
        return ClaimStatus.SUBROGATION
    if "litig" in low:
        return ClaimStatus.PENDING_LITIGATION
    return ClaimStatus.CLOSED


class SourceNormalizer(ABC):
    """Base class for source-specific data normalizers."""

    source_id: str = ""
    source_name: str = ""

    @abstractmethod
    def normalize(self, raw: dict[str, Any], submission_id: str | None = None) -> StructuredSubmission: ...

    def _make_submission(self, submission_id: str | None = None) -> StructuredSubmission:
        return StructuredSubmission(
            submission_id=submission_id or f"norm-{uuid4().hex[:12]}",
            source=self.source_id,
            received_at=datetime.now(timezone.utc),
        )


# ── Cloud Storage (5) ────────────────────────────────────────────


class GoogleDriveNormalizer(SourceNormalizer):
    source_id = "google-drive"
    source_name = "Google Drive"

    def normalize(self, raw: dict[str, Any], submission_id: str | None = None) -> StructuredSubmission:
        sub = self._make_submission(submission_id)
        meta = raw.get("metadata", raw)
        sub.named_insured = NamedInsured(
            legal_name=meta.get("insured_name", meta.get("legal_name", "Unknown")),
            tax_id=meta.get("tax_id"),
        )
        if meta.get("broker_name"):
            sub.broker = BrokerInfo(broker_name=meta["broker_name"], broker_id=meta.get("broker_id"))
        eff = _parse_date(meta.get("effective_date") or meta.get("policy_start"))
        exp = _parse_date(meta.get("expiration_date") or meta.get("policy_end"))
        if eff and exp:
            sub.policy_period = PolicyPeriod(effective_date=eff, expiration_date=exp)
        for loc in raw.get("locations", meta.get("locations", [])):
            sub.locations.append(
                LocationData(
                    address=loc.get("address", ""),
                    city=loc.get("city", ""),
                    state=loc.get("state", ""),
                    zip_code=loc.get("zip", loc.get("zip_code", "")),
                    year_built=_to_int(loc.get("year_built")),
                    square_footage=_to_float(loc.get("square_footage")),
                )
            )
        for cov in raw.get("coverages", meta.get("coverages", [])):
            sub.coverages.append(
                CoverageDetail(
                    coverage_type=cov.get("type", cov.get("coverage_type", "")),
                    limit_amount=_to_float(cov.get("limit", cov.get("limit_amount"))) or 0,
                    deductible=_to_float(cov.get("deductible")) or 0,
                    premium=_to_float(cov.get("premium", cov.get("annual_premium"))) or 0,
                )
            )
        fin = raw.get("financial", meta.get("financial", {}))
        if fin:
            sub.financial = FinancialData(
                annual_revenue=_to_float(fin.get("annual_revenue")),
                payroll=_to_float(fin.get("payroll")),
                total_asset_value=_to_float(fin.get("total_assets")),
            )
        risk = raw.get("risk", meta.get("risk", {}))
        if risk:
            sub.risk_profile = RiskProfile(
                naics_code=str(risk.get("naics_code", risk.get("naicsCode", ""))),
                sic_code=str(risk.get("sic_code", "")),
                construction_type=risk.get("construction_type"),
                occupancy_type=risk.get("occupancy"),
                protection_class=_to_int(risk.get("protection_class")),
            )
        return sub


class SharePointNormalizer(GoogleDriveNormalizer):
    source_id = "sharepoint"
    source_name = "SharePoint / OneDrive"


class S3BucketNormalizer(GoogleDriveNormalizer):
    source_id = "s3-bucket"
    source_name = "AWS S3"


class AzureBlobNormalizer(GoogleDriveNormalizer):
    source_id = "azure-blob"
    source_name = "Azure Blob Storage"


class BoxNormalizer(GoogleDriveNormalizer):
    source_id = "box"
    source_name = "Box Enterprise"


# ── Submission Intake (4) ────────────────────────────────────────


class EmailInboxNormalizer(SourceNormalizer):
    source_id = "email-inbox"
    source_name = "Email Inbox"

    def normalize(self, raw: dict[str, Any], submission_id: str | None = None) -> StructuredSubmission:
        sub = self._make_submission(submission_id)
        email = raw.get("email", raw)
        sub.named_insured = NamedInsured(
            legal_name=email.get("insured_name", email.get("from_name", "Unknown")),
            tax_id=email.get("tax_id"),
        )
        if email.get("broker_name") or email.get("from_name"):
            sub.broker = BrokerInfo(
                broker_name=email.get("broker_name", email.get("from_name", "")),
                contact_email=email.get("from", email.get("from_email")),
            )
        for att in email.get("attachments", raw.get("attachments", [])):
            content = att.get("content", "")
            if "acord" in att.get("filename", "").lower() or "<acord" in content[:200].lower():
                from insureflow.ingestion.acord_parser import ACORDParser

                try:
                    parsed = ACORDParser().parse(content, submission_id or "email-001")
                    if parsed.named_insured:
                        sub.named_insured = parsed.named_insured
                    if parsed.broker:
                        sub.broker = parsed.broker
                    if parsed.policy_period:
                        sub.policy_period = parsed.policy_period
                    sub.coverages = parsed.coverages
                    sub.locations = parsed.locations
                    if parsed.risk_profile:
                        sub.risk_profile = parsed.risk_profile
                    sub.raw_xml = content
                except Exception:
                    pass
        eff = _parse_date(email.get("effective_date"))
        exp = _parse_date(email.get("expiration_date"))
        if eff and exp:
            sub.policy_period = PolicyPeriod(effective_date=eff, expiration_date=exp)
        return sub


class SFTPNormalizer(SourceNormalizer):
    source_id = "sftp"
    source_name = "SFTP / Broker Portal"

    def normalize(self, raw: dict[str, Any], submission_id: str | None = None) -> StructuredSubmission:
        file_data = raw.get("file", raw)
        content = file_data.get("content", "")
        if file_data.get("format") == "acord_xml" or content.strip().startswith("<?xml") or "<acord" in content[:500].lower():
            from insureflow.ingestion.acord_parser import ACORDParser

            try:
                sub = ACORDParser().parse(content, submission_id or "sftp-001")
                sub.source = self.source_id
                return sub
            except Exception:
                pass
        if file_data.get("format") == "json" or content.strip().startswith("{"):
            from insureflow.ingestion.json_parser import JSONBrokerParser

            try:
                sub = JSONBrokerParser().parse(content, submission_id or "sftp-001")
                sub.source = self.source_id
                return sub
            except Exception:
                pass
        sub = self._make_submission(submission_id)
        sub.named_insured = NamedInsured(legal_name=file_data.get("insured_name", "Unknown"))
        return sub


class BoldPenguinNormalizer(SourceNormalizer):
    source_id = "bold-penguin"
    source_name = "Bold Penguin"

    def normalize(self, raw: dict[str, Any], submission_id: str | None = None) -> StructuredSubmission:
        sub = self._make_submission(submission_id)
        app = raw.get("application", raw)
        sub.named_insured = NamedInsured(
            legal_name=app.get("business_name", app.get("legal_name", "Unknown")),
            dba=app.get("dba"),
            tax_id=app.get("ein", app.get("tax_id")),
            entity_type=app.get("entity_type", app.get("business_type")),
        )
        agent = app.get("agent", app.get("broker", {}))
        if agent:
            sub.broker = BrokerInfo(
                broker_name=agent.get("name", agent.get("agent_name", "")),
                broker_id=agent.get("id", agent.get("agent_id")),
                contact_email=agent.get("email"),
            )
        eff = _parse_date(app.get("effective_date") or app.get("policy_start_date"))
        exp = _parse_date(app.get("expiration_date") or app.get("policy_end_date"))
        if eff and exp:
            sub.policy_period = PolicyPeriod(effective_date=eff, expiration_date=exp)
        for loc in app.get("locations", []):
            sub.locations.append(
                LocationData(
                    address=loc.get("street_address", loc.get("address", "")),
                    city=loc.get("city", ""),
                    state=loc.get("state", ""),
                    zip_code=loc.get("zip_code", loc.get("zip", "")),
                    year_built=_to_int(loc.get("year_built")),
                    square_footage=_to_float(loc.get("square_footage")),
                    building_value=_to_float(loc.get("building_value")),
                )
            )
        for cov in app.get("coverages", app.get("requested_coverages", [])):
            sub.coverages.append(
                CoverageDetail(
                    coverage_type=cov.get("type", cov.get("coverage_type", "")),
                    limit_amount=_to_float(cov.get("limit", cov.get("limit_amount"))) or 0,
                    deductible=_to_float(cov.get("deductible")) or 0,
                    premium=_to_float(cov.get("premium")) or 0,
                )
            )
        risk = app.get("risk", app.get("business_info", {}))
        if risk:
            sub.risk_profile = RiskProfile(
                naics_code=str(risk.get("naics_code", risk.get("naics", ""))),
                business_description=risk.get("description", risk.get("business_description")),
                occupancy_type=risk.get("occupancy"),
                construction_type=risk.get("construction"),
            )
        fin = app.get("financial", {})
        if fin:
            sub.financial = FinancialData(
                annual_revenue=_to_float(fin.get("annual_revenue", fin.get("revenue"))),
                payroll=_to_float(fin.get("payroll")),
            )
        return sub


class IVANSDownloadNormalizer(SourceNormalizer):
    source_id = "ivans-download"
    source_name = "IVANS Download"

    def normalize(self, raw: dict[str, Any], submission_id: str | None = None) -> StructuredSubmission:
        transaction = raw.get("transaction", raw)
        content = transaction.get("content", "")
        if transaction.get("format") == "al3" or content.strip().startswith("01"):
            return self._parse_al3(content, submission_id)
        if transaction.get("format") == "acord_xml" or "<acord" in content[:500].lower():
            from insureflow.ingestion.acord_parser import ACORDParser

            try:
                return ACORDParser().parse(content, submission_id or "ivans-001")
            except Exception:
                pass
        sub = self._make_submission(submission_id)
        sub.named_insured = NamedInsured(
            legal_name=transaction.get("insured_name", transaction.get("entity_name", "Unknown")),
            tax_id=transaction.get("ein"),
        )
        if transaction.get("broker_name"):
            sub.broker = BrokerInfo(broker_name=transaction["broker_name"])
        eff = _parse_date(transaction.get("effective_date"))
        exp = _parse_date(transaction.get("expiration_date"))
        if eff and exp:
            sub.policy_period = PolicyPeriod(effective_date=eff, expiration_date=exp)
        return sub

    def _parse_al3(self, content: str, submission_id: str | None) -> StructuredSubmission:
        sub = self._make_submission(submission_id)
        lines = content.split("\n")
        for line in lines:
            if len(line) < 5:
                continue
            tag = line[:3].strip()
            value = line[5:].strip() if len(line) > 5 else ""
            if tag == "QTE" or tag == "POL":
                eff_str = value[0:8] if len(value) >= 8 else ""
                exp_str = value[8:16] if len(value) >= 16 else ""
                if eff_str and exp_str:
                    eff = _parse_date(eff_str)
                    exp = _parse_date(exp_str)
                    if eff and exp:
                        sub.policy_period = PolicyPeriod(effective_date=eff, expiration_date=exp)
            elif tag == "NAM":
                name = value.split("|")[0] if "|" in value else value
                sub.named_insured = NamedInsured(legal_name=name.strip() or "Unknown")
        return sub


# ── Industry Exchange (2) ────────────────────────────────────────


class ACORDAL3Normalizer(SourceNormalizer):
    source_id = "acord-al3"
    source_name = "ACORD AL3 / XML Hub"

    def normalize(self, raw: dict[str, Any], submission_id: str | None = None) -> StructuredSubmission:
        content = raw.get("content", raw.get("xml", ""))
        if isinstance(content, str) and ("<acord" in content[:500].lower() or "<?xml" in content[:100].lower()):
            from insureflow.ingestion.acord_parser import ACORDParser

            try:
                sub = ACORDParser().parse(content, submission_id or "acord-al3-001")
                sub.source = self.source_id
                return sub
            except Exception:
                pass
        sub = IVANSDownloadNormalizer()._parse_al3(content, submission_id)
        sub.source = self.source_id
        return sub


# ── Policy Admin (3) ─────────────────────────────────────────────


class GuidewireNormalizer(SourceNormalizer):
    source_id = "guidewire-policycenter"
    source_name = "Guidewire PolicyCenter"

    def normalize(self, raw: dict[str, Any], submission_id: str | None = None) -> StructuredSubmission:
        sub = self._make_submission(submission_id)
        policy = raw.get("policy", raw.get("submission", raw))
        ins = policy.get("insured", policy.get("namedInsured", {}))
        sub.named_insured = NamedInsured(
            legal_name=ins.get("displayName", ins.get("legalName", ins.get("name", "Unknown"))),
            tax_id=ins.get("taxId", ins.get("ssn")),
            entity_type=ins.get("entityType"),
            address=self._format_address(ins.get("primaryAddress", ins.get("address", {}))),
        )
        broker = policy.get("producer", policy.get("broker", policy.get("agent", {})))
        if broker:
            sub.broker = BrokerInfo(
                broker_name=broker.get("displayName", broker.get("name", "")),
                broker_id=broker.get("id", broker.get("producerCode")),
                contact_email=broker.get("email"),
                agency=broker.get("agencyName", broker.get("companyName")),
            )
        period = policy.get("policyPeriod", policy.get("period", {}))
        eff = _parse_date(period.get("expirationDate", period.get("startDate")))
        exp = _parse_date(period.get("expirationDate"))
        if eff and exp:
            sub.policy_period = PolicyPeriod(effective_date=eff, expiration_date=exp)
        for cov in policy.get("coverages", policy.get("lines", [])):
            sub.coverages.append(
                CoverageDetail(
                    coverage_type=cov.get("coverageType", cov.get("line", cov.get("type", ""))),
                    limit_amount=_to_float(cov.get("limitAmount", cov.get("limit"))) or 0,
                    deductible=_to_float(cov.get("deductibleAmount", cov.get("deductible"))) or 0,
                    premium=_to_float(cov.get("premium", cov.get("totalPremium"))) or 0,
                    sublimits={k: _to_float(v) or 0 for k, v in cov.get("sublimits", {}).items()},
                )
            )
        for loc in policy.get("locations", []):
            addr = loc.get("address", loc)
            sub.locations.append(
                LocationData(
                    address=addr.get("addressLine1", addr.get("address", "")),
                    city=addr.get("city", ""),
                    state=addr.get("state", addr.get("stateCode", "")),
                    zip_code=addr.get("postalCode", addr.get("zipCode", addr.get("zip", ""))),
                    year_built=_to_int(loc.get("yearBuilt")),
                    square_footage=_to_float(loc.get("squareFeet", loc.get("squareFootage"))),
                    construction_type=loc.get("constructionType"),
                    building_occupancy=loc.get("occupancyType", loc.get("occupancy")),
                    building_value=_to_float(loc.get("buildingValue")),
                    contents_value=_to_float(loc.get("contentsValue")),
                )
            )
        fin = policy.get("financial", policy.get("financialInfo", {}))
        if fin:
            sub.financial = FinancialData(
                annual_revenue=_to_float(fin.get("annualRevenue", fin.get("revenue"))),
                payroll=_to_float(fin.get("payroll")),
                total_asset_value=_to_float(fin.get("totalAssetValue", fin.get("totalAssets"))),
            )
        risk = policy.get("risk", policy.get("riskProfile", {}))
        if risk:
            sub.risk_profile = RiskProfile(
                naics_code=str(risk.get("naicsCode", risk.get("naics", ""))),
                sic_code=str(risk.get("sicCode", "")),
                business_description=risk.get("description"),
                construction_type=risk.get("constructionType"),
                occupancy_type=risk.get("occupancyType"),
                protection_class=_to_int(risk.get("protectionClass")),
                sprinklered=risk.get("sprinklered"),
                number_of_stories=_to_int(risk.get("stories", risk.get("numberOfStories"))),
                total_square_footage=_to_float(risk.get("totalSquareFootage")),
            )
        return sub

    def _format_address(self, addr: dict[str, Any]) -> str:
        if not addr:
            return ""
        parts = [addr.get("addressLine1", ""), addr.get("city", ""), addr.get("state", ""), addr.get("postalCode", "")]
        return ", ".join(p for p in parts if p)


class DuckCreekNormalizer(GuidewireNormalizer):
    source_id = "duck-creek"
    source_name = "Duck Creek Policy"


class MajescoNormalizer(GuidewireNormalizer):
    source_id = "majesco-policy"
    source_name = "Majesco Policy"


# ── Agency Management (2) ───────────────────────────────────────


class AppliedEpicNormalizer(SourceNormalizer):
    source_id = "applied-epic"
    source_name = "Applied Epic (Vertafore)"

    def normalize(self, raw: dict[str, Any], submission_id: str | None = None) -> StructuredSubmission:
        sub = self._make_submission(submission_id)
        epic = raw.get("submission", raw)
        client = epic.get("client", epic.get("insured", {}))
        sub.named_insured = NamedInsured(
            legal_name=client.get("companyName", client.get("name", client.get("legalName", "Unknown"))),
            dba=client.get("dba"),
            tax_id=client.get("taxId", client.get("ein")),
            entity_type=client.get("entityType", client.get("businessType")),
        )
        agent = epic.get("agent", epic.get("producer", {}))
        if agent:
            sub.broker = BrokerInfo(
                broker_name=agent.get("agentName", agent.get("name", "")),
                broker_id=agent.get("agentCode", agent.get("code")),
                contact_name=agent.get("contactName"),
                contact_email=agent.get("email"),
                agency=agent.get("agencyName"),
            )
        policy = epic.get("policy", {})
        eff = _parse_date(policy.get("effectiveDate"))
        exp = _parse_date(policy.get("expirationDate"))
        if eff and exp:
            sub.policy_period = PolicyPeriod(effective_date=eff, expiration_date=exp)
        for loc in epic.get("locations", client.get("locations", [])):
            sub.locations.append(
                LocationData(
                    address=loc.get("address", loc.get("street", "")),
                    city=loc.get("city", ""),
                    state=loc.get("state", ""),
                    zip_code=loc.get("zip", loc.get("zipCode", "")),
                    year_built=_to_int(loc.get("yearBuilt")),
                    square_footage=_to_float(loc.get("squareFootage", loc.get("sqft"))),
                )
            )
        for cov in epic.get("coverages", policy.get("coverages", [])):
            sub.coverages.append(
                CoverageDetail(
                    coverage_type=cov.get("classCode", cov.get("type", cov.get("coverageType", ""))),
                    limit_amount=_to_float(cov.get("limit", cov.get("limitAmount"))) or 0,
                    deductible=_to_float(cov.get("deductible")) or 0,
                    premium=_to_float(cov.get("premium", cov.get("annualPremium"))) or 0,
                )
            )
        fin = epic.get("financial", client.get("financial", {}))
        if fin:
            sub.financial = FinancialData(
                annual_revenue=_to_float(fin.get("annualRevenue", fin.get("revenue"))),
                payroll=_to_float(fin.get("payroll")),
                total_asset_value=_to_float(fin.get("totalAssets")),
            )
        risk = epic.get("risk", epic.get("riskProfile", {}))
        if risk:
            sub.risk_profile = RiskProfile(
                naics_code=str(risk.get("naicsCode", risk.get("naics", ""))),
                sic_code=str(risk.get("sicCode", "")),
                business_description=risk.get("description"),
                construction_type=risk.get("construction"),
                occupancy_type=risk.get("occupancy"),
                protection_class=_to_int(risk.get("protectionClass")),
            )
        return sub


class HawkSoftNormalizer(AppliedEpicNormalizer):
    source_id = "hawksoft"
    source_name = "HawkSoft AMS"


# ── CRM / Distribution (1) ──────────────────────────────────────


class SalesforceNormalizer(SourceNormalizer):
    source_id = "salesforce-crm"
    source_name = "Salesforce"

    def normalize(self, raw: dict[str, Any], submission_id: str | None = None) -> StructuredSubmission:
        sub = self._make_submission(submission_id)
        opp = raw.get("opportunity", raw.get("record", raw))
        account = opp.get("account", opp.get("Insured__r", opp.get("Account", {})))
        sub.named_insured = NamedInsured(
            legal_name=account.get("Name", account.get("legal_name", opp.get("Insured_Name__c", "Unknown"))),
            tax_id=account.get("Tax_ID__c", account.get("EIN__c")),
            entity_type=account.get("Entity_Type__c"),
        )
        broker = opp.get("broker", opp.get("Broker__r", opp.get("Producer__r", {})))
        if broker:
            sub.broker = BrokerInfo(
                broker_name=broker.get("Name", broker.get("name", "")),
                broker_id=broker.get("Id", broker.get("id")),
                contact_email=broker.get("Email", broker.get("email")),
                agency=broker.get("Agency_Name__c", broker.get("agency")),
            )
        eff = _parse_date(opp.get("Effective_Date__c", opp.get("effective_date")))
        exp = _parse_date(opp.get("Expiration_Date__c", opp.get("expiration_date")))
        if eff and exp:
            sub.policy_period = PolicyPeriod(effective_date=eff, expiration_date=exp)
        for loc in opp.get("locations", opp.get("Locations__r", [])):
            sub.locations.append(
                LocationData(
                    address=loc.get("Address__c", loc.get("address", "")),
                    city=loc.get("City__c", loc.get("city", "")),
                    state=loc.get("State__c", loc.get("state", "")),
                    zip_code=loc.get("Zip__c", loc.get("zip", "")),
                    year_built=_to_int(loc.get("Year_Built__c")),
                    square_footage=_to_float(loc.get("Square_Footage__c")),
                )
            )
        for cov in opp.get("coverages", opp.get("Coverages__r", [])):
            sub.coverages.append(
                CoverageDetail(
                    coverage_type=cov.get("Type__c", cov.get("type", "")),
                    limit_amount=_to_float(cov.get("Limit__c", cov.get("limit"))) or 0,
                    deductible=_to_float(cov.get("Deductible__c", cov.get("deductible"))) or 0,
                    premium=_to_float(cov.get("Premium__c", cov.get("premium"))) or 0,
                )
            )
        fin = opp.get("financial", opp.get("Financial__c", {}))
        if fin:
            sub.financial = FinancialData(
                annual_revenue=_to_float(fin.get("Annual_Revenue__c", fin.get("annual_revenue"))),
                payroll=_to_float(fin.get("Payroll__c", fin.get("payroll"))),
            )
        risk = opp.get("risk", opp.get("Risk_Profile__c", {}))
        if risk:
            sub.risk_profile = RiskProfile(
                naics_code=str(risk.get("NAICS_Code__c", risk.get("naics_code", ""))),
                business_description=risk.get("Description__c", risk.get("description")),
                construction_type=risk.get("Construction_Type__c"),
                occupancy_type=risk.get("Occupancy_Type__c"),
            )
        return sub


# ── Rating & Loss Data (2) ──────────────────────────────────────


class VeriskISONormalizer(SourceNormalizer):
    source_id = "verisk-iso"
    source_name = "Verisk / ISO"

    def normalize(self, raw: dict[str, Any], submission_id: str | None = None) -> StructuredSubmission:
        sub = self._make_submission(submission_id)
        data = raw.get("rating_data", raw)
        sub.named_insured = NamedInsured(legal_name=data.get("insured_name", data.get("entity_name", "Unknown")))
        sub.risk_profile = RiskProfile(
            naics_code=str(data.get("naics_code", "")),
            construction_type=data.get("construction_type"),
            occupancy_type=data.get("occupancy_type"),
            protection_class=_to_int(data.get("protection_class")),
            total_square_footage=_to_float(data.get("square_footage")),
        )
        territory = data.get("territory", {})
        if territory:
            sub.locations.append(
                LocationData(
                    address=territory.get("address", ""),
                    city=territory.get("city", ""),
                    state=territory.get("state", ""),
                    zip_code=territory.get("zip_code", ""),
                )
            )
        for loss_cost in data.get("loss_costs", []):
            sub.coverages.append(
                CoverageDetail(
                    coverage_type=loss_cost.get("line", loss_cost.get("coverage", "")),
                    limit_amount=0,
                    deductible=0,
                    premium=_to_float(loss_cost.get("loss_cost", loss_cost.get("rate"))) or 0,
                )
            )
        return sub


class CoreLogicNormalizer(SourceNormalizer):
    source_id = "corelogic"
    source_name = "CoreLogic / Cotality"

    def normalize(self, raw: dict[str, Any], submission_id: str | None = None) -> StructuredSubmission:
        sub = self._make_submission(submission_id)
        prop = raw.get("property", raw)
        sub.named_insured = NamedInsured(legal_name=prop.get("insured_name", prop.get("owner_name", "Unknown")))
        sub.locations.append(
            LocationData(
                address=prop.get("address", prop.get("street_address", "")),
                city=prop.get("city", ""),
                state=prop.get("state", ""),
                zip_code=prop.get("zip_code", prop.get("zip", "")),
                year_built=_to_int(prop.get("year_built", prop.get("yearBuilt"))),
                square_footage=_to_float(prop.get("square_footage", prop.get("grossLivingArea"))),
                construction_type=prop.get("construction_type", prop.get("construction")),
                building_value=_to_float(prop.get("replacement_cost", prop.get("replacementCostValue"))),
            )
        )
        risk = prop.get("risk", prop.get("riskData", {}))
        if risk:
            sub.risk_profile = RiskProfile(
                construction_type=risk.get("construction_type"),
                occupancy_type=risk.get("occupancy"),
                protection_class=_to_int(risk.get("protection_class")),
            )
        cat = raw.get("catastrophe", {})
        if cat:
            prior_losses = []
            for claim in cat.get("claims", cat.get("prior_losses", [])):
                prior_losses.append(
                    {
                        "date": claim.get("date", ""),
                        "type": claim.get("type", claim.get("event_type", "")),
                        "amount": _to_float(claim.get("amount", claim.get("loss_amount", 0))),
                        "description": claim.get("description", ""),
                    }
                )
            fin = FinancialData(
                total_asset_value=_to_float(cat.get("total_insured_value", cat.get("total_asset_value"))),
                prior_losses=prior_losses,
            )
            sub.financial = fin
            total_cat_loss = sum(loss.get("amount", 0) for loss in prior_losses)
            if total_cat_loss > 0 and sub.risk_profile:
                existing_claims = sub.risk_profile.prior_claims
                for pl in prior_losses:
                    existing_claims.append(
                        ClaimRecord(
                            claim_id=pl.get("type", "cat"),
                            date_of_loss=_parse_date(pl.get("date")) or date.min,
                            line_of_business="catastrophe",
                            cause=pl.get("type", "cat"),
                            incurred_amount=_to_float(pl.get("amount", 0)) or 0.0,
                            claim_status=ClaimStatus.OPEN,
                        )
                    )
        return sub


# ── Document Storage (1) ─────────────────────────────────────────


class ImageRightNormalizer(SourceNormalizer):
    source_id = "imageright"
    source_name = "ImageRight (Vertafore)"

    def normalize(self, raw: dict[str, Any], submission_id: str | None = None) -> StructuredSubmission:
        doc = raw.get("document", raw)
        meta = doc.get("metadata", doc)
        content = doc.get("content", "")
        if "<acord" in content[:500].lower() or "<?xml" in content[:100].lower():
            from insureflow.ingestion.acord_parser import ACORDParser

            try:
                return ACORDParser().parse(content, submission_id or "imageright-001")
            except Exception:
                pass
        sub = self._make_submission(submission_id)
        sub.named_insured = NamedInsured(legal_name=meta.get("insured_name", meta.get("title", "Unknown")))
        if meta.get("broker_name"):
            sub.broker = BrokerInfo(broker_name=meta["broker_name"])
        return sub


# ── eSignature (1) ───────────────────────────────────────────────


class DocuSignNormalizer(SourceNormalizer):
    source_id = "docusign"
    source_name = "DocuSign"

    def normalize(self, raw: dict[str, Any], submission_id: str | None = None) -> StructuredSubmission:
        envelope = raw.get("envelope", raw)
        docs = envelope.get("documents", [])
        for doc in docs:
            content = doc.get("content", doc.get("document_base64", ""))
            name = doc.get("name", doc.get("documentName", "")).lower()
            if "acord" in name or "<acord" in content[:500].lower():
                from insureflow.ingestion.acord_parser import ACORDParser

                try:
                    sub = ACORDParser().parse(content, submission_id or "docusign-001")
                    sub.source = self.source_id
                    return sub
                except Exception:
                    pass
        sub = self._make_submission(submission_id)
        signer = envelope.get("signer", envelope.get("signers", [{}])[0] if envelope.get("signers") else {})
        sub.named_insured = NamedInsured(
            legal_name=envelope.get("insured_name") or signer.get("name") or "Unknown",
        )
        eff = _parse_date(envelope.get("effective_date"))
        exp = _parse_date(envelope.get("expiration_date"))
        if eff and exp:
            sub.policy_period = PolicyPeriod(effective_date=eff, expiration_date=exp)
        return sub


# ── Collaboration (2) ────────────────────────────────────────────


class MicrosoftTeamsNormalizer(SourceNormalizer):
    source_id = "microsoft-teams"
    source_name = "Microsoft Teams"

    def normalize(self, raw: dict[str, Any], submission_id: str | None = None) -> StructuredSubmission:
        message = raw.get("message", raw)
        attachments = message.get("attachments", [])
        for att in attachments:
            content = att.get("content", "")
            filename = att.get("filename", att.get("name", "")).lower()
            if "acord" in filename or "<acord" in content[:500].lower():
                from insureflow.ingestion.acord_parser import ACORDParser

                try:
                    return ACORDParser().parse(content, submission_id or "teams-001")
                except Exception:
                    pass
            if filename.endswith(".json") and content.strip().startswith("{"):
                from insureflow.ingestion.json_parser import JSONBrokerParser

                try:
                    return JSONBrokerParser().parse(content, submission_id or "teams-001")
                except Exception:
                    pass
        sub = self._make_submission(submission_id)
        sender = message.get("from", message.get("sender", {}))
        sub.named_insured = NamedInsured(legal_name=message.get("insured_name", sender.get("name", "Unknown")))
        if sender.get("name"):
            sub.broker = BrokerInfo(broker_name=sender["name"], contact_email=sender.get("email"))
        return sub


class SlackIntakeNormalizer(SourceNormalizer):
    source_id = "slack-intake"
    source_name = "Slack"

    def normalize(self, raw: dict[str, Any], submission_id: str | None = None) -> StructuredSubmission:
        event = raw.get("event", raw)
        files = event.get("files", [])
        for f in files:
            content = f.get("content", "")
            name = f.get("name", f.get("title", "")).lower()
            if "acord" in name or "<acord" in content[:500].lower():
                from insureflow.ingestion.acord_parser import ACORDParser

                try:
                    return ACORDParser().parse(content, submission_id or "slack-001")
                except Exception:
                    pass
            if name.endswith(".json") and content.strip().startswith("{"):
                from insureflow.ingestion.json_parser import JSONBrokerParser

                try:
                    return JSONBrokerParser().parse(content, submission_id or "slack-001")
                except Exception:
                    pass
        sub = self._make_submission(submission_id)
        user = event.get("user", event.get("sender", {}))
        sub.named_insured = NamedInsured(legal_name=event.get("insured_name", user.get("name", "Unknown")))
        if user.get("name"):
            sub.broker = BrokerInfo(broker_name=user["name"])
        return sub


# ── Data Warehouse (1) ──────────────────────────────────────────


class SnowflakeNormalizer(SourceNormalizer):
    source_id = "snowflake"
    source_name = "Snowflake"

    def normalize(self, raw: dict[str, Any], submission_id: str | None = None) -> StructuredSubmission:
        row = raw.get("row", raw)
        sub = self._make_submission(submission_id)
        sub.named_insured = NamedInsured(
            legal_name=row.get("legal_name", row.get("insured_name", row.get("entity_name", "Unknown"))),
            tax_id=row.get("tax_id", row.get("ein")),
            entity_type=row.get("entity_type"),
        )
        if row.get("broker_name") or row.get("producer_name"):
            sub.broker = BrokerInfo(
                broker_name=row.get("broker_name", row.get("producer_name", "")),
                broker_id=row.get("broker_id", row.get("producer_code")),
            )
        eff = _parse_date(row.get("effective_date"))
        exp = _parse_date(row.get("expiration_date"))
        if eff and exp:
            sub.policy_period = PolicyPeriod(effective_date=eff, expiration_date=exp)
        sub.financial = FinancialData(
            annual_revenue=_to_float(row.get("annual_revenue", row.get("revenue"))),
            payroll=_to_float(row.get("payroll")),
            total_asset_value=_to_float(row.get("total_asset_value", row.get("total_assets"))),
        )
        sub.risk_profile = RiskProfile(
            naics_code=str(row.get("naics_code", "")),
            sic_code=str(row.get("sic_code", "")),
            business_description=row.get("business_description"),
            construction_type=row.get("construction_type"),
            occupancy_type=row.get("occupancy_type"),
        )
        if row.get("loss_run") or row.get("prior_claims"):
            claims_raw = row.get("loss_run", row.get("prior_claims", []))
            claims = []
            for c in claims_raw:
                claims.append(
                    ClaimRecord(
                        claim_id=c.get("claim_id", f"SF-{uuid4().hex[:6]}"),
                        date_of_loss=_parse_date(c.get("date_of_loss")) or date.today(),
                        line_of_business=c.get("line", c.get("lob", "")),
                        cause=c.get("cause", ""),
                        description=c.get("description", ""),
                        incurred_amount=_to_float(c.get("incurred")) or 0,
                        paid_amount=_to_float(c.get("paid")) or 0,
                        open_reserve=_to_float(c.get("reserve")) or 0,
                        claim_status=_find_claim_status(c.get("status", "open")),
                    )
                )
            total_incurred = sum(c.incurred_amount for c in claims)
            total_paid = sum(c.paid_amount for c in claims)
            sub.financial.loss_run = LossRunData(
                total_claims=len(claims),
                total_incurred=total_incurred,
                total_paid=total_paid,
                total_open_reserves=sum(c.open_reserve for c in claims),
                claims=claims,
            )
            sub.risk_profile.prior_claims = claims
        if row.get("locations"):
            for loc in row["locations"]:
                sub.locations.append(
                    LocationData(
                        address=loc.get("address", ""),
                        city=loc.get("city", ""),
                        state=loc.get("state", ""),
                        zip_code=loc.get("zip_code", ""),
                        year_built=_to_int(loc.get("year_built")),
                        square_footage=_to_float(loc.get("square_footage")),
                        building_value=_to_float(loc.get("building_value")),
                    )
                )
        if row.get("coverages"):
            for cov in row["coverages"]:
                sub.coverages.append(
                    CoverageDetail(
                        coverage_type=cov.get("type", cov.get("coverage_type", "")),
                        limit_amount=_to_float(cov.get("limit")) or 0,
                        deductible=_to_float(cov.get("deductible")) or 0,
                        premium=_to_float(cov.get("premium")) or 0,
                    )
                )
        return sub


# ── Registry ─────────────────────────────────────────────────────

_NORMALIZERS: dict[str, SourceNormalizer] = {}


def _register(normalizer: SourceNormalizer) -> None:
    _NORMALIZERS[normalizer.source_id] = normalizer


_register(GoogleDriveNormalizer())
_register(SharePointNormalizer())
_register(S3BucketNormalizer())
_register(AzureBlobNormalizer())
_register(BoxNormalizer())
_register(EmailInboxNormalizer())
_register(SFTPNormalizer())
_register(BoldPenguinNormalizer())
_register(IVANSDownloadNormalizer())
_register(ACORDAL3Normalizer())
_register(GuidewireNormalizer())
_register(DuckCreekNormalizer())
_register(MajescoNormalizer())
_register(AppliedEpicNormalizer())
_register(HawkSoftNormalizer())
_register(SalesforceNormalizer())
_register(VeriskISONormalizer())
_register(CoreLogicNormalizer())
_register(ImageRightNormalizer())
_register(DocuSignNormalizer())
_register(MicrosoftTeamsNormalizer())
_register(SlackIntakeNormalizer())
_register(SnowflakeNormalizer())


def get_normalizer(source_id: str) -> SourceNormalizer | None:
    return _NORMALIZERS.get(source_id)


def normalize_source(source_id: str, raw: dict[str, Any], submission_id: str | None = None) -> StructuredSubmission:
    normalizer = _NORMALIZERS.get(source_id)
    if normalizer is None:
        raise ValueError(f"No normalizer registered for source: {source_id}")
    return normalizer.normalize(raw, submission_id)


def supported_sources() -> list[str]:
    return sorted(_NORMALIZERS.keys())
