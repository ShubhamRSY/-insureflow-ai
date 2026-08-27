"""Single source of truth for the score-based decision-tier thresholds.

Both the decision engine (``uw_decision_agent.py``, ``memo_sync.py``) and any
UI surfacing a "what does this score mean" legend must read these same
constants — never duplicate the numbers inline, or the two will drift.
See docs/underwriting_decision_policy.md for the full tier rationale.
"""

from __future__ import annotations

# Aggregate risk score (0.0-1.0) at/above which the decision escalates to
# REFER on its own (any CRITICAL/HIGH finding also triggers REFER regardless
# of score).
REFER_SCORE_THRESHOLD = 0.70

# Aggregate risk score (0.0-1.0) at/above which the decision escalates to
# DECLINE on its own. See memo_sync.enforce_decision_consistency.
DECLINE_SCORE_THRESHOLD = 0.85


def thresholds_payload() -> dict[str, float]:
    """JSON-serializable thresholds for exposing to the frontend."""
    return {
        "accept_max": REFER_SCORE_THRESHOLD,
        "refer_min": REFER_SCORE_THRESHOLD,
        "refer_max": DECLINE_SCORE_THRESHOLD,
        "decline_min": DECLINE_SCORE_THRESHOLD,
    }
