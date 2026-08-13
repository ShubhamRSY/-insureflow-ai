"""Pydantic models for the fraud security stack.

Device intelligence, behavioral biometrics, and GenAI-attack defense all emit a
shared assessment shape: an overall 0..1 risk score, a risk level, the signals
that contributed, and a recommended action. This keeps the three engines
interchangeable for the API and for downstream gating.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class RiskAssessment(BaseModel):
    """Canonical fraud-security assessment output."""

    engine: str
    subject_id: str
    risk_score: float = Field(ge=0, le=1)
    risk_level: str = Field(description="low / medium / high / critical")
    signals: list[dict[str, Any]] = Field(default_factory=list)
    flagged_patterns: list[str] = Field(default_factory=list)
    recommended_action: str = ""
    assessed_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class DeviceFingerprint(BaseModel):
    """Observed device characteristics used for fingerprinting."""

    device_id: str = ""
    user_agent: str = ""
    platform: str = ""
    screen_resolution: str = ""
    color_depth: Optional[int] = None
    languages: str = ""
    timezone: str = ""
    canvas_hash: str = ""
    webgl_hash: str = ""
    plugin_hashes: list[str] = Field(default_factory=list)
    fonts_hash: str = ""
    is_headless_browser: bool = False


class DeviceSignals(BaseModel):
    """Contextual signals beyond the fingerprint itself."""

    ip_address: str = ""
    ip_country: str = ""
    billing_country: str = ""
    ip_is_datacenter: bool = False
    ip_is_vpn: bool = False
    devices_per_identity: int = 0
    identities_per_device: int = 0
    logins_per_hour: float = 0.0
    account_age_days: float = 0.0
    is_new_account: bool = False
    session_count_24h: int = 0
    header_platform: str = ""  # platform reported by HTTP headers
    navigator_platform: str = ""  # platform reported by JS navigator
    extra: dict[str, Any] = Field(default_factory=dict)


class KeystrokeEvent(BaseModel):
    key: str = ""
    dwell_ms: float = 0.0  # time key held down
    flight_ms: float = 0.0  # time between key-up and next key-down
    was_paste: bool = False


class PointerEvent(BaseModel):
    x: float = 0.0
    y: float = 0.0
    t_ms: float = 0.0
    kind: str = "move"  # move | down | up | scroll | focus


class BehavioralSession(BaseModel):
    """A single session's raw interaction telemetry."""

    session_id: str
    subject_id: str = ""
    keystrokes: list[KeystrokeEvent] = Field(default_factory=list)
    pointers: list[PointerEvent] = Field(default_factory=list)
    input_field_count: int = 0
    pasted_field_count: int = 0
    focus_events: int = 0
    scroll_events: int = 0
    session_duration_ms: float = 0.0
    copy_events: int = 0


class GenAiDocument(BaseModel):
    """A document (or field value) to screen for AI-generation artifacts."""

    document_id: str
    subject_id: str = ""
    content: str = ""
    filename: str = ""
    author: str = ""
