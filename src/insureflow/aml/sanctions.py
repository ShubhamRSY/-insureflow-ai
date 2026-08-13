"""OFAC / SDN-style sanctions screening against an embedded watchlist.

The list is a *demo* subset plus explicit test names for CI. Production
deployments should replace it with a live OFAC / World-Check feed via the
marketplace connect registry (`ofac-sdn`, `world-check`, `lexisnexis-bridger`).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from insureflow.aml.models import SanctionsHit, SanctionsResult

# Public / well-known designations + synthetic test subjects. Not exhaustive.
_WATCHLIST: list[dict[str, Any]] = [
    {"name": "Osama bin Laden", "aliases": ["Usama Bin Laden", "Osama Bin Ladin"], "list": "OFAC-SDN", "program": "SDGT", "type": "individual"},
    {"name": "Islamic State of Iraq and the Levant", "aliases": ["ISIL", "ISIS", "Daesh"], "list": "OFAC-SDN", "program": "SDGT", "type": "organization"},
    {"name": "Hizballah", "aliases": ["Hezbollah", "Hizbullah"], "list": "OFAC-SDN", "program": "SDGT", "type": "organization"},
    {"name": "Al-Qaida", "aliases": ["Al Qaeda", "Al-Qaeda", "QAEDA"], "list": "OFAC-SDN", "program": "SDGT", "type": "organization"},
    {"name": "Kim Jong Un", "aliases": ["Kim Jong-un", "Kim Jongun"], "list": "OFAC-SDN", "program": "DPRK", "type": "individual"},
    {"name": "Vladimir Putin", "aliases": ["Vladimir Vladimirovich Putin"], "list": "OFAC-SDN", "program": "UKRAINE-EO14024", "type": "individual"},
    {"name": "Evgeny Prigozhin", "aliases": ["Yevgeny Prigozhin", "Evgeni Prigozhin"], "list": "OFAC-SDN", "program": "CYBER2", "type": "individual"},
    {"name": "Wagner Group", "aliases": ["PMC Wagner", "ChVK Vagner"], "list": "OFAC-SDN", "program": "UKRAINE-EO14024", "type": "organization"},
    {"name": "Bank Rossiya", "aliases": ["Rossiya Bank"], "list": "OFAC-SDN", "program": "UKRAINE-EO13662", "type": "organization"},
    {"name": "Cartel de Sinaloa", "aliases": ["Sinaloa Cartel", "CDS"], "list": "OFAC-SDN", "program": "SDNTK", "type": "organization"},
    {"name": "Joaquin Guzman Loera", "aliases": ["El Chapo", "Joaquin Guzman"], "list": "OFAC-SDN", "program": "SDNTK", "type": "individual"},
    {"name": "Taliban", "aliases": ["Islamic Emirate of Afghanistan"], "list": "OFAC-SDN", "program": "SDGT", "type": "organization"},
    {"name": "Hamas", "aliases": ["Islamic Resistance Movement"], "list": "OFAC-SDN", "program": "SDGT", "type": "organization"},
    {"name": "Quds Force", "aliases": ["IRGC-QF", "Islamic Revolutionary Guard Corps Quds Force"], "list": "OFAC-SDN", "program": "IRAN", "type": "organization"},
    {"name": "Rytera Sanctioned Test Person", "aliases": ["SANCTIONED PERSON TEST", "Rytera SDN Test"], "list": "OFAC-SDN", "program": "TEST", "type": "individual"},
    {"name": "Acme Blocked Holdings LLC", "aliases": ["ACME BLOCKED HOLDINGS"], "list": "OFAC-SDN", "program": "TEST", "type": "organization"},
]

_STOP = {"the", "of", "and", "llc", "inc", "corp", "co", "group", "bank"}


def _fold(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text or "")
    ascii_only = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9\s]", " ", ascii_only.lower())


def _tokens(text: str) -> set[str]:
    return {t for t in _fold(text).split() if t and t not in _STOP}


def _score(query: str, name: str, aliases: list[str]) -> float:
    q_fold = _fold(query).strip()
    candidates = [name, *aliases]
    best = 0.0
    q_tokens = _tokens(query)
    if not q_fold:
        return 0.0
    for cand in candidates:
        c_fold = _fold(cand).strip()
        if not c_fold:
            continue
        if q_fold == c_fold:
            return 1.0
        if q_fold in c_fold or c_fold in q_fold:
            best = max(best, 0.92)
            continue
        c_tokens = _tokens(cand)
        if not q_tokens or not c_tokens:
            continue
        overlap = len(q_tokens & c_tokens) / len(q_tokens | c_tokens)
        # Require last-name style token match for individuals.
        if overlap >= 0.6:
            best = max(best, min(0.99, 0.55 + overlap * 0.45))
        elif overlap >= 0.4 and len(q_tokens & c_tokens) >= 2:
            best = max(best, 0.7)
    return round(best, 4)


class SanctionsScreener:
    """Screens a name / entity against the embedded watchlist."""

    threshold = 0.7

    def __init__(self, extra_entries: list[dict[str, Any]] | None = None) -> None:
        self._list = list(_WATCHLIST)
        if extra_entries:
            self._list.extend(extra_entries)

    def screen(self, query: str, *, entity_type: str = "") -> SanctionsResult:
        hits: list[SanctionsHit] = []
        for entry in self._list:
            if entity_type and entry.get("type") and entity_type != entry["type"]:
                continue
            score = _score(query, str(entry["name"]), list(entry.get("aliases") or []))
            if score >= self.threshold:
                hits.append(
                    SanctionsHit(
                        list_name=str(entry["list"]),
                        matched_name=str(entry["name"]),
                        query=query,
                        score=score,
                        aliases=list(entry.get("aliases") or []),
                        program=str(entry.get("program") or ""),
                        entity_type=str(entry.get("type") or "individual"),
                    )
                )
        hits.sort(key=lambda h: h.score, reverse=True)
        cleared = not hits
        if any(h.score >= 0.92 for h in hits):
            action = "block_and_file_sar"
        elif hits:
            action = "refer_aml_officer"
        else:
            action = "clear"
        return SanctionsResult(query=query, cleared=cleared, hits=hits, recommended_action=action)


def screen_name(query: str, *, entity_type: str = "") -> SanctionsResult:
    return SanctionsScreener().screen(query, entity_type=entity_type)
