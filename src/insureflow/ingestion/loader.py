from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from insureflow.ingestion.acord_parser import ACORDParser
from insureflow.ingestion.chunker import DocumentChunker
from insureflow.ingestion.classifier import DocumentClassifier
from insureflow.ingestion.excel_parser import ExcelParser
from insureflow.ingestion.json_parser import JSONBrokerParser
from insureflow.ingestion.loss_run_parser import LossRunParser
from insureflow.ingestion.ocr import OCRProcessor
from insureflow.ingestion.report_extractor import InspectionReportExtractor
from insureflow.ingestion.sov_parser import SOVParser
from insureflow.models.submissions import (
    DocumentType,
    ExtractedChunk,
    StructuredSubmission,
    SubmissionBundle,
    SubmissionStatus,
    UnstructuredSubmission,
)


class SubmissionLoader:
    def __init__(self) -> None:
        self.acord_parser = ACORDParser()
        self.json_parser = JSONBrokerParser()
        self.report_extractor = InspectionReportExtractor()
        self.loss_run_parser = LossRunParser()
        self.sov_parser = SOVParser()
        self.excel_parser = ExcelParser()
        self.ocr_processor = OCRProcessor()
        self.classifier = DocumentClassifier()
        self.chunker = DocumentChunker()

    def load_bundle(
        self,
        acord_xml: Optional[str] = None,
        inspection_reports: Optional[list[str]] = None,
        supplemental_docs: Optional[list[str]] = None,
        json_payload: Optional[str] = None,
        loss_run: Optional[str] = None,
        schedule_of_values: Optional[str] = None,
        excel_data: Optional[list[str]] = None,
        pdf_paths: Optional[list[str]] = None,
        bundle_id: Optional[str] = None,
        auto_classify: bool = False,
        raw_docs: Optional[list[str]] = None,
    ) -> SubmissionBundle:
        bundle = SubmissionBundle(
            bundle_id=bundle_id or f"bundle-{uuid4().hex[:12]}",
            status=SubmissionStatus.RECEIVED,
        )

        if auto_classify and raw_docs:
            return self._load_auto_classified(raw_docs, bundle)

        if acord_xml:
            bundle.structured = self.acord_parser.parse(acord_xml, bundle.bundle_id)
            bundle.status = SubmissionStatus.PARSED

        if json_payload:
            parsed_json = self.json_parser.parse(json_payload, bundle.bundle_id)
            if bundle.structured:
                # Multiple structured sources (ACORD + broker API): merge with
                # fill-missing semantics so no source's fields are dropped.
                self._merge_structured(bundle.structured, parsed_json)
            else:
                bundle.structured = parsed_json
            bundle.status = SubmissionStatus.PARSED

        if inspection_reports:
            for i, report_text in enumerate(inspection_reports):
                sub_id = f"{bundle.bundle_id}-inspection-{i}"
                report = self.report_extractor.parse(report_text, sub_id)
                bundle.unstructured.append(report)

        if loss_run:
            sub_id = f"{bundle.bundle_id}-loss-run"
            parsed = self.loss_run_parser.parse(loss_run, sub_id)
            bundle.unstructured.append(parsed)

            loss_data = self.loss_run_parser.parse_structured(loss_run)
            if bundle.structured and bundle.structured.financial:
                bundle.structured.financial.loss_run = loss_data
                bundle.structured.financial.prior_losses = [
                    {
                        "claim_id": c.claim_id,
                        "date_of_loss": c.date_of_loss.isoformat(),
                        "line_of_business": c.line_of_business,
                        "cause": c.cause,
                        "incurred_amount": c.incurred_amount,
                    }
                    for c in loss_data.claims
                ]
            elif bundle.structured:
                from insureflow.models.submissions import FinancialData

                bundle.structured.financial = FinancialData(
                    loss_run=loss_data,
                    prior_losses=[
                        {
                            "claim_id": c.claim_id,
                            "date_of_loss": c.date_of_loss.isoformat(),
                            "line_of_business": c.line_of_business,
                            "cause": c.cause,
                            "incurred_amount": c.incurred_amount,
                        }
                        for c in loss_data.claims
                    ],
                )

        if schedule_of_values:
            sub_id = f"{bundle.bundle_id}-sov"
            parsed = self.sov_parser.parse(schedule_of_values, sub_id)
            bundle.unstructured.append(parsed)

            sows = self.sov_parser.parse_structured(schedule_of_values)
            if bundle.structured:
                bundle.structured.schedule_of_values = sows

        if excel_data:
            for i, data in enumerate(excel_data):
                sub_id = f"{bundle.bundle_id}-excel-{i}"
                is_csv = data.strip().startswith(",") or ("first_name" in data[:200].lower() and "," in data[:500])
                if is_csv:
                    parsed = self.excel_parser.parse_csv(data, sub_id)
                else:
                    parsed = self.excel_parser.parse(data, sub_id)
                bundle.unstructured.append(parsed)

                try:
                    sows = self.excel_parser.parse_structured(data, sub_id)
                    if sows and bundle.structured:
                        bundle.structured.schedule_of_values.extend(sows)
                except Exception:
                    pass

        if pdf_paths:
            for path in pdf_paths:
                sub_id = f"{bundle.bundle_id}-pdf-{len(bundle.unstructured)}"
                parsed = self.ocr_processor.extract_text(path, sub_id)
                doc_type = self.classifier.classify(parsed.raw_text, path)
                parsed.document_type = doc_type.value
                bundle.unstructured.append(parsed)

        if supplemental_docs:
            for i, doc_text in enumerate(supplemental_docs):
                sub_id = f"{bundle.bundle_id}-supplemental-{i}"
                sup = UnstructuredSubmission(
                    submission_id=sub_id,
                    source="supplemental_document",
                    document_type="supplemental",
                    raw_text=doc_text,
                    processed_at=datetime.now(timezone.utc),
                )

                # Apply safe document chunking to prevent LLM context limits
                raw_chunks = self.chunker.chunk_text(doc_text)
                sup.chunks = [
                    ExtractedChunk(
                        chunk_index=idx,
                        text=chunk_text,
                        start_char=0,  # Simplified for supplemental fallback
                        end_char=len(chunk_text),
                    )
                    for idx, chunk_text in enumerate(raw_chunks)
                ]
                bundle.supplemental.append(sup)

        return bundle

    def _merge_structured(self, dst: StructuredSubmission, src: StructuredSubmission) -> None:
        """Merge a second structured source into the first with fill-missing
        semantics: dst values win, src only fills gaps (None / empty). Matched
        list items (coverages, locations) merge field-by-field; unmatched items
        are appended. This keeps every source's extracted data without
        double-claiming fields it did not provide."""
        if src.named_insured:
            if dst.named_insured is None:
                dst.named_insured = src.named_insured.model_copy(deep=True)
            else:
                for field_name in ("legal_name", "dba", "tax_id", "entity_type", "address"):
                    if getattr(dst.named_insured, field_name) in (None, ""):
                        setattr(dst.named_insured, field_name, getattr(src.named_insured, field_name))

        if src.broker:
            if dst.broker is None:
                dst.broker = src.broker.model_copy(deep=True)
            else:
                for field_name in ("broker_name", "broker_id", "contact_name", "contact_email", "agency"):
                    if getattr(dst.broker, field_name) in (None, ""):
                        setattr(dst.broker, field_name, getattr(src.broker, field_name))

        if src.policy_period:
            if dst.policy_period is None:
                dst.policy_period = src.policy_period.model_copy(deep=True)
            else:
                for field_name in ("effective_date", "expiration_date", "is_bound"):
                    if getattr(dst.policy_period, field_name) in (None, False):
                        setattr(dst.policy_period, field_name, getattr(src.policy_period, field_name))

        if src.coverages:
            dst_by_type = {c.coverage_type.lower(): c for c in dst.coverages}
            for cov in src.coverages:
                cov_match = dst_by_type.get(cov.coverage_type.lower())
                if cov_match is None:
                    dst.coverages.append(cov.model_copy(deep=True))
                    continue
                for field_name in ("limit_amount", "deductible", "premium"):
                    if getattr(cov_match, field_name) in (None, 0.0):
                        setattr(cov_match, field_name, getattr(cov, field_name))
                if not cov_match.sublimits and cov.sublimits:
                    cov_match.sublimits.update(cov.sublimits)
                if not cov_match.endorsements and cov.endorsements:
                    cov_match.endorsements = list(cov.endorsements)

        if src.locations:
            dst_by_addr = {loc.address.lower(): loc for loc in dst.locations if loc.address}
            for loc in src.locations:
                loc_match = dst_by_addr.get(loc.address.lower())
                if loc_match is None:
                    dst.locations.append(loc.model_copy(deep=True))
                    continue
                for field_name in (
                    "city",
                    "state",
                    "zip_code",
                    "building_occupancy",
                    "year_built",
                    "square_footage",
                    "construction_type",
                    "protection_class",
                    "building_value",
                    "contents_value",
                    "bi_value",
                ):
                    if getattr(loc_match, field_name) in (None, "", 0, 0.0):
                        setattr(loc_match, field_name, getattr(loc, field_name))

        if src.risk_profile:
            if dst.risk_profile is None:
                dst.risk_profile = src.risk_profile.model_copy(deep=True)
            else:
                for field_name in (
                    "naics_code",
                    "sic_code",
                    "ncci_class_code",
                    "business_description",
                    "occupancy_type",
                    "construction_type",
                    "protection_class",
                    "sprinklered",
                    "number_of_stories",
                    "total_square_footage",
                ):
                    if getattr(dst.risk_profile, field_name) in (None, ""):
                        setattr(dst.risk_profile, field_name, getattr(src.risk_profile, field_name))
                if not dst.risk_profile.prior_claims and src.risk_profile.prior_claims:
                    dst.risk_profile.prior_claims = list(src.risk_profile.prior_claims)
                if not dst.risk_profile.safety_certifications and src.risk_profile.safety_certifications:
                    dst.risk_profile.safety_certifications = list(src.risk_profile.safety_certifications)

        if src.financial:
            if dst.financial is None:
                dst.financial = src.financial.model_copy(deep=True)
            else:
                for field_name in ("total_asset_value", "annual_revenue", "payroll", "credit_rating"):
                    if getattr(dst.financial, field_name) in (None, ""):
                        setattr(dst.financial, field_name, getattr(src.financial, field_name))
                if not dst.financial.prior_losses and src.financial.prior_losses:
                    dst.financial.prior_losses = list(src.financial.prior_losses)
                if dst.financial.loss_run is None and src.financial.loss_run:
                    dst.financial.loss_run = src.financial.loss_run.model_copy(deep=True)

        for path, conf in (src.field_confidence or {}).items():
            dst.field_confidence.setdefault(path, conf)
        for path, note in (src.field_notes or {}).items():
            dst.field_notes.setdefault(path, note)

    def _load_auto_classified(self, raw_docs: list[str], bundle: SubmissionBundle) -> SubmissionBundle:
        acord_docs: list[str] = []
        json_docs: list[str] = []
        inspection_docs: list[str] = []
        loss_run_docs: list[str] = []
        sov_docs: list[str] = []
        supplemental_docs: list[str] = []

        for doc in raw_docs:
            doc_type = self.classifier.classify(doc)
            if doc_type == DocumentType.ACORD_XML:
                acord_docs.append(doc)
            elif doc_type == DocumentType.BROKER_API_JSON:
                json_docs.append(doc)
            elif doc_type == DocumentType.INSPECTION_REPORT:
                inspection_docs.append(doc)
            elif doc_type == DocumentType.LOSS_RUN:
                loss_run_docs.append(doc)
            elif doc_type == DocumentType.SCHEDULE_OF_VALUES:
                sov_docs.append(doc)
            else:
                supplemental_docs.append(doc)

        if acord_docs:
            bundle.structured = self.acord_parser.parse(acord_docs[0], bundle.bundle_id)
            bundle.status = SubmissionStatus.PARSED

        if json_docs and not bundle.structured:
            bundle.structured = self.json_parser.parse(json_docs[0], bundle.bundle_id)
            bundle.status = SubmissionStatus.PARSED

        for i, doc in enumerate(inspection_docs):
            sub_id = f"{bundle.bundle_id}-inspection-{i}"
            bundle.unstructured.append(self.report_extractor.parse(doc, sub_id))

        for i, doc in enumerate(loss_run_docs):
            sub_id = f"{bundle.bundle_id}-loss-run-{i}"
            bundle.unstructured.append(self.loss_run_parser.parse(doc, sub_id))
            loss_data = self.loss_run_parser.parse_structured(doc)
            if bundle.structured:
                if bundle.structured.financial:
                    bundle.structured.financial.loss_run = loss_data
                else:
                    from insureflow.models.submissions import FinancialData

                    bundle.structured.financial = FinancialData(loss_run=loss_data)
                bundle.structured.financial.prior_losses = [
                    {
                        "claim_id": c.claim_id,
                        "date_of_loss": c.date_of_loss.isoformat(),
                        "line_of_business": c.line_of_business,
                        "cause": c.cause,
                        "incurred_amount": c.incurred_amount,
                    }
                    for c in loss_data.claims
                ]

        for i, doc in enumerate(sov_docs):
            sub_id = f"{bundle.bundle_id}-sov-{i}"
            bundle.unstructured.append(self.sov_parser.parse(doc, sub_id))
            sows = self.sov_parser.parse_structured(doc)
            if bundle.structured:
                bundle.structured.schedule_of_values.extend(sows)

        for i, doc in enumerate(supplemental_docs):
            sub_id = f"{bundle.bundle_id}-supplemental-{i}"
            sup = UnstructuredSubmission(
                submission_id=sub_id,
                source="supplemental_document",
                raw_text=doc,
                processed_at=datetime.now(timezone.utc),
            )

            raw_chunks = self.chunker.chunk_text(doc)
            sup.chunks = [
                ExtractedChunk(
                    chunk_index=idx,
                    text=chunk_text,
                    start_char=0,
                    end_char=len(chunk_text),
                )
                for idx, chunk_text in enumerate(raw_chunks)
            ]
            bundle.supplemental.append(sup)

        if bundle.structured:
            bundle.status = SubmissionStatus.PARSED
            if bundle.unstructured or bundle.supplemental:
                pass

        return bundle
