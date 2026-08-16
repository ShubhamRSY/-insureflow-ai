"""Spatial graph / layout-masking checks (technique: geometric column alignment).

Rather than trusting flat text order, treat each page as a geometric graph of
bounding boxes. Two checks:

- ``detect_columns`` — cluster line ``x0`` positions into column boundaries so
  tables can be read column-first instead of row-first.
- ``column_alignment_check`` — within each visual row band (shared rounded ``y0``),
  every row should span the same set of columns. A row with fewer column cells
  than its neighbors is a likely mix-up (value in the wrong column, or a value
  merged into an adjacent cell) and is flagged for human review with its box.

Pure and deterministic; consumes the OCR ``spatial_lines`` index
``{page: {line_text: [x0, y0, x1, y1]}}``.
"""

from __future__ import annotations

from typing import Mapping

from insureflow.models.submissions import VerificationIssue
from insureflow.verification.common import SEVERITY_WARNING

_COLUMN_GAP = 0.06  # minimum normalized horizontal gap between columns
_ROW_BAND = 0.02  # y0 rounding band for grouping lines into visual rows


def _x0(box: list[float]) -> float:
    return float(box[0])


def detect_columns(lines: Mapping[str, list[float]]) -> list[float]:
    """Return normalized x0 column boundaries for a page's line boxes."""
    starts = sorted({round(_x0(box), 3) for box in lines.values() if box})
    if len(starts) < 2:
        return starts
    columns: list[float] = [starts[0]]
    for start in starts[1:]:
        if start - columns[-1] >= _COLUMN_GAP:
            columns.append(start)
    return columns


def _row_bands(lines: Mapping[str, list[float]]) -> dict[float, list[tuple[str, list[float]]]]:
    bands: dict[float, list[tuple[str, list[float]]]] = {}
    for text, box in lines.items():
        if not box:
            continue
        band = round(float(box[1]) / _ROW_BAND) * _ROW_BAND
        bands.setdefault(band, []).append((text, box))
    return bands


def _column_ranges(lines: Mapping[str, list[float]]) -> list[tuple[float, float]]:
    """Infer (start, end) x-ranges for each detected column on a page."""
    starts = detect_columns(lines)
    if len(starts) < 2:
        return [(starts[0], max((float(b[2]) for b in lines.values() if b), default=1.0))]
    max_x1 = max((float(b[2]) for b in lines.values() if b), default=1.0)
    ranges = []
    for idx, start in enumerate(starts):
        end = starts[idx + 1] - 0.01 if idx + 1 < len(starts) else max_x1
        ranges.append((start, end))
    return ranges


def _columns_covered(box: list[float], ranges: list[tuple[float, float]]) -> int:
    x0, x1 = float(box[0]), float(box[2])
    return sum(1 for start, end in ranges if x0 <= start + 1e-6 and x1 >= start + _COLUMN_GAP)


def column_alignment_check(
    spatial_lines: Mapping[int, Mapping[str, list[float]]],
) -> list[VerificationIssue]:
    """Flag rows whose column coverage deviates from the band's norm.

    Within a visual row band, the modal column coverage is the layout the OCR
    produced for the rest of the table; a row that spans more *or* fewer columns
    than that norm is a likely multi-column mix-up (a value merged across cells,
    or truncated into one cell) and is flagged for human review with its box.
    """
    issues: list[VerificationIssue] = []
    for page, lines in spatial_lines.items():
        if not lines:
            continue
        columns = detect_columns(lines)
        if len(columns) < 2:
            continue  # single column — no alignment ambiguity
        ranges = _column_ranges(lines)
        for band, rows in _row_bands(lines).items():
            coverages = [(text, box, _columns_covered(box, ranges)) for text, box in rows]
            if len(coverages) < 2:
                continue
            distinct = {c for _, _, c in coverages}
            if len(distinct) < 2:
                continue
            mode = max(distinct, key=lambda c: sum(1 for _, _, x in coverages if x == c))
            for text, box, count in coverages:
                if count != mode and count > 0:
                    issues.append(
                        VerificationIssue(
                            code="column_misalignment",
                            severity=SEVERITY_WARNING,
                            message=(f"page {page}: row {text!r} spans {count} column(s) while the band norm is {mode}; possible value/header misalignment"),
                            page_number=page,
                            bbox=[float(v) for v in box],
                        )
                    )
    return issues
