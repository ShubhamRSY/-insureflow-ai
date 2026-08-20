"""Production business KPIs for underwriting performance.

Tracks the seven carrier-facing metrics:
  1. Cycle time (first-pass)
  2. ROI% = (Net Profit / Cost of Investment) × 100
     Net Profit = Total Return − Total Cost
  3. Override rate (UW vs AI)
  4. Bind rate after Accept
  5. Loss ratio (AI-assisted book)
  6. Straight-through vs referred mix
  7. Missing-doc / conflict catch rate

Persists durable JSONL events under ``audit_logs/metrics/`` so numbers survive restarts.
"""

from __future__ import annotations

import logging
import os
import threading
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from insureflow.storage.lock import atomic_append

logger = logging.getLogger(__name__)

# Pilot / production targets (also documented in PILOT_PARTNER_BRIEF)
TARGETS: dict[str, dict[str, Any]] = {
    "cycle_time": {"p95_seconds_max": 900.0, "label": "p95 first-pass ≤ 15 min"},
    "override_rate": {"max": 0.25, "label": "override rate < 25%"},
    "bind_rate_after_accept": {"min": 0.40, "label": "bind rate after Accept ≥ 40%"},
    "loss_ratio": {"max": 0.70, "label": "portfolio LR ≤ 70% (book-dependent)"},
    "stp_rate": {"min": 0.30, "label": "straight-through share ≥ 30% (when Accept path exists)"},
    "catch_rate": {"min": 0.90, "label": "missing-doc/conflict catch ≥ 90% on labeled cases"},
    "roi": {
        "baseline_first_pass_seconds": 7200.0,
        "loaded_uw_usd_per_hour": 175.0,
        "planning_volume": 1000,
        "min_percent": 0.0,
        "label": "ROI% = (Net Profit / Cost of Investment) × 100 · Net Profit = Total Return − Total Cost",
    },
}

# Published monthly list from pricing.html — Cost of Investment, not an invoice.
_PLAN_MONTHLY_USD = {
    "pilot": 0.0,
    "desk": 799.0,
    "book": 2490.0,
    "enterprise": 6500.0,
}


class DecisionRoutingRecord(BaseModel):
    """One pipeline decision for STP / refer / decline mix."""

    bundle_id: str
    decision: str
    routing: str  # straight_through | referred | declined | other
    human_review_required: bool = False
    missing_docs: bool = False
    conflict_detected: bool = False
    org_id: str = "default"
    source: str = "pipeline"  # pipeline | labeled_scenario | bootstrap
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    record_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    cycle_ms: float | None = None


class CatchEventRecord(BaseModel):
    """Whether the system caught a known data-quality issue."""

    bundle_id: str
    catch_type: str  # missing_doc | conflict | other
    caught: bool
    expected: bool = True  # labeled case expected a catch
    detail: str = ""
    org_id: str = "default"
    source: str = "pipeline"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    record_id: str = Field(default_factory=lambda: uuid.uuid4().hex)


def _routing_bucket(decision: str, human_review_required: bool = False) -> str:
    d = (decision or "").strip().lower()
    if d in {"decline", "declined"}:
        return "declined"
    if d in {"refer", "conditional_accept"} or human_review_required:
        return "referred"
    if d in {"accept", "approve", "accepted"}:
        return "straight_through"
    return "other"


