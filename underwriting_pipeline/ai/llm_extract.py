"""LLM extraction. Groq or any OpenAI-compatible host comes from the environment.

    LLM_BASE_URL   required. No default. Ollama runs only when this explicitly names localhost (http://localhost:11434/v1)
    LLM_MODEL      required. No default.
    LLM_API_KEY    required for a remote host; local host uses the dummy "ollama"

P-023 (B-214, D-064). If LLM_BASE_URL or LLM_MODEL is unset the run stops with a clear message before any call and
before any cache read or write. A refusal is a stop, not "no data" and not a failed extraction.

A 429 waits and retries. Do not put a real key in a file in this project.

P-008. Settings come from the shell only; no settings file is read. Every run prints the host and the model first,
and no model is called unless LLM_BASE_URL is the Groq URL below or a localhost (Ollama) URL, or ALLOW_PROVIDER is exactly
the host name in LLM_BASE_URL. A run whose every result comes from the cache makes no model call and is not refused.

# ponytail: one chat call per submission. Batch when a queue is large enough to measure.
"""

import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

MIN_CONFIDENCE = 0.75
MAX_CHARS = 120000  # P-016 L1: text sent to the model in one call
DEFAULT_KEY = "ollama"
MAX_WAIT = float(os.environ.get("LLM_MAX_WAIT") or 60)  # seconds to wait on one 429; a batch scorer sets this higher

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


# P-007. A model result is saved under a key made from the files, the prompt, the OCR settings, and the model.
# P-014 (D-030): the host name and the temperature are in the key too, so a result from another host or temperature is not reused.
# The same key is never called twice. Rules after the model (gates, validation, status, conflicts, carrier match)
# run again on the saved result with no model call. A failed or empty call is never saved.
CACHE = Path(os.environ.get("LLM_CACHE_DIR") or Path(__file__).resolve().parents[1] / "cache")
PROMPT_VERSION = hashlib.sha256(SYSTEM.encode()).hexdigest()[:12]
USAGE: list[dict] = []  # every extraction in this process: tokens, or cached
TEMPERATURE = 0  # the one value sent to the model, and part of the cache key
# P-014 (R2): one id for every row this process writes. LLM_RUN_ID names the run; without it, start time and process id.
RUN = os.environ.get("LLM_RUN_ID") or f"{time.strftime('%Y%m%dT%H%M%S')}-{os.getpid()}"


def _host() -> str:
    """The host name in LLM_BASE_URL: no scheme, port, or path, and never the key (P-014, O1)."""
    try:
        return urllib.parse.urlsplit((os.environ.get("LLM_BASE_URL") or "").rstrip("/")).hostname or ""
    except ValueError:
        return ""


def cache_key(docs: list[dict], model: str) -> str:
    files = [[doc["name"], doc.get("sha256"), doc.get("ocr"), doc.get("needs_human", False), doc["text"]] for doc in docs]
    return hashlib.sha256(json.dumps([PROMPT_VERSION, model, _host(), TEMPERATURE, files]).encode()).hexdigest()


def _log_row(row: dict) -> dict:
    """One row in the token log. P-014: every row starts on a new line and carries the run id and the host name.

    The log is only ever appended to. A line a killed run cut short stays as it is, on its own line.
    """
    row = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "epoch": int(time.time()), "run": _safe(RUN), "host": _host(), **row}
    CACHE.mkdir(parents=True, exist_ok=True)
    with (CACHE / "token_log.jsonl").open("ab+") as log:
        if log.seek(0, os.SEEK_END):
            log.seek(-1, os.SEEK_END)
            if log.read(1) != b"\n":
                log.write(b"\n")
        log.write((json.dumps(row) + "\n").encode())
    return row


def _log_tokens(model: str, names: list[str], usage: dict, attempts: int = 1, key: str | None = None) -> None:
    USAGE.append(
        _log_row(
            {
                "model": model,
                "files": names,
                "key": key,  # P-014: the cache key of the files, not the API key
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
                "attempts": attempts,  # P-012: posts this reply took; 1 means the first attempt
            }
        )
    )


def _log_rows() -> tuple[list[dict], int]:
    """P-014 (U1). The readable rows of the token log, and how many lines were skipped.

    A line that is not JSON (a write cut short), or is JSON with no epoch or model, is skipped and counted. Nothing is repaired.
    """
    rows, skipped = [], 0
    log = CACHE / "token_log.jsonl"
    for line in log.read_text(errors="replace").splitlines() if log.exists() else []:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            row = None
        if isinstance(row, dict) and isinstance(row.get("epoch"), (int, float)) and isinstance(row.get("model"), str):
            rows.append(row)
        else:
            skipped += 1
    return rows, skipped


def run_totals() -> dict:
    """P-014. Each run's totals rebuilt from the token log alone. Rows written before P-014 are under "no run id"."""
    runs: dict[str, dict] = {}
    for row in _log_rows()[0]:
        item = runs.setdefault(row.get("run") or "no run id", {"hosts": [], "model_calls": 0, "from_cache": 0, "tokens": 0, "failed_attempts": dict.fromkeys(FAILURE_KINDS, 0)})
        if row.get("host") and row["host"] not in item["hosts"]:
            item["hosts"].append(row["host"])
        event = row.get("event")
        if not event:
            item["model_calls"] += 1
            item["tokens"] += row.get("total_tokens") or 0
        elif event == "cache_hit":
            item["from_cache"] += 1
        elif event in FAILURE_KINDS:
            item["failed_attempts"][event] += 1
    return runs


def budget() -> dict:
    """Tokens and calls in this run, and tokens per model in the last 24 hours from the log."""
    day: dict[str, dict] = {}
    rows, skipped = _log_rows()
    for row in rows:
        if row["epoch"] >= time.time() - 86400 and not row.get("event"):  # a row with an event is a failed attempt or a cache hit, not a call
            item = day.setdefault(row["model"], {"calls": 0, "tokens": 0})
            item["calls"] += 1
            item["tokens"] += row.get("total_tokens") or 0
    calls = [row for row in USAGE if not row.get("cached")]
    return {
        "run": _safe(RUN),
        "skipped_lines": skipped,  # P-014 (U1): lines in the log that could not be read and are not counted
        "this_run": {
            "model_calls": len(calls),
            "from_cache": len(USAGE) - len(calls),
            "tokens": sum(row["total_tokens"] for row in calls),
            "tokens_per_call": round(sum(row["total_tokens"] for row in calls) / len(calls)) if calls else 0,
        },
        "last_24_hours": day,
    }


def _safe(message: str) -> str:
    key = os.environ.get("LLM_API_KEY", "")
    if key and key != DEFAULT_KEY and key in message:
        message = message.replace(key, "[redacted]")
    return message


def _local(base: str) -> bool:
    try:
        return urllib.parse.urlsplit(base).hostname in ("localhost", "127.0.0.1", "::1")
    except ValueError:
        return False


UNSET = "refused: LLM_BASE_URL and LLM_MODEL must both be set in the shell. There is no default host and no default model. For Ollama set LLM_BASE_URL=http://localhost:11434/v1 on purpose. No model was called."


def endpoint_settings() -> dict:
    base = (os.environ.get("LLM_BASE_URL") or "").rstrip("/")
    model = os.environ.get("LLM_MODEL") or ""
    key = os.environ.get("LLM_API_KEY") or ""
    if not base or not model:  # P-023: no default host and no default model
        raise RuntimeError(UNSET)
    if _local(base):
        return {"base": base, "model": model, "key": key or DEFAULT_KEY}
    if not key:
        raise RuntimeError("LLM_API_KEY is not set. Do not write the key into a file.")
    return {"base": base, "model": model, "key": key}


EXPECTED_BASE = "https://api.groq.com/openai/v1"
_announced: list[str] = []  # the provider line is printed once per process


