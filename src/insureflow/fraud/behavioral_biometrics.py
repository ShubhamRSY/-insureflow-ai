"""Behavioral biometrics — keystroke, pointer, and session-level anomaly scoring.

Humans type and move with noisy, slightly irregular rhythms; automation is
mechanically regular. This engine turns raw interaction telemetry into
statistical features (timing variance, paste ratio, pointer kinematics, session
breadth) and flags signatures consistent with scripts, bots, and hybrid
AI-human mimics.

All scoring is deterministic and explainable — each point maps to a named
behavioral signal.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Callable
from typing import Any

from insureflow.fraud.models import BehavioralSession, RiskAssessment

_PASTE_DEFAULT = 0.0


def _risk_level(score: float) -> str:
    return "critical" if score > 0.75 else "high" if score > 0.55 else "medium" if score > 0.3 else "low"


def _action(level: str) -> str:
    return {
        "critical": "force_manual_review",
        "high": "challenge_with_captcha",
        "medium": "step_up_verification",
        "low": "standard_processing",
    }[level]


def _cv(values: list[float]) -> float:
    """Coefficient of variation — normalized dispersion; very low = mechanical."""
    if len(values) < 2:
        return 0.0
    mean = statistics.fmean(values)
    if mean <= 0:
        return 1.0
    stdev = statistics.pstdev(values)
    return stdev / mean


class BehavioralBiometricsEngine:
    """Scores one interaction session for automation/impersonation signals."""

    def assess(self, session: BehavioralSession) -> RiskAssessment:
        score = 0.0
        signal_list: list[dict[str, Any]] = []
        flagged: list[str] = []

        def _add(name: str, weight: float, detail: str) -> None:
            nonlocal score
            if weight <= 0:
                return
            score = min(1.0, score + weight)
            signal_list.append({"signal": name, "weight": round(weight, 3), "detail": detail})
            flagged.append(detail)

        self._score_typing(session, _add)
        self._score_pointer(session, _add)
        self._score_session(session, _add)

        level = _risk_level(score)
        return RiskAssessment(
            engine="behavioral_biometrics",
            subject_id=session.subject_id or session.session_id,
            risk_score=round(score, 4),
            risk_level=level,
            signals=signal_list,
            flagged_patterns=flagged,
            recommended_action=_action(level),
        )

    def _score_typing(
        self,
        session: BehavioralSession,
        add: Callable[[str, float, str], None],
    ) -> None:
        flights = [k.flight_ms for k in session.keystrokes if k.flight_ms > 0]
        dwells = [k.dwell_ms for k in session.keystrokes if k.dwell_ms > 0]
        if not session.keystrokes:
            return

        flight_cv = _cv(flights)
        dwell_cv = _cv(dwells)

        # Mechanical regularity: near-zero variance in a decent-sized sample.
        if len(flights) >= 8 and flight_cv < 0.12:
            add("mechanical_timing", 0.4, f"keystroke flight-time CV {flight_cv:.3f} — abnormally regular for a human")

        if len(dwells) >= 8 and dwell_cv < 0.10:
            add("mechanical_dwell", 0.35, f"keystroke dwell-time CV {dwell_cv:.3f} — abnormally regular")

        # Scripted pacing: events occurring at a fixed grid interval.
        if len(flights) >= 5:
            rounded = [round(f, -1) for f in flights]
            if sum(1 for r in rounded if r == 0) == len(flights):
                add("scripted_pacing", 0.4, "keystroke timings cluster at a fixed grid — script-like")

        # Negative / impossible timings.
        if any(k.flight_ms < 0 or k.dwell_ms < 0 for k in session.keystrokes):
            add("impossible_timing", 0.25, "keystroke events report negative timing values")

        # Paste-dominant input.
        pastes = sum(1 for k in session.keystrokes if k.was_paste)
        if session.input_field_count > 0 and pastes / max(session.input_field_count, 1) > 0.7:
            add("autofill_paste_dominant", 0.3, f"{pastes} fields populated via paste/autofill")

    def _score_pointer(self, session: BehavioralSession, add: Callable[[str, float, str], None]) -> None:
        moves = [p for p in session.pointers if p.kind == "move"]
        if len(moves) < 3:
            if session.keystrokes and session.input_field_count > 0:
                add("no_pointer_activity", 0.15, "typing session with no mouse movement at all")
            return

        dists = []
        speeds: list[float] = []
        for i in range(1, len(moves)):
            dx = moves[i].x - moves[i - 1].x
            dy = moves[i].y - moves[i - 1].y
            dt = moves[i].t_ms - moves[i - 1].t_ms
            d = math.hypot(dx, dy)
            dists.append(d)
            if dt > 0:
                speeds.append(d / dt)

        # Perfectly straight pointer paths — humans curve; robots draw lines.
        if len(moves) >= 6:
            max_straightness = self._max_straight_run(moves)
            if max_straightness / len(moves) >= 0.9:
                add("teleporting_pointer", 0.3, f"{max_straightness} consecutive collinear pointer points")

        # Teleportation: instantaneous large jumps.
        if speeds and max(speeds) > 40:
            add("pointer_teleportation", 0.25, f"pointer velocity spike {max(speeds):.1f} px/ms")

        # Abnormally constant speed.
        if len(speeds) >= 6 and _cv(speeds) < 0.15:
            add("mechanical_pointer_speed", 0.3, "pointer speed CV abnormally low — scripted path")

        # Zero-dwell snaps (discrete jumps, e.g. coordinate-injected).
        jumps = sum(1 for d, dt in zip(dists, [moves[i + 1].t_ms - moves[i].t_ms for i in range(len(moves) - 1)]) if d > 60 and dt < 5)
        if jumps >= 3:
            add("coordinate_injection", 0.35, f"{jumps} instant pointer jumps — coordinate injection signature")

    def _score_session(self, session: BehavioralSession, add: Callable[[str, float, str], None]) -> None:
        if session.focus_events == 0 and session.scroll_events == 0 and session.session_duration_ms > 30_000:
            add("no_human_interaction", 0.2, "30s+ session with zero focus or scroll events")

        if session.input_field_count > 0 and session.pasted_field_count == session.input_field_count:
            add("all_fields_pasted", 0.2, "every input field populated by paste/autofill")

    @staticmethod
    def _max_straight_run(moves: list[Any]) -> int:
        best = 1
        run = 1
        for i in range(2, len(moves)):
            cross = abs((moves[i - 1].x - moves[i - 2].x) * (moves[i].y - moves[i - 1].y) - (moves[i - 1].y - moves[i - 2].y) * (moves[i].x - moves[i - 1].x))
            if cross < 0.0001:
                run += 1
                best = max(best, run)
            else:
                run = 1
        return best


def assess_session(session: BehavioralSession) -> RiskAssessment:
    return BehavioralBiometricsEngine().assess(session)
