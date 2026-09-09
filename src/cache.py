"""
Content-addressed disk cache for LLM calls.

Why this exists: the assignment requires a grader to reproduce the headline
results in under 15 minutes. Every LLM response is stored on disk keyed by a
hash of (model, prompt, params), and the cache directory is committed. So:

    make repro        -> replays from cache, offline, ~1 min, identical numbers
    make repro-live   -> re-issues every call against the API

It also means a re-run during development never pays for the same call twice.
"""
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable

from src.config import CACHE

CACHE.mkdir(parents=True, exist_ok=True)

# When set, a cache miss is an error instead of an API call. `make repro` sets
# this so a grader can verify the committed numbers came from the committed cache.
OFFLINE = os.getenv("CACHE_OFFLINE", "0") == "1"


class CacheMiss(RuntimeError):
    pass


def _key(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def _path(key: str) -> Path:
    # Shard by first 2 chars so the directory stays listable.
    d = CACHE / key[:2]
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{key}.json"


def cached_call(payload: dict[str, Any], fn: Callable[[], str]) -> str:
    """Return fn()'s result, memoised on disk under a hash of `payload`.

    `payload` must contain everything that could change the output — model,
    prompt, temperature, max_tokens. If it does not, the cache silently lies.
    """
    key = _key(payload)
    p = _path(key)
    if p.exists():
        return json.loads(p.read_text())["response"]

    if OFFLINE:
        raise CacheMiss(
            f"Cache miss for {key} while CACHE_OFFLINE=1.\n"
            f"The committed cache does not cover this call. Run `make repro-live`."
        )

    response = fn()
    p.write_text(json.dumps(
        {"key": key, "payload": payload, "response": response},
        ensure_ascii=False, indent=2,
    ))
    return response


def stats() -> dict[str, int]:
    files = list(CACHE.rglob("*.json"))
    return {
        "entries": len(files),
        "bytes": sum(f.stat().st_size for f in files),
    }