def provider_guard(calling: bool = True) -> dict:
    """P-008. Print the host and the model, then refuse any host but Groq or localhost unless ALLOW_PROVIDER is exactly that host.

    Localhost is judged by the URL's host name, so a remote URL with "localhost" somewhere in it is still refused.
    ALLOW_PROVIDER is compared with the URL's host name (no scheme, port, or path). Any other value is refused.
    calling=False prints and returns the settings without refusing: it is for the start of a run and for the cache lookup.
    Every model call goes through llm_extract, which calls this again with calling=True just before the call.

    The refusal is SystemExit, not an error a caller turns into "extraction_failed": the run stops.
    """
    base = (os.environ.get("LLM_BASE_URL") or "").rstrip("/")
    model = os.environ.get("LLM_MODEL") or ""
    if not base or not model:  # P-023: stop the run, no call, no cache read or write. SystemExit, so prepare.py does not turn it into a failed extraction.
        raise SystemExit(UNSET)
    allowed = (os.environ.get("ALLOW_PROVIDER") or "").strip()
    line = _safe(f"provider {base} model {model}" + (f" ALLOW_PROVIDER={allowed}" if allowed else ""))
    if line not in _announced:
        _announced.append(line)
        print(line, flush=True)
    try:
        host = urllib.parse.urlsplit(base).hostname
    except ValueError:
        host = None
    refusal = None
    if base != EXPECTED_BASE and host not in ("localhost", "127.0.0.1", "::1") and not (host and allowed == host):
        refusal = _safe(f"refused: LLM_BASE_URL is {base}, not {EXPECTED_BASE} or localhost. To use this host on purpose, set ALLOW_PROVIDER={host or '<host>'}.")
    if refusal and calling:
        raise SystemExit(refusal)
    try:
        return endpoint_settings()
    except RuntimeError:
        if refusal:  # a refused host with no key or model cannot even look in the cache: stop, do not report a failed call
            raise SystemExit(refusal) from None
        raise


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


# P-016 (D-039). Exact citations: no quote match, no value. The value must be inside the quote.
_AMOUNT = re.compile(
    r"(?i)^(?:about|around|approximately|roughly)?\s*"
    r"\$?\s*(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(mm|[kmb])?"
    r"(?:\s*(?:square\s+feet|sq\.?\s*ft\.?|sqft|sf))?\s*$"
)


def amount_value(value: str) -> int | None:
    """220k, $1.2M, $1.2MM (million, P-021), 220,000, and 2,200 sq ft are numbers. A sentence is not. (Moved here from prepare.py for N2; rules unchanged.)"""
    if not value:
        return None
    match = _AMOUNT.match(value.strip())
    if not match:
        return None
    number = float(match.group(1).replace(",", ""))
    suffix = (match.group(2) or "").lower()
    factor = {"": 1, "k": 1_000, "m": 1_000_000, "mm": 1_000_000, "b": 1_000_000_000}[suffix]
    return int(round(number * factor))


NUMBER_FIELDS = ("sales_or_payroll", "tiv_building", "year_built", "square_feet")
DATE_FIELDS = ("effective_date", "loss_run_valued_through")
TEXT_FIELDS = ("named_insured", "premises_address")
SOFT_FIELDS = ("operations", "construction")
_NUM = re.compile(r"(?<![\d.,])\d[\d,]*(?:\.\d+)?(?:\s?(?:mm|[kmb])\b)?", re.I)
_DATE_SHAPE = re.compile(r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}")
_DATES = re.compile(r"\d{4}-\d{2}-\d{2}|\d{1,2}[/.-]\d{1,2}[/.-]\d{4}|[A-Za-z]{3,9}\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}|\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}\.?,?\s+\d{4}")
REASON_QUOTE = "quote not found in {}"
REASON_VALUE = "value not inside the cited text"
REASON_REWORDED = "value is not in the cited text (translated or reworded)"
REASON_SCAN = "number or date read from a scan"


def _squash(text: str) -> str:
    return " ".join(text.casefold().split())


def _quote_numbers(quote: str) -> set[int]:
    """Whole numbers in the quote (N2: amount_value reads 1.2M). H2: a number joined to other digits by - or / is not whole, except inside a date."""
    found = set()
    for match in _NUM.finditer(quote):
        raw = match.group(0).rstrip(",")
        before, after = quote[max(0, match.start() - 2) : match.start()], quote[match.end() : match.end() + 2]
        joined = bool(re.search(r"\d[-/]$", before) or re.match(r"[-/]\d", after))
        if joined and not any(m.start() <= match.start() and match.end() <= m.end() for m in _DATE_SHAPE.finditer(quote)):
            continue
        number = amount_value(raw)
        if number is not None:
            found.add(number)
    return found


def _quote_dates(quote: str) -> set:
    """D2: ISO dates, and dates in a short fixed list of formats. A day-first or month-first date that cannot be told apart is skipped."""
    import datetime

    found = set()
    for match in _DATES.finditer(quote):
        raw = match.group(0)
        try:
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
                found.add(datetime.date.fromisoformat(raw))
            elif re.fullmatch(r"\d{1,2}[/.-]\d{1,2}[/.-]\d{4}", raw):
                one, two, year = (int(x) for x in re.split(r"[/.-]", raw))
                if one > 12 or one == two:
                    found.add(datetime.date(year, two, one))
                elif two > 12:
                    found.add(datetime.date(year, one, two))
                # both could be the month: not stored
            else:
                clean = re.sub(r"(?<=\d)(st|nd|rd|th)", "", raw.replace(",", " ").replace(".", " "))
                for form in ("%B %d %Y", "%b %d %Y", "%d %B %Y", "%d %b %Y"):
                    try:
                        found.add(datetime.datetime.strptime(" ".join(clean.split()), form).date())
                        break
                    except ValueError:
                        continue
        except ValueError:
            continue
    return found


def value_in_span(field_id: str, value: str, span_text: str) -> str | None:
    """P-016 (a). None when the value is inside the cited text. Else the reason it is not.

    A name or address: its characters are in the quote (case and runs of spaces ignored). A number: one whole number in the
    quote equals it. A date: it parses, and the same day is in the quote. Operations and construction that are not in the
    quote come back as REASON_REWORDED: the caller keeps them flagged. Any other field is not checked.
    """
    import datetime

    value = str(value).strip()
    if field_id in TEXT_FIELDS:
        return None if _squash(value) in _squash(span_text) else REASON_VALUE
    if field_id in NUMBER_FIELDS:
        number = amount_value(value)
        return None if number is not None and number in _quote_numbers(span_text) else REASON_VALUE
    if field_id in DATE_FIELDS:
        try:
            day = datetime.date.fromisoformat(value)
        except ValueError:
            return "the date does not parse"
        return None if day in _quote_dates(span_text) else REASON_VALUE
    if field_id in SOFT_FIELDS:
        low = _squash(span_text)
        return None if all(word in low for word in _squash(value).split()) else REASON_REWORDED
    return None


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.casefold())


def cited_ocr_score(quote: str, value: str, words: list) -> float:
    """P-016 (b), option C3. The lowest Tesseract score among the quote's words that hold the value (all the quote's words if none do).

    A cited word that is not in the page's word list counts as 0. A word seen more than once takes its lowest score.
    # ponytail: the word list has no position in the text, so a repeated word takes its lowest score. Add boxes if that costs too many right values.
    """
    scores: dict[str, float] = {}
    for word, score in words:
        for token in _tokens(word):
            scores[token] = min(score, scores.get(token, 1.0))
    held = set(_tokens(value))
    cited = [token for token in _tokens(quote) if token in held] or _tokens(quote)
    return min((scores.get(token, 0.0) for token in cited), default=0.0)


