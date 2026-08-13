"""Device intelligence — fingerprinting + spoof/device-farm detection.

Traditional device fingerprinting relies on a stable combination of browser,
screen, and network attributes. Modern fraud farms spoof those attributes, so
this engine scores *consistency* as well as presence: cross-source conflicts
(header vs navigator platform, timezone vs IP region, spoof-prone hashes) and
device-identity velocity (many identities per device / many devices per
identity) are stronger signals than any single attribute.

Heuristic, fully deterministic, and explainable — every point of the score maps
to a named signal a fraud analyst can verify.
"""

from __future__ import annotations

import re
from typing import Any

from insureflow.fraud.models import DeviceFingerprint, DeviceSignals, RiskAssessment

_DATACENTER_HINTS = re.compile(
    r"amazon|aws|googlecloud|azure|digitalocean|linode|ovh|vultr|hetzner|alibaba|oracle-cloud|rackspace|contabo",
    re.IGNORECASE,
)
_VPN_HINTS = re.compile(r"vpn|openvpn|wireguard|expressvpn|nordvpn|surfshark|protonvpn|cloudflare", re.IGNORECASE)
_HEADLESS_HINTS = re.compile(r"headless|phantomjs|phantom|selenium|webdriver|playwright|puppeteer", re.IGNORECASE)


def _risk_level(score: float) -> str:
    return "critical" if score > 0.75 else "high" if score > 0.55 else "medium" if score > 0.3 else "low"


def _action(level: str) -> str:
    return {
        "critical": "block_and_review",
        "high": "step_up_verification",
        "medium": "challenge_questions",
        "low": "standard_processing",
    }[level]


class DeviceIntelligenceEngine:
    """Scores a device fingerprint + contextual signals for spoof/farm risk."""

    def assess(self, fingerprint: DeviceFingerprint, signals: DeviceSignals | None = None) -> RiskAssessment:
        signals = signals or DeviceSignals()
        score = 0.0
        flagged: list[str] = []
        signal_list: list[dict[str, Any]] = []

        def _add(name: str, weight: float, detail: str) -> None:
            nonlocal score
            if weight <= 0:
                return
            score = min(1.0, score + weight)
            signal_list.append({"signal": name, "weight": round(weight, 3), "detail": detail})

        if signals.identities_per_device > 5:
            _add("device_farm_many_identities", 0.35, f"{signals.identities_per_device} identities seen on one device")
        if signals.devices_per_identity > 5:
            _add("device_farm_many_devices", 0.3, f"{signals.devices_per_identity} devices for one identity")

        if signals.header_platform and signals.navigator_platform:
            if signals.header_platform.lower() != signals.navigator_platform.lower():
                _add("spoof_platform_mismatch", 0.3, f"header '{signals.header_platform}' vs navigator '{signals.navigator_platform}'")

        if fingerprint.timezone and signals.ip_country:
            _tz_region = self._timezone_region(fingerprint.timezone)
            if _tz_region and signals.ip_country.upper() != _tz_region:
                _add("geo_timezone_mismatch", 0.2, f"timezone {fingerprint.timezone} vs IP country {signals.ip_country}")

        if signals.billing_country and signals.ip_country:
            if signals.billing_country.upper() != signals.ip_country.upper():
                _add("ip_billing_country_mismatch", 0.2, f"IP {signals.ip_country} vs billing {signals.billing_country}")

        if signals.ip_is_vpn or _VPN_HINTS.search(signals.ip_address):
            _add("ip_vpn_proxy", 0.2, f"VPN/proxy IP: {signals.ip_address}")
        if signals.ip_is_datacenter or _DATACENTER_HINTS.search(signals.ip_address):
            _add("ip_datacenter", 0.2, f"datacenter/hosting IP: {signals.ip_address}")

        if fingerprint.is_headless_browser or _HEADLESS_HINTS.search(fingerprint.user_agent):
            _add("headless_browser", 0.25, "headless/automation browser indicators detected")

        if not fingerprint.canvas_hash and not fingerprint.webgl_hash:
            _add("spoof_no_canvas", 0.15, "canvas/WebGL fingerprint absent — consistent with spoofed or automated browser")
        if fingerprint.canvas_hash and fingerprint.canvas_hash == fingerprint.webgl_hash:
            _add("spoof_identical_hashes", 0.3, "canvas and WebGL hashes identical — suspicious")

        spoof_markers = self._count_spoof_markers(fingerprint)
        if spoof_markers >= 2:
            _add("spoof_marker_cluster", 0.2 * spoof_markers, f"{spoof_markers} spoof-prone attribute markers present")

        if signals.is_new_account and fingerprint.device_id:
            _add("new_account", 0.1, "brand-new account on this device")
        if signals.logins_per_hour > 10:
            _add("login_velocity", 0.25, f"{signals.logins_per_hour:.1f} logins/hour from this device")
        if signals.session_count_24h > 50:
            _add("session_velocity", 0.2, f"{signals.session_count_24h} sessions in 24h from this device")

        flagged = [s["detail"] for s in signal_list]
        level = _risk_level(score)
        return RiskAssessment(
            engine="device_intelligence",
            subject_id=str(fingerprint.device_id or signals.ip_address or "device"),
            risk_score=round(score, 4),
            risk_level=level,
            signals=signal_list,
            flagged_patterns=flagged,
            recommended_action=_action(level),
        )

    @staticmethod
    def _timezone_region(timezone_name: str) -> str:
        region = timezone_name.split("/", 1)[0].upper()
        return region if len(region) <= 3 and region.isalpha() else ""

    @staticmethod
    def _count_spoof_markers(fingerprint: DeviceFingerprint) -> int:
        markers = 0
        if not fingerprint.screen_resolution:
            markers += 1
        if not fingerprint.languages:
            markers += 1
        if not fingerprint.platform:
            markers += 1
        if not fingerprint.plugin_hashes and not fingerprint.fonts_hash:
            markers += 1
        return markers


def assess_device(
    fingerprint: DeviceFingerprint,
    signals: DeviceSignals | None = None,
) -> RiskAssessment:
    return DeviceIntelligenceEngine().assess(fingerprint, signals)
