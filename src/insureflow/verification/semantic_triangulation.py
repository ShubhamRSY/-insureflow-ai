"""Semantic triangulation (RAE-style): bind table figures to their footnotes.

A figure read without its governing footnote is a classic misreading (an
exclusion or modifier hidden in fine print). This module extracts footnote
definitions from markdown-ified documents, finds markers ``[1]`` / ``(1)`` / ``*``
inside table cells, and reports any figure whose footnote carries a modifier
("excluding", "not covered", "subject to", "cap", "deductible", ...) so the
figure is never interpreted out of context.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from insureflow.models.submissions import VerificationIssue
from insureflow.verification.common import SEVERITY_WARNING

_FOOTNOTE_DEF_RE = re.compile(r"^\s*(?:\[\s*(\d+)\s*\]|\(\s*(\d+)\s*\)|\*|\u2020|\u2021)\s*(.+)$")
_MARKER_RE = re.compile(r"(?:\[\s*(\d+)\s*\]|\(\s*(\d+)\s*\)|\*)")
_MODIFIER_TERMS = (
    "excluding",
    "excludes",
    "does not include",
    "not covered",
    "subject to",
    "cap",
    "limit",
    "deductible",
    "reduced",
    "maximum",
    "min",
    "max",
    "excess",
    "per occurrence",
    "aggregate",
)


@dataclass(frozen=True)
class FootnoteBinding:
    table: str
    figure: str
    marker: str
    footnote: str

    @property
    def carries_modifier(self) -> bool:
        lower = self.footnote.lower()
        return any(term in lower for term in _MODIFIER_TERMS)


@dataclass
class FootnoteIndex:
    definitions: dict[str, str] = field(default_factory=dict)
    bindings: list[FootnoteBinding] = field(default_factory=list)

    def is_complete(self) -> bool:
        """Every binding resolves to a definition; no dangling markers."""
        return all(b.footnote for b in self.bindings)


def parse_footnotes(markdown: str) -> FootnoteIndex:
    """Index ``[1]``/``(1)``/``*`` definitions and bind them to table cells."""
    index = FootnoteIndex()
    defs: dict[str, str] = {}
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        match = _FOOTNOTE_DEF_RE.match(line)
        if match:
            marker = match.group(1) or match.group(2)
            if marker:
                defs.setdefault(marker, match.group(3).strip())
    index.definitions = defs

    for table_idx, table_block in enumerate(_split_tables(markdown)):
        for line_idx, line in enumerate(table_block):
            separator = set(line.replace("|", "").strip())
            is_separator_row = bool(separator) and separator <= {"-", ":", " "}
            if "|" not in line or is_separator_row:
                continue  # header separator row
            for match in _MARKER_RE.finditer(line):
                marker = match.group(1) or match.group(2) or "*"
                figure = _figure_for(line, match.start())
                index.bindings.append(
                    FootnoteBinding(
                        table=f"table {table_idx + 1}",
                        figure=figure,
                        marker=marker,
                        footnote=defs.get(marker, ""),
                    )
                )
    return index


def _figure_for(line: str, marker_pos: int) -> str:
    cells = [c.strip() for c in line.split("|")]
    token = ""
    for cell in cells:
        if cell and marker_pos >= line.find(cell):
            token = cell
    return token or line[:80]


def _split_tables(markdown: str) -> list[list[str]]:
    tables: list[list[str]] = []
    current: list[str] = []
    for line in markdown.splitlines():
        if "|" in line:
            current.append(line)
        else:
            if current:
                tables.append(current)
                current = []
    if current:
        tables.append(current)
    return tables


def triangulation_issues(markdown: str) -> list[VerificationIssue]:
    """Flag figures bound to modifier-carrying footnotes (misinterpretation risk)."""
    index = parse_footnotes(markdown)
    issues: list[VerificationIssue] = []
    for binding in index.bindings:
        if not binding.footnote:
            issues.append(
                VerificationIssue(
                    code="dangling_footnote",
                    severity=SEVERITY_WARNING,
                    message=f"{binding.table}: figure {binding.figure!r} references unresolved marker [{binding.marker}]",
                    field_name=binding.figure,
                )
            )
        elif binding.carries_modifier:
            issues.append(
                VerificationIssue(
                    code="footnote_modifier",
                    severity=SEVERITY_WARNING,
                    message=f"{binding.table}: figure {binding.figure!r} is governed by footnote [{binding.marker}] '{binding.footnote[:120]}' — must not be read in isolation",
                    field_name=binding.figure,
                )
            )
    return issues
