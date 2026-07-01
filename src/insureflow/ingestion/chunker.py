from __future__ import annotations

from insureflow.config import settings


class DocumentChunker:
    def __init__(self, chunk_size: int = 0, overlap: int = 0) -> None:
        # Use config defaults if not explicitly provided
        self.chunk_size = chunk_size or settings.extraction_chunk_size
        self.overlap = overlap or settings.extraction_overlap

    def chunk_text(self, text: str) -> list[str]:
        """Splits a large document into overlapping chunks safely."""
        if not text:
            return []

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + self.chunk_size
            # Ensure we don't break in the middle of a word if possible
            if end < text_length and not text[end].isspace():
                end = text.rfind(" ", start, end) + 1 or end
            chunks.append(text[start:end].strip())
            start = end - self.overlap

        return chunks
