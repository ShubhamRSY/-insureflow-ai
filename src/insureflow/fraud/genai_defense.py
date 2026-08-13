"""Malicious GenAI attack defense — generated text, prompt injection, and AI spoofing.

Heuristic and deterministic: every point on the score maps to a named signal.
Screens submission narratives, loss-run notes, and broker emails for
AI-generated artifacts, jailbreaks, and injection payloads.
"""

from __future__ import annotations

import math
import re
import statistics
from typing import Any

from insureflow.fraud.models import GenAiDocument, RiskAssessment

_INJECTION = re.compile(
    r"(ignore\s+(all\s+)?previous\s+instructions|ignore\s+all\s+prior|"
    r"you\s+are\s+now\s+(?:dan|jailbroken)|do\s+anything\s+now|"
    r"reveal\s+(?:your|the)\s+(?:system\s+)?prompt|jailbreak|"
    r"system\s*prompt\s*:|<\s*script|\[\s*inst\s*\]|"
    r"disregard\s+(?:the\s+)?(?:above|prior)\s+(?:rules|instructions))",
    re.IGNORECASE,
)
_AI_SELF = re.compile(
    r"(as an ai(?: language model)?|i(?:'m| am) (?:an? )?(?:ai|language model)|"
    r"i don't have personal (?:experiences|opinions)|i cannot (?:provide|browse|access)|"
    r"as a large language model)",
    re.IGNORECASE,
)
_AI_TELLS = re.compile(
    r"\b(delve|tapestry|landscape|leverage|robust|comprehensive|furthermore|"
    r"moreover|it is important to note|in conclusion|certainly[!]? here's|"
    r"happy to help|underscores the|multifaceted|paradigm shift)\b",
    re.IGNORECASE,
)
_PLACEHOLDERS = re.compile(
    r"(\[your name\]|\[company\]|\[insert|acme corp|lorem ipsum|john doe|jane doe|example\.com)",
    re.IGNORECASE,
)
_ZW = re.compile(r"[\u200b\u200c\u200d\ufeff\u2060]")
_SENTENCE = re.compile(r"[.!?]+[\s\n]+")


def _risk_level(score: float) -> str:
    return "critical" if score > 0.75 else "high" if score > 0.55 else "medium" if score > 0.3 else "low"


def _action(level: str) -> str:
    return {
        "critical": "block_and_escalate",
        "high": "quarantine_and_review",
        "medium": "flag_for_analyst",
        "low": "standard_processing",
    }[level]


def _sentences(text: str) -> list[str]:
    parts = _SENTENCE.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


def _ngram_repeats(text: str, n: int = 5) -> int:
    tokens = re.findall(r"[a-z0-9']+", text.lower())
    if len(tokens) < n * 3:
        return 0
    grams = [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]
    counts: dict[str, int] = {}
    for g in grams:
        counts[g] = counts.get(g, 0) + 1
    return sum(1 for c in counts.values() if c >= 3)


class GenAiDefenseEngine:
    """Scores a document/field for GenAI generation and attack artifacts."""

    def assess(self, document: GenAiDocument) -> RiskAssessment:
        text = document.content or ""
        score = 0.0
        signals: list[dict[str, Any]] = []
        flagged: list[str] = []

        def add(name: str, weight: float, detail: str) -> None:
            nonlocal score
            if weight <= 0:
                return
            score = min(1.0, score + weight)
            signals.append({"signal": name, "weight": round(weight, 3), "detail": detail})
            flagged.append(detail)

        if not text.strip():
            add("empty_content", 0.05, "document has no content to screen")
            level = _risk_level(score)
            return RiskAssessment(
                engine="genai_defense",
                subject_id=document.subject_id or document.document_id,
                risk_score=round(score, 4),
                risk_level=level,
                signals=signals,
                flagged_patterns=flagged,
                recommended_action=_action(level),
            )

        inj = _INJECTION.findall(text)
        if inj:
            add("prompt_injection", 0.55, f"prompt-injection / jailbreak phrase(s): {inj[:3]}")

        if _AI_SELF.search(text):
            add("ai_self_identification", 0.45, "text self-identifies as an AI / language model")

        tells = _AI_TELLS.findall(text)
        if len(tells) >= 4:
            add("ai_style_tells", 0.3, f"{len(tells)} high-frequency LLM style markers")
        elif len(tells) >= 2:
            add("ai_style_tells", 0.15, f"{len(tells)} LLM style markers")

        if _PLACEHOLDERS.search(text):
            add("template_placeholders", 0.25, "placeholder / dummy identity tokens (John Doe, [Your Name], ACME)")

        zw = _ZW.findall(text)
        if zw:
            add("zero_width_injection", 0.4, f"{len(zw)} zero-width / invisible characters — steganographic injection")

        sents = _sentences(text)
        if len(sents) >= 6:
            lengths = [len(s.split()) for s in sents]
            mean = statistics.fmean(lengths)
            if mean > 0:
                cv = statistics.pstdev(lengths) / mean
                if cv < 0.18:
                    add("uniform_sentence_length", 0.25, f"sentence-length CV {cv:.3f} — mechanically even (LLM burstiness)")

        md_lines = sum(1 for line in text.splitlines() if re.match(r"^\s*(#{1,6}\s+|[-*]\s+|\d+\.\s+|\*\*)", line))
        if text.count("\n") >= 8 and md_lines / max(text.count("\n"), 1) > 0.45:
            add("markdown_overuse", 0.15, "markdown/list density consistent with chatbot formatting")

        repeats = _ngram_repeats(text)
        if repeats >= 3:
            add("repeated_ngrams", 0.2, f"{repeats} 5-grams repeated 3+ times — copy-paste / generation loop")

        tokens = re.findall(r"[A-Za-z]+", text)
        if len(tokens) >= 80:
            unique = len({t.lower() for t in tokens})
            ttr = unique / len(tokens)
            if ttr < 0.28:
                add("low_lexical_diversity", 0.2, f"type-token ratio {ttr:.2f} — repetitive generated prose")

        # Homoglyph / mixed-script abuse (Cyrillic lookalikes in otherwise Latin text).
        cyr = sum(1 for ch in text if "\u0400" <= ch <= "\u04ff")
        latin = sum(1 for ch in text if ("A" <= ch <= "Z") or ("a" <= ch <= "z"))
        if cyr and latin and cyr / max(cyr + latin, 1) < 0.15 and cyr >= 3:
            add("homoglyph_mix", 0.3, f"{cyr} Cyrillic characters mixed into Latin text")

        entropy = _shannon_entropy(text[:4000])
        if len(text) >= 200 and entropy < 3.2:
            add("low_entropy", 0.15, f"character entropy {entropy:.2f} — highly repetitive payload")

        level = _risk_level(score)
        return RiskAssessment(
            engine="genai_defense",
            subject_id=document.subject_id or document.document_id,
            risk_score=round(score, 4),
            risk_level=level,
            signals=signals,
            flagged_patterns=flagged,
            recommended_action=_action(level),
        )


def _shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    freq: dict[str, int] = {}
    for ch in text:
        freq[ch] = freq.get(ch, 0) + 1
    n = len(text)
    return -sum((c / n) * math.log2(c / n) for c in freq.values())


def assess_document(document: GenAiDocument) -> RiskAssessment:
    return GenAiDefenseEngine().assess(document)
