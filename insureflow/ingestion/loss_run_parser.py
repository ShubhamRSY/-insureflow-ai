from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Optional

from insureflow.ingestion.base import BaseParser
from insureflow.models.submissions import (
    ClaimRecord,
    ClaimStatus,
    ExtractedChunk,
    ExtractedField,
    LossRunData,
    UnstructuredSubmission,
)


class LossRunParser(BaseParser):
    CLAIM_BLOCK_RE = re.compile(
        r"(?i)(?:claim|loss)\s*(?:#|id|number|no\.?)?\s*(?:\d+\s*:\s*)?\s*"
        r"([A-Za-z0-9][-A-Za-z0-9/_.]*\d[-A-Za-z0-9/_.]*)(?:\s*[-–—]|\n|$)",
    )
    DATE_RE = re.compile(r"(\d{4}[-/]\d{2}[-/]\d{2})")
    LINE_RE = re.compile(
        r"(?i)(?:line\s*:\s*)?(workers\s*(?:comp|compensation)|commercial\s+auto|"
        r"general\s+liability|property|inland\s+marine|cargo|"
        r"auto|wc|gl|umbrella|crime|spoilage)"
    )
    CAUSE_RE = re.compile(
        r"(?i)\*{0,2}(?:cause|reason|nature)\*{0,2}\s*:\s*\*{0,2}\s*(.+?)(?:\n|$)"
    )
    AMOUNT_RE = re.compile(
        r"(?i)\*{0,2}(?:incurred|paid|reserve|open\s+reserve|amount)"
        r"\*{0,2}\s*:\s*\*{0,2}\s*\$?([\d,]+(?:\.\d{2})?)"
    )
    STATUS_RE = re.compile(
        r"(?i)\*{0,2}status\*{0,2}\s*:\s*\*{0,2}\s*(open|closed|pending|litigation|subrogation)"
    )

    SECTION_HEADINGS = re.compile(
        r"(?i)^(#{1,3}\s*)?(?:claim\s+detail|loss\s+run|claims?\s+summary|"
        r"claim\s+detail|loss\s+history)\s*$",
        re.MULTILINE,
    )

    def parse(self, raw_text: str, submission_id: str) -> UnstructuredSubmission:
        lines = raw_text.split("\n")
        claims = self._extract_claims(raw_text, lines)
        summary = self._build_summary(claims, raw_text)

        submission = UnstructuredSubmission(
            submission_id=submission_id,
            source="loss_run",
            document_type="loss_run",
            raw_text=raw_text,
            processed_at=datetime.now(timezone.utc),
        )

        submission.extracted_fields = {
            "total_claims": [
                ExtractedField(
                    field_name="total_claims",
                    value=str(summary.total_claims),
                    confidence=0.85,
                    context=f"Parsed {summary.total_claims} claims",
                )
            ],
            "total_incurred": [
                ExtractedField(
                    field_name="total_incurred",
                    value=str(summary.total_incurred),
                    confidence=0.85,
                    context=f"Total incurred: ${summary.total_incurred:,.0f}",
                )
            ],
            "total_paid": [
                ExtractedField(
                    field_name="total_paid",
                    value=str(summary.total_paid),
                    confidence=0.85,
                    context=f"Total paid: ${summary.total_paid:,.0f}",
                )
            ],
        }

        for i, claim in enumerate(claims):
            submission.extracted_fields[f"claim.{i}.id"] = [
                ExtractedField(
                    field_name=f"claim.{i}.id",
                    value=claim.claim_id,
                    confidence=0.85,
                    context=claim.cause[:100],
                )
            ]
            submission.extracted_fields[f"claim.{i}.incurred"] = [
                ExtractedField(
                    field_name=f"claim.{i}.incurred",
                    value=str(claim.incurred_amount),
                    confidence=0.85,
                    context=claim.cause[:100],
                )
            ]

        submission.chunks = self._chunk_by_claims(raw_text, claims)

        return submission

    def parse_structured(self, raw_text: str) -> LossRunData:
        lines = raw_text.split("\n")
        claims = self._extract_claims(raw_text, lines)
        return self._build_summary(claims, raw_text)

    def _extract_claims(self, text: str, lines: list[str]) -> list[ClaimRecord]:
        blocks = self._split_claim_blocks(text)
        claims: list[ClaimRecord] = []

        for block in blocks:
            claim = self._parse_single_claim(block)
            if claim is not None:
                claims.append(claim)

        return claims

    def _split_claim_blocks(self, text: str) -> list[str]:
        blocks: list[str] = []
        current: list[str] = []
        in_claim = False

        for line in text.split("\n"):
            is_heading = bool(
                re.match(
                    r"(?i)^(?:#{1,3}\s+)?(?:claim|loss)\s+(?:#|id|number|no\.?)?\s*"
                    r"(?:\d+|[A-Za-z0-9][-A-Za-z0-9_.]*\d)",
                    line,
                )
            )
            if is_heading:
                if current:
                    blocks.append("\n".join(current))
                current = []
                in_claim = True

            if in_claim:
                current.append(line)

        if current:
            blocks.append("\n".join(current))

        if len(blocks) <= 1 and self.CLAIM_BLOCK_RE.search(text):
            blocks = re.split(
                r"(?=(?:#{1,3}\s+)?(?:claim|loss)\s+(?:#|id|number|no\.?)?\s*(?:\d+\s*:\s*)?\s*"
                r"(?:\d+|[A-Za-z0-9][-A-Za-z0-9_.]*\d))",
                text,
                flags=re.IGNORECASE,
            )
            blocks = [b.strip() for b in blocks if b.strip()]

        return blocks

    def _parse_single_claim(self, block: str) -> Optional[ClaimRecord]:
        id_match = self.CLAIM_BLOCK_RE.search(block)
        if not id_match:
            return None
        claim_id = id_match.group(1).strip()

        dates = self.DATE_RE.findall(block)
        date_of_loss = date.today()
        if dates:
            try:
                dt = datetime.strptime(dates[0].replace("/", "-"), "%Y-%m-%d")
                date_of_loss = dt.date()
            except ValueError:
                pass

        line_match = self.LINE_RE.search(block)
        line_of_business = line_match.group(1).strip() if line_match else "Unknown"

        cause_match = self.CAUSE_RE.search(block)
        cause = cause_match.group(1).strip() if cause_match else ""

        amounts = [float(a.replace(",", "")) for a in self.AMOUNT_RE.findall(block)]
        incurred = 0.0
        paid = 0.0
        reserve = 0.0

        if len(amounts) >= 1:
            incurred = amounts[0]
        if len(amounts) >= 2:
            paid = amounts[1]
        if len(amounts) >= 3:
            reserve = amounts[2]

        status_match = self.STATUS_RE.search(block)
        status = ClaimStatus.OPEN
        if status_match:
            val = status_match.group(1).lower()
            if "closed" in val:
                status = ClaimStatus.CLOSED
            elif "litigation" in val:
                status = ClaimStatus.PENDING_LITIGATION
            elif "subrogation" in val:
                status = ClaimStatus.SUBROGATION

        description_lines = []
        capture = False
        for line in block.split("\n"):
            stripped = line.strip()
            if re.match(r"(?i)(?:cause|description|details?|narrative)", stripped):
                capture = True
                continue
            if capture:
                if re.match(r"(?i)^(?:claim|loss)\s", stripped):
                    break
                if stripped and not stripped.startswith("**") and ":" not in stripped[:20]:
                    description_lines.append(stripped)

        if not cause:
            description = " ".join(description_lines)[:300] if description_lines else ""
        else:
            description = cause

        return ClaimRecord(
            claim_id=claim_id,
            date_of_loss=date_of_loss,
            line_of_business=line_of_business,
            cause=cause or description[:100],
            description=description,
            incurred_amount=incurred,
            paid_amount=paid,
            open_reserve=reserve,
            claim_status=status,
            notes=" | ".join(description_lines) if description_lines else "",
        )

    def _build_summary(self, claims: list[ClaimRecord], text: str) -> LossRunData:
        return LossRunData(
            total_claims=len(claims),
            total_incurred=sum(c.incurred_amount for c in claims),
            total_paid=sum(c.paid_amount for c in claims),
            total_open_reserves=sum(c.open_reserve for c in claims),
            claims=claims,
            loss_ratios=self._parse_loss_ratios(text),
        )

    def _parse_loss_ratios(self, text: str) -> dict[str, float]:
        ratios: dict[str, float] = {}
        table_pattern = re.compile(
            r"(?i)(\d{4}[-–]\d{4}|\d{4})\s+"
            r"\$?([\d,]+)\s+\$?([\d,]+)\s+([\d.]+)%"
        )
        for match in table_pattern.finditer(text):
            ratios[match.group(1)] = float(match.group(4))
        return ratios

    def _chunk_by_claims(
        self, text: str, claims: list[ClaimRecord]
    ) -> list[ExtractedChunk]:
        if not claims:
            return [
                ExtractedChunk(
                    chunk_index=0, text=text, start_char=0, end_char=len(text)
                )
            ]
        chunks: list[ExtractedChunk] = []
        pos = 0
        for i, claim in enumerate(claims):
            claim_tag = claim.claim_id
            idx = text.find(claim_tag, pos)
            if idx == -1:
                continue
            next_idx = len(text)
            if i + 1 < len(claims):
                next_tag = claims[i + 1].claim_id
                next_pos = text.find(next_tag, idx + len(claim_tag))
                if next_pos != -1:
                    next_idx = next_pos
            chunk_text = text[idx:next_idx].strip()
            if chunk_text:
                chunks.append(
                    ExtractedChunk(
                        chunk_index=i,
                        text=chunk_text,
                        start_char=idx,
                        end_char=next_idx,
                    )
                )
            pos = next_idx
        if not chunks:
            chunks.append(
                ExtractedChunk(
                    chunk_index=0, text=text, start_char=0, end_char=len(text)
                )
            )
        return chunks
