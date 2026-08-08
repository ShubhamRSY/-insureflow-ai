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
        r"(?i)(?:line\s*:\s*)?(workers\s*(?:compensation|comp)|commercial\s+auto|"
        r"general\s+liability|property|inland\s+marine|cargo|"
        r"auto|wc|gl|umbrella|crime|spoilage)"
    )
    CAUSE_RE = re.compile(r"(?i)\*{0,2}(?:cause|reason|nature)\*{0,2}\s*:\s*\*{0,2}\s*(.+?)(?:\n|$)")
    AMOUNT_RE = re.compile(
        r"(?i)\*{0,2}(?:incurred|paid|reserve|open\s+reserve|amount)"
        r"\*{0,2}\s*:\s*\*{0,2}\s*\$?([\d,]+(?:\.\d{2})?)"
    )
    STATUS_RE = re.compile(r"(?i)\*{0,2}status\*{0,2}\s*:\s*\*{0,2}\s*(open|closed|pending|litigation|subrogation)")
    REOPENED_RE = re.compile(r"(?i)(?:reopened|re-?opened)")

    SECTION_HEADINGS = re.compile(
        r"(?i)^(#{1,3}\s*)?(?:claim\s+detail|loss\s+run|claims?\s+summary|"
        r"claim\s+detail|loss\s+history)\s*$",
        re.MULTILINE,
    )

    # ── Table-aware extraction (real carrier loss runs arrive as tables) ──
    # Role → regex over a single normalized header cell (word-boundary matched so
    # e.g. "id" never matches inside "paid").
    TABLE_TOKENS: dict[str, re.Pattern[str]] = {
        "id": re.compile(r"(?i)\b(claim\s*id|claim\s*#|claim\s*no\.?|claim\s*number|claim\s*nbr|claimid|reference|claim)\b|\bid\b"),
        "date": re.compile(r"(?i)\b(date\s+of\s+loss|loss\s+date|accident\s+date|occurrence\s*date|dol|loss\s+dt|date)\b"),
        "line": re.compile(r"(?i)\b(line\s+of\s+business|lob|coverage\s+type|business\s+line|coverage|line)\b"),
        "cause": re.compile(r"(?i)\b(cause\s+of\s+loss|loss\s+description|loss\s+cause|description\s+of\s+loss|cause|description|nature)\b"),
        "incurred": re.compile(r"(?i)\b(total\s+incurred|incurred\s+loss|incurred\s+amount|amt\s+incurred|incurred)\b"),
        "paid": re.compile(r"(?i)\b(paid\s+loss|paid\s+amount|amount\s+paid|amt\s+paid|paid\s+to\s+date|paid)\b"),
        "status": re.compile(r"(?i)\b(claim\s+status|current\s+status|open[/\\-]closed|status)\b"),
    }
    # "incurred"/"paid" also appear in LOSS RATE ANALYSIS tables; require the id
    # column to keep claims tables distinct from policy-period tables.
    _CELL_DATE_RE = re.compile(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})")
    _MONEY_RE = re.compile(r"^[$£€]?\s*([\d,]+(?:\.\d{1,2})?)$")
    _SEPARATOR_RE = re.compile(r"^[\s|\-_:+.,=~]+$")

    def parse(self, raw_text: str, submission_id: str) -> UnstructuredSubmission:
        claims, confidences = self._extract_claims_with_confidence(raw_text)
        summary = self._build_summary(claims, raw_text)

        submission = UnstructuredSubmission(
            submission_id=submission_id,
            source="loss_run",
            document_type="loss_run",
            raw_text=raw_text,
            processed_at=datetime.now(timezone.utc),
        )

        aggregate_conf = round(sum(confidences) / len(confidences), 2) if confidences else 0.85

        submission.extracted_fields = {
            "total_claims": [
                ExtractedField(
                    field_name="total_claims",
                    value=str(summary.total_claims),
                    confidence=aggregate_conf,
                    context=f"Parsed {summary.total_claims} claims",
                )
            ],
            "total_incurred": [
                ExtractedField(
                    field_name="total_incurred",
                    value=str(summary.total_incurred),
                    confidence=aggregate_conf,
                    context=f"Total incurred: ${summary.total_incurred:,.0f}",
                )
            ],
            "total_paid": [
                ExtractedField(
                    field_name="total_paid",
                    value=str(summary.total_paid),
                    confidence=aggregate_conf,
                    context=f"Total paid: ${summary.total_paid:,.0f}",
                )
            ],
        }

        for i, claim in enumerate(claims):
            conf = round(confidences[i], 2) if i < len(confidences) else claim.extraction_confidence
            claim_ctx = claim.cause[:100] or claim.claim_id
            submission.extracted_fields[f"claim.{i}.id"] = [
                ExtractedField(
                    field_name=f"claim.{i}.id",
                    value=claim.claim_id,
                    confidence=conf,
                    context=claim_ctx,
                )
            ]
            submission.extracted_fields[f"claim.{i}.incurred"] = [
                ExtractedField(
                    field_name=f"claim.{i}.incurred",
                    value=str(claim.incurred_amount),
                    confidence=conf,
                    context=claim_ctx,
                )
            ]
            submission.extracted_fields[f"claim.{i}.paid"] = [
                ExtractedField(
                    field_name=f"claim.{i}.paid",
                    value=str(claim.paid_amount),
                    confidence=conf,
                    context=claim_ctx,
                )
            ]
            submission.extracted_fields[f"claim.{i}.status"] = [
                ExtractedField(
                    field_name=f"claim.{i}.status",
                    value=claim.claim_status.value,
                    confidence=conf,
                    context=claim_ctx,
                )
            ]
            submission.extracted_fields[f"claim.{i}.date_of_loss"] = [
                ExtractedField(
                    field_name=f"claim.{i}.date_of_loss",
                    value=claim.date_of_loss.isoformat(),
                    confidence=conf,
                    context=claim_ctx,
                )
            ]
            if claim.line_of_business and claim.line_of_business != "Unknown":
                submission.extracted_fields[f"claim.{i}.line_of_business"] = [
                    ExtractedField(
                        field_name=f"claim.{i}.line_of_business",
                        value=claim.line_of_business,
                        confidence=conf,
                        context=claim_ctx,
                    )
                ]

        submission.chunks = self._chunk_by_claims(raw_text, claims)

        return submission

    def parse_structured(self, raw_text: str) -> LossRunData:
        claims, confidences = self._extract_claims_with_confidence(raw_text)
        for claim, conf in zip(claims, confidences):
            claim.extraction_confidence = round(conf, 2)
        return self._build_summary(claims, raw_text)

    def _extract_claims(self, text: str, lines: list[str]) -> list[ClaimRecord]:
        claims, _ = self._extract_claims_with_confidence(text)
        return claims

    def _extract_claims_with_confidence(self, text: str) -> tuple[list[ClaimRecord], list[float]]:
        """Table-aware extraction: parse carrier claim tables AND claim-detail
        blocks, then merge by claim id. Returns (claims, per-claim confidence)."""
        table_claims, table_conf = self._parse_table_claims(text)
        block_claims, block_conf = self._parse_block_claims_with_confidence(text)

        if not block_claims:
            return table_claims, table_conf
        if not table_claims:
            return block_claims, block_conf

        return self._merge_claims(table_claims, table_conf, block_claims, block_conf)

    # ── Table path ──────────────────────────────────────────────────────
    @staticmethod
    def _split_cells(line: str) -> Optional[list[str]]:
        # Pipe (markdown) and tab-delimited exports are reliable; comma CSV is
        # not used because prose prose inside claim narratives is full of commas.
        if "|" in line:
            cells = [c.strip() for c in line.split("|")]
            return [c for c in cells if c != ""]
        if "\t" in line:
            cells = [c.strip() for c in line.split("\t")]
            return [c for c in cells if c != ""]
        return None

    def _match_header_role(self, cell: str) -> Optional[str]:
        norm = re.sub(r"[^a-z0-9 ]", "", cell.lower()).strip()
        for role, pattern in self.TABLE_TOKENS.items():
            if pattern.search(norm):
                return role
        return None

    def _parse_table_claims(self, text: str) -> tuple[list[ClaimRecord], list[float]]:
        lines = text.split("\n")
        for i, line in enumerate(lines):
            cells = self._split_cells(line)
            if not cells or len(cells) < 3:
                continue
            roles: dict[str, int] = {}
            for idx, cell in enumerate(cells):
                role = self._match_header_role(cell)
                if role and role not in roles:
                    roles[role] = idx
            # A claims table must have an id column plus a date or amount column.
            if "id" not in roles:
                continue
            if not ({"date", "incurred", "paid"} & set(roles)):
                continue

            claims: list[ClaimRecord] = []
            confidences: list[float] = []
            for row in lines[i + 1 :]:
                row_cells = self._split_cells(row)
                if not row_cells:
                    break  # tables are contiguous; a non-delimited line ends the table
                # Skip markdown separator rows like |---|---|
                if self._SEPARATOR_RE.match("".join(row_cells)) or all(self._SEPARATOR_RE.match(c) for c in row_cells if c):
                    continue
                if all(not c for c in row_cells):
                    continue
                claim, conf = self._row_to_claim(row_cells, roles)
                if claim is not None:
                    claims.append(claim)
                    confidences.append(conf)
            if claims:
                return claims, confidences
        return [], []

    def _row_to_claim(self, cells: list[str], roles: dict[str, int]) -> tuple[Optional[ClaimRecord], float]:
        def cell(role: str) -> str:
            idx = roles.get(role)
            if idx is None or idx >= len(cells):
                return ""
            return cells[idx].strip()

        claim_id = cell("id")
        # Reject cells that carry markup/colon content (prose, not an ID column).
        if not claim_id or claim_id == "-" or "**" in claim_id or ":" in claim_id:
            return None, 0.0

        conf = 0.95
        missing = []

        date_raw = cell("date")
        date_of_loss = date.today()
        if date_raw:
            m = self._CELL_DATE_RE.search(date_raw)
            if m:
                try:
                    parsed = self._parse_flexible_date(m.group(1))
                    if parsed:
                        date_of_loss = parsed
                except (ValueError, TypeError):
                    missing.append("date")
            else:
                missing.append("date")
        else:
            missing.append("date")

        money = {}
        for role in ("incurred", "paid"):
            raw = cell(role).replace(",", "").replace("$", "").replace("£", "").replace("€", "").strip()
            if raw:
                m = self._MONEY_RE.match(raw)
                if m:
                    money[role] = float(m.group(1).replace(",", ""))
                else:
                    missing.append(role)
            else:
                missing.append(role)

        status = ClaimStatus.OPEN
        status_raw = cell("status").lower()
        if "closed" in status_raw:
            status = ClaimStatus.CLOSED
        elif "litigat" in status_raw or "pending" in status_raw:
            status = ClaimStatus.PENDING_LITIGATION
        elif "subrogat" in status_raw:
            status = ClaimStatus.SUBROGATION

        cause = cell("cause")
        line = cell("line") or "Unknown"

        for req in ("id", "date", "incurred"):
            if req in missing:
                conf -= 0.2
        if "paid" in missing:
            conf -= 0.1
        if not status_raw:
            conf -= 0.05
        conf = round(max(conf, 0.5), 2)

        claim = ClaimRecord(
            claim_id=claim_id,
            date_of_loss=date_of_loss,
            line_of_business=line,
            cause=cause,
            incurred_amount=money.get("incurred", 0.0),
            paid_amount=money.get("paid", 0.0),
            claim_status=status,
            extraction_confidence=conf,
        )
        return claim, conf

    @staticmethod
    def _parse_flexible_date(raw: str) -> Optional[date]:
        raw = raw.replace("/", "-")
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d-%m-%Y"):
            try:
                return datetime.strptime(raw[:10], fmt).date()
            except ValueError:
                continue
        # Ambiguous d/m vs m/d: prefer month-first (US carrier convention) when
        # both parts are <= 12, otherwise day-first is unambiguous.
        try:
            parts = [int(p) for p in raw.split("-")]
            if len(parts) == 3 and parts[0] > 12:
                return date(parts[2], parts[1], parts[0]) if parts[2] >= 1000 else date(2000 + parts[2], parts[1], parts[0])
        except (ValueError, TypeError):
            pass
        return None

    # ── Claim-detail block path (existing behavior, now confidence-scored) ──
    def _parse_block_claims_with_confidence(self, text: str) -> tuple[list[ClaimRecord], list[float]]:
        blocks = self._split_claim_blocks(text)
        claims: list[ClaimRecord] = []
        confidences: list[float] = []
        for block in blocks:
            claim = self._parse_single_claim(block)
            if claim is not None:
                claims.append(claim)
                confidences.append(self._score_block_confidence(claim, block))
        return claims, confidences

    @staticmethod
    def _score_block_confidence(claim: ClaimRecord, block: str) -> float:
        conf = 0.85
        if claim.date_reported is not None:
            conf += 0.05
        if claim.date_closed is not None:
            conf += 0.03
        if claim.open_reserve > 0 or claim.claim_status == ClaimStatus.OPEN:
            conf += 0.03
        if not claim.cause:
            conf -= 0.05
        if not re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", block):
            conf -= 0.15
        return round(min(max(conf, 0.5), 0.95), 2)

    # ── Merge ────────────────────────────────────────────────────────────
    def _merge_claims(
        self,
        table_claims: list[ClaimRecord],
        table_conf: list[float],
        block_claims: list[ClaimRecord],
        block_conf: list[float],
    ) -> tuple[list[ClaimRecord], list[float]]:
        block_by_id = {c.claim_id: (c, conf) for c, conf in zip(block_claims, block_conf)}
        merged: list[ClaimRecord] = []
        confidences: list[float] = []
        seen: set[str] = set()

        for claim, conf in zip(table_claims, table_conf):
            if claim.claim_id in block_by_id:
                detail, detail_conf = block_by_id[claim.claim_id]
                # Detail blocks carry the richer fields; table supplies row-level
                # certainty. Conflict on incurred = misaligned sources.
                amounts_agree = abs(detail.incurred_amount - claim.incurred_amount) < 1
                merged_claim = detail.model_copy(deep=True)
                if merged_claim.incurred_amount == 0.0 and claim.incurred_amount > 0:
                    merged_claim.incurred_amount = claim.incurred_amount
                if not merged_claim.line_of_business or merged_claim.line_of_business == "Unknown":
                    merged_claim.line_of_business = claim.line_of_business
                merged_claim.cause = merged_claim.cause or claim.cause
                merged_conf = round(min(detail_conf, conf), 2) if amounts_agree else 0.6
                merged.append(merged_claim)
                confidences.append(merged_conf)
                seen.add(claim.claim_id)
            else:
                merged.append(claim)
                confidences.append(conf)

        for claim, conf in zip(block_claims, block_conf):
            if claim.claim_id not in seen:
                merged.append(claim)
                confidences.append(conf)

        return merged, confidences

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
        date_reported: Optional[date] = None
        date_closed: Optional[date] = None
        parsed_dates: list[date] = []
        for raw in dates:
            try:
                parsed_dates.append(datetime.strptime(raw.replace("/", "-"), "%Y-%m-%d").date())
            except ValueError:
                continue
        if parsed_dates:
            date_of_loss = parsed_dates[0]
        if len(parsed_dates) >= 2:
            date_reported = parsed_dates[1]
        if len(parsed_dates) >= 3:
            date_closed = parsed_dates[2]
        # Valuation point = the most recent date in the block (the report "as of").
        valuation_date = max(parsed_dates) if parsed_dates else date.today()

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

        # "Open (lawsuit pending)" and "Litigation is in the discovery phase"
        # carry material status signals outside the Status: label.
        if status == ClaimStatus.OPEN:
            if re.search(r"(?i)\blitigat", block):
                status = ClaimStatus.PENDING_LITIGATION
            elif re.search(r"(?i)\bsubrogation\b\s*:\s*(?!none\b)", block):
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
            date_reported=date_reported,
            date_closed=date_closed,
            valuation_date=valuation_date,
            reopened=bool(self.REOPENED_RE.search(block)),
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
        # Table-based: | Policy Period | Earned Premium | Total Incurred | Loss Ratio |
        for line in text.split("\n"):
            cells = self._split_cells(line)
            if not cells or len(cells) < 4:
                continue
            period = cells[0].strip()
            ratio_match = re.search(r"([\d.]+)\s*%", cells[3])
            if not ratio_match:
                continue
            value = float(ratio_match.group(1))
            if re.match(r"(?i)(aggregate|total|5\s*[-–/]\s*yr)", period):
                ratios["aggregate"] = value
            elif re.match(r"(?i)\d{4}[-–/]\d{4}|\d{4}", period):
                ratios[period] = value
        # Headline "Loss Ratio: 92%" / "5-year loss ratio: 0.92"
        if not ratios:
            headline = re.search(r"(?i)loss\s*ratio[:\s]+([\d.]+)\s*%", text)
            if headline:
                ratios["aggregate"] = float(headline.group(1)) / 100.0 if float(headline.group(1)) > 1 else float(headline.group(1))
            else:
                headline_pct = re.search(r"(?i)loss\s*ratio[:\s]+([\d.]+)\s*%?", text)
                if headline_pct:
                    val = float(headline_pct.group(1))
                    ratios["aggregate"] = val / 100.0 if val > 1 else val
        return ratios

    def _chunk_by_claims(self, text: str, claims: list[ClaimRecord]) -> list[ExtractedChunk]:
        if not claims:
            return [ExtractedChunk(chunk_index=0, text=text, start_char=0, end_char=len(text))]
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
            chunks.append(ExtractedChunk(chunk_index=0, text=text, start_char=0, end_char=len(text)))
        return chunks
