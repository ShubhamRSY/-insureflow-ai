"""Graph neural net for fraud-ring detection.

Builds a graph of applicants linked by shared phone, email, tax ID, address, or
IP, then runs a two-layer mean-aggregation GraphSAGE scorer. Weights are fixed
and deterministic so the same cluster always scores the same way — this is not
a trained vendor model, and it does not invent rings that are not in the graph.

Requires no PyTorch. Weights are fixed in this file. Same cluster, same score.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Sequence

from insureflow.models.submissions import SubmissionBundle


def _norm_phone(value: str) -> str:
    digits = re.sub(r"\D+", "", value or "")
    return digits[-10:] if len(digits) >= 10 else digits


def _norm_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def _norm_email(value: str) -> str:
    return (value or "").strip().lower()


@dataclass
class EntitySnapshot:
    entity_id: str
    legal_name: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""
    tax_id: str = ""
    ip_address: str = ""
    prior_claims: int = 0
    declined: bool = False
    loss_ratio: float = 0.0

    def identity_keys(self) -> dict[str, str]:
        keys: dict[str, str] = {}
        phone = _norm_phone(self.phone)
        if phone:
            keys["phone"] = phone
        email = _norm_email(self.email)
        if email and "@" in email:
            keys["email"] = email
        tax = _norm_text(self.tax_id)
        if len(tax) >= 4:
            keys["tax_id"] = tax
        addr = _norm_text(self.address)
        if len(addr) >= 8:
            keys["address"] = addr
        ip = (self.ip_address or "").strip()
        if ip:
            keys["ip"] = ip
        return keys


@dataclass
class FraudRingHit:
    member_ids: list[str]
    shared_keys: list[str]
    ring_score: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "member_ids": list(self.member_ids),
            "shared_keys": list(self.shared_keys),
            "ring_score": round(self.ring_score, 4),
            "reason": self.reason,
        }


# 6 → 8 → 4 → 1 GraphSAGE weights (fixed, not trained at runtime).
_W1 = (
    (0.8, 0.1, 0.2, 0.4, 0.3, 0.1, 0.0, 0.2),
    (0.2, 0.9, 0.1, 0.3, 0.2, 0.0, 0.1, 0.1),
    (0.4, 0.2, 1.0, 0.5, 0.1, 0.2, 0.0, 0.3),
    (0.3, 0.1, 0.2, 1.1, 0.6, 0.2, 0.1, 0.4),
    (0.2, 0.0, 0.1, 0.5, 1.0, 0.3, 0.2, 0.2),
    (0.1, 0.1, 0.0, 0.2, 0.1, 0.4, 0.8, 0.1),
)
_W2 = (
    (0.9, 0.2, 0.1, 0.3),
    (0.2, 0.8, 0.1, 0.2),
    (0.3, 0.2, 0.7, 0.4),
    (0.5, 0.4, 0.6, 0.9),
    (0.4, 0.3, 0.5, 0.8),
    (0.2, 0.1, 0.3, 0.4),
    (0.1, 0.2, 0.2, 0.3),
    (0.3, 0.2, 0.4, 0.5),
)
_W_OUT = (0.7, 0.5, 0.9, 1.1)


def _relu(v: float) -> float:
    return v if v > 0 else 0.0


def _sigmoid(v: float) -> float:
    if v >= 20:
        return 1.0
    if v <= -20:
        return 0.0
    return 1.0 / (1.0 + math.exp(-v))


def _matmul(a: list[list[float]], b: Sequence[Sequence[float]]) -> list[list[float]]:
    rows = len(a)
    cols = len(b[0])
    inner = len(b)
    out = [[0.0] * cols for _ in range(rows)]
    for i in range(rows):
        for k in range(inner):
            aik = a[i][k]
            if aik == 0:
                continue
            bk = b[k]
            row = out[i]
            for j in range(cols):
                row[j] += aik * bk[j]
    return out


def _mean_aggregate(adj: list[list[int]], x: list[list[float]]) -> list[list[float]]:
    n = len(x)
    dim = len(x[0]) if x else 0
    out = [[0.0] * dim for _ in range(n)]
    for i, neighbors in enumerate(adj):
        members = [i, *neighbors]
        scale = 1.0 / len(members)
        for j in members:
            src = x[j]
            dst = out[i]
            for d in range(dim):
                dst[d] += src[d] * scale
    return out


def _features(entities: Sequence[EntitySnapshot], degrees: Sequence[int], shared_counts: Sequence[int]) -> list[list[float]]:
    rows: list[list[float]] = []
    for i, ent in enumerate(entities):
        rows.append(
            [
                min(ent.prior_claims / 10.0, 1.0),
                min(max(ent.loss_ratio, 0.0), 3.0) / 3.0,
                1.0 if ent.declined else 0.0,
                min(shared_counts[i] / 4.0, 1.0),
                min(degrees[i] / 8.0, 1.0),
                1.0,
            ]
        )
    return rows


def _build_graph(entities: Sequence[EntitySnapshot]) -> tuple[list[list[int]], list[int], dict[str, list[int]]]:
    inverted: dict[str, list[int]] = {}
    for i, ent in enumerate(entities):
        for kind, key in ent.identity_keys().items():
            inverted.setdefault(f"{kind}:{key}", []).append(i)
    n = len(entities)
    neighbors: list[set[int]] = [set() for _ in range(n)]
    for idxs in inverted.values():
        if len(idxs) < 2:
            continue
        for a in idxs:
            for b in idxs:
                if a != b:
                    neighbors[a].add(b)
    adj = [sorted(s) for s in neighbors]
    degrees = [len(row) for row in adj]
    return adj, degrees, inverted


def _components(adj: list[list[int]]) -> list[list[int]]:
    n = len(adj)
    seen = [False] * n
    groups: list[list[int]] = []
    for start in range(n):
        if seen[start]:
            continue
        stack = [start]
        seen[start] = True
        group = []
        while stack:
            i = stack.pop()
            group.append(i)
            for j in adj[i]:
                if not seen[j]:
                    seen[j] = True
                    stack.append(j)
        groups.append(sorted(group))
    return groups


def _gnn_scores(x: list[list[float]], adj: list[list[int]]) -> list[float]:
    h1 = _mean_aggregate(adj, x)
    h1 = _matmul(h1, _W1)
    h1 = [[_relu(v) for v in row] for row in h1]
    h2 = _mean_aggregate(adj, h1)
    h2 = _matmul(h2, _W2)
    scores = []
    for row in h2:
        logit = sum(row[i] * _W_OUT[i] for i in range(len(_W_OUT)))
        scores.append(_sigmoid(logit - 1.4))
    return scores


def detect_fraud_rings(entities: Sequence[EntitySnapshot], *, min_size: int = 2, score_floor: float = 0.35) -> list[FraudRingHit]:
    """Score linked applicants. Isolated entities never become a ring."""
    if len(entities) < 2:
        return []
    adj, degrees, inverted = _build_graph(entities)
    shared_counts = [0] * len(entities)
    for idxs in inverted.values():
        if len(idxs) < 2:
            continue
        for i in idxs:
            shared_counts[i] += 1
    x = _features(entities, degrees, shared_counts)
    scores = _gnn_scores(x, adj)
    hits: list[FraudRingHit] = []
    for group in _components(adj):
        if len(group) < min_size:
            continue
        if all(degrees[i] == 0 for i in group):
            continue
        keys = []
        for label, idxs in inverted.items():
            if sum(1 for i in idxs if i in group) >= 2:
                keys.append(label.split(":", 1)[0])
        if not keys:
            continue
        ring_score = max(scores[i] for i in group)
        strong = any(k in {"phone", "tax_id", "email", "ip"} for k in keys)
        if not strong and ring_score < score_floor and len(group) < 3:
            continue
        member_ids = [entities[i].entity_id for i in group]
        reason = f"{len(group)} files share {', '.join(sorted(set(keys)))}; graph-net ring score {ring_score:.2f}"
        hits.append(
            FraudRingHit(
                member_ids=member_ids,
                shared_keys=sorted(set(keys)),
                ring_score=ring_score,
                reason=reason,
            )
        )
    hits.sort(key=lambda h: h.ring_score, reverse=True)
    return hits


def _extracted_map(bundle: SubmissionBundle) -> dict[str, str]:
    out: dict[str, str] = {}
    for blob in (*bundle.unstructured, *bundle.supplemental):
        for key, entries in (blob.extracted_fields or {}).items():
            if entries and getattr(entries[0], "value", ""):
                out[key.lower()] = str(entries[0].value)
    return out


def snapshot_from_bundle(bundle: SubmissionBundle) -> EntitySnapshot:
    fields = _extracted_map(bundle)
    name = ""
    address = ""
    tax_id = ""
    email = ""
    phone = fields.get("phone") or fields.get("business_phone") or fields.get("contact_phone") or ""
    ip_address = fields.get("ip_address") or fields.get("source_ip") or ""
    prior_claims = 0
    loss_ratio = 0.0
    if bundle.structured:
        ni = bundle.structured.named_insured
        if ni:
            name = ni.legal_name or ""
            tax_id = ni.tax_id or ""
            address = ni.address or address
        if bundle.structured.locations:
            loc = bundle.structured.locations[0]
            address = address or f"{loc.address}, {loc.city}, {loc.state} {loc.zip_code}"
        if bundle.structured.risk_profile:
            prior_claims = len(bundle.structured.risk_profile.prior_claims or [])
        if bundle.structured.financial and bundle.structured.financial.prior_losses:
            incurred = 0.0
            for row in bundle.structured.financial.prior_losses:
                if isinstance(row, dict):
                    incurred += float(row.get("incurred_amount") or 0)
            premium = sum(c.premium or 0 for c in bundle.structured.coverages) or 1.0
            loss_ratio = incurred / premium if premium else 0.0
    # Applicant-side email only — never the broker's own contact address.
    # One broker legitimately submits many unrelated clients through the same
    # desk email, so using it as a ring-matching identity key would flag every
    # busy brokerage's normal submission stream as a "fraud ring".
    email = fields.get("email") or fields.get("contact_email") or ""
    return EntitySnapshot(
        entity_id=bundle.bundle_id,
        legal_name=name,
        address=address,
        phone=phone,
        email=email,
        tax_id=tax_id,
        ip_address=ip_address,
        prior_claims=prior_claims,
        declined=bundle.status.value == "appetite_declined" if hasattr(bundle.status, "value") else False,
        loss_ratio=loss_ratio,
    )


class FraudRingIndex:
    """In-process memory of recent applicants so rings can form across files.

    Bounded to the most recent ``max_entities`` submissions: a genuine fraud
    ring is a cluster of *recent, related* submissions, so an identity match
    against a submission from long ago (or, in a long-running process, from
    an entirely unrelated batch) is weak signal and shouldn't be remembered
    forever — this was previously unbounded, so this index only ever grew,
    letting stale applicants retroactively flag unrelated later submissions
    as a "ring" purely for sharing incidental data (e.g. a placeholder email
    reused across many synthetic fixtures).
    """

    def __init__(self, max_entities: int = 500) -> None:
        from collections import OrderedDict

        self._entities: OrderedDict[str, EntitySnapshot] = OrderedDict()
        self._max_entities = max_entities

    def clear(self) -> None:
        self._entities.clear()

    def upsert(self, snapshot: EntitySnapshot) -> None:
        self._entities[snapshot.entity_id] = snapshot
        self._entities.move_to_end(snapshot.entity_id)
        while len(self._entities) > self._max_entities:
            self._entities.popitem(last=False)

    def ingest_bundle(self, bundle: SubmissionBundle) -> EntitySnapshot:
        snap = snapshot_from_bundle(bundle)
        self.upsert(snap)
        return snap

    def score(self, bundle: SubmissionBundle | None = None) -> list[FraudRingHit]:
        if bundle is not None:
            self.ingest_bundle(bundle)
        return detect_fraud_rings(list(self._entities.values()))

    def hits_for(self, entity_id: str) -> list[FraudRingHit]:
        return [h for h in detect_fraud_rings(list(self._entities.values())) if entity_id in h.member_ids]


_INDEX = FraudRingIndex()


def default_ring_index() -> FraudRingIndex:
    return _INDEX
