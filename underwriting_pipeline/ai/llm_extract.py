"""LLM extraction. Groq or any OpenAI-compatible host comes from the environment.

    LLM_BASE_URL   default http://localhost:11434/v1  (Ollama)
    LLM_MODEL      default qwen2.5:7b when the host is local
    LLM_API_KEY    required for a remote host; local host uses the dummy "ollama"

A 429 waits and retries. Do not put a real key in a file in this project.

# ponytail: one chat call per submission. Batch when a queue is large enough to measure.
"""

import json
import os
import re
import time
import urllib.error
import urllib.request

MIN_CONFIDENCE = 0.75
DEFAULT_BASE = "http://localhost:11434/v1"
DEFAULT_MODEL = "qwen2.5:7b"
DEFAULT_KEY = "ollama"

SYSTEM = """You extract commercial insurance fields from the documents.
Return one JSON object and nothing else.
Use only facts copied from the documents. If a fact is not there, value is null and confidence is 0.
Never guess. A no-known-loss letter is not a loss-run date; leave loss_run_valued_through null.
Spanish and unlabeled email prose are allowed. Put the English value in value. quote must be copied character for character from one file, with no added words and no added accents.
For operations, keep the specific English words from the source and do not shorten them to one class word. If they cook a named food, the value must contain that food word and the word restaurant. If the source is Spanish, translate it and still quote the Spanish line exactly. A bar or night club is a bar and nightclub. mamposteria means masonry, and the construction value is the English word.
loss_run_valued_through is only the valued-through date copied from the file. Never invent a date. If the file does not show that date, use null even if you think runs exist.
If square feet or the premises address differ across files, do not pick a side. Leave that field null and add a conflict whose values include both numbers or both addresses, each with an exact quote.
quote must be an exact substring of one document. source is that document's file name.
confidence is a number from 0 to 1. Use below 0.75 when you are unsure.
If two documents disagree, do not pick a side. Leave that field null and add a conflict with both values.
Fields: named_insured, premises_address, effective_date, operations, sales_or_payroll, tiv_building, construction, year_built, loss_run_valued_through.
Schema: {"fields":[{"field_id":"","value":null,"source":"","quote":"","confidence":0}],"conflicts":[{"field":"","values":[{"value":"","source":"","quote":"","confidence":0}]}]}
"""


def _safe(message: str) -> str:
    key = os.environ.get("LLM_API_KEY", "")
    if key and key != DEFAULT_KEY and key in message:
        message = message.replace(key, "[redacted]")
    return message


def _local(base: str) -> bool:
    host = base.lower()
    return "localhost" in host or "127.0.0.1" in host


def endpoint_settings() -> dict:
    base = (os.environ.get("LLM_BASE_URL") or DEFAULT_BASE).rstrip("/")
    model = os.environ.get("LLM_MODEL") or ""
    key = os.environ.get("LLM_API_KEY") or ""
    if _local(base):
        return {"base": base, "model": model or DEFAULT_MODEL, "key": key or DEFAULT_KEY}
    if not key:
        raise RuntimeError("LLM_API_KEY is not set. Do not write the key into a file.")
    if not model:
        raise RuntimeError("LLM_MODEL is not set.")
    return {"base": base, "model": model, "key": key}


def _parse_json(content: str) -> dict:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            return json.loads(content[start : end + 1])
        raise


def find_quote(text: str, quote: str) -> tuple[int, int] | None:
    if not quote:
        return None
    found = text.find(quote)
    if found >= 0:
        return found, found + len(quote)
    parts = quote.split()
    if not parts:
        return None
    match = re.search(r"\s+".join(re.escape(part) for part in parts), text)
    if not match:
        return None
    return match.start(), match.end()


def accept_field(item: dict, docs: dict[str, str], ocr_confidence: dict | None = None) -> dict:
    """Drop anything that is uncited or below the confidence line. Never keep a guess.

    A scanned source uses the Tesseract word score. A typed file keeps the model score.
    """
    field_id = item.get("field_id") or item.get("field")
    value = item.get("value")
    source = item.get("source") or ""
    quote = item.get("quote") or ""
    try:
        model_confidence = float(item.get("confidence") or 0)
    except (TypeError, ValueError):
        model_confidence = 0.0
    confidence = model_confidence
    if ocr_confidence and source in ocr_confidence:
        confidence = ocr_confidence[source]
    base = {
        "field_id": field_id,
        "value": None,
        "source": source or None,
        "start": None,
        "end": None,
        "confidence": confidence,
        "model_confidence": model_confidence,
        "needs_review": True,
    }
    if value is None or str(value).strip() == "" or str(value).lower() == "null":
        return base
    if confidence < MIN_CONFIDENCE:
        return base
    text = docs.get(source, "")
    span = find_quote(text, quote) or find_quote(text, str(value))
    if span is None:
        base["confidence"] = 0.0
        return base
    if field_id == "loss_run_valued_through" and "no known loss" in text[span[0] : span[1]].lower():
        return base
    return {
        "field_id": field_id,
        "value": str(value).strip(),
        "source": source,
        "start": span[0],
        "end": span[1],
        "confidence": confidence,
        "model_confidence": model_confidence,
        "needs_review": False,
    }


