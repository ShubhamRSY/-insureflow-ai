from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from insureflow.registry.models import (
    AgentLogicVersion,
    ChangeRequest,
    ComplianceRuleVersion,
    ComponentType,
    LLMConfigVersion,
    PromptVersion,
    RegistryEntry,
    RegistryEntryStatus,
    RegistrySnapshot,
    ReviewComment,
)


class RegistryService:
    """Track, version, diff, and review model component changes.

    Stores entries as JSON under ``.insureflow/registry/`` so no external
    database is required.  Designed for compliance-team workflows:
    draft → submit for review → approve / reject.
    """

    def __init__(self, base_path: Path | None = None) -> None:
        self.base_path = base_path or Path.cwd() / ".insureflow" / "registry"
        self.base_path.mkdir(parents=True, exist_ok=True)
        (self.base_path / "prompts").mkdir(exist_ok=True)
        (self.base_path / "llm_configs").mkdir(exist_ok=True)
        (self.base_path / "compliance_rules").mkdir(exist_ok=True)
        (self.base_path / "agent_logic").mkdir(exist_ok=True)
        (self.base_path / "change_requests").mkdir(exist_ok=True)
        (self.base_path / "snapshots").mkdir(exist_ok=True)

    # ── helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _compute_checksum(data: dict[str, Any]) -> str:
        raw = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]

    def _entry_path(self, entry: RegistryEntry) -> Path:
        folder = {
            ComponentType.PROMPT: "prompts",
            ComponentType.LLM_CONFIG: "llm_configs",
            ComponentType.COMPLIANCE_RULE: "compliance_rules",
            ComponentType.AGENT_LOGIC: "agent_logic",
        }[entry.component_type]
        return self.base_path / folder / f"{entry.entry_id}.json"

    def _all_in_folder(self, folder: str) -> list[Path]:
        folder_path = self.base_path / folder
        if not folder_path.exists():
            return []
        return sorted(folder_path.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)

    @staticmethod
    def _load_entry(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _entry_from_dict(data: dict[str, Any]) -> RegistryEntry:
        ct = ComponentType(data["component_type"])
        if ct == ComponentType.PROMPT:
            return PromptVersion(**data)
        if ct == ComponentType.LLM_CONFIG:
            return LLMConfigVersion(**data)
        if ct == ComponentType.COMPLIANCE_RULE:
            return ComplianceRuleVersion(**data)
        if ct == ComponentType.AGENT_LOGIC:
            return AgentLogicVersion(**data)
        return RegistryEntry(**data)

    @staticmethod
    def _snapshot_path(base: Path, snapshot_id: str) -> Path:
        return base / "snapshots" / f"{snapshot_id}.json"

    # ── CRUD ────────────────────────────────────────────────────────────

    def create(self, entry: RegistryEntry) -> RegistryEntry:
        entry.checksum = self._compute_checksum(entry.model_dump())
        entry.updated_at = datetime.now(tz=timezone.utc)
        self._entry_path(entry).write_text(
            json.dumps(entry.model_dump(), indent=2, default=str, ensure_ascii=False),
            encoding="utf-8",
        )
        return entry

    def get(
        self,
        entry_id: str,
        component_type: ComponentType | None = None,
    ) -> RegistryEntry | None:
        if component_type:
            candidates = [
                self.base_path
                / {
                    ComponentType.PROMPT: "prompts",
                    ComponentType.LLM_CONFIG: "llm_configs",
                    ComponentType.COMPLIANCE_RULE: "compliance_rules",
                    ComponentType.AGENT_LOGIC: "agent_logic",
                }[component_type]
                / f"{entry_id}.json"
            ]
        else:
            candidates = []
            for folder in ("prompts", "llm_configs", "compliance_rules", "agent_logic"):
                p = self.base_path / folder / f"{entry_id}.json"
                if p.exists():
                    candidates.append(p)
                    break
        for path in candidates:
            if path.exists():
                return self._entry_from_dict(self._load_entry(path))
        return None

    def update(self, entry: RegistryEntry) -> RegistryEntry:
        entry.checksum = self._compute_checksum(entry.model_dump())
        entry.updated_at = datetime.now(tz=timezone.utc)
        self._entry_path(entry).write_text(
            json.dumps(entry.model_dump(), indent=2, default=str, ensure_ascii=False),
            encoding="utf-8",
        )
        return entry

    def list_versions(self, component_type: ComponentType) -> list[RegistryEntry]:
        folder = {
            ComponentType.PROMPT: "prompts",
            ComponentType.LLM_CONFIG: "llm_configs",
            ComponentType.COMPLIANCE_RULE: "compliance_rules",
            ComponentType.AGENT_LOGIC: "agent_logic",
        }[component_type]
        entries = []
        for path in self._all_in_folder(folder):
            try:
                entries.append(self._entry_from_dict(self._load_entry(path)))
            except Exception:
                continue
        return entries

    def get_active_version(
        self,
        component_type: ComponentType,
        key: str = "",
    ) -> RegistryEntry | None:
        entries = self.list_versions(component_type)
        for e in entries:
            if e.status == RegistryEntryStatus.APPROVED:
                if not key:
                    return e
                if isinstance(e, PromptVersion) and e.prompt_key == key:
                    return e
                if isinstance(e, LLMConfigVersion) and e.model_tier == key:
                    return e
                if isinstance(e, AgentLogicVersion) and e.agent_type == key:
                    return e
        return None

    def mark_superseded(self, entry_id: str, superseded_by: str) -> None:
        entry = self.get(entry_id)
        if entry:
            entry.status = RegistryEntryStatus.SUPERSEDED
            entry.superseded_by = superseded_by
            self.update(entry)

    # ── Review workflow ─────────────────────────────────────────────────

    def submit_for_review(self, entry_id: str) -> RegistryEntry | None:
        entry = self.get(entry_id)
        if entry and entry.status == RegistryEntryStatus.DRAFT:
            entry.status = RegistryEntryStatus.REVIEW
            self.update(entry)
        return entry

    def approve(self, entry_id: str, reviewer: str = "", comment: str = "") -> RegistryEntry | None:
        entry = self.get(entry_id)
        if entry and entry.status == RegistryEntryStatus.REVIEW:
            old_active = self.get_active_version(entry.component_type)
            entry.status = RegistryEntryStatus.APPROVED
            entry.active_at = datetime.now(tz=timezone.utc)
            if comment:
                entry.review_comments.append(ReviewComment(reviewer=reviewer, comment=comment))
            self.update(entry)
            if old_active and old_active.entry_id != entry.entry_id:
                self.mark_superseded(old_active.entry_id, entry.entry_id)
        return entry

    def reject(self, entry_id: str, reviewer: str = "", comment: str = "") -> RegistryEntry | None:
        entry = self.get(entry_id)
        if entry and entry.status == RegistryEntryStatus.REVIEW:
            entry.status = RegistryEntryStatus.REJECTED
            if comment:
                entry.review_comments.append(ReviewComment(reviewer=reviewer, comment=comment))
            self.update(entry)
        return entry

    def add_comment(self, entry_id: str, reviewer: str, comment: str) -> RegistryEntry | None:
        entry = self.get(entry_id)
        if entry:
            entry.review_comments.append(ReviewComment(reviewer=reviewer, comment=comment))
            self.update(entry)
        return entry

    # ── Diff ────────────────────────────────────────────────────────────

    def compute_diff(self, entry_id_a: str, entry_id_b: str) -> dict[str, Any]:
        entry_a = self.get(entry_id_a)
        entry_b = self.get(entry_id_b)
        if not entry_a or not entry_b:
            return {"error": "One or both entries not found"}
        if entry_a.component_type != entry_b.component_type:
            return {"error": "Cannot diff across different component types"}
        if isinstance(entry_a, PromptVersion) and isinstance(entry_b, PromptVersion):
            return entry_a.compute_diff(entry_b)
        if isinstance(entry_a, LLMConfigVersion) and isinstance(entry_b, LLMConfigVersion):
            return entry_a.compute_diff(entry_b)
        if isinstance(entry_a, ComplianceRuleVersion) and isinstance(
            entry_b,
            ComplianceRuleVersion,
        ):
            return entry_a.compute_diff(entry_b)
        if isinstance(entry_a, AgentLogicVersion) and isinstance(entry_b, AgentLogicVersion):
            return entry_a.compute_diff(entry_b)
        return {
            "from_version": entry_b.version_label,
            "to_version": entry_a.version_label,
            "checksums": {"from": entry_b.checksum, "to": entry_a.checksum},
            "changed": entry_a.checksum != entry_b.checksum,
        }

    # ── Snapshots ──────────────────────────────────────────────────────

    def take_snapshot(self, bundle_id: str = "") -> RegistrySnapshot:
        snapshot = RegistrySnapshot(bundle_id=bundle_id)
        for prompt in self.list_versions(ComponentType.PROMPT):
            if prompt.status == RegistryEntryStatus.APPROVED and isinstance(prompt, PromptVersion):
                snapshot.prompts[prompt.prompt_key] = prompt.entry_id
        for llm in self.list_versions(ComponentType.LLM_CONFIG):
            if llm.status == RegistryEntryStatus.APPROVED and isinstance(llm, LLMConfigVersion):
                snapshot.llm_configs[llm.model_tier] = llm.entry_id
        for rule in self.list_versions(ComponentType.COMPLIANCE_RULE):
            if rule.status == RegistryEntryStatus.APPROVED:
                snapshot.compliance_rules.append(rule.entry_id)
        for agent in self.list_versions(ComponentType.AGENT_LOGIC):
            if agent.status == RegistryEntryStatus.APPROVED and isinstance(
                agent,
                AgentLogicVersion,
            ):
                snapshot.agent_logic[agent.agent_type] = agent.entry_id
        self._snapshot_path(self.base_path, snapshot.snapshot_id).write_text(
            json.dumps(snapshot.model_dump(), indent=2, default=str, ensure_ascii=False),
            encoding="utf-8",
        )
        return snapshot

    def get_snapshot(self, snapshot_id: str) -> RegistrySnapshot | None:
        path = self._snapshot_path(self.base_path, snapshot_id)
        if path.exists():
            return RegistrySnapshot(**json.loads(path.read_text(encoding="utf-8")))
        return None

    def list_snapshots(self) -> list[RegistrySnapshot]:
        snapshots = []
        for path in self._all_in_folder("snapshots"):
            try:
                snapshots.append(RegistrySnapshot(**json.loads(path.read_text(encoding="utf-8"))))
            except Exception:
                continue
        return snapshots

    # ── Change requests ─────────────────────────────────────────────────

    def create_change_request(self, title: str, entry_ids: list[str], description: str = "", requested_by: str = "") -> ChangeRequest:
        cr = ChangeRequest(
            title=title,
            description=description,
            entries=entry_ids,
            requested_by=requested_by,
        )
        self._save_change_request(cr)
        return cr

    def _save_change_request(self, cr: ChangeRequest) -> None:
        path = self.base_path / "change_requests" / f"{cr.request_id}.json"
        path.write_text(
            json.dumps(cr.model_dump(), indent=2, default=str, ensure_ascii=False),
            encoding="utf-8",
        )

    def approve_change_request(
        self,
        request_id: str,
        reviewer: str = "",
        notes: str = "",
    ) -> ChangeRequest | None:
        cr = self._load_change_request(request_id)
        if not cr:
            return None
        cr.status = RegistryEntryStatus.APPROVED
        cr.reviewed_by = reviewer
        cr.review_decision = "approved"
        cr.review_comments = notes
        cr.updated_at = datetime.now(tz=timezone.utc)
        for entry_id in cr.entries:
            self.approve(entry_id, reviewer=reviewer, comment=notes)
        self._save_change_request(cr)
        return cr

    def reject_change_request(
        self,
        request_id: str,
        reviewer: str = "",
        notes: str = "",
    ) -> ChangeRequest | None:
        cr = self._load_change_request(request_id)
        if not cr:
            return None
        cr.status = RegistryEntryStatus.REJECTED
        cr.reviewed_by = reviewer
        cr.review_decision = "rejected"
        cr.review_comments = notes
        cr.updated_at = datetime.now(tz=timezone.utc)
        for entry_id in cr.entries:
            self.reject(entry_id, reviewer=reviewer, comment=notes)
        self._save_change_request(cr)
        return cr

    def _load_change_request(self, request_id: str) -> ChangeRequest | None:
        path = self.base_path / "change_requests" / f"{request_id}.json"
        if path.exists():
            return ChangeRequest(**json.loads(path.read_text(encoding="utf-8")))
        return None

    def list_change_requests(self) -> list[ChangeRequest]:
        results = []
        for path in self._all_in_folder("change_requests"):
            try:
                results.append(ChangeRequest(**json.loads(path.read_text(encoding="utf-8"))))
            except Exception:
                continue
        return results

    # ── Bootstrap: seed approved versions from current code ────────────

    def bootstrap(self, created_by: str = "system") -> list[RegistryEntry]:
        from insureflow.agents.prompts import SYSTEM_PROMPTS
        from insureflow.config import settings
        from insureflow.mortgage.compliance import BANK_RULES

        created: list[RegistryEntry] = []

        for prompt_key, prompt_text in SYSTEM_PROMPTS.items():
            entry = PromptVersion(
                component_type=ComponentType.PROMPT,
                version_label="1.0.0",
                status=RegistryEntryStatus.APPROVED,
                created_by=created_by,
                description=f"Initial {prompt_key} prompt",
                prompt_key=prompt_key,
                prompt_text=prompt_text,
                prompt_hash=hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()[:16],
                active_at=datetime.now(tz=timezone.utc),
            )
            e = self.create(entry)
            created.append(e)

        for tier, provider, model, temp, tokens in [
            (
                "cheap",
                settings.llm_cheap_provider,
                settings.llm_cheap_model,
                settings.llm_temperature,
                settings.llm_max_tokens,
            ),
            (
                "expensive",
                settings.llm_expensive_provider,
                settings.llm_expensive_model,
                settings.llm_temperature,
                settings.llm_max_tokens,
            ),
            (
                "default",
                settings.llm_provider,
                settings.llm_model,
                settings.llm_temperature,
                settings.llm_max_tokens,
            ),
        ]:
            entry = LLMConfigVersion(
                component_type=ComponentType.LLM_CONFIG,
                version_label="1.0.0",
                status=RegistryEntryStatus.APPROVED,
                created_by=created_by,
                description=f"Initial {tier} LLM config",
                model_tier=tier,
                provider=provider or "",
                model_name=model,
                temperature=temp,
                max_tokens=tokens,
                active_at=datetime.now(tz=timezone.utc),
            )
            e = self.create(entry)
            created.append(e)

        rules_snapshot = {}
        for rule in BANK_RULES:
            rules_snapshot[rule.rule_id] = {
                "name": rule.name,
                "severity": rule.severity,
                "product_lines": [p.value for p in rule.product_lines],
            }
        rule_entry = ComplianceRuleVersion(
            component_type=ComponentType.COMPLIANCE_RULE,
            version_label="1.0.0",
            status=RegistryEntryStatus.APPROVED,
            created_by=created_by,
            description="Initial bank compliance rules",
            rules_snapshot=rules_snapshot,
            active_at=datetime.now(tz=timezone.utc),
        )
        e = self.create(rule_entry)
        created.append(e)

        agent_types = [
            ("compliance_agent", "insureflow/agents/compliance_agent.py"),
            ("loss_run_analyst", "insureflow/agents/loss_run_analyst.py"),
            ("fraud_detection", "insureflow/agents/fraud_detection_agent.py"),
            ("uw_decision", "insureflow/agents/uw_decision_agent.py"),
            ("risk_analyst", "insureflow/agents/react_agent.py"),
        ]
        for agent_type, source_file in agent_types:
            entry = AgentLogicVersion(
                component_type=ComponentType.AGENT_LOGIC,
                version_label="1.0.0",
                status=RegistryEntryStatus.APPROVED,
                created_by=created_by,
                description=f"Initial {agent_type} agent logic",
                agent_type=agent_type,
                source_file=source_file,
                source_hash="bootstrap",
                active_at=datetime.now(tz=timezone.utc),
            )
            e = self.create(entry)
            created.append(e)

        return created

    def version_context(self) -> dict[str, Any]:
        prompts = {}
        for p in self.list_versions(ComponentType.PROMPT):
            if p.status == RegistryEntryStatus.APPROVED and isinstance(p, PromptVersion):
                if p.prompt_key not in prompts:
                    prompts[p.prompt_key] = {
                        "version": p.version_label,
                        "entry_id": p.entry_id,
                        "hash": p.prompt_hash,
                        "approved_at": p.active_at.isoformat() if p.active_at else None,
                    }
        llm_configs = {}
        for c in self.list_versions(ComponentType.LLM_CONFIG):
            if c.status == RegistryEntryStatus.APPROVED and isinstance(c, LLMConfigVersion):
                if c.model_tier not in llm_configs:
                    llm_configs[c.model_tier] = {
                        "version": c.version_label,
                        "entry_id": c.entry_id,
                        "model": c.model_name,
                        "provider": c.provider,
                        "approved_at": c.active_at.isoformat() if c.active_at else None,
                    }
        rules = []
        for r in self.list_versions(ComponentType.COMPLIANCE_RULE):
            if r.status == RegistryEntryStatus.APPROVED:
                rules.append(r.entry_id)
        agents = {}
        for a in self.list_versions(ComponentType.AGENT_LOGIC):
            if a.status == RegistryEntryStatus.APPROVED and isinstance(a, AgentLogicVersion):
                if a.agent_type not in agents:
                    agents[a.agent_type] = {
                        "version": a.version_label,
                        "entry_id": a.entry_id,
                        "source_file": a.source_file,
                        "hash": a.source_hash,
                        "approved_at": a.active_at.isoformat() if a.active_at else None,
                    }
        return {
            "prompts": prompts,
            "llm_configs": llm_configs,
            "compliance_rules": rules,
            "agent_logic": agents,
        }
