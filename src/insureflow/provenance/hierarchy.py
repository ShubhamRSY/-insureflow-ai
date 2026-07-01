from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from insureflow.config import settings
from insureflow.models.provenance import (
    DataSource,
    ProvenanceHierarchy,
    ProvenanceNode,
    ProvenanceRecord,
    SourceType,
    TrustLevel,
    VerificationStatus,
)
from insureflow.models.submissions import (
    StructuredSubmission,
    SubmissionBundle,
    UnstructuredSubmission,
)


class ProvenanceEngine:
    def __init__(self, deduplicate: bool = True) -> None:
        self.hierarchy = ProvenanceHierarchy()
        self.deduplicate = deduplicate

    def build_provenance(
        self, bundle: SubmissionBundle
    ) -> ProvenanceRecord:
        if self.deduplicate:
            from insureflow.entities.resolver import EntityResolver
            self._resolver = EntityResolver()
        else:
            self._resolver = None
        record = ProvenanceRecord(
            record_id=f"prov-{uuid4().hex[:12]}",
            bundle_id=bundle.bundle_id,
            hierarchy=self.hierarchy,
        )

        if bundle.structured:
            self._index_structured_fields(record, bundle.structured)

        for unstructured in bundle.unstructured:
            self._index_unstructured_fields(record, unstructured)

        for supplemental in bundle.supplemental:
            self._index_unstructured_fields(record, supplemental, is_supplemental=True)

        record.resolved_at = datetime.now(timezone.utc)

        if self._resolver:
            record = self._resolver.resolve_record(record)

        return record

    def _index_structured_fields(
        self, record: ProvenanceRecord, structured: StructuredSubmission
    ) -> None:
        source = DataSource(
            source_id=structured.submission_id,
            source_type=SourceType.STRUCTURED,
            source_name=structured.source,
            received_at=structured.received_at,
            trust_level=TrustLevel.HIGH,
            hierarchy_rank=self.hierarchy.rank_for_source(structured.source),
        )

        fields: dict[str, Any] = {}
        if structured.named_insured:
            fields["named_insured.legal_name"] = structured.named_insured.legal_name
            fields["named_insured.tax_id"] = structured.named_insured.tax_id
            fields["named_insured.entity_type"] = structured.named_insured.entity_type

        if structured.policy_period:
            fields["policy_period.effective_date"] = (
                structured.policy_period.effective_date.isoformat()
            )
            fields["policy_period.expiration_date"] = (
                structured.policy_period.expiration_date.isoformat()
            )

        if structured.risk_profile:
            fields["risk_profile.naics_code"] = structured.risk_profile.naics_code
            fields["risk_profile.sic_code"] = structured.risk_profile.sic_code
            fields["risk_profile.construction_type"] = structured.risk_profile.construction_type
            fields["risk_profile.occupancy_type"] = structured.risk_profile.occupancy_type
            fields["risk_profile.protection_class"] = structured.risk_profile.protection_class
            fields["risk_profile.number_of_stories"] = structured.risk_profile.number_of_stories
            fields["risk_profile.total_square_footage"] = structured.risk_profile.total_square_footage

        if structured.financial:
            fields["financial.annual_revenue"] = structured.financial.annual_revenue
            fields["financial.payroll"] = structured.financial.payroll

        for i, coverage in enumerate(structured.coverages):
            fields[f"coverage.{i}.type"] = coverage.coverage_type
            fields[f"coverage.{i}.limit"] = coverage.limit_amount
            fields[f"coverage.{i}.deductible"] = coverage.deductible
            fields[f"coverage.{i}.premium"] = coverage.premium

        for i, location in enumerate(structured.locations):
            fields[f"location.{i}.address"] = location.address
            fields[f"location.{i}.city"] = location.city
            fields[f"location.{i}.state"] = location.state
            fields[f"location.{i}.year_built"] = location.year_built
            fields[f"location.{i}.square_footage"] = location.square_footage

        self._add_nodes(record, fields, source, confidence=0.95)

    def _index_unstructured_fields(
        self,
        record: ProvenanceRecord,
        unstructured: UnstructuredSubmission,
        is_supplemental: bool = False,
    ) -> None:
        trust = TrustLevel.MEDIUM if is_supplemental else TrustLevel.LOW
        source_name = unstructured.source
        source = DataSource(
            source_id=unstructured.submission_id,
            source_type=SourceType.UNSTRUCTURED,
            source_name=source_name,
            received_at=unstructured.received_at,
            trust_level=trust,
            hierarchy_rank=self.hierarchy.rank_for_source(source_name),
        )

        fields: dict[str, Any] = {}

        for field_name, extracted_list in unstructured.extracted_fields.items():
            for ef in extracted_list:
                key = f"extracted.{field_name}"
                if key not in fields:
                    fields[key] = []
                fields[key].append({
                    "value": ef.value,
                    "confidence": ef.confidence,
                    "context": ef.context,
                })

        if not is_supplemental:
            for field_name, extracted_list in unstructured.extracted_fields.items():
                for ef in extracted_list:
                    mapped_key = self._map_extracted_to_structured(field_name)
                    fields[mapped_key] = ef.value

        self._add_nodes(record, fields, source, confidence=0.6)

    def _map_extracted_to_structured(self, field_name: str) -> str:
        return settings.field_mapping.get(field_name, f"extracted.{field_name}")

    def _add_nodes(
        self,
        record: ProvenanceRecord,
        fields: dict[str, Any],
        source: DataSource,
        confidence: float = 0.0,
    ) -> None:
        for field_path, value in fields.items():
            node = ProvenanceNode(
                node_id=f"node-{uuid4().hex[:8]}",
                field_path=field_path,
                value=value,
                source=source,
                confidence=confidence,
                extracted_at=datetime.now(timezone.utc),
            )
            if field_path not in record.nodes:
                record.nodes[field_path] = []
            record.nodes[field_path].append(node)

    def verify_against_authority(
        self, record: ProvenanceRecord, field_path: str, authoritative_value: Any
    ) -> VerificationStatus:
        if field_path not in record.nodes:
            return VerificationStatus.UNVERIFIED

        nodes = sorted(
            record.nodes[field_path],
            key=lambda n: n.source.hierarchy_rank,
            reverse=True,
        )

        authoritative = None
        for node in nodes:
            if node.value == authoritative_value:
                authoritative = node
                break

        if authoritative is None:
            return VerificationStatus.CONTRADICTED

        for node in nodes:
            if node.source.source_id == authoritative.source.source_id:
                node.verification_status = VerificationStatus.VERIFIED
                node.verified_against.append(authoritative.node_id)
            else:
                if node.value == authoritative_value:
                    node.verification_status = VerificationStatus.VERIFIED
                    node.verified_against.append(authoritative.node_id)
                else:
                    node.verification_status = VerificationStatus.CONTRADICTED
                    node.verified_against.append(authoritative.node_id)

        return VerificationStatus.VERIFIED
