"""Bounding-box grounding and spatial citations.

Technique #4: every extracted value is tied back to a normalized pixel box on a
specific page so compliance reviewers can jump straight to the source location.
``SpatialRef`` records ``(page_number, [x0, y0, x1, y1])`` normalized to
0..1 on the page. Attaching a ref sets ``page_number``/``bbox``/``source_ref``
on the ``ExtractedField``; ``grounding_citations`` renders them for audit UIs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from insureflow.models.submissions import ExtractedField


@dataclass(frozen=True)
class SpatialRef:
    page_number: int = 1
    bbox: tuple[float, float, float, float] | list[float] | None = None

    def citation(self) -> str:
        if self.bbox is None:
            return f"page {self.page_number}"
        x0, y0, x1, y1 = (float(v) for v in self.bbox)
        return f"page {self.page_number}, region {x0:.3f},{y0:.3f}..{x1:.3f},{y1:.3f}"


def attach_spatial_ref(field: ExtractedField, ref: SpatialRef | None) -> ExtractedField:
    if ref is None:
        return field
    field.page_number = ref.page_number
    if ref.bbox is not None:
        field.bbox = [float(v) for v in ref.bbox]
    if not field.source_ref:
        field.source_ref = ref.citation()
    return field


def attach_citation(field: ExtractedField, page_number: int, bbox: list[float] | None = None) -> ExtractedField:
    return attach_spatial_ref(field, SpatialRef(page_number=page_number, bbox=bbox))


def grounding_citations(fields: Iterable[ExtractedField]) -> list[str]:
    """Audit-ready citations for every spatially-grounded field."""
    out: list[str] = []
    for field in fields:
        ref = field.source_ref or (f"page {field.page_number}" if field.page_number else "")
        if ref:
            out.append(f"{field.field_name}: {field.value} → {ref}")
    return out


def find_line_bbox(lines: dict[str, list[float]] | dict[str, SpatialRef], token: str) -> SpatialRef | None:
    """Look up a token in a page's line map (exact or prefix) and return its box."""
    if token in lines:
        return _as_ref(lines[token])
    lower = token.lower()
    for key, ref in lines.items():
        if key.lower().startswith(lower) or lower in key.lower():
            return _as_ref(ref)
    return None


def _as_ref(value: object) -> SpatialRef:
    if isinstance(value, SpatialRef):
        return value
    if isinstance(value, (list, tuple)) and len(value) == 4:
        return SpatialRef(bbox=list(value))
    return SpatialRef()
