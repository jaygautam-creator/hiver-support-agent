"""
Thin LLM client. One place where a model call happens, so the cache, the
retry policy, and the free-tier rate limiting are all in one auditable spot.

Every call goes through src.cache, so a re-run costs nothing and `make repro`
can replay the committed responses offline.
"""
import random
import threading
import time

from google import genai
from google.genai import types

from src.cache import cached_call
from src.config import AGENT_MODEL, GOOGLE_API_KEY, JUDGE_MODEL

_client: genai.Client | None = None

# Free-tier requests-per-minute is the binding constraint, not cost.
#
# Measured the hard way: 6 concurrent workers at a 1s interval produced 42
# retries and zero completed calls -- past the quota, every request 429s and the
# backoff makes throughput worse than serial. The global interval below caps the
# request RATE regardless of worker count, while a few workers hide the judge
# model's ~20s latency. Rate is the constraint; concurrency only helps under it.
_MIN_INTERVAL_S = 2.5
_last_call_at = 0.0
_throttle_lock = threading.Lock()


def client() -> genai.Client:
    global _client
    if _client is None:
        if not GOOGLE_API_KEY:
            raise RuntimeError(
                "GOOGLE_API_KEY is not set. Get a free key at "
                "https://aistudio.google.com/apikey and put it in .env"
            )
        _client = genai.Client(api_key=GOOGLE_API_KEY)
    return _client


def _throttle() -> None:
    global _last_call_at
    with _throttle_lock:
        wait = _MIN_INTERVAL_S - (time.monotonic() - _last_call_at)
        if wait > 0:
            time.sleep(wait)
        _last_call_at = time.monotonic()


def generate(
    prompt: str,
    *,
    model: str | None = None,
    system: str | None = None,
    temperature: float = 0.0,
    max_output_tokens: int = 2048,
    json_schema: dict | None = None,
    max_retries: int = 8,
) -> str:
    """Single-turn completion, memoised on disk.

    temperature defaults to 0.0: the evaluation compares systems, so run-to-run
    sampling noise would be measured as if it were a real difference.
    """
    model = model or AGENT_MODEL

    # Everything that could change the output must be in the cache key.
    payload = {
        "model": model,
        "system": system,
        "prompt": prompt,
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
        "json_schema": json_schema,
    }

    def _call() -> str:
        cfg = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            system_instruction=system,
            # Schema-constrained decoding when a shape is required, so a parse
            # failure is impossible rather than merely unlikely. Free-text
            # prompting for JSON fails silently on a few percent of calls, and
            # those failures would land in the metrics as model errors.
            **({"response_mime_type": "application/json",
                "response_schema": json_schema} if json_schema else {}),
        )
        last_err: Exception | None = None
        for attempt in range(max_retries):
            try:
                _throttle()
                resp = client().models.generate_content(
                    model=model, contents=prompt, config=cfg
                )
                return (resp.text or "").strip()
            except Exception as e:  # noqa: BLE001 - free tier surfaces many shapes
                last_err = e
                msg = str(e).lower()
                # Matched on the exception TYPE first, then on message text.
                # Text matching alone silently missed real transients: httpx
                # raises ReadTimeout("[Errno 60] Operation timed out"), whose
                # message contains "timed out" and not "timeout", so a plain
                # network hiccup was classified unretryable and killed an entire
                # multi-hundred-call run at whatever item it happened to hit.
                # Types are checked by name so this stays free of a hard httpx
                # import.
                exc_name = type(e).__name__.lower()
                retryable = (
                    any(t in exc_name for t in
                        ("timeout", "connect", "remoteprotocol", "readerror"))
                    or any(s in msg for s in
                           ("429", "resource_exhausted", "503", "500",
                            "unavailable", "timeout", "timed out",
                            "deadline", "connection reset", "connection error",
                            "temporarily", "overloaded"))
                )
                if not retryable or attempt == max_retries - 1:
                    raise
                # 503 ("high demand") on the free tier can persist for minutes,
                # so it gets a longer ceiling than a plain rate limit.
                ceiling = 180.0 if "503" in msg or "unavailable" in msg else 60.0
                sleep = min(ceiling, 5.0 * (2 ** attempt)) + random.uniform(0, 2)
                print(f"    {'overloaded' if '503' in msg else 'rate-limited'}, "
                      f"retrying in {sleep:.0f}s ({attempt + 1}/{max_retries})",
                      flush=True)
                time.sleep(sleep)
        raise last_err  # unreachable

    return cached_call(payload, _call)


def judge(prompt: str, **kw) -> str:
    """Same call, routed to the judge model. Separate function so it is obvious
    at every call site which model produced a number."""
    return generate(prompt, model=JUDGE_MODEL, **kw)