def _post(settings: dict, payload: dict) -> dict:
    for attempt in range(6):
        request = urllib.request.Request(
            settings["base"] + "/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {settings['key']}",
                "Content-Type": "application/json",
                "User-Agent": "curl/8.7.1",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < 5:
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                exc.read()
                try:
                    wait = float(retry_after)
                except (TypeError, ValueError):
                    wait = min(60, 2**attempt)
                time.sleep(min(wait, 60))
                continue
            if exc.code == 401:
                raise RuntimeError("model call failed: HTTP 401 authentication failed.") from None
            detail = exc.read().decode(errors="replace")[:300]
            raise RuntimeError(_safe(f"model call failed: HTTP {exc.code} {detail}")) from None
    raise RuntimeError("model call failed: HTTP 429")


def llm_extract(docs: list[dict]) -> dict:
    settings = endpoint_settings()
    parts = []
    for doc in docs:
        if doc.get("needs_human"):
            parts.append(f"--- file: {doc['name']} ---\nUNREADABLE. Do not guess any field from this file.")
        else:
            parts.append(f"--- file: {doc['name']} ---\n{doc['text']}")
    packed = "\n\n".join(parts)
    payload = {
        "model": settings["model"],
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": packed[:120000]},
        ],
    }
    try:
        body = _post(settings, payload)
    except RuntimeError as exc:
        if "HTTP 400" not in str(exc):
            raise
        payload.pop("response_format", None)
        body = _post(settings, payload)
    content = body["choices"][0]["message"]["content"]
    parsed = _parse_json(content)
    by_name = {doc["name"]: doc["text"] for doc in docs}
    ocr_confidence = {
        doc["name"]: doc["ocr_confidence"]
        for doc in docs
        if doc.get("ocr_confidence") is not None
    }
    fields = [accept_field(item, by_name, ocr_confidence) for item in parsed.get("fields") or []]
    conflicts = []
    for item in parsed.get("conflicts") or []:
        sides = [
            accept_field({**side, "field_id": item.get("field")}, by_name, ocr_confidence) for side in item.get("values") or []
        ]
        kept = [side for side in sides if side["value"]]
        if len(kept) >= 2 and len({side["value"] for side in kept}) > 1:
            conflicts.append(
                {
                    "field": item.get("field"),
                    "values": [{"value": side["value"], "source": side["source"]} for side in kept],
                    "resolution": "unresolved",
                    "resolved_value": None,
                    "resolved_by": None,
                }
            )
    return {"fields": fields, "conflicts": conflicts}


if __name__ == "__main__":
    docs = {"application.md": "Named insured: Example LLC\nSales or payroll: 10"}
    low = accept_field(
        {
            "field_id": "named_insured",
            "value": "Example LLC",
            "source": "application.md",
            "quote": "Example LLC",
            "confidence": 0.2,
        },
        docs,
    )
    assert low["value"] is None and low["needs_review"] is True
    bad = accept_field(
        {
            "field_id": "named_insured",
            "value": "Invented LLC",
            "source": "application.md",
            "quote": "Invented LLC",
            "confidence": 0.99,
        },
        docs,
    )
    assert bad["value"] is None
    good = accept_field(
        {
            "field_id": "named_insured",
            "value": "Example LLC",
            "source": "application.md",
            "quote": "Named insured: Example LLC",
            "confidence": 0.9,
        },
        docs,
    )
    assert good["value"] == "Example LLC"
    scan = accept_field(
        {
            "field_id": "named_insured",
            "value": "Example LLC",
            "source": "scan.jpg",
            "quote": "Example LLC",
            "confidence": 0.99,
        },
        {"scan.jpg": "Example LLC"},
        {"scan.jpg": 0.2},
    )
    assert scan["value"] is None and scan["model_confidence"] == 0.99
    assert good["model_confidence"] == 0.9
    assert docs["application.md"][good["start"] : good["end"]] == "Named insured: Example LLC"
    os.environ.pop("LLM_BASE_URL", None)
    os.environ.pop("LLM_MODEL", None)
    os.environ.pop("LLM_API_KEY", None)
    settings = endpoint_settings()
    assert settings["base"] == DEFAULT_BASE
    assert settings["model"] == DEFAULT_MODEL
    assert settings["key"] == DEFAULT_KEY
    print("llm gate ok")
