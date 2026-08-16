"""Layer 5 — external database cross-referencing.

Never trust an extracted document in isolation when a registry can corroborate
it. ``lookup_entity`` verifies a legal name / address / EIN against an
authoritative registry API.

Trust & egress policy (bank mode): nothing is ever sent externally unless the
operator has explicitly configured ``EXTERNAL_REGISTRY_API_URL`` **and** the URL
is HTTPS. Requests carry ``EXTERNAL_REGISTRY_API_KEY`` when set. Without
configuration the layer is inert (returns ``None``) and reports "disabled" so
the verification trail shows the check never ran.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from insureflow.models.submissions import ExtractedField, VerificationIssue
from insureflow.verification.common import SEVERITY_WARNING

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 10


@dataclass(frozen=True)
class RegistryLookup:
    matched: bool
    entity_name: str
    message: str
    raw: Any = None


def external_lookup_enabled() -> bool:
    url = os.getenv("EXTERNAL_REGISTRY_API_URL", "").strip()
    return url.startswith("https://")  # https-only, and requires explicit config


def lookup_entity(
    entity_name: str,
    address: str = "",
    ein: str = "",
    timeout: int = _DEFAULT_TIMEOUT,
) -> RegistryLookup | None:
    """Cross-reference an entity against the configured registry; None if disabled."""
    if not external_lookup_enabled():
        return None
    url = os.getenv("EXTERNAL_REGISTRY_API_URL", "").strip()
    params = {"name": entity_name}
    if address:
        params["address"] = address
    if ein:
        params["ein"] = ein
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(f"{url}?{query}", method="GET")
    api_key = os.getenv("EXTERNAL_REGISTRY_API_KEY", "").strip()
    if api_key:
        request.add_header("Authorization", f"Bearer {api_key}")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - egress is operator-configured
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError) as exc:
        logger.warning("registry lookup failed for %r: %s", entity_name, exc)
        return None
    matched = bool(payload.get("match") or payload.get("matched") or payload.get("found"))
    return RegistryLookup(
        matched=matched,
        entity_name=entity_name,
        message=payload.get("message") or ("registry confirmed" if matched else "registry could not confirm"),
        raw=payload,
    )


def registry_verification_issues(
    fields: Mapping[str, Iterable[ExtractedField]],
    lookup: Any = None,
) -> list[VerificationIssue]:
    """Run name/EIN/address lookups when configured and report mismatches.

    ``lookup`` is injectable for tests; defaults to :func:`lookup_entity`.
    """
    if not external_lookup_enabled():
        return []
    issues: list[VerificationIssue] = []
    flat = {k: (v[0].value if v else "") for k, v in fields.items() if v}

    def _value(*needles: str) -> str:
        for needle in needles:
            for key in flat:
                if needle in key.lower() and flat[key]:
                    return flat[key].strip()
        return ""

    name = _value("legal_name", "named_insured", "business_name", "entity_name", "name")
    address = _value("address", "mailing_address", "street")
    ein = _value("ein", "tax_id", "fein")
    if not name:
        return []
    result = lookup(name, address, ein) if lookup is not None else lookup_entity(name, address, ein)
    if result is None:
        return []
    if not result.matched:
        issues.append(
            VerificationIssue(
                code="registry_unconfirmed",
                severity=SEVERITY_WARNING,
                message=f"external registry could not confirm entity {result.entity_name!r}: {result.message}",
            )
        )
    return issues