def accept_field(item: dict, docs: dict[str, str], ocr_confidence: dict | None = None, ocr_words: dict | None = None) -> dict:
    """Drop anything that is uncited or below the confidence line. Never keep a guess.

    A scanned source gets the lower of the model score and the OCR score of the cited words (P-016 C3). A typed file keeps the model score.
    A scan with no word list takes the page score, as before. P-016: no quote match, no value; the value must be in the quote.
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
    on_scan = bool(ocr_confidence and source in ocr_confidence)
    cited = None
    if on_scan:
        if ocr_words and ocr_words.get(source):
            cited = cited_ocr_score(quote, str(value or ""), ocr_words[source])
        else:
            cited = ocr_confidence[source]
        confidence = min(model_confidence, cited)
    base = {
        "field_id": field_id,
        "value": None,
        "source": source or None,
        "start": None,
        "end": None,
        "confidence": confidence,
        "model_confidence": model_confidence,
        "ocr_cited_confidence": cited,
        "needs_review": True,
        "reason": None,
        "quote": None,
    }
    if value is None or str(value).strip() == "" or str(value).lower() == "null":
        return base
    if confidence < MIN_CONFIDENCE:
        base["reason"] = f"confidence {confidence:.2f} is under {MIN_CONFIDENCE}"
        return base
    text = docs.get(source, "")
    span = find_quote(text, quote)  # P-016 N: the old fallback to the value's own characters is gone
    if span is None:
        base["confidence"] = 0.0
        base["reason"] = REASON_QUOTE.format(source or "no file")
        return base
    cited_text = text[span[0] : span[1]]
    if field_id == "loss_run_valued_through" and "no known loss" in cited_text.lower():
        return base
    problem = value_in_span(field_id, value, cited_text)
    flag, reason = False, None
    if problem == REASON_REWORDED:
        flag, reason = True, problem
    elif problem:
        base["reason"] = problem
        return base
    if on_scan and field_id in NUMBER_FIELDS + DATE_FIELDS:  # S2
        flag, reason = True, REASON_SCAN
    return {
        "field_id": field_id,
        "value": str(value).strip(),
        "source": source,
        "start": span[0],
        "end": span[1],
        "confidence": confidence,
        "model_confidence": model_confidence,
        "ocr_cited_confidence": cited,
        "needs_review": flag,
        "reason": reason,
        "quote": cited_text,
    }


# D-028: reply_not_usable (the host answered, the reply was empty or not JSON) is a failed attempt and its own cause.
FAILURE_KINDS = ("rate_limit_429", "timeout", "other", "reply_not_usable")
CALL_LOG: list[dict] = []  # every failed attempt in this process: {"kind": one of FAILURE_KINDS, "detail": ...}
_swept: set[Path] = set()  # cache folders whose leftover temp files this process has already removed
_TMP = re.compile(r"[0-9a-f]{64}\.json\.\d+\.tmp")  # the only name the atomic write in llm_extract gives its temp file


def failure_counts() -> dict:
    """Failed attempts in this process by cause. Every cause is shown, so a 0 is a count and not a gap."""
    return {kind: sum(1 for item in CALL_LOG if item["kind"] == kind) for kind in FAILURE_KINDS}


def _sweep_tmp() -> list[str]:
    """D-028. Remove temp files a killed run left in the cache folder in use. A saved result is never removed.

    Only a regular file in CACHE/extractions whose whole name is <key>.json.<process id>.tmp is removed.
    # ponytail: a temp file under a minute old is left for the next run, because another run may be about to rename it.
    """
    removed = []
    for path in (CACHE / "extractions").glob("*.tmp"):
        try:
            if _TMP.fullmatch(path.name) and path.is_file() and not path.is_symlink() and time.time() - path.stat().st_mtime > 60:
                path.unlink()
                removed.append(path.name)
        except OSError:
            pass  # another run removed or renamed it first
    if removed:
        print(f"removed {len(removed)} leftover temp file(s) from {CACHE / 'extractions'}", flush=True)
    return removed
_budget: dict = {}  # token budget from the host's last reply


def _pace(need: int) -> None:
    """Wait until the host's per-minute token budget can take this request.

    # ponytail: reads Groq's x-ratelimit headers; a host without them is not paced, and 429 still waits and retries.
    """
    if not _budget:
        return
    refill = _budget["limit"] / 60
    have = min(_budget["limit"], _budget["remaining"] + (time.time() - _budget["at"]) * refill)
    need = min(need, _budget["limit"])
    if need > have:
        time.sleep((need - have) / refill)


def _note_budget(headers) -> None:
    try:
        _budget.update(
            limit=float(headers["x-ratelimit-limit-tokens"]),
            remaining=float(headers["x-ratelimit-remaining-tokens"]),
            at=time.time(),
        )
    except (KeyError, TypeError, ValueError):
        pass


def _failed(settings: dict, kind: str, detail: str, attempt: int | None = None, retry_in: float | None = None) -> None:
    """P-012. Every failed attempt is one row in the token log, written before the wait, so a run killed while it waits keeps it.

    retry_in is the seconds waited before the next attempt. None means no further attempt was made by _post.
    """
    if kind in FAILURE_KINDS:
        CALL_LOG.append({"kind": kind, "detail": detail})
    _log_row({"model": settings["model"], "files": settings.get("files", []), "key": settings.get("cache_key"), "event": kind, "attempt": attempt, "retry_in": retry_in, "detail": detail, "total_tokens": 0})


def _post(settings: dict, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    for attempt in range(6):
        request = urllib.request.Request(
            settings["base"] + "/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {settings['key']}",
                "Content-Type": "application/json",
                "User-Agent": "curl/8.7.1",
            },
            method="POST",
        )
        _pace(len(data) // 4 + 2000)
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                _note_budget(response.headers)
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            detail = _safe(exc.read().decode(errors="replace")[:300])
            if exc.code == 429:
                limit = "tokens per day" if "(TPD)" in detail else "requests per day" if "(RPD)" in detail else "per minute"
                if attempt < 5:
                    _note_budget(exc.headers or {})
                    try:
                        wait = float(exc.headers.get("Retry-After")) + 1
                    except (AttributeError, TypeError, ValueError):
                        wait = min(60, 2**attempt)
                    # Wait as long as the host asks, up to MAX_WAIT. Retrying sooner only spends another refused call.
                    _failed(settings, "rate_limit_429", f"{limit}: {detail}", attempt + 1, min(wait, MAX_WAIT))
                    time.sleep(min(wait, MAX_WAIT))
                    continue
                _failed(settings, "rate_limit_429", f"{limit}: {detail}", attempt + 1)
                raise RuntimeError(f"model call failed: HTTP 429 rate limit, {limit}") from None
            _failed(settings, "other", f"HTTP {exc.code} {detail}", attempt + 1)
            if exc.code == 401:
                raise RuntimeError("model call failed: HTTP 401 authentication failed.") from None
            raise RuntimeError(f"model call failed: HTTP {exc.code} {detail}") from None
        except (TimeoutError, urllib.error.URLError) as exc:
            timed_out = isinstance(exc, TimeoutError) or isinstance(getattr(exc, "reason", None), TimeoutError)
            _failed(settings, "timeout" if timed_out else "other", _safe(str(exc))[:300], attempt + 1, min(60, 2**attempt) if attempt < 5 else None)
            if attempt < 5:
                time.sleep(min(60, 2**attempt))
                continue
            raise RuntimeError(f"model call failed: {'timeout' if timed_out else _safe(str(exc))[:300]}") from None
    raise RuntimeError("model call failed: HTTP 429 rate limit")


def llm_extract(docs: list[dict]) -> dict:
    settings = provider_guard(calling=False)  # refused only below, when the cache has no result and a model call is next
    docs = [doc for doc in docs if not doc.get("unread")]  # P-016 (c): a file type that is not read, or a file that cannot be opened, never reaches the model or the key
    parts, not_sent, size = [], [], 0
    for doc in docs:
        if doc.get("needs_human"):
            part = f"--- file: {doc['name']} ---\nUNREADABLE. Do not guess any field from this file."
        else:
            part = f"--- file: {doc['name']} ---\n{doc['text']}"
        if size + len(part) + (2 if parts else 0) > MAX_CHARS:  # P-016 L1: files go whole, in order; one that does not fit is listed, never cut
            not_sent.append(doc["name"])
            continue
        size += len(part) + (2 if parts else 0)
        parts.append(part)
    packed = "\n\n".join(parts)
    payload = {
        "model": settings["model"],
        "temperature": TEMPERATURE,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": packed},
        ],
    }
    names = [doc["name"] for doc in docs]
    if CACHE not in _swept:  # D-028: once per run and per cache folder, before the first read or write
        _swept.add(CACHE)
        _sweep_tmp()
    key = cache_key(docs, settings["model"])
    settings = {**settings, "files": names, "cache_key": key}  # so every log row names its files and its cache key
    saved = CACHE / "extractions" / f"{key}.json"
    parsed = None
    if saved.exists():
        try:
            parsed = json.loads(saved.read_text())["parsed"]
        except (OSError, ValueError, KeyError, TypeError):
            pass
        if not isinstance(parsed, dict):  # P-013: a half-written or unreadable saved file is not a saved result; call again
            parsed = None
            _failed(settings, "cache_unreadable", saved.name)
    if parsed is not None:
        try:  # P-014 (H1): a result served from the cache is one row, with an event, so it is never counted as a call
            _log_row({"model": settings["model"], "files": names, "key": key, "event": "cache_hit", "total_tokens": 0})
        except OSError as exc:  # P-014 (L1): the log is complete or the run does not go on. Not a failed extraction.
            raise SystemExit(_safe(f"stopped: the token log in {CACHE} could not be written ({type(exc).__name__}: {exc}). The saved result was not used.")) from None
        USAGE.append({"model": settings["model"], "files": names, "cached": True, "total_tokens": 0})
    else:
        provider_guard()
        before = len(CALL_LOG)
        try:
            body = _post(settings, payload)
        except RuntimeError as exc:
            if "HTTP 400" not in str(exc):
                raise
            payload.pop("response_format", None)
            _failed(settings, "retry", "HTTP 400: sent again without response_format")
            body = _post(settings, payload)
        _log_tokens(settings["model"], names, body.get("usage") or {}, len(CALL_LOG) - before + 1, key)
        try:
            parsed = _parse_json(body["choices"][0]["message"]["content"])
            if not parsed.get("conflicts") and not any(item.get("value") for item in parsed.get("fields") or []):
                raise RuntimeError("model call returned no fields")
        except Exception as exc:  # P-012: the host answered but the reply is not usable; log it, then fail exactly as before
            _failed(settings, "reply_not_usable", _safe(f"{type(exc).__name__}: {exc}")[:300])
            raise
        saved.parent.mkdir(parents=True, exist_ok=True)
        # P-013: write beside the result, then rename, so a run killed during the write leaves no half-written result.
        part = saved.with_name(f"{saved.name}.{os.getpid()}.tmp")
        part.write_text(
            json.dumps({"model": settings["model"], "prompt_version": PROMPT_VERSION, "files": names, "usage": body.get("usage"), "parsed": parsed}, indent=2)
            + "\n"
        )
        os.replace(part, saved)
    by_name = {doc["name"]: doc["text"] for doc in docs}
    ocr_confidence = {
        doc["name"]: doc["ocr_confidence"]
        for doc in docs
        if doc.get("ocr_confidence") is not None
    }
    ocr_words = {doc["name"]: doc["ocr_words"] for doc in docs if doc.get("ocr_words")}
    fields = [accept_field(item, by_name, ocr_confidence, ocr_words) for item in parsed.get("fields") or []]
    conflicts = []
    for item in parsed.get("conflicts") or []:
        sides = [
            accept_field({**side, "field_id": item.get("field")}, by_name, ocr_confidence, ocr_words) for side in item.get("values") or []
        ]
        kept = [side for side in sides if side["value"]]
        if len(kept) >= 2 and len({side["value"] for side in kept}) > 1:
            conflicts.append(
                {
                    "field": item.get("field"),
                    "values": [  # P-024: each side keeps its flag, reason and quote so an agreeing merge cannot lose them
                        {k: side.get(k) for k in ("value", "source", "start", "end", "quote", "needs_review", "reason", "confidence")}
                        for side in kept
                    ],
                    "resolution": "unresolved",
                    "resolved_value": None,
                    "resolved_by": None,
                }
            )
    return {"fields": fields, "conflicts": conflicts, "not_sent": not_sent}


if __name__ == "__main__":
    LOCAL_BASE, LOCAL_MODEL = "http://localhost:11434/v1", "qwen2.5:7b"  # the self-check names localhost on purpose (P-023); the module has no default
    os.environ["LLM_BASE_URL"], os.environ["LLM_MODEL"] = LOCAL_BASE, LOCAL_MODEL
    _budget.update(limit=6000.0, remaining=6000.0, at=time.time())
    began = time.time()
    _pace(3000)
    assert time.time() - began < 0.5, "a request inside the budget must not wait"
    _budget.clear()
    if sys.argv[1:] == ["--budget"]:
        print(json.dumps({**budget(), "runs": run_totals()}, indent=2))  # P-014: each run's totals, from the file only
        raise SystemExit(0)
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        CACHE, real_post, posts = Path(tmp), _post, []
        page = [{"name": "a.md", "text": "Named insured: Example LLC", "sha256": "x"}]
        reply = {"fields": [{"field_id": "named_insured", "value": "Example LLC", "source": "a.md", "quote": "Example LLC", "confidence": 0.9}]}

        def _post(settings, payload):  # noqa: F811
            posts.append(1)
            return {"choices": [{"message": {"content": json.dumps(reply)}}], "usage": {"total_tokens": 50}}

        first = llm_extract(page)
        assert llm_extract(page) == first and len(posts) == 1, "the same files must not call the model twice"
        assert budget()["this_run"] == {"model_calls": 1, "from_cache": 1, "tokens": 50, "tokens_per_call": 50}
        llm_extract([{**page[0], "sha256": "y"}])
        assert len(posts) == 2, "a changed file is a new key"
        reply = {"fields": []}
        empty = [{"name": "b.md", "text": "nothing here", "sha256": "z"}]
        for _ in range(2):
            try:
                llm_extract(empty)
                raise SystemExit("an empty reply should fail")
            except RuntimeError:
                pass
        assert len(posts) == 4, "a failed call is never cached and is called again"
        # P-013. A half-written saved file, and one with no result in it, are not trusted: the model is called again.
        reply = {"fields": [{"field_id": "named_insured", "value": "Example LLC", "source": "a.md", "quote": "Example LLC", "confidence": 0.9}]}
        whole = CACHE / "extractions" / f"{cache_key(page, provider_guard(calling=False)['model'])}.json"
        good_bytes = whole.read_bytes()
        for planted in (good_bytes[: len(good_bytes) // 2], b"", b'{"model": "m"}', b'{"parsed": null}', b"\xff\xfe"):
            whole.write_bytes(planted)
            before = len(posts)
            assert llm_extract(page) == first, "a half-written saved file was trusted"
            assert len(posts) == before + 1, "an unreadable saved file must be called again, not trusted"
            assert json.loads(whole.read_text())["parsed"] == reply, "the new result replaces the unreadable file"
        before = len(posts)
        assert llm_extract(page) == first and len(posts) == before, "the repaired result is reused with no call"
        assert [path.name for path in whole.parent.iterdir() if path.suffix != ".json"] == [], "no temp file is left behind"
        assert sum(1 for line in (CACHE / "token_log.jsonl").read_text().splitlines() if json.loads(line).get("event") == "cache_unreadable") == 5
        real_replace, os.replace = os.replace, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt())  # the run is killed before the rename
        try:
            llm_extract([{**page[0], "sha256": "killed"}])
            raise SystemExit("the stubbed kill did not happen")
        except KeyboardInterrupt:
            pass
        finally:
            os.replace = real_replace
        assert len(list(whole.parent.glob("*.json"))) == 2, "a write that was killed must not leave a result under the key"
        # D-028. The next run removes the temp file the killed write left, and nothing else.
        left = [path for path in whole.parent.iterdir() if path.suffix == ".tmp"]
        assert len(left) == 1 and _TMP.fullmatch(left[0].name), "the killed write leaves exactly one temp file, with the name the cleanup knows"
        old = time.time() - 3600
        key = "a" * 64
        fresh = whole.parent / f"{key}.json.1.tmp"  # under a minute old: another run may be writing it
        keep = [
            fresh,
            whole.parent / "notes.tmp",  # not our name
            whole.parent / f"{key}.json.tmp",  # no process id
            whole.parent / f"{key}.json.2.tmp.json",  # ends like a saved result
            whole.parent / f"x{key}.json.2.tmp",  # a longer name that only ends like ours
            CACHE / f"{key}.json.2.tmp",  # our name, but not in the extractions folder
        ]
        for path in keep:
            path.write_text("keep")
            os.utime(path, (old, old))
        os.utime(fresh)
        folder = whole.parent / f"{'b' * 64}.json.3.tmp"  # our name, but a folder
        folder.mkdir()
        os.utime(folder, (old, old))
        os.utime(left[0], (old, old))
        with tempfile.TemporaryDirectory() as other:  # a cache folder that is not the one in use
            outside = Path(other) / "extractions" / f"{key}.json.2.tmp"
            outside.parent.mkdir()
            outside.write_text("keep")
            os.utime(outside, (old, old))
            results = {path.name: path.read_bytes() for path in whole.parent.glob("*.json")}
            def not_hits() -> list[str]:  # P-014: a cache hit is now a row, so compare every other row
                return [line for line in (CACHE / "token_log.jsonl").read_text().splitlines() if json.loads(line).get("event") != "cache_hit"]

            log_before = not_hits()
            before = len(posts)
            assert llm_extract(page) == first and len(posts) == before, "a run already started in this folder does not sweep again"
            assert left[0].exists(), "the cleanup runs at the start of a run, not on every file"
            _swept.clear()  # a new run starts
            assert llm_extract(page) == first and len(posts) == before, "the cleanup must not cost a model call"
            assert not left[0].exists(), "a temp file left by a killed run is removed at the start of the next run"
            assert all(path.read_text() == "keep" for path in keep) and folder.is_dir() and outside.read_text() == "keep", "only our own old temp files, only in the cache folder in use"
            assert {path.name: path.read_bytes() for path in whole.parent.glob("*.json")} == results, "a saved result is never removed or changed"
            assert not_hits() == log_before, "the cleanup does not touch the token log"
            os.utime(fresh, (old, old))
            _swept.clear()
            assert _sweep_tmp() == [fresh.name] and not fresh.exists(), "once it is old, the next run removes it"
        _post = real_post
        USAGE.clear()

    # P-012. A stubbed host: every 429, every other failed attempt, and every retry must be a row in the token log.
    # The log is a temporary file. No model is called and the real token log is not touched.
    import email.message
    import io

    real_log = Path(__file__).resolve().parents[1] / "cache" / "token_log.jsonl"
    real_before = real_log.read_bytes() if real_log.exists() else None
    real_cache = sorted((path.name, path.stat().st_size) for path in real_log.parent.rglob("*") if path != real_log)
    CALL_LOG.clear()
    assert failure_counts() == {"rate_limit_429": 0, "timeout": 0, "other": 0, "reply_not_usable": 0}, "every cause is shown, also at 0"
    real_open, real_sleep, waits = urllib.request.urlopen, time.sleep, []
    answer = json.dumps({"choices": [{"message": {"content": json.dumps(reply)}}], "usage": {"total_tokens": 50}})  # reply is the good reply again

    class _Reply(io.BytesIO):
        headers = {}

    def http(code: int, text: str, retry_after: str | None = None):
        headers = email.message.Message()
        if retry_after is not None:
            headers["Retry-After"] = retry_after
        return urllib.error.HTTPError("http://stub.test", code, "stub", headers, io.BytesIO(text.encode()))

    def host(*script):
        """The stubbed host answers each post with the next item: an exception to raise, or a reply body."""
        queue = list(script)

        def urlopen(request, timeout=None):
            assert request.full_url.startswith(LOCAL_BASE), "the stub only stands in for localhost"
            item = queue.pop(0)
            if isinstance(item, Exception):
                raise item
            return _Reply(item.encode())

        urllib.request.urlopen = urlopen
        return queue

    def rows() -> list[dict]:
        log = CACHE / "token_log.jsonl"
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    time.sleep = waits.append
    for name in ("LLM_API_KEY", "ALLOW_PROVIDER"):
        os.environ.pop(name, None)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            CACHE = Path(tmp)
            left = host(http(429, "Rate limit reached (TPD)", "12"), TimeoutError("timed out"), answer)
            assert llm_extract(page)["fields"][0]["value"] == "Example LLC" and not left
            log = rows()
            assert [row.get("event") for row in log] == ["rate_limit_429", "timeout", None], f"a 429 or a retry is missing from the token log: {log}"
            assert log[0]["attempt"] == 1 and log[0]["retry_in"] == 13 and "tokens per day" in log[0]["detail"] and log[0]["files"] == ["a.md"]
            assert log[1]["attempt"] == 2 and log[1]["retry_in"] == 2 and waits == [13.0, 2], "each wait before a retry is saved, and saved before the wait"
            assert log[2]["attempts"] == 3 and log[2]["total_tokens"] == 50, "the reply's row says how many posts it took"
            assert budget()["last_24_hours"][LOCAL_MODEL] == {"calls": 1, "tokens": 50}, "a failed attempt is not counted as a call"
            assert failure_counts() == {"rate_limit_429": 1, "timeout": 1, "other": 0, "reply_not_usable": 0}

        with tempfile.TemporaryDirectory() as tmp:
            CACHE = Path(tmp)
            host(*[http(429, "Rate limit reached (TPM)") for _ in range(6)])
            try:
                llm_extract(page)
                raise SystemExit("six 429s should fail")
            except RuntimeError:
                pass
            log = rows()
            assert [(row["event"], row["attempt"]) for row in log] == [("rate_limit_429", n) for n in range(1, 7)], "every 429 is a row, not only the last"
            assert log[5]["retry_in"] is None and all(row["retry_in"] for row in log[:5]) and not (CACHE / "extractions").exists()

        with tempfile.TemporaryDirectory() as tmp:
            CACHE = Path(tmp)
            host(http(400, "response_format is not supported"), answer, http(500, "boom"), json.dumps({"choices": [{"message": {"content": "{}"}}]}))
            llm_extract(page)
            assert [row.get("event") for row in rows()] == ["other", "retry", None], "the second post after an HTTP 400 is a retry and is saved"
            for _ in range(2):  # an HTTP 500, then an empty reply: both fail, both are saved
                try:
                    llm_extract(empty)
                    raise SystemExit("this call should fail")
                except RuntimeError:
                    pass
            assert [row.get("event") for row in rows()][3:] == ["other", None, "reply_not_usable"], "a failed call that a later run retries is saved"
            assert all("total_tokens" in row and "epoch" in row and "model" in row for row in rows())
            # D-028. The totals by cause count reply_not_usable, as its own cause, and match the rows in the token log.
            CALL_LOG.clear()
            for content in ("not json", "{}"):  # a reply that is not JSON, then an empty reply
                host(json.dumps({"choices": [{"message": {"content": content}}], "usage": {"total_tokens": 7}}))
                try:
                    llm_extract(empty)
                    raise SystemExit("an unusable reply should fail")
                except (RuntimeError, ValueError):
                    pass
            host(http(500, "boom"))
            try:
                llm_extract(empty)
                raise SystemExit("an HTTP 500 should fail")
            except RuntimeError:
                pass
            assert failure_counts() == {"rate_limit_429": 0, "timeout": 0, "other": 1, "reply_not_usable": 2}, f"reply_not_usable is missing from the failure totals: {failure_counts()}"
            logged = [row["event"] for row in rows()[-5:] if row.get("event")]
            assert logged == ["reply_not_usable", "reply_not_usable", "other"] and sum(failure_counts().values()) == len(logged), "the totals match the token log"
            assert not (CACHE / "extractions" / f"{cache_key(empty, LOCAL_MODEL)}.json").exists(), "an unusable reply is still never saved"
            assert rows()[-5]["attempts"] == 1 and rows()[-3]["attempts"] == 1, "counting the cause does not change a later call's attempt count"

        # P-014. The token log survives a cut line, and a run's totals can be rebuilt from the file alone.
        unusable = json.dumps({"choices": [{"message": {"content": "not json"}}], "usage": {"total_tokens": 7}})
        fake_key = "TEST_NOT_A_REAL_KEY"
        with tempfile.TemporaryDirectory() as tmp:
            CACHE = Path(tmp)
            CALL_LOG.clear()
            USAGE.clear()
            old_row = json.dumps({"at": "x", "epoch": int(time.time()), "model": LOCAL_MODEL, "files": ["old.md"], "total_tokens": 11, "attempts": 1})
            cut = b'{"at": "2026-10-11T00:00:00", "epoch": 17'  # a run killed during the write: no end, no line break
            (CACHE / "token_log.jsonl").write_bytes(old_row.encode() + b"\n" + cut)
            assert budget()["skipped_lines"] == 1 and budget()["last_24_hours"][LOCAL_MODEL] == {"calls": 1, "tokens": 11}, "a cut last line must be skipped and counted, not stop the report"
            os.environ["LLM_API_KEY"] = fake_key
            RUN = "run-a"
            host(http(429, "Rate limit reached (TPM)", "1"), answer)
            llm_extract(page)  # one 429, then one call
            raw = (CACHE / "token_log.jsonl").read_bytes()
            assert raw.startswith(old_row.encode() + b"\n" + cut + b"\n"), "the cut line stays as it was, on its own line"
            assert raw.split(b"\n")[1] == cut and len(rows_ok := _log_rows()[0]) == 3 and _log_rows()[1] == 1, "the row after a cut line must be whole and readable"
            with (CACHE / "token_log.jsonl").open("a") as log:  # JSON, but not a row
                log.write('{"model": "m", "total_tokens": 5}\n[1]\n{"epoch": 1}\n\xff\n')
            assert budget()["skipped_lines"] == 5, "a line with no epoch or no model is skipped, not a crash"
            llm_extract(page)  # one cache hit
            host(unusable)
            try:
                llm_extract(empty)  # one call whose reply is not usable
                raise SystemExit("an unusable reply should fail")
            except (RuntimeError, ValueError):
                pass
            memory = budget()["this_run"]
            assert memory == {"model_calls": 2, "from_cache": 1, "tokens": 57, "tokens_per_call": 28}
            rebuilt = run_totals()
            assert rebuilt["run-a"] == {"hosts": ["localhost"], "model_calls": memory["model_calls"], "from_cache": memory["from_cache"], "tokens": memory["tokens"], "failed_attempts": failure_counts()}, f"the totals rebuilt from the file differ from the run's own: {rebuilt}"
            assert failure_counts() == {"rate_limit_429": 1, "timeout": 0, "other": 0, "reply_not_usable": 1}
            assert rebuilt["no run id"]["model_calls"] == 1 and rebuilt["no run id"]["tokens"] == 11, "a row written before P-014 is read, under 'no run id'"
            assert budget()["last_24_hours"][LOCAL_MODEL] == {"calls": 3, "tokens": 68}, "a cache hit is not counted as a call"
            RUN = "run-b"  # a second run into the same log
            USAGE.clear()
            CALL_LOG.clear()
            llm_extract(page)
            rebuilt_b = run_totals()
            assert rebuilt_b["run-a"] == rebuilt["run-a"], "a later run must not change an earlier run's totals"
            assert rebuilt_b["run-b"] == {"hosts": ["localhost"], "model_calls": 0, "from_cache": 1, "tokens": 0, "failed_attempts": dict.fromkeys(FAILURE_KINDS, 0)}
            new = [row for row in _log_rows()[0] if row.get("run")]
            assert [row["run"] for row in new] == ["run-a"] * 5 + ["run-b"] and len(new) == len(_log_rows()[0]) - 1, "every new row carries its own run id"
            assert all(row["host"] == "localhost" and re.fullmatch(r"[0-9a-f]{64}", row["key"] or "") for row in new), "every new row carries the host name and the cache key"
            assert {row["key"] for row in new} == {cache_key(page, LOCAL_MODEL), cache_key(empty, LOCAL_MODEL)}
            assert [row.get("event") for row in new] == ["rate_limit_429", None, "cache_hit", None, "reply_not_usable", "cache_hit"]
            assert fake_key not in (CACHE / "token_log.jsonl").read_text(errors="replace") and "Bearer" not in (CACHE / "token_log.jsonl").read_text(errors="replace"), "no row holds the API key"
            RUN = f"named-{fake_key}"  # a run id that someone set to the key by mistake is not written either
            llm_extract(page)
            assert fake_key not in (CACHE / "token_log.jsonl").read_text(errors="replace") and fake_key not in json.dumps(budget())
            os.environ.pop("LLM_API_KEY")
            RUN = "run-c"

            # D-030. The host name and the temperature are in the cache key.
            here = cache_key(page, LOCAL_MODEL)
            old_files = [[doc["name"], doc.get("sha256"), doc.get("ocr"), doc.get("needs_human", False), doc["text"]] for doc in page]
            assert here != hashlib.sha256(json.dumps([PROMPT_VERSION, LOCAL_MODEL, old_files]).encode()).hexdigest(), "the key from before P-014 must not reach a new result"
            os.environ["LLM_BASE_URL"] = "http://127.0.0.1:11434/v1"
            assert cache_key(page, LOCAL_MODEL) != here, "another host is another key"
            os.environ["LLM_BASE_URL"] = "http://localhost:9999/other/path"
            assert cache_key(page, LOCAL_MODEL) == here, "the key holds the host name only: no port, no path"
            os.environ["LLM_BASE_URL"] = LOCAL_BASE
            TEMPERATURE = 1
            assert cache_key(page, LOCAL_MODEL) != here, "another temperature is another key"
            left = host(answer)
            llm_extract(page)
            assert not left and _log_rows()[0][-1].get("event") is None, "a result saved at another temperature is not reused: the model is called"
            TEMPERATURE = 0
            before = len(_log_rows()[0])
            llm_extract(page)
            assert _log_rows()[0][-1]["event"] == "cache_hit" and len(_log_rows()[0]) == before + 1, "back at the first temperature, the first result is reused"

            # L1. A cache-hit row that cannot be written stops the run. It is not a failed extraction and the saved result is not used.
            real_row, used = _log_row, len(USAGE)

            def _log_row(row):  # noqa: F811
                raise PermissionError("stub: the log cannot be written")

            try:
                llm_extract(page)
                raise AssertionError("a cache hit that cannot be logged must stop the run")
            except SystemExit as stop:
                assert "token log" in str(stop) and not isinstance(stop, Exception), "the stop must not be an error that prepare.py turns into extraction_failed"
            finally:
                _log_row = real_row
            assert len(USAGE) == used, "a cache hit that was not logged is not counted"

        # R2. The run id is LLM_RUN_ID when set; without it, the start time and the process id.
        import subprocess

        for env_id, shape in (("T-066-run-2", "T-066-run-2"), ("", r"\d{8}T\d{6}-\d+")):
            said = subprocess.run(
                [sys.executable, "-c", "import llm_extract; print(llm_extract.RUN)"],
                cwd=Path(__file__).resolve().parent, env={**os.environ, "LLM_RUN_ID": env_id, "LLM_CACHE_DIR": tempfile.gettempdir()}, capture_output=True, text=True,
            ).stdout.strip()
            assert re.fullmatch(shape, said), f"run id {said!r} for LLM_RUN_ID={env_id!r}"
    finally:
        urllib.request.urlopen, time.sleep = real_open, real_sleep
        CALL_LOG.clear()
        USAGE.clear()
    assert (real_log.read_bytes() if real_log.exists() else None) == real_before, "the self-check must not write the real token log"
    assert sorted((path.name, path.stat().st_size) for path in real_log.parent.rglob("*") if path != real_log) == real_cache, "the self-check must not add or remove a file in the real cache"
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
    os.environ.pop("LLM_API_KEY", None)
    settings = endpoint_settings()
    assert settings["base"] == LOCAL_BASE and settings["model"] == LOCAL_MODEL and settings["key"] == DEFAULT_KEY, "an explicit localhost still works (Ollama)"

    # P-008. The provider guard. No model is called here: a post would fail the check.
    import contextlib
    import io

    def _post(settings, payload):  # noqa: F811
        raise AssertionError("the guard let a call through")

    def guard(run=provider_guard, **env) -> tuple[bool, str]:
        """Set only these variables, run, and return (refused, everything printed or said)."""
        for name in ("LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY", "ALLOW_PROVIDER"):
            os.environ.pop(name, None)
        os.environ.update(env)
        _announced.clear()
        said = io.StringIO()
        try:
            with contextlib.redirect_stdout(said):
                run()
        except SystemExit as stop:
            return True, said.getvalue() + str(stop)
        return False, said.getvalue()

    paid = {"LLM_BASE_URL": "https://api.openai.com/v1", "LLM_MODEL": "gpt-x", "LLM_API_KEY": "TEST_NOT_A_REAL_KEY"}
    refused, said = guard(LLM_BASE_URL=LOCAL_BASE, LLM_MODEL=LOCAL_MODEL)
    assert not refused and f"provider {LOCAL_BASE} model {LOCAL_MODEL}" in said, "localhost (Ollama) is allowed when named"
    assert not guard(LLM_BASE_URL="http://127.0.0.1:11434/v1", LLM_MODEL=LOCAL_MODEL)[0]
    # P-023 (B-214). Unset settings: refused, no HTTP attempt, no cache write, and not a failed extraction.
    attempts = []

    def _post(settings, payload):  # noqa: F811
        attempts.append(1)
        raise AssertionError("an unset setting reached the model")

    real_open = urllib.request.urlopen
    urllib.request.urlopen = lambda *a, **k: attempts.append(1)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            CACHE = Path(tmp)
            for env in ({}, {"LLM_BASE_URL": LOCAL_BASE}, {"LLM_MODEL": LOCAL_MODEL}, {"LLM_BASE_URL": EXPECTED_BASE, "LLM_API_KEY": "k9k9k9"}, {"LLM_MODEL": "m", "LLM_API_KEY": "k9k9k9"}):
                for run in (provider_guard, lambda: provider_guard(calling=False), lambda: llm_extract(page)):
                    refused, said = guard(run, **env)
                    assert refused and "LLM_BASE_URL and LLM_MODEL must both be set" in said and "no default" in said.lower(), f"unset settings must be refused with a clear message: {env}"
            assert not attempts, "an unset setting made an HTTP attempt"
            assert list(CACHE.rglob("*")) == [], "an unset setting wrote to the cache or the token log"
            try:
                guard(endpoint_settings)
                os.environ.pop("LLM_BASE_URL", None)
                endpoint_settings()
                raise AssertionError("endpoint_settings must refuse an unset host")
            except RuntimeError:
                pass
        assert USAGE == [] and failure_counts() == dict.fromkeys(FAILURE_KINDS, 0), "a refusal is not a call and not a failed attempt"
    finally:
        urllib.request.urlopen = real_open
    assert not _local("https://example.test/localhost/v1") and _local("http://localhost:11434/v1"), "Ollama only when the host name is localhost"
    for remote in ("https://localhost.example.test/v1", "https://example.test/localhost/v1", "https://example.test/v1?h=127.0.0.1"):
        assert guard(LLM_BASE_URL=remote, LLM_MODEL="m", LLM_API_KEY="k9k9k9")[0], f"{remote} is not this machine"
    refused, said = guard(**paid)
    assert refused and "https://api.openai.com/v1" in said and "gpt-x" in said, "another host must be refused and named"
    assert "TEST_NOT_A_REAL_KEY" not in said, "the key is never printed"
    assert guard(LLM_BASE_URL="https://api.groq.com.example.test/openai/v1", LLM_MODEL="m", LLM_API_KEY="k9k9k9")[0], "a look-alike host"
    assert guard(lambda: llm_extract(page), **paid)[0], "an extraction with no saved result must stop before the model"
    refused, said = guard(LLM_BASE_URL=EXPECTED_BASE + "/", LLM_MODEL="openai/gpt-oss-120b", LLM_API_KEY="gsk-not-a-real-key")
    assert not refused and f"provider {EXPECTED_BASE} model openai/gpt-oss-120b" in said and "gsk-not-a-real-key" not in said
    refused, said = guard(**paid, ALLOW_PROVIDER="api.openai.com")
    assert not refused and "ALLOW_PROVIDER=api.openai.com" in said, "the user can allow another host by its exact host name"
    for wrong in ("openai", "1", "api.groq.com", "openai.com", "https://api.openai.com/v1"):
        refused, said = guard(**paid, ALLOW_PROVIDER=wrong)
        assert refused and "TEST_NOT_A_REAL_KEY" not in said, f"ALLOW_PROVIDER={wrong} is not the host and must be refused"
    refused, said = guard(lambda: provider_guard(calling=False), **paid)
    assert not refused and "provider https://api.openai.com/v1 model gpt-x" in said, "the start of a run prints the host and does not refuse yet"
    assert guard(lambda: provider_guard(calling=False), LLM_BASE_URL="https://api.openai.com/v1")[0], "a refused host with no key or model stops"
    with tempfile.TemporaryDirectory() as tmp:
        CACHE = Path(tmp)

        def _post(settings, payload):  # noqa: F811
            return {"choices": [{"message": {"content": json.dumps({"fields": [{"field_id": "named_insured", "value": "Example LLC", "source": "a.md", "quote": "Example LLC", "confidence": 0.9}]})}}], "usage": {"total_tokens": 50}}

        assert not guard(lambda: llm_extract(page), **paid, ALLOW_PROVIDER="api.openai.com")[0], "the exact host lets the call through"

        def _post(settings, payload):  # noqa: F811
            raise AssertionError("the guard let a call through")

        USAGE.clear()
        refused, said = guard(lambda: llm_extract(page), **paid)
        assert not refused and "provider https://api.openai.com/v1 model gpt-x" in said, "a saved result on a refused host is used, and the host is still printed"
        assert budget()["this_run"]["model_calls"] == 0 and budget()["this_run"]["from_cache"] == 1, "the cache-only run made no model call"
        assert guard(lambda: llm_extract(empty), **paid)[0], "the next file has no saved result: the run stops before the call"
        assert guard(lambda: llm_extract(empty), **paid, ALLOW_PROVIDER="openai")[0], "a wrong ALLOW_PROVIDER does not let the call through"
        assert budget()["this_run"]["model_calls"] == 0
        USAGE.clear()
    # P-016. Each lettered option, no model call.
    def one(field, value, quote, text, conf=0.9, scan=None, words=None):
        return accept_field({"field_id": field, "value": value, "source": "f", "quote": quote, "confidence": conf}, {"f": text}, {"f": scan} if scan is not None else None, {"f": words} if words else None)

    # N (no value fallback): the quote is not in the file, so no value, even if the value's characters are there.
    for field, value, text in (("year_built", "1990", "Phone 210-555-1990"), ("tiv_building", "850000", "Policy no. 8500001"), ("construction", "Masonry", "Prior carrier: Masonry Mutual")):
        row = one(field, value, "an invented quote", text)
        assert row["value"] is None and row["reason"] == "quote not found in f" and row["needs_review"], field
    # N2: the value is read from the quote by amount_value ($1.2M, 220k). Digits that sit inside a longer number are not the number.
    assert one("tiv_building", "1200000", "TIV $1.2M", "TIV $1.2M")["value"] == "1200000"
    assert one("tiv_building", "220000", "TIV 220k", "TIV 220k")["value"] == "220000"
    assert one("sales_or_payroll", "10", "Sales: 2010000", "Sales: 2010000")["reason"] == REASON_VALUE, "10 is not inside 2010000"
    assert one("year_built", "2021", "Year built: 1948", "Year built: 1948")["reason"] == REASON_VALUE
    assert one("tiv_building", "850000", "Policy no. 8500001", "Policy no. 8500001")["value"] is None
    assert one("tiv_building", "850000", "TIV: 850,000", "TIV: 850,000")["quote"] == "TIV: 850,000"
    # H2: a number joined to other digits by - or / is not whole. A date keeps its numbers.
    assert one("year_built", "1990", "210-555-1990", "Call 210-555-1990")["reason"] == REASON_VALUE
    assert one("year_built", "1990", "Year built: 1990", "Year built: 1990")["value"] == "1990"
    assert one("year_built", "1990", "Built 1990-1991", "Built 1990-1991")["value"] is None
    # D2: ISO, or a fixed list of formats that parse to the same day. A date that does not parse, or cannot be told apart, is not stored.
    for day, written in (("2026-11-01", "2026-11-01"), ("2026-11-01", "November 1, 2026"), ("2026-11-01", "1 Nov 2026"), ("2026-11-13", "11/13/2026"), ("2026-11-13", "13/11/2026")):
        assert one("effective_date", day, f"Effective: {written}", f"Effective: {written}")["value"] == day, written
    for bad_date in ("2O2H-01-O1", "RO2F-O1-01", "A2F-O1-O1", "2026-13-45"):
        row = one("effective_date", bad_date, f"Effective: {bad_date}", f"Effective: {bad_date}")
        assert row["value"] is None and row["reason"] == "the date does not parse", bad_date
    assert one("effective_date", "2026-01-02", "Effective: 01/02/2026", "Effective: 01/02/2026")["value"] is None, "day-first and month-first cannot be told apart"
    assert one("loss_run_valued_through", "2026-01-05", "Valued through: 2026-01-06", "Valued through: 2026-01-06")["value"] is None, "the value must be the date in the quote"
    # Names and addresses: the value is in the quote, case and runs of spaces ignored.
    assert one("named_insured", "ACME  llc", "Named insured: Acme LLC", "Named insured: Acme LLC")["value"] == "ACME  llc"
    assert one("named_insured", "Other LLC", "Named insured: Acme LLC", "Named insured: Acme LLC")["reason"] == REASON_VALUE
    # Translated or reworded operations and construction are kept and flagged (R1: flag only, the value still counts).
    row = one("construction", "masonry", "Construccion: mamposteria", "Construccion: mamposteria")
    assert row["value"] == "masonry" and row["needs_review"] and row["reason"] == REASON_REWORDED
    assert not one("operations", "taqueria", "Operaciones: taqueria", "Operaciones: taqueria")["needs_review"]
    # Q1: the exact cited text is on the row, and it is the text between start and end.
    row = one("named_insured", "Acme LLC", "Named   insured:\nAcme LLC", "Named insured:\n Acme LLC")
    assert row["quote"] == "Named insured:\n Acme LLC" and "Named insured:\n Acme LLC"[0:4] == row["quote"][:4]
    # C3 and S2: on a scan the gate is the lower of the model score and the lowest cited word that holds the value; a scan number or date stays flagged.
    words = [["Year", 0.95], ["built:", 0.9], ["1942", 0.6], ["Name:", 0.99], ["Acme", 0.99], ["LLC", 0.97]]
    low = one("year_built", "1942", "Year built: 1942", "Year built: 1942", conf=0.99, scan=0.9, words=words)
    assert low["value"] is None and low["ocr_cited_confidence"] == 0.6, "the cited word '1942' scored 0.6"
    assert one("named_insured", "Acme LLC", "Name: Acme LLC", "Name: Acme LLC", conf=0.99, scan=0.5, words=words)["confidence"] == 0.97, "the page score is not used when the words are known; the lowest word that holds the value is"
    assert one("named_insured", "Acme LLC", "Name: Acme LLC", "Name: Acme LLC", conf=0.6, scan=0.9, words=words)["value"] is None, "the model's 0.6 is the lower score"
    assert one("named_insured", "Zed LLC", "Name: Zed LLC", "Name: Zed LLC", conf=0.99, scan=0.9, words=words)["value"] is None, "a cited word not in the word list counts as 0"
    ok = one("year_built", "1942", "Year built: 1942", "Year built: 1942", conf=0.99, scan=0.9, words=[["Year", 0.9], ["built:", 0.9], ["1942", 0.85]])
    assert ok["value"] == "1942" and ok["needs_review"] and ok["reason"] == REASON_SCAN, "S2: a number from a scan that passes the gate is kept flagged"
    assert not one("named_insured", "Acme LLC", "Name: Acme LLC", "Name: Acme LLC", conf=0.99, scan=0.9, words=words)["needs_review"], "S2 marks numbers and dates only"
    assert one("year_built", "1942", "Year built: 1942", "Year built: 1942", conf=0.99)["needs_review"] is False, "a typed file keeps the model score and no flag"
    assert one("named_insured", "Acme LLC", "Acme LLC", "Acme LLC", scan=0.2)["value"] is None, "a scan with no word list takes the page score, as before"
    # L1: files go whole and in order; one that does not fit is listed and not cut. No model call.
    sent = []

    def _post(settings, payload):  # noqa: F811
        sent.append(payload["messages"][1]["content"])
        return {"choices": [{"message": {"content": json.dumps({"fields": [{"field_id": "named_insured", "value": "Example LLC", "source": "a.md", "quote": "Example LLC", "confidence": 0.9}]})}}], "usage": {"total_tokens": 1}}

    real_max, MAX_CHARS = MAX_CHARS, 200
    try:
        with tempfile.TemporaryDirectory() as tmp:
            CACHE = Path(tmp)
            os.environ.update(LLM_BASE_URL=LOCAL_BASE, LLM_MODEL=LOCAL_MODEL)
            big = [{"name": "a.md", "text": "Named insured: Example LLC", "sha256": "1"}, {"name": "big.md", "text": "x" * 500, "sha256": "2"}, {"name": "z.md", "text": "tail", "sha256": "3"}]
            out = llm_extract(big)
            assert out["not_sent"] == ["big.md"] and "xxx" not in sent[0] and "z.md" in sent[0], "big.md is listed, not cut, and the files after it are still sent"
            assert llm_extract(big)["not_sent"] == ["big.md"] and len(sent) == 1, "the list is the same on a saved result"
            # (c1, E1) a file the reader did not open never reaches the model or the key.
            unreadable = big[:1] + [{"name": "x.docx", "text": "", "needs_human": True, "unread": "file type .docx is not read"}]
            assert cache_key([d for d in unreadable if not d.get("unread")], LOCAL_MODEL) == cache_key(big[:1], LOCAL_MODEL)
            llm_extract(unreadable)
            assert len(sent) == 2 and "x.docx" not in sent[1], "an unread file is not sent"
            llm_extract(big[:1])
            assert len(sent) == 2, "and it does not change the key: the same files without it are a cache hit"
    finally:
        MAX_CHARS = real_max
        USAGE.clear()
    banned = re.compile("dot" + "env|" + r"""["'/]\.env\b""")  # no pipeline file may load a settings file
    for source in Path(__file__).resolve().parents[1].rglob("*.py"):
        assert not banned.search(source.read_text()), f"{source} reads a settings file"
    print("llm gate ok")
