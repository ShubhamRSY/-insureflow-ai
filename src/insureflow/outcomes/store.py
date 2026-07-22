from __future__ import annotations

import logging
from pathlib import Path

from insureflow.config import settings
from insureflow.outcomes.models import BindOutcome, LossExperience, PredictionRecord

logger = logging.getLogger(__name__)


class OutcomeStore:
    """Persist bind outcomes and loss experience for feedback loops."""

    def __init__(self, base_path: Path | None = None) -> None:
        self.base_path = base_path or settings.audit_log_path / "outcomes"
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _org_dir(self, org_id: str) -> Path:
        d = self.base_path / org_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_outcome(self, outcome: BindOutcome) -> None:
        path = self._org_dir(outcome.org_id) / f"{outcome.bundle_id}_outcome.json"
        path.write_text(outcome.model_dump_json(indent=2), encoding="utf-8")

    def get_outcome(self, bundle_id: str, org_id: str = "default") -> BindOutcome | None:
        path = self._org_dir(org_id) / f"{bundle_id}_outcome.json"
        if not path.exists():
            return None
        return BindOutcome.model_validate_json(path.read_text(encoding="utf-8"))

    def save_experience(self, exp: LossExperience) -> None:
        path = self._org_dir(exp.org_id) / f"{exp.policy_number}_{exp.policy_year}.json"
        path.write_text(exp.model_dump_json(indent=2), encoding="utf-8")

    def list_experiences(self, org_id: str = "default") -> list[LossExperience]:
        org_dir = self._org_dir(org_id)
        results: list[LossExperience] = []
        for path in org_dir.glob("*_*.json"):
            if "_outcome" in path.name:
                continue
            try:
                results.append(LossExperience.model_validate_json(path.read_text(encoding="utf-8")))
            except Exception as exc:
                logger.warning("Skipping corrupt experience file %s: %s", path.name, exc)
        return results

    def save_prediction(self, record: PredictionRecord, org_id: str = "default") -> None:
        path = self._org_dir(org_id) / f"{record.bundle_id}_prediction.json"
        path.write_text(record.model_dump_json(indent=2), encoding="utf-8")

    def get_prediction(self, bundle_id: str, org_id: str = "default") -> PredictionRecord | None:
        path = self._org_dir(org_id) / f"{bundle_id}_prediction.json"
        if not path.exists():
            return None
        return PredictionRecord.model_validate_json(path.read_text(encoding="utf-8"))