class DecisionRoutingTracker:
    def __init__(self, persist_path: Path | None = None) -> None:
        self._lock = threading.Lock()
        self._records: list[DecisionRoutingRecord] = []
        self._persist_path = persist_path or Path(os.getenv("DECISION_ROUTING_PATH", "./audit_logs/metrics/decision_routing.jsonl"))
        self._load()

    def _load(self) -> None:
        if not self._persist_path.exists():
            return
        try:
            for line in self._persist_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self._records.append(DecisionRoutingRecord.model_validate_json(line))
        except Exception as exc:
            logger.debug("Decision routing load failed: %s", exc)

    def record(
        self,
        bundle_id: str,
        decision: str,
        *,
        human_review_required: bool = False,
        missing_docs: bool = False,
        conflict_detected: bool = False,
        org_id: str = "default",
        source: str = "pipeline",
        cycle_ms: float | None = None,
    ) -> DecisionRoutingRecord:
        rec = DecisionRoutingRecord(
            bundle_id=bundle_id,
            decision=decision,
            routing=_routing_bucket(decision, human_review_required),
            human_review_required=human_review_required,
            missing_docs=missing_docs,
            conflict_detected=conflict_detected,
            org_id=org_id,
            source=source,
            cycle_ms=cycle_ms,
        )
        with self._lock:
            self._records.append(rec)
            try:
                atomic_append(self._persist_path, rec.model_dump_json())
            except OSError:
                logger.debug("Failed to persist decision routing", exc_info=True)
        return rec

    def stats(self, org_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            rows = [r for r in self._records if org_id is None or r.org_id == org_id]
        if not rows:
            return {
                "sample_size": 0,
                "straight_through": 0,
                "referred": 0,
                "declined": 0,
                "other": 0,
                "stp_rate": 0.0,
                "refer_rate": 0.0,
                "decline_rate": 0.0,
                "by_decision": {},
            }
        buckets: dict[str, int] = defaultdict(int)
        by_decision: dict[str, int] = defaultdict(int)
        for r in rows:
            buckets[r.routing] += 1
            by_decision[r.decision.lower()] += 1
        n = len(rows)
        return {
            "sample_size": n,
            "straight_through": buckets["straight_through"],
            "referred": buckets["referred"],
            "declined": buckets["declined"],
            "other": buckets["other"],
            "stp_rate": round(buckets["straight_through"] / n, 4),
            "refer_rate": round(buckets["referred"] / n, 4),
            "decline_rate": round(buckets["declined"] / n, 4),
            "by_decision": dict(by_decision),
        }


class CatchRateTracker:
    def __init__(self, persist_path: Path | None = None) -> None:
        self._lock = threading.Lock()
        self._records: list[CatchEventRecord] = []
        self._persist_path = persist_path or Path(os.getenv("CATCH_RATE_PATH", "./audit_logs/metrics/catch_rate.jsonl"))
        self._load()

    def _load(self) -> None:
        if not self._persist_path.exists():
            return
        try:
            for line in self._persist_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self._records.append(CatchEventRecord.model_validate_json(line))
        except Exception as exc:
            logger.debug("Catch rate load failed: %s", exc)

    def record(
        self,
        bundle_id: str,
        catch_type: str,
        caught: bool,
        *,
        expected: bool = True,
        detail: str = "",
        org_id: str = "default",
        source: str = "pipeline",
    ) -> CatchEventRecord:
        rec = CatchEventRecord(
            bundle_id=bundle_id,
            catch_type=catch_type,
            caught=caught,
            expected=expected,
            detail=detail,
            org_id=org_id,
            source=source,
        )
        with self._lock:
            self._records.append(rec)
            try:
                atomic_append(self._persist_path, rec.model_dump_json())
            except OSError:
                logger.debug("Failed to persist catch event", exc_info=True)
        return rec

    def stats(self, org_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            rows = [r for r in self._records if org_id is None or r.org_id == org_id]
        expected = [r for r in rows if r.expected]
        if not expected:
            return {"sample_size": 0, "caught": 0, "missed": 0, "catch_rate": 0.0, "by_type": {}}
        caught = sum(1 for r in expected if r.caught)
        by_type: dict[str, dict[str, int]] = defaultdict(lambda: {"caught": 0, "missed": 0})
        for r in expected:
            key = "caught" if r.caught else "missed"
            by_type[r.catch_type][key] += 1
        return {
            "sample_size": len(expected),
            "caught": caught,
            "missed": len(expected) - caught,
            "catch_rate": round(caught / len(expected), 4),
            "by_type": dict(by_type),
        }


class BusinessKPIService:
    """Aggregate production KPIs from metrics + outcomes stores."""

    def __init__(
        self,
        *,
        decision_tracker: DecisionRoutingTracker | None = None,
        catch_tracker: CatchRateTracker | None = None,
    ) -> None:
        self.decisions = decision_tracker or DecisionRoutingTracker()
        self.catches = catch_tracker or CatchRateTracker()

    def record_pipeline_result(
        self,
        *,
        bundle_id: str,
        decision: str,
        org_id: str = "default",
        human_review_required: bool = False,
        missing_docs: list[str] | bool | None = None,
        conflict_detected: bool = False,
        cycle_ms: float | None = None,
        source: str = "pipeline",
    ) -> None:
        missing = bool(missing_docs) if not isinstance(missing_docs, list) else len(missing_docs) > 0
        self.decisions.record(
            bundle_id,
            decision,
            human_review_required=human_review_required or missing,
            missing_docs=missing,
            conflict_detected=conflict_detected,
            org_id=org_id,
            source=source,
            cycle_ms=cycle_ms,
        )
        if missing:
            self.catches.record(
                bundle_id,
                "missing_doc",
                caught=True,
                expected=True,
                detail=str(missing_docs)[:200] if missing_docs else "missing docs",
                org_id=org_id,
                source=source,
            )
        if conflict_detected:
            self.catches.record(
                bundle_id,
                "conflict",
                caught=True,
                expected=True,
                detail="reconciliation conflict",
                org_id=org_id,
                source=source,
            )

    def compute(self, org_id: str = "default") -> dict[str, Any]:
        from insureflow.analytics.metrics import get_pipeline_metrics
        from insureflow.outcomes.feedback import FeedbackEngine
        from insureflow.outcomes.store import OutcomeStore

        metrics = get_pipeline_metrics()
        cycle = metrics.cycle_time.get_stats()
        override = metrics.override_rate.get_override_rate()
        routing = self.decisions.stats(org_id=org_id)
        catch = self.catches.stats(org_id=org_id)

        store = OutcomeStore()
        outcomes = store.list_outcomes(org_id)
        accepts = [o for o in outcomes if (o.uw_decision or o.ai_decision or "").lower() in {"accept", "conditional_accept", "approve"}]
        bound = [o for o in accepts if o.status.value == "bound" or bool(o.policy_number)]
        bind_rate = (len(bound) / len(accepts)) if accepts else 0.0

        cal = FeedbackEngine(store).calibration_summary(org_id)
        # Control LR: experiences without AI book tag aren't separate yet — use portfolio LR
        # and expose sample_size so UI can show "not production-ready" when n=0.
        loss_ratio = float(cal.get("portfolio_loss_ratio") or cal.get("avg_loss_ratio") or 0.0)

        avg_s = (cycle.get("avg_cycle_ms") or 0) / 1000.0
        p95_s = (cycle.get("p95_cycle_ms") or 0) / 1000.0

        kpis = {
            "cycle_time": {
                "status": _status_cycle(cycle.get("total_runs", 0), p95_s),
                "sample_size": cycle.get("total_runs", 0),
                "value": round(avg_s, 3),
                "unit": "seconds_avg",
                "p50_seconds": round((cycle.get("p50_cycle_ms") or 0) / 1000.0, 3),
                "p95_seconds": round(p95_s, 3),
                "min_seconds": round((cycle.get("min_cycle_ms") or 0) / 1000.0, 3),
                "max_seconds": round((cycle.get("max_cycle_ms") or 0) / 1000.0, 3),
                "target": TARGETS["cycle_time"],
                "pass": cycle.get("total_runs", 0) > 0 and p95_s <= TARGETS["cycle_time"]["p95_seconds_max"],
                "what_to_say": _say_cycle(cycle.get("total_runs", 0), avg_s, p95_s),
            },
            "override_rate": {
                "status": _status_sample(override.get("total", 0), min_n=10),
                "sample_size": override.get("total", 0),
                "value": override.get("override_rate", 0.0),
                "unit": "rate",
                "overrides": override.get("overrides", 0),
                "agreements": override.get("agreements", 0),
                "upgrades": override.get("upgrade_count", 0),
                "downgrades": override.get("downgrade_count", 0),
                "target": TARGETS["override_rate"],
                "pass": override.get("total", 0) >= 10 and override.get("override_rate", 1) < TARGETS["override_rate"]["max"],
                "what_to_say": _say_override(override),
            },
            "bind_rate_after_accept": {
                "status": _status_sample(len(accepts), min_n=5),
                "sample_size": len(accepts),
                "value": round(bind_rate, 4),
                "unit": "rate",
                "accepts": len(accepts),
                "bound": len(bound),
                "target": TARGETS["bind_rate_after_accept"],
                "pass": len(accepts) >= 5 and bind_rate >= TARGETS["bind_rate_after_accept"]["min"],
                "what_to_say": _say_bind(len(accepts), len(bound), bind_rate),
            },
            "loss_ratio": {
                "status": _status_sample(cal.get("sample_size", 0), min_n=5),
                "sample_size": cal.get("sample_size", 0),
                "value": round(loss_ratio, 4),
                "unit": "ratio",
                "avg_loss_ratio": cal.get("avg_loss_ratio", 0.0),
                "portfolio_loss_ratio": cal.get("portfolio_loss_ratio", 0.0),
                "total_claims": cal.get("total_claims", 0),
                "target": TARGETS["loss_ratio"],
                "pass": cal.get("sample_size", 0) >= 5 and loss_ratio <= TARGETS["loss_ratio"]["max"],
                "what_to_say": _say_lr(cal.get("sample_size", 0), loss_ratio),
            },
            "stp_vs_referred": {
                "status": _status_sample(routing.get("sample_size", 0), min_n=10),
                "sample_size": routing.get("sample_size", 0),
                "value": routing.get("stp_rate", 0.0),
                "unit": "stp_rate",
                "straight_through": routing.get("straight_through", 0),
                "referred": routing.get("referred", 0),
                "declined": routing.get("declined", 0),
                "refer_rate": routing.get("refer_rate", 0.0),
                "decline_rate": routing.get("decline_rate", 0.0),
                "by_decision": routing.get("by_decision", {}),
                "target": TARGETS["stp_rate"],
                "pass": routing.get("sample_size", 0) >= 10,
                "what_to_say": _say_stp(routing),
            },
            "missing_doc_conflict_catch": {
                "status": _status_sample(catch.get("sample_size", 0), min_n=5),
                "sample_size": catch.get("sample_size", 0),
                "value": catch.get("catch_rate", 0.0),
                "unit": "rate",
                "caught": catch.get("caught", 0),
                "missed": catch.get("missed", 0),
                "by_type": catch.get("by_type", {}),
                "target": TARGETS["catch_rate"],
                "pass": catch.get("sample_size", 0) >= 5 and catch.get("catch_rate", 0) >= TARGETS["catch_rate"]["min"],
                "what_to_say": _say_catch(catch),
            },
            "roi": _compute_roi(cycle.get("total_runs", 0), avg_s),
        }

        ready_count = sum(1 for k in kpis.values() if k["status"] == "production_ready")
        measured_count = sum(1 for k in kpis.values() if k["sample_size"] > 0)

        return {
            "org_id": org_id,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "production_ready_count": ready_count,
            "measured_count": measured_count,
            "total_kpis": len(kpis),
            "overall": "production_ready" if ready_count >= 4 else "partial" if measured_count >= 3 else "not_ready",
            "targets": TARGETS,
            "kpis": kpis,
        }


def _platform_annual_usd() -> tuple[float, str]:
    """Annual Cost of Investment from published plan list (or RYTERA_ROI_PLATFORM_USD_ANNUAL)."""
    override = os.getenv("RYTERA_ROI_PLATFORM_USD_ANNUAL", "").strip()
    if override:
        try:
            return max(0.0, float(override)), "env:RYTERA_ROI_PLATFORM_USD_ANNUAL"
        except ValueError:
            pass
    try:
        from insureflow.billing.plan import current_plan

        plan_id = current_plan().plan_id
    except Exception:
        plan_id = "pilot"
    monthly = float(_PLAN_MONTHLY_USD.get(plan_id, 0.0))
    return monthly * 12.0, f"plan:{plan_id} list ${monthly:,.0f}/mo"


def _llm_annual_usd(n: int, volume: int) -> float:
    """Annualize measured LLM spend at planning volume. Zero when no tokens recorded."""
    if n <= 0:
        return 0.0
    try:
        from insureflow.llm.tracker import get_token_tracker

        spent = float(get_token_tracker().get_session_totals().get("total_cost") or 0.0)
    except Exception:
        spent = 0.0
    if spent <= 0:
        return 0.0
    return round((spent / n) * volume, 2)


def _compute_roi(
    n: int,
    avg_s: float,
    *,
    platform_usd_annual: float | None = None,
    llm_usd_annual: float | None = None,
    platform_source: str | None = None,
) -> dict[str, Any]:
    """ROI% = (Net Profit / Cost of Investment) × 100.

    Total Return = UW hours saved vs a 2-hour first pass × loaded hourly cost × planning volume.
    Cost of Investment = annual platform list + annualized LLM spend.
    Net Profit = Total Return − Cost of Investment.
    Assumptions labeled — not a billed invoice.
    """
    tgt = TARGETS["roi"]
    baseline = float(tgt["baseline_first_pass_seconds"])
    rate = float(tgt["loaded_uw_usd_per_hour"])
    volume = int(tgt["planning_volume"])
    hours_saved = max(0.0, (baseline - avg_s) / 3600.0) if n > 0 else 0.0
    usd_per_file = round(hours_saved * rate, 2)
    total_return = round(usd_per_file * volume, 2)

    if platform_usd_annual is None:
        platform_usd_annual, inferred_source = _platform_annual_usd()
        platform_source = platform_source or inferred_source
    else:
        platform_usd_annual = max(0.0, float(platform_usd_annual))
        platform_source = platform_source or "caller"

    if llm_usd_annual is None:
        llm_usd_annual = _llm_annual_usd(n, volume)
    else:
        llm_usd_annual = max(0.0, float(llm_usd_annual))

    cost = round(float(platform_usd_annual) + float(llm_usd_annual), 2)
    net_profit = round(total_return - cost, 2)
    roi_percent: float | None = round((net_profit / cost) * 100.0, 1) if cost > 0 else None

    desk_monthly = float(_PLAN_MONTHLY_USD["desk"])
    desk_cost = round(desk_monthly * 12.0 + float(llm_usd_annual), 2)
    planning_desk_net = round(total_return - desk_cost, 2)
    planning_desk_roi = round((planning_desk_net / desk_cost) * 100.0, 1) if desk_cost > 0 else None

    status = _status_sample(n, min_n=10)
    if n >= 10 and cost <= 0:
        status = "lab_partial"

    return {
        "status": status,
        "sample_size": n,
        "value": roi_percent,
        "unit": "percent",
        "formula": "ROI = (Net Profit / Cost of Investment) × 100",
        "net_profit_formula": "Net Profit = Total Return − Total Cost",
        "total_return_usd": total_return,
        "cost_of_investment_usd": cost,
        "net_profit_usd": net_profit,
        "platform_usd_annual": round(float(platform_usd_annual), 2),
        "llm_usd_annual": round(float(llm_usd_annual), 2),
        "cost_source": platform_source,
        "hours_saved_per_file": round(hours_saved, 3),
        "usd_per_file": usd_per_file,
        "annual_at_planning_volume_usd": total_return,
        "planning_volume": volume,
        "baseline_minutes": int(baseline / 60),
        "loaded_uw_usd_per_hour": rate,
        "measured_avg_seconds": round(avg_s, 3) if n else 0.0,
        "planning_at_desk": {
            "cost_of_investment_usd": desk_cost,
            "net_profit_usd": planning_desk_net,
            "roi_percent": planning_desk_roi,
            "note": f"Desk list ${desk_monthly:,.0f}/mo × 12 + LLM — labeled planning, not an invoice",
        },
        "target": tgt,
        "pass": n >= 10 and roi_percent is not None and roi_percent > float(tgt["min_percent"]),
        "what_to_say": _say_roi(n, hours_saved, usd_per_file, total_return, cost, net_profit, roi_percent, volume, rate),
    }


def _say_roi(
    n: int,
    hours_saved: float,
    usd_per_file: float,
    total_return: float,
    cost: float,
    net_profit: float,
    roi_percent: float | None,
    volume: int,
    rate: float,
) -> str:
    if n <= 0:
        return "No cycle-time samples yet — Total Return needs measured first-pass time vs a 2-hour desk. ROI% = (Net Profit / Cost of Investment) × 100."
    return_bit = f"Total Return ${total_return:,.0f} = {hours_saved:.2f}h saved/file × ${rate:.0f}/h × {volume:,} files/year (${usd_per_file:,.0f}/file vs a 2-hour first pass)."
    if cost <= 0:
        return f"{n} runs · {return_bit} Cost of Investment $0 (Pilot list / no LLM spend) — ROI% is undefined until there is a non-zero investment. Assumptions labeled — not a billed invoice."
    return (
        f"{n} runs · {return_bit} Cost of Investment ${cost:,.0f}. "
        f"Net Profit ${net_profit:,.0f} = Total Return − Total Cost. "
        f"ROI = ({net_profit:,.0f} / {cost:,.0f}) × 100 = {roi_percent:.1f}%. "
        "Assumptions labeled — not a billed invoice."
    )


def _status_sample(n: int, min_n: int) -> str:
    if n <= 0:
        return "not_measured"
    if n < min_n:
        return "lab_partial"
    return "production_ready"


def _status_cycle(n: int, p95_s: float) -> str:
    if n <= 0:
        return "not_measured"
    if n < 10:
        return "lab_partial"
    if p95_s <= TARGETS["cycle_time"]["p95_seconds_max"]:
        return "production_ready"
    return "lab_partial"


def _say_cycle(n: int, avg_s: float, p95_s: float) -> str:
    if n <= 0:
        return "No cycle-time samples yet — run submissions or bootstrap labeled scenarios."
    return f"{n} runs · avg {avg_s:.2f}s · p95 {p95_s:.2f}s (target p95 ≤ 15 min)."


def _say_override(o: dict[str, Any]) -> str:
    n = o.get("total", 0)
    if n <= 0:
        return "No licensed UW sign-offs recorded yet — override rate needs real HITL."
    return f"{o.get('overrides', 0)}/{n} decision changes ({o.get('override_rate', 0):.1%}). Target < 25%."


def _say_bind(accepts: int, bound: int, rate: float) -> str:
    if accepts <= 0:
        return "No Accept→bind outcomes yet — bind path ready, conversion not measured."
    return f"{bound}/{accepts} Accepts bound ({rate:.1%})."


def _say_lr(n: int, lr: float) -> str:
    if n <= 0:
        return "No loss experience posted — need 6–12 months of partner claims for LR vs control."
    return f"{n} policy-years · portfolio LR {lr:.1%}."


def _say_stp(r: dict[str, Any]) -> str:
    n = r.get("sample_size", 0)
    if n <= 0:
        return "No routing samples — pipeline decisions not recorded yet."
    return f"{n} decisions · STP {r.get('straight_through', 0)} ({r.get('stp_rate', 0):.1%}) · refer {r.get('referred', 0)} · decline {r.get('declined', 0)}."


def _say_catch(c: dict[str, Any]) -> str:
    n = c.get("sample_size", 0)
    if n <= 0:
        return "No labeled catch events yet — bootstrap missing-doc / conflict scenarios."
    return f"{c.get('caught', 0)}/{n} catches ({c.get('catch_rate', 0):.1%})."


_kpi_service: BusinessKPIService | None = None


def get_business_kpi_service() -> BusinessKPIService:
    global _kpi_service
    if _kpi_service is None:
        _kpi_service = BusinessKPIService()
    return _kpi_service


def bootstrap_business_kpis(*, org_id: str = "kpi-lab") -> dict[str, Any]:
    """Run labeled real-world scenarios and record production KPI events.

    Produces real measured numbers for cycle time, STP mix, and catch rate.
    Records lab sign-off agreements using each scenario's expected decision as
    UW ground truth (clearly sourced as ``labeled_scenario``).
    """
    import os
    import time

    from insureflow.analytics.metrics import get_pipeline_metrics
    from insureflow.testing.realworld_scenarios import build_all_scenarios, evaluate_result, run_scenario

    # Default oracles to auto; queries return errors when API keys are missing
    os.environ.setdefault("ORACLE_MODE", "auto")
    for k in ("CLUE_API_KEY", "APLUS_API_KEY", "NCCI_API_KEY", "CAT_API_KEY"):
        os.environ.pop(k, None)

    service = get_business_kpi_service()
    metrics = get_pipeline_metrics()
    scenarios = build_all_scenarios()
    rows: list[dict[str, Any]] = []

    for scenario in scenarios:
        bid = f"kpi-{scenario.id}-{uuid.uuid4().hex[:6]}"
        metrics.cycle_time.start_pipeline(bid, org_id=org_id)
        t0 = time.perf_counter()
        try:
            result = run_scenario(scenario, org_id=f"{org_id}-{scenario.id}")
            failures = evaluate_result(scenario, result)
            passed = len(failures) == 0
        except Exception as exc:
            metrics.cycle_time.finish_pipeline(bid, status="failed")
            rows.append({"id": scenario.id, "error": str(exc), "passed": False})
            continue
        elapsed_ms = (time.perf_counter() - t0) * 1000
        metrics.cycle_time.finish_pipeline(bid, status="completed" if passed else "failed")

        decision = str(result.get("ai_decision") or "").lower()
        # Label catch expectations from scenario id / condition
        expect_missing = scenario.id == "missing_docs_refer" or scenario.condition == "missing_data"
        expect_conflict = "discrepancy" in scenario.id or "cope" in scenario.id
        caught_missing = decision in {"refer", "conditional_accept", "decline"} if expect_missing else False
        caught_conflict = decision in {"refer", "conditional_accept", "decline"} if expect_conflict else False

        human_review = decision in {"refer", "conditional_accept"}
        service.record_pipeline_result(
            bundle_id=bid,
            decision=decision,
            org_id=org_id,
            human_review_required=human_review,
            missing_docs=expect_missing and caught_missing,
            conflict_detected=expect_conflict and caught_conflict,
            cycle_ms=elapsed_ms,
            source="labeled_scenario",
        )
        if expect_missing:
            service.catches.record(
                bid,
                "missing_doc",
                caught=caught_missing,
                expected=True,
                detail=scenario.id,
                org_id=org_id,
                source="labeled_scenario",
            )
        if expect_conflict:
            service.catches.record(
                bid,
                "conflict",
                caught=caught_conflict,
                expected=True,
                detail=scenario.id,
                org_id=org_id,
                source="labeled_scenario",
            )

        # Lab override proxy: primary expected decision vs AI
        expected = scenario.expectation.decision_in[0] if scenario.expectation.decision_in else decision
        # If AI decision is within allowed set, treat as UW agreement on that decision
        uw_decision = decision if decision in scenario.expectation.decision_in else expected
        metrics.override_rate.record_sign_off(
            bundle_id=bid,
            ai_decision=decision,
            human_decision=uw_decision,
            signed_by="labeled_scenario_ground_truth",
            override_reason="" if decision in scenario.expectation.decision_in else "outside_expectation",
            org_id=org_id,
        )

        rows.append(
            {
                "id": scenario.id,
                "decision": decision,
                "passed": passed,
                "failures": failures,
                "cycle_ms": round(elapsed_ms, 2),
                "expectation": list(scenario.expectation.decision_in),
            }
        )

    report = service.compute(org_id=org_id)
    report["bootstrap"] = {
        "scenarios_run": len(rows),
        "scenarios_passed": sum(1 for r in rows if r.get("passed")),
        "rows": rows,
        "note": (
            "Cycle time, STP mix, and catch rate are measured from labeled scenarios. "
            "Override rate here uses scenario expectations as UW ground truth (lab), "
            "not live licensed UW sign-offs. Bind rate and loss ratio still need production outcomes."
        ),
    }
    return report
