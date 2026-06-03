from __future__ import annotations

import importlib
import re
from dataclasses import dataclass
from enum import Enum


class PIICategory(str, Enum):
    SSN = "ssn"
    EMAIL = "email"
    PHONE = "phone"
    NAME = "person_name"
    DATE_OF_BIRTH = "date_of_birth"
    ADDRESS = "address"
    MEDICAL_RECORD = "medical_record_number"
    HEALTH_DIAGNOSIS = "health_diagnosis"
    CREDIT_CARD = "credit_card"
    BANK_ACCOUNT = "bank_account"
    TAX_ID = "tax_id"
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    IP_ADDRESS = "ip_address"


@dataclass
class PIISpan:
    text: str
    category: PIICategory
    start: int
    end: int
    score: float


PATTERNS: dict[PIICategory, list[re.Pattern]] = {
    PIICategory.SSN: [
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    ],
    PIICategory.EMAIL: [
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ],
    PIICategory.PHONE: [
        re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
        re.compile(r"\(\d{3}\)\s*\d{3}[-.]?\d{4}\b"),
    ],
    PIICategory.CREDIT_CARD: [
        re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    ],
    PIICategory.BANK_ACCOUNT: [
        re.compile(r"\b\d{8,17}\b", re.ASCII),
    ],
    PIICategory.TAX_ID: [
        re.compile(r"\b\d{2}-\d{7}\b"),
        re.compile(r"\bEIN\s*[:#]?\s*\d{2}-\d{7}\b", re.IGNORECASE),
    ],
    PIICategory.DATE_OF_BIRTH: [
        re.compile(
            r"\b(?:DOB|Date of Birth|Birth Date|Born)"
            r"\s*[:#]?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            re.IGNORECASE,
        ),
    ],
    PIICategory.IP_ADDRESS: [
        re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
    ],
}


NAME_PATTERN = re.compile(
    r"\b(?:Patient|Claimant|Insured|Employee|Dr\.|Mr\.|Mrs\.|Ms\.)\s+"
    r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b",
)


DIAGNOSIS_PATTERNS = [
    re.compile(r"\b(?:diagnosis|diagnosed with|suffering from|complains of|"
               r"medical history|treatment for|condition:|impression:|"
               r"assessment:)\s*.{3,80}", re.IGNORECASE),
]


ADDRESS_PATTERNS = [
    re.compile(r"\b\d{1,5}\s+[A-Za-z0-9\s,]+(?:Street|St|Avenue|Ave|Road|Rd|"
               r"Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way|Place|Pl)\b", re.IGNORECASE),
]


class PIIDetector:
    def __init__(self, use_presidio: bool = False) -> None:
        self.use_presidio = use_presidio
        self._presidio_available = False
        if use_presidio:
            try:
                importlib.import_module("presidio_analyzer")
                self._presidio_available = True
            except ImportError:
                pass

    def detect(self, text: str) -> list[PIISpan]:
        spans: list[PIISpan] = []

        spans.extend(self._regex_scan(text))

        if self.use_presidio and self._presidio_available:
            spans.extend(self._presidio_scan(text))

        return self._deduplicate(spans)

    def _regex_scan(self, text: str) -> list[PIISpan]:
        spans: list[PIISpan] = []

        for category, patterns in PATTERNS.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    spans.append(PIISpan(
                        text=match.group(),
                        category=category,
                        start=match.start(),
                        end=match.end(),
                        score=0.95,
                    ))

        for match in NAME_PATTERN.finditer(text):
            spans.append(PIISpan(
                text=match.group(),
                category=PIICategory.NAME,
                start=match.start(),
                end=match.end(),
                score=0.85,
            ))

        for pattern in DIAGNOSIS_PATTERNS:
            for match in pattern.finditer(text):
                spans.append(PIISpan(
                    text=match.group(),
                    category=PIICategory.HEALTH_DIAGNOSIS,
                    start=match.start(),
                    end=match.end(),
                    score=0.75,
                ))

        for pattern in ADDRESS_PATTERNS:
            for match in pattern.finditer(text):
                spans.append(PIISpan(
                    text=match.group(),
                    category=PIICategory.ADDRESS,
                    start=match.start(),
                    end=match.end(),
                    score=0.7,
                ))

        return spans

    def _presidio_scan(self, text: str) -> list[PIISpan]:
        from presidio_analyzer import AnalyzerEngine
        engine = AnalyzerEngine()
        results = engine.analyze(
            text=text,
            entities=[
                "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "SSN",
                "CREDIT_CARD", "US_BANK_NUMBER", "US_DRIVER_LICENSE",
                "DATE_OF_BIRTH", "LOCATION", "MEDICAL_LICENSE",
            ],
            language="en",
        )
        category_map = {
            "PERSON": PIICategory.NAME,
            "EMAIL_ADDRESS": PIICategory.EMAIL,
            "PHONE_NUMBER": PIICategory.PHONE,
            "SSN": PIICategory.SSN,
            "CREDIT_CARD": PIICategory.CREDIT_CARD,
            "US_BANK_NUMBER": PIICategory.BANK_ACCOUNT,
            "US_DRIVER_LICENSE": PIICategory.DRIVERS_LICENSE,
            "DATE_OF_BIRTH": PIICategory.DATE_OF_BIRTH,
            "LOCATION": PIICategory.ADDRESS,
        }
        spans: list[PIISpan] = []
        for result in results:
            cat = category_map.get(result.entity_type, PIICategory.TAX_ID)
            spans.append(PIISpan(
                text=text[result.start:result.end],
                category=cat,
                start=result.start,
                end=result.end,
                score=result.score,
            ))
        return spans

    @staticmethod
    def _deduplicate(spans: list[PIISpan]) -> list[PIISpan]:
        spans.sort(key=lambda s: (-s.score, s.start))
        merged: list[PIISpan] = []
        for span in spans:
            if not merged:
                merged.append(span)
                continue
            last = merged[-1]
            if span.start >= last.start and span.end <= last.end:
                continue
            if span.start < last.end and span.end > last.start:
                merged[-1] = PIISpan(
                    text=last.text,
                    category=last.category,
                    start=min(last.start, span.start),
                    end=max(last.end, span.end),
                    score=max(last.score, span.score),
                )
            else:
                merged.append(span)
        return merged
