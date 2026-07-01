from __future__ import annotations

from typing import Optional

from insureflow.redaction.detector import PIICategory, PIIDetector, PIISpan

REDACT_LABELS: dict[PIICategory, str] = {
    PIICategory.SSN: "[REDACTED SSN]",
    PIICategory.EMAIL: "[REDACTED EMAIL]",
    PIICategory.PHONE: "[REDACTED PHONE]",
    PIICategory.NAME: "[REDACTED NAME]",
    PIICategory.DATE_OF_BIRTH: "[REDACTED DOB]",
    PIICategory.ADDRESS: "[REDACTED ADDRESS]",
    PIICategory.MEDICAL_RECORD: "[REDACTED MEDICAL RECORD]",
    PIICategory.HEALTH_DIAGNOSIS: "[REDACTED DIAGNOSIS]",
    PIICategory.CREDIT_CARD: "[REDACTED CC]",
    PIICategory.BANK_ACCOUNT: "[REDACTED BANK ACCT]",
    PIICategory.TAX_ID: "[REDACTED TAX ID]",
    PIICategory.PASSPORT: "[REDACTED PASSPORT]",
    PIICategory.DRIVERS_LICENSE: "[REDACTED DL]",
    PIICategory.IP_ADDRESS: "[REDACTED IP]",
}


class PIIRedactor:
    def __init__(self, detector: Optional[PIIDetector] = None) -> None:
        self.detector = detector or PIIDetector()

    def redact(self, text: str, mask: bool = True) -> str:
        spans = self.detector.detect(text)
        if not spans:
            return text

        spans.sort(key=lambda s: s.start)

        result: list[str] = []
        pos = 0
        for span in spans:
            if span.start > pos:
                result.append(text[pos : span.start])
            replacement = self._replace(span, mask)
            result.append(replacement)
            pos = max(pos, span.end)

        result.append(text[pos:])
        return "".join(result)

    def redact_fields(
        self,
        data: dict,
        mask: bool = True,
    ) -> dict:
        redacted: dict = {}
        for key, value in data.items():
            if isinstance(value, str):
                redacted[key] = self.redact(value, mask=mask)
            elif isinstance(value, dict):
                redacted[key] = self.redact_fields(value, mask=mask)
            elif isinstance(value, list):
                redacted[key] = [self.redact_fields(item, mask=mask) if isinstance(item, dict) else self.redact(str(item), mask=mask) if isinstance(item, str) else item for item in value]
            else:
                redacted[key] = value
        return redacted

    @staticmethod
    def _replace(span: PIISpan, mask: bool) -> str:
        if not mask:
            return REDACT_LABELS.get(span.category, "[REDACTED]")
        label = REDACT_LABELS.get(span.category, "[REDACTED]")
        if span.category in (PIICategory.SSN, PIICategory.EMAIL, PIICategory.PHONE):
            if span.category == PIICategory.SSN:
                return span.text[:4] + "XX-XXXX"
            elif span.category == PIICategory.EMAIL:
                local, domain = span.text.split("@", 1)
                return local[:2] + "***@" + domain
            elif span.category == PIICategory.PHONE:
                return "***-***-" + span.text[-4:] if len(span.text) >= 4 else label
        return label
