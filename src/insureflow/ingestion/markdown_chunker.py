"""Markdown normalization and structural (hierarchical) chunking.

Technique #3: before anything goes into the vector DB, all inputs — PDFs,
Excel files, Word docs, scans — are normalized to clean Markdown that preserves
semantic hierarchy (H1/H2 headers, lists, block quotes, tables). Chunking then
splits strictly along those structural boundaries instead of arbitrary token
windows, so retrieval returns whole logical units rather than clipped noise.
"""

from __future__ import annotations

import re

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_TABLE_LINE_RE = re.compile(r"^\s*\|.*\|\s*$")
_LIST_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_BLOCKQUOTE_RE = re.compile(r"^\s*>\s?")
_FENCE_RE = re.compile(r"^```")


def normalize_to_markdown(text: str) -> str:
    """Best-effort normalization of plain/OCR text into Markdown structure.

    Preserves existing markdown already produced by structured-doc parsers;
    promotes table-shaped text lines into pipes, defers blank-line collapsing,
    and keeps heading-like lines as-is. Non-markdown prose is unchanged.
    """
    if not text:
        return ""
    lines = text.splitlines()
    out: list[str] = []
    in_fence = False
    for line in lines:
        stripped = line.strip()
        if _FENCE_RE.match(stripped):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        if not stripped:
            out.append("")
            continue
        # Table-shaped rows with pipes already (structured_docs output).
        if "|" in line:
            out.append(line)
            continue
        if _HEADING_RE.match(stripped) or _LIST_RE.match(stripped) or _BLOCKQUOTE_RE.match(stripped):
            out.append(line)
            continue
        # Lines of mostly short "cell" tokens separated by whitespace look like
        # a layout table → convert to a pipe row.
        tokens = [t for t in stripped.split() if t]
        if len(tokens) >= 3 and _looks_like_layout_row(tokens):
            out.append("| " + " | ".join(tokens) + " |")
            continue
        out.append(line)
    return "\n".join(out)


def _looks_like_layout_row(tokens: list[str]) -> bool:
    """Heuristic: >=3 tokens where most are non-prose (numbers, short codes)."""
    if len(tokens) < 3:
        return False
    non_prose = sum(1 for t in tokens if len(t) <= 14 and not any(c.isalpha() for c in t))
    return non_prose >= max(2, len(tokens) // 2)


class MarkdownHierarchicalChunker:
    """Split normalized Markdown along semantic boundaries (headings, tables, lists).

    Each chunk is one logical unit: a section tree rooted at the nearest heading,
    a standalone table, or a paragraph. ``max_chars`` (default 0 = no cap) soft-
    wraps oversized sections by re-chunking their text with the classic chunker.
    """

    def __init__(self, max_chars: int = 0, overlap: int = 200) -> None:
        self.max_chars = max_chars
        self.overlap = overlap

    def chunk_markdown(self, markdown: str) -> list[str]:
        if not markdown:
            return []
        sections = self._split_sections(markdown)
        chunks: list[str] = []
        for title, body in sections:
            body_str = "\n".join(body).strip()
            if not body_str and not title:
                continue
            block = f"## {title}\n{body_str}" if title else body_str
            block = block.strip()
            if not block:
                continue
            if self.max_chars and len(block) > self.max_chars:
                chunks.extend(self._wrap_text(block, self.max_chars))
            else:
                chunks.append(block)
        return chunks

    def chunk_text(self, text: str) -> list[str]:
        return self.chunk_markdown(normalize_to_markdown(text))

    def _split_sections(self, markdown: str) -> list[tuple[str, list[str]]]:
        sections: list[tuple[str, list[str]]] = []
        current_title = ""
        current: list[str] = []
        table_lines: list[str] = []

        def flush_table() -> None:
            nonlocal table_lines
            if table_lines:
                sections.append((current_title, table_lines))
                table_lines = []

        for line in markdown.splitlines():
            heading = _HEADING_RE.match(line)
            if heading:
                flush_table()
                if current:
                    sections.append((current_title, current))
                    current = []
                current_title = heading.group(2).strip()
                continue
            stripped = line.strip()
            if stripped == "|---|" or stripped.startswith("| ---"):
                table_lines.append(line)
                continue
            if table_lines:
                if _TABLE_LINE_RE.match(line):
                    table_lines.append(line)
                    continue
                flush_table()
            current.append(line)
        flush_table()
        if current:
            sections.append((current_title, current))
        return sections

    def _wrap_text(self, text: str, size: int) -> list[str]:
        from insureflow.ingestion.chunker import DocumentChunker

        return [c for c in DocumentChunker(chunk_size=size, overlap=self.overlap).chunk_text(text) if c]


def hierarchical_chunks(raw_text: str, max_chars: int = 0) -> list[str]:
    """One-call helper: normalize + structure-aware chunk a raw text blob."""
    chunker = MarkdownHierarchicalChunker(max_chars=max_chars)
    return chunker.chunk_text(raw_text)
