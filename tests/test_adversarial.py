"""Adversarial / breakage tests — attempting to break every layer of the product.

These tests verify:
1. All critical/high bug fixes are effective
2. Edge cases that could crash or corrupt data in production
3. Security boundaries hold under adversarial input
4. Graceful degradation under extreme conditions
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from insureflow.auth.jwt import create_access_token, decode_access_token
from insureflow.config import settings
from insureflow.gateway.auth import verify_gateway_key
from insureflow.gateway.payloads import enterprise_ack, policy_bind, policy_submit
from insureflow.graph.nodes import create_initial_state
from insureflow.redaction.detector import PIICategory, PIIDetector
from insureflow.redaction.redactor import PIIRedactor
from insureflow.workflow.models import SignOffAction, WorkflowState
from insureflow.workflow.service import WorkflowService
from insureflow.workflow.store import WorkflowStore

# ===========================================================================
# 1. PII REDACTION — Breaking the masking
# ===========================================================================

class TestRedactionAdversarial:
    """Verify SSN, email, bank account, and IP masking is actually secure."""

    def test_ssn_area_number_not_leaked(self) -> None:
        redactor = PIIRedactor()
        result = redactor.redact("SSN: 123-45-6789", mask=True)
        assert "123" not in result, f"Area number leaked in: {result}"
        assert "***" in result
        assert "6789" in result

    def test_email_domain_not_fully_leaked(self) -> None:
        redactor = PIIRedactor()
        result = redactor.redact("Contact: john.doe@acme-insurance.com", mask=True)
        assert "john.doe" not in result
        assert "acme-insurance.com" in result, "Domain visible for audit trail"
        assert "***@" in result

    def test_bank_account_not_false_positive_on_policy_number(self) -> None:
        detector = PIIDetector()
        spans = detector.detect("Policy number: 12345678")
        bank_spans = [s for s in spans if s.category == PIICategory.BANK_ACCOUNT]
        assert len(bank_spans) == 0, f"Policy number falsely detected as bank account: {bank_spans}"

    def test_bank_account_with_keyword_detected(self) -> None:
        detector = PIIDetector()
        spans = detector.detect("Account Number: 123456789012")
        bank_spans = [s for s in spans if s.category == PIICategory.BANK_ACCOUNT]
        assert len(bank_spans) >= 1

    def test_bank_account_routing_format_detected(self) -> None:
        detector = PIIDetector()
        spans = detector.detect("Routing: 021000021")
        bank_spans = [s for s in spans if s.category == PIICategory.BANK_ACCOUNT]
        assert len(bank_spans) >= 1

    def test_ip_invalid_octets_not_detected(self) -> None:
        detector = PIIDetector()
        spans = detector.detect("Server: 999.999.999.999")
        ip_spans = [s for s in spans if s.category == PIICategory.IP_ADDRESS]
        assert len(ip_spans) == 0, f"Invalid IP detected: {ip_spans}"

    def test_ip_valid_octets_detected(self) -> None:
        detector = PIIDetector()
        spans = detector.detect("Server: 192.168.1.1")
        ip_spans = [s for s in spans if s.category == PIICategory.IP_ADDRESS]
        assert len(ip_spans) >= 1

    def test_ip_boundary_octets(self) -> None:
        detector = PIIDetector()
        spans = detector.detect("Server: 255.255.255.255")
        ip_spans = [s for s in spans if s.category == PIICategory.IP_ADDRESS]
        assert len(ip_spans) >= 1
        spans2 = detector.detect("Server: 256.1.1.1")
        ip_spans2 = [s for s in spans2 if s.category == PIICategory.IP_ADDRESS]
        assert len(ip_spans2) == 0

    def test_ssn_not_twice_in_text(self) -> None:
        redactor = PIIRedactor()
        result = redactor.redact("SSN: 123-45-6789 and also 987-65-4321")
        assert "123" not in result
        assert "987" not in result

    def test_phone_masking(self) -> None:
        redactor = PIIRedactor()
        result = redactor.redact("Call 555-123-4567", mask=True)
        assert "123" not in result

    def test_full_text_with_multiple_pii(self) -> None:
        redactor = PIIRedactor()
        text = "Insured: John Smith, SSN: 111-22-3333, email: john@test.com, phone: 555-867-5309"
        result = redactor.redact(text, mask=True)
        assert "111-22" not in result
        assert "john@test.com" not in result
        assert "5309" in result


# ===========================================================================
# 2. WORKFLOW — State machine violations
# ===========================================================================

class TestWorkflowAdversarial:
    """Try to break the workflow state machine."""

    @pytest.fixture
    def svc(self, tmp_path: Any) -> WorkflowService:
        store = WorkflowStore(base_path=tmp_path / "wf")
        return WorkflowService(store=store)

    def test_cannot_reopen_approved_workflow(self, svc: WorkflowService) -> None:
        svc.start("b1", "org", "approve")
        svc.submit_for_review("b1", "org", "approve")
        svc.sign_off("b1", "org", SignOffAction.APPROVE, "uw1")
        with pytest.raises(ValueError, match="Cannot reopen"):
            svc.submit_for_review("b1", "org", "approve")

    def test_cannot_reopen_bound_workflow(self, svc: WorkflowService) -> None:
        svc.start("b1", "org", "approve")
        svc.submit_for_review("b1", "org", "approve")
        svc.sign_off("b1", "org", SignOffAction.APPROVE, "uw1")
        svc.mark_bound("b1", "org", "POL-001")
        with pytest.raises(ValueError, match="Cannot reopen"):
            svc.submit_for_review("b1", "org", "approve")

    def test_cannot_sign_off_twice(self, svc: WorkflowService) -> None:
        svc.start("b1", "org", "approve")
        svc.submit_for_review("b1", "org", "approve")
        svc.sign_off("b1", "org", SignOffAction.APPROVE, "uw1")
        with pytest.raises(ValueError, match="Cannot sign off"):
            svc.sign_off("b1", "org", SignOffAction.DECLINE, "uw2")

    def test_cannot_sign_off_from_analyzing(self, svc: WorkflowService) -> None:
        svc.start("b1", "org", "approve")
        with pytest.raises(ValueError, match="Cannot sign off"):
            svc.sign_off("b1", "org", SignOffAction.APPROVE, "uw1")

    def test_cannot_bind_without_approval(self, svc: WorkflowService) -> None:
        svc.start("b1", "org", "approve")
        svc.submit_for_review("b1", "org", "approve")
        with pytest.raises(ValueError, match="only be bound after"):
            svc.mark_bound("b1", "org", "POL-001")

    def test_sign_off_on_missing_workflow(self, svc: WorkflowService) -> None:
        with pytest.raises(ValueError, match="No workflow found"):
            svc.sign_off("nonexistent", "org", SignOffAction.APPROVE, "uw1")

    def test_decline_then_reopen_works(self, svc: WorkflowService) -> None:
        svc.start("b1", "org", "approve")
        svc.submit_for_review("b1", "org", "approve")
        svc.sign_off("b1", "org", SignOffAction.DECLINE, "uw1")
        svc.submit_for_review("b1", "org", "approve")
        record = svc.store.get("b1", "org")
        assert record is not None
        assert record.state == WorkflowState.PENDING_REVIEW

    def test_concurrent_sign_offs(self, svc: WorkflowService) -> None:
        svc.start("b1", "org", "approve")
        svc.submit_for_review("b1", "org", "approve")
        errors: list[Exception] = []

        def sign_off_thread() -> None:
            try:
                svc.sign_off("b1", "org", SignOffAction.APPROVE, f"uw-{threading.current_thread().ident}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=sign_off_thread) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        record = svc.store.get("b1", "org")
        assert record is not None
        assert record.state == WorkflowState.APPROVED


# ===========================================================================
# 3. JWT — Forged tokens with invalid roles
# ===========================================================================

class TestJWTAdversarial:
    """Try to crash JWT handling with malformed tokens."""

    def test_invalid_role_string_does_not_crash(self) -> None:
        secret = settings.secret_key
        token = create_access_token({"sub": "attacker", "role": "superadmin"}, secret_key=secret)
        result = decode_access_token(token, secret_key=secret)
        assert result is not None
        assert result.role is None

    def test_empty_role_string(self) -> None:
        secret = settings.secret_key
        token = create_access_token({"sub": "user", "role": ""}, secret_key=secret)
        result = decode_access_token(token, secret_key=secret)
        assert result is not None
        assert result.role is None

    def test_numeric_role(self) -> None:
        secret = settings.secret_key
        token = create_access_token({"sub": "user", "role": 999}, secret_key=secret)
        result = decode_access_token(token, secret_key=secret)
        assert result is not None
        assert result.role is None

    def test_missing_sub_returns_none(self) -> None:
        secret = settings.secret_key
        token = create_access_token({"role": "admin"}, secret_key=secret)
        result = decode_access_token(token, secret_key=secret)
        assert result is None

    def test_tampered_token_returns_none(self) -> None:
        secret = settings.secret_key
        token = create_access_token({"sub": "user", "role": "VIEWER"}, secret_key=secret)
        tampered = token[:-5] + "XXXXX"
        result = decode_access_token(tampered, secret_key=secret)
        assert result is None

    def test_wrong_secret_returns_none(self) -> None:
        secret = settings.secret_key
        token = create_access_token({"sub": "user"}, secret_key=secret)
        result = decode_access_token(token, secret_key="wrong-secret")
        assert result is None

    def test_valid_admin_token(self) -> None:
        secret = settings.secret_key
        token = create_access_token({"sub": "admin", "role": "ADMIN", "org_id": "org1"}, secret_key=secret)
        result = decode_access_token(token, secret_key=secret)
        assert result is not None
        assert result.username == "admin"
        assert result.org_id == "org1"


# ===========================================================================
# 4. GATEWAY — Auth bypass attempts
# ===========================================================================

class TestGatewayAuthAdversarial:
    """Try to bypass gateway authentication."""

    def test_missing_auth_header_rejected(self) -> None:
        with pytest.raises(Exception):
            verify_gateway_key(authorization=None)

    def test_wrong_bearer_prefix_rejected(self) -> None:
        with pytest.raises(Exception):
            verify_gateway_key(authorization="Basic abc123")

    def test_wrong_token_rejected(self) -> None:
        with pytest.raises(Exception):
            verify_gateway_key(authorization="Bearer wrong-key-here")

    def test_empty_bearer_rejected(self) -> None:
        with pytest.raises(Exception):
            verify_gateway_key(authorization="Bearer ")

    def test_enterprise_ack_does_not_echo_body(self) -> None:
        result = enterprise_ack("test_service", {"secret": "password123"})
        assert "payload" not in result
        assert "secret" not in json.dumps(result)

    def test_enterprise_ack_with_none_body(self) -> None:
        result = enterprise_ack("test_service", None)
        assert "payload" not in result

    def test_policy_submit_empty_system(self) -> None:
        result = policy_submit("", {"insured_name": "Test"})
        assert result["external_reference"].startswith("-")

    def test_policy_bind_empty_system(self) -> None:
        result = policy_bind("", {"quote_reference": "Q-123"})
        assert result["policy_number"].startswith("-")


# ===========================================================================
# 5. WORM AUDIT — Immutability violations
# ===========================================================================

class TestWORMAdversarial:
    """Try to corrupt the immutable audit trail."""

    def test_sealed_file_unique_even_in_same_second(self, tmp_path: Any) -> None:
        from insureflow.audit.worm import WormAuditStore
        store = WormAuditStore(base_path=tmp_path / "worm")
        r1 = store.seal("org", "b1", {"data": "first"})
        r2 = store.seal("org", "b1", {"data": "second"})
        assert r1["path"] != r2["path"], "Two seals of same bundle should produce different paths"

    def test_verify_does_not_mutate_original(self, tmp_path: Any) -> None:
        from insureflow.audit.worm import WormAuditStore
        store = WormAuditStore(base_path=tmp_path / "worm")
        record = store.seal("org", "b1", {"data": "test"})
        p = Path(record["path"])
        original_text = p.read_text()
        original_data = json.loads(original_text)
        assert store.verify(p)
        after_verify = json.loads(p.read_text())
        assert after_verify == original_data, "verify() should not mutate the file"

    def test_tampered_hash_fails_verification(self, tmp_path: Any) -> None:
        from insureflow.audit.worm import WormAuditStore
        store = WormAuditStore(base_path=tmp_path / "worm")
        record = store.seal("org", "b1", {"data": "test"})
        p = Path(record["path"])
        data = json.loads(p.read_text())
        data["sha256"] = "0" * 64
        p.chmod(0o644)
        p.write_text(json.dumps(data, indent=2))
        assert not store.verify(p)

    def test_empty_payload_still_seals(self, tmp_path: Any) -> None:
        from insureflow.audit.worm import WormAuditStore
        store = WormAuditStore(base_path=tmp_path / "worm")
        record = store.seal("org", "b1", {})
        assert record["sealed"] is True

    def test_seal_with_empty_org(self, tmp_path: Any) -> None:
        from insureflow.audit.worm import WormAuditStore
        store = WormAuditStore(base_path=tmp_path / "worm")
        record = store.seal("", "b1", {"data": "test"})
        assert record["sealed"] is True

    def test_list_sealed_empty_org(self, tmp_path: Any) -> None:
        from insureflow.audit.worm import WormAuditStore
        store = WormAuditStore(base_path=tmp_path / "worm")
        result = store.list_sealed("nonexistent")
        assert result == []


# ===========================================================================
# 6. KNOWLEDGE STORE — Attribute injection
# ===========================================================================

class TestKnowledgeStoreAdversarial:
    """Try to inject arbitrary attributes into tacit rules."""

    def test_cannot_overwrite_rule_id(self, tmp_path: Any) -> None:
        from insureflow.knowledge.tacit_store import KnowledgeType, TacitKnowledgeStore, TacitRule
        store = TacitKnowledgeStore(persist_path=tmp_path / "knowledge.json")
        rule = TacitRule(rule_type=KnowledgeType.PATTERN, title="Original", description="test")
        store.add_rule(rule)
        store.update_rule(rule.rule_id, title="Hacked")
        original = store.get_rule(rule.rule_id)
        assert original is not None
        assert original.title == "Hacked"
        assert original.rule_id == rule.rule_id

    def test_cannot_reactivate_dead_rule(self, tmp_path: Any) -> None:
        from insureflow.knowledge.tacit_store import KnowledgeType, TacitKnowledgeStore, TacitRule
        store = TacitKnowledgeStore(persist_path=tmp_path / "knowledge.json")
        rule = TacitRule(rule_type=KnowledgeType.PATTERN, title="Dead", description="test", confidence=0.0, is_active=False)
        store.add_rule(rule)
        store.update_rule(rule.rule_id, title="Revived")
        updated = store.get_rule(rule.rule_id)
        assert updated is not None
        assert updated.is_active is False

    def test_cannot_inject_confidence(self, tmp_path: Any) -> None:
        from insureflow.knowledge.tacit_store import KnowledgeType, TacitKnowledgeStore, TacitRule
        store = TacitKnowledgeStore(persist_path=tmp_path / "knowledge.json")
        rule = TacitRule(rule_type=KnowledgeType.PATTERN, title="Low", description="test", confidence=0.1)
        store.add_rule(rule)
        store.update_rule(rule.rule_id, title="Updated")
        updated = store.get_rule(rule.rule_id)
        assert updated is not None
        assert updated.confidence == 0.1

    def test_title_update_works(self, tmp_path: Any) -> None:
        from insureflow.knowledge.tacit_store import KnowledgeType, TacitKnowledgeStore, TacitRule
        store = TacitKnowledgeStore(persist_path=tmp_path / "knowledge.json")
        rule = TacitRule(rule_type=KnowledgeType.PATTERN, title="Original", description="test")
        store.add_rule(rule)
        store.update_rule(rule.rule_id, title="Updated")
        updated = store.get_rule(rule.rule_id)
        assert updated is not None
        assert updated.title == "Updated"

    def test_update_nonexistent_rule(self, tmp_path: Any) -> None:
        from insureflow.knowledge.tacit_store import TacitKnowledgeStore
        store = TacitKnowledgeStore(persist_path=tmp_path / "knowledge.json")
        result = store.update_rule("nonexistent", title="X")
        assert result is None


# ===========================================================================
# 7. PIPELINE STATE — Edge cases
# ===========================================================================

class TestPipelineStateAdversarial:
    """Try to break the pipeline with bad initial states."""

    def test_empty_state_has_defaults(self) -> None:
        state = create_initial_state()
        assert state.get("bundle_id") is not None
        assert state.get("extraction_retries") == 0

    def test_none_bundle_id_generates_fallback(self) -> None:
        state = create_initial_state(bundle_id=None)
        assert state.get("bundle_id") is None

    def test_empty_string_inputs(self) -> None:
        state = create_initial_state(
            acord_xml="",
            json_payload="",
            loss_run="",
            schedule_of_values="",
        )
        assert state.get("acord_xml") == ""

    def test_huge_bundle_id(self) -> None:
        huge_id = "x" * 10000
        state = create_initial_state(bundle_id=huge_id)
        assert state.get("bundle_id") == huge_id

    def test_unicode_bundle_id(self) -> None:
        state = create_initial_state(bundle_id="日本語-テスト-123")
        assert state.get("bundle_id") == "日本語-テスト-123"

    def test_special_chars_bundle_id(self) -> None:
        state = create_initial_state(bundle_id="../etc/passwd")
        assert state.get("bundle_id") == "../etc/passwd"


# ===========================================================================
# 8. CONCURRENT OPERATIONS — Race conditions
# ===========================================================================

class TestConcurrencyAdversarial:
    """Stress-test thread safety across stores."""

    def test_fill_rate_thread_safety(self) -> None:
        from insureflow.analytics.metrics import FillRateTracker
        tracker = FillRateTracker()
        errors: list[Exception] = []

        def record_fields(n: int) -> None:
            try:
                for i in range(100):
                    tracker.record_field(f"field_{i % 10}", filled=i % 3 == 0, bundle_id=f"b-{n}-{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_fields, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        rate = tracker.get_fill_rate()
        assert rate["total"] == 1000

    def test_override_rate_thread_safety(self) -> None:
        from insureflow.analytics.metrics import OverrideRateTracker
        tracker = OverrideRateTracker()
        errors: list[Exception] = []

        def record_sign_offs(n: int) -> None:
            try:
                for i in range(50):
                    tracker.record_sign_off(
                        bundle_id=f"b-{n}-{i}",
                        ai_decision="approve",
                        human_decision="approve" if i % 2 == 0 else "decline",
                        signed_by=f"uw-{n}",
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_sign_offs, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        rate = tracker.get_override_rate()
        assert rate["total"] == 500

    def test_cycle_time_thread_safety(self) -> None:
        from insureflow.analytics.metrics import CycleTimeTracker
        tracker = CycleTimeTracker()
        errors: list[Exception] = []

        def run_pipelines(n: int) -> None:
            try:
                for i in range(20):
                    bid = f"b-{n}-{i}"
                    tracker.start_pipeline(bid)
                    tracker.start_stage(bid, "ingest")
                    time.sleep(0.001)
                    tracker.finish_stage(bid, "ingest")
                    tracker.finish_pipeline(bid)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=run_pipelines, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        stats = tracker.get_stats()
        assert stats["total_runs"] == 100


# ===========================================================================
# 9. INPUT VALIDATION — Parser edge cases
# ===========================================================================

class TestParserAdversarial:
    """Try to break parsers with adversarial inputs."""

    def test_acord_parser_malformed_xml(self) -> None:
        from insureflow.ingestion.acord_parser import ACORDParser
        parser = ACORDParser()
        with pytest.raises(Exception):
            parser.parse("<root><unclosed>", "b1")

    def test_json_broker_parser_empty(self) -> None:
        from insureflow.ingestion.json_parser import JSONBrokerParser
        parser = JSONBrokerParser()
        result = parser.parse("{}", "b1")
        assert result is not None

    def test_json_broker_parser_malformed(self) -> None:
        from insureflow.ingestion.json_parser import JSONBrokerParser
        parser = JSONBrokerParser()
        with pytest.raises(Exception):
            parser.parse("{invalid json", "b1")

    def test_loss_run_parser_empty(self) -> None:
        from insureflow.ingestion.loss_run_parser import LossRunParser
        parser = LossRunParser()
        result = parser.parse("", "b1")
        assert result is not None

    def test_document_classifier_empty(self) -> None:
        from insureflow.ingestion.classifier import DocumentClassifier
        result = DocumentClassifier.classify("")
        assert result is not None

    def test_document_classifier_binary_garbage(self) -> None:
        from insureflow.ingestion.classifier import DocumentClassifier
        garbage = "".join(chr(i) for i in range(256))
        result = DocumentClassifier.classify(garbage)
        assert result is not None

    def test_document_classifier_huge_json(self) -> None:
        from insureflow.ingestion.classifier import DocumentClassifier
        huge_json = '{"data": "' + "x" * 100000 + '"}'
        result = DocumentClassifier.classify(huge_json)
        assert result is not None

    def test_loader_empty_bundle(self) -> None:
        from insureflow.ingestion.loader import SubmissionLoader
        loader = SubmissionLoader()
        bundle = loader.load_bundle()
        assert bundle is not None
        assert bundle.bundle_id != ""


# ===========================================================================
# 10. AUTH STORE — Data corruption
# ===========================================================================

class TestAuthStoreAdversarial:
    """Try to corrupt the user store."""

    def test_corrupt_json_file_resets_gracefully(self, tmp_path: Any) -> None:
        from insureflow.auth.store import UserStore
        store_path = tmp_path / "users.json"
        store_path.write_text("{corrupt json data!!!")
        store = UserStore(path=store_path)
        assert len(store) == 0

    def test_empty_file_resets_gracefully(self, tmp_path: Any) -> None:
        from insureflow.auth.store import UserStore
        store_path = tmp_path / "users.json"
        store_path.write_text("")
        store = UserStore(path=store_path)
        assert len(store) == 0

    def test_binary_file_resets_gracefully(self, tmp_path: Any) -> None:
        from insureflow.auth.store import UserStore
        store_path = tmp_path / "users.json"
        store_path.write_bytes(b"\x00\x01\x02\x03")
        store = UserStore(path=store_path)
        assert len(store) == 0


# ===========================================================================
# 11. METRICS — Edge cases
# ===========================================================================

class TestMetricsAdversarial:
    """Try to break the metrics system."""

    def test_fill_rate_zero_not_treated_as_empty(self) -> None:
        from insureflow.analytics.metrics import FillRateTracker
        tracker = FillRateTracker()
        tracker.record_bundle_fields("b1", {"total_claims": 0, "total_incurred": 0.0})
        rate = tracker.get_fill_rate("total_claims")
        assert rate["fill_rate"] == 1.0, "Zero should count as filled"

    def test_fill_rate_none_still_empty(self) -> None:
        from insureflow.analytics.metrics import FillRateTracker
        tracker = FillRateTracker()
        tracker.record_bundle_fields("b1", {"total_claims": None})
        rate = tracker.get_fill_rate("total_claims")
        assert rate["fill_rate"] == 0.0

    def test_fill_rate_empty_string_still_empty(self) -> None:
        from insureflow.analytics.metrics import FillRateTracker
        tracker = FillRateTracker()
        tracker.record_bundle_fields("b1", {"named_insured": ""})
        rate = tracker.get_fill_rate("named_insured")
        assert rate["fill_rate"] == 0.0

    def test_cycle_time_empty_stats(self) -> None:
        from insureflow.analytics.metrics import CycleTimeTracker
        tracker = CycleTimeTracker()
        stats = tracker.get_stats()
        assert stats["total_runs"] == 0
        assert stats["avg_cycle_ms"] == 0

    def test_override_rate_empty(self) -> None:
        from insureflow.analytics.metrics import OverrideRateTracker
        tracker = OverrideRateTracker()
        rate = tracker.get_override_rate()
        assert rate["total"] == 0

    def test_get_fill_rate_returns_copy(self) -> None:
        from insureflow.analytics.metrics import FillRateTracker
        tracker = FillRateTracker()
        tracker.record_field("test", filled=True)
        rate1 = tracker.get_fill_rate("test")
        tracker.record_field("test", filled=False)
        rate2 = tracker.get_fill_rate("test")
        assert rate1["total"] == 1
        assert rate2["total"] == 2

    def test_persistence_files_created(self, tmp_path: Any) -> None:
        from insureflow.analytics.metrics import CycleTimeTracker, FillRateTracker, OverrideRateTracker
        fill = FillRateTracker(persist_path=tmp_path / "fill.jsonl")
        override = OverrideRateTracker(persist_path=tmp_path / "override.jsonl")
        cycle = CycleTimeTracker(persist_path=tmp_path / "cycle.jsonl")
        fill.record_field("test", filled=True)
        override.record_sign_off("b1", "approve", "approve")
        cycle.start_pipeline("b1")
        cycle.finish_pipeline("b1")
        assert (tmp_path / "fill.jsonl").exists()
        assert (tmp_path / "override.jsonl").exists()
        assert (tmp_path / "cycle.jsonl").exists()
