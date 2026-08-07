"""Sandbox / live-integration readiness for insurance pilot onboarding."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from typing import Any

_DEV_GATEWAY = "rytera-dev-gateway-key-change-in-production"


@dataclass
class FeedReadiness:
    name: str
    category: str  # oracle | policy_admin | enterprise | infra
    required_for_pilot: bool
    mode: str
    configured: bool
    reachable: bool | None
    status: str  # ready | sandbox_ready | simulated | missing | degraded
    next_action: str
    env_keys: list[str] = field(default_factory=list)


def _key_ok(name: str) -> bool:
    val = (os.getenv(name) or "").strip()
    return bool(val) and val != _DEV_GATEWAY


def _mode(name: str, default: str = "auto") -> str:
    return (os.getenv(name) or default).strip().lower()


def _pas_configured() -> bool:
    """True when Guidewire (or BriteCore) has a non-dev key and URL for bind."""
    gw = _key_ok("GUIDEWIRE_API_KEY") and bool((os.getenv("GUIDEWIRE_API_URL") or "").strip())
    bc = _key_ok("BRITECORE_API_KEY") and bool((os.getenv("BRITECORE_API_URL") or "").strip())
    return gw or bc


def operating_mode() -> str:
    """Product posture: ``ready`` (bind allowed) or ``shadow`` (bind blocked).

    Resolution order:
    1. ``OPERATING_MODE`` = ready|live|production → ready; shadow|pilot → shadow
    2. Explicit ``PILOT_SHADOW_MODE`` true/false
    3. Default **ready** (bind enabled when PAS credentials are present)
    """
    raw = (os.getenv("OPERATING_MODE") or "").strip().lower()
    if raw in {"ready", "live", "production"}:
        return "ready"
    if raw in {"shadow", "pilot"}:
        return "shadow"

    explicit = os.getenv("PILOT_SHADOW_MODE", "").strip().lower()
    if explicit in {"1", "true", "yes"}:
        return "shadow"
    if explicit in {"0", "false", "no"}:
        return "ready"

    return "ready"


def is_shadow_mode() -> bool:
    """Shadow: analyze + UW sign-off allowed; live bind blocked."""
    return operating_mode() == "shadow"


def is_ready_mode() -> bool:
    """Ready: bind path enabled when PAS credentials are configured."""
    return operating_mode() == "ready"


def bind_is_allowed() -> bool:
    """Whether policy bind may proceed (ready mode + PAS configured)."""
    if is_shadow_mode():
        return False
    return _pas_configured()


def assess_sandbox_readiness(*, ping: bool = True) -> dict[str, Any]:
    """Return a pilot-ready report of what is live vs still simulated."""
    from insureflow.integrations.health import IntegrationHealthService, effective_mode
    from insureflow.integrations.http_client import build_http_client
    from insureflow.oracles.factory import (
        build_aplus_client,
        build_cat_client,
        build_clue_client,
        build_ncci_client,
    )
    from insureflow.security.posture import resolve_security_posture

    feeds: list[FeedReadiness] = []

    oracle_specs = [
        ("CLUE", "CLUE_API_KEY", "CLUE_API_URL", build_clue_client, True),
        ("A-PLUS", "APLUS_API_KEY", "APLUS_API_URL", build_aplus_client, True),
        ("NCCI", "NCCI_API_KEY", "NCCI_API_URL", build_ncci_client, False),
        ("CAT", "CAT_API_KEY", "CAT_API_URL", build_cat_client, False),
    ]
    for label, key_env, url_env, builder, is_required in oracle_specs:
        client: Any = builder()
        configured = _key_ok(key_env) and bool(os.getenv(url_env))
        reachable: bool | None = None
        mode = _mode("ORACLE_MODE")
        if ping and configured:
            try:
                health = client.http.health_check()
                reachable = bool(health.get("reachable"))
                mode = effective_mode(_mode("ORACLE_MODE"), client.http)
            except Exception:
                reachable = False
                mode = "degraded"
        elif not configured:
            mode = "simulated"
        status = _status(configured, reachable, mode)
        feeds.append(
            FeedReadiness(
                name=label,
                category="oracle",
                required_for_pilot=is_required,
                mode=mode,
                configured=configured,
                reachable=reachable,
                status=status,
                next_action=_next_action(label, status, [key_env, url_env]),
                env_keys=[key_env, url_env, "ORACLE_MODE"],
            )
        )

    policy_specs = [
        ("Guidewire", "GUIDEWIRE_API_KEY", "GUIDEWIRE_API_URL", "GUIDEWIRE_MODE", True),
        ("BriteCore", "BRITECORE_API_KEY", "BRITECORE_API_URL", "BRITECORE_MODE", False),
        ("ISO Rating", "ISO_RATING_API_KEY", "ISO_RATING_API_URL", "ISO_RATING_MODE", False),
    ]
    for label, key_env, url_env, mode_env, is_required in policy_specs:
        configured = _key_ok(key_env) and bool(os.getenv(url_env))
        reachable = None
        mode = _mode(mode_env)
        if ping and configured:
            try:
                http = build_http_client(os.getenv(key_env, ""), os.getenv(url_env, ""))
                health = http.health_check()
                reachable = bool(health.get("reachable"))
                mode = effective_mode(_mode(mode_env), http)
            except Exception:
                reachable = False
                mode = "degraded"
        elif not configured:
            mode = "simulated"
        status = _status(configured, reachable, mode)
        feeds.append(
            FeedReadiness(
                name=label,
                category="policy_admin",
                required_for_pilot=is_required,
                mode=mode,
                configured=configured,
                reachable=reachable,
                status=status,
                next_action=_next_action(label, status, [key_env, url_env]),
                env_keys=[key_env, url_env, mode_env],
            )
        )

    # Infra
    redis_url = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL") or ""
    redis_ok = redis_url.startswith("redis")
    feeds.append(
        FeedReadiness(
            name="Redis job store",
            category="infra",
            required_for_pilot=True,
            mode="configured" if redis_ok else "missing",
            configured=redis_ok,
            reachable=None,
            status="ready" if redis_ok else "missing",
            next_action="Set REDIS_URL=redis://… for durable async jobs" if not redis_ok else "OK",
            env_keys=["REDIS_URL", "JOB_STORE_BACKEND"],
        )
    )
    enc_ok = bool(os.getenv("ENCRYPTION_KEY"))
    feeds.append(
        FeedReadiness(
            name="Audit encryption",
            category="infra",
            required_for_pilot=True,
            mode="configured" if enc_ok else "missing",
            configured=enc_ok,
            reachable=None,
            status="ready" if enc_ok else "missing",
            next_action=(
                'Generate ENCRYPTION_KEY: python -c "from insureflow.storage.encryption import EnvelopeEncryption; print(EnvelopeEncryption.generate_key())"'
                if not enc_ok
                else "OK"
            ),
            env_keys=["ENCRYPTION_KEY"],
        )
    )

    gateway = os.getenv("INTEGRATION_GATEWAY_API_KEY", "")
    gateway_ok = bool(gateway) and gateway != _DEV_GATEWAY
    feeds.append(
        FeedReadiness(
            name="Integration gateway key",
            category="infra",
            required_for_pilot=True,
            mode="production" if gateway_ok else "dev_placeholder",
            configured=gateway_ok,
            reachable=None,
            status="ready" if gateway_ok else "missing",
            next_action="Replace INTEGRATION_GATEWAY_API_KEY (not the rytera-dev placeholder)" if not gateway_ok else "OK",
            env_keys=["INTEGRATION_GATEWAY_API_KEY"],
        )
    )

    posture = resolve_security_posture()
    shadow = is_shadow_mode()
    ready = is_ready_mode()
    pas_ok = _pas_configured()

    required_feeds = [f for f in feeds if f.required_for_pilot]
    ready_required = [f for f in required_feeds if f.status in {"ready", "sandbox_ready"}]
    blocked = [f for f in required_feeds if f.status in {"missing", "degraded", "simulated"}]
    infra_required = [f for f in required_feeds if f.category == "infra"]
    infra_ready = all(f.status in {"ready", "sandbox_ready"} for f in infra_required)
    oracle_live = any(
        f.status in {"ready", "sandbox_ready"} for f in feeds if f.category == "oracle" and f.required_for_pilot
    )
    packages_ok = _pilot_packages_present()

    # Live-ready = every required feed configured.
    # Ready = bind enabled + PAS + infra (oracles may still be sandbox).
    # Shadow-ready = durable local infra + packages; bind off.
    if len(ready_required) == len(required_feeds) and ready:
        overall = "pilot_live_ready"
    elif ready and pas_ok and infra_ready:
        overall = "pilot_ready"
    elif len(ready_required) == len(required_feeds):
        overall = "pilot_live_ready"
    elif infra_ready and packages_ok and shadow:
        overall = "pilot_shadow_ready"
    elif oracle_live and packages_ok and shadow:
        overall = "pilot_shadow_ready"
    elif ready and packages_ok and infra_ready:
        overall = "pilot_ready"
    else:
        overall = "not_ready"

    checklist = [
        {"step": 1, "title": "Copy production env template", "done": gateway_ok, "cmd": "cp .env.production.example .env"},
        {"step": 2, "title": "Set ENCRYPTION_KEY + REDIS_URL", "done": enc_ok and redis_ok},
        {"step": 3, "title": "Configure LexisNexis CLUE credentials", "done": _key_ok("CLUE_API_KEY")},
        {"step": 4, "title": "Configure Verisk A-PLUS credentials", "done": _key_ok("APLUS_API_KEY")},
        {"step": 5, "title": "Configure Guidewire / PAS endpoint", "done": pas_ok},
        {"step": 6, "title": "Drop packages into pilot_packages/", "done": packages_ok},
        {
            "step": 7,
            "title": "Ready mode (bind enabled)" if ready else "Shadow mode (bind disabled)",
            "done": ready and pas_ok if ready else shadow,
        },
        {
            "step": 8,
            "title": "Verify feeds",
            "done": overall != "not_ready",
            "cmd": "PYTHONPATH=src python cli.py sandbox-status",
        },
    ]

    ecosystem: dict[str, Any] = {}
    if ping:
        try:
            ecosystem = IntegrationHealthService().check_all()
        except Exception as exc:
            ecosystem = {"error": str(exc)}

    return {
        "overall": overall,
        "operating_mode": operating_mode(),
        "shadow_mode": shadow,
        "ready_mode": ready,
        "bind_allowed": bind_is_allowed(),
        "pas_configured": pas_ok,
        "bank_mode": posture.is_hardened,
        "required_ready": len(ready_required),
        "required_total": len(required_feeds),
        "blocked": [asdict(f) for f in blocked],
        "feeds": [asdict(f) for f in feeds],
        "checklist": checklist,
        "ecosystem": ecosystem,
        "partner_ask": [
            "20–50 redacted commercial submissions (ACORD XML/PDF, loss runs, SOV, inspection)",
            "Sandbox or production credentials for CLUE and A-PLUS (or carrier-proxied feeds)",
            "UAT/production Guidewire/BriteCore/Duck Creek endpoint for ready-mode bind",
            "Licensed UW contact for HITL calibration (2–4 hrs/week for 30 days)",
            "Success metrics: override rate < 25%, no silent ACCEPT on missing docs, bind only after UW approve",
        ],
    }


def _status(configured: bool, reachable: bool | None, mode: str) -> str:
    if not configured:
        return "simulated" if mode in {"auto", "simulated", ""} else "missing"
    if reachable is True and mode == "live":
        return "ready"
    if reachable is True:
        return "sandbox_ready"
    if reachable is False:
        return "degraded"
    return "sandbox_ready" if configured else "missing"


def _next_action(label: str, status: str, keys: list[str]) -> str:
    if status in {"ready", "sandbox_ready"}:
        return "OK — feed configured"
    if status == "degraded":
        return f"{label} credentials present but host not reachable — check VPN / URL / firewall"
    return f"Obtain sandbox credentials and set {', '.join(keys)}"


def _pilot_packages_present() -> bool:
    from pathlib import Path

    root = Path.cwd() / "pilot_packages"
    if not root.exists():
        return False
    return any(p.is_dir() and p.name != "_template" for p in root.iterdir())
