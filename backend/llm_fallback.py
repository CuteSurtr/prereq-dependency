"""Anthropic Haiku fallback for prereq strings the rule-based parser can't handle.

Stub interface: returns `None` unless `ANTHROPIC_API_KEY` is set, in which case it
calls Claude Haiku with a structured-output prompt and caches by string hash.

Wire-up later — interface is stable so callers don't need to change.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from backend.parser import ParseResult, PrereqKind

CACHE_DIR = Path(__file__).parent.parent / "data" / "llm_cache"


def _cache_path(text: str) -> Path:
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return CACHE_DIR / f"{h}.json"


def fallback(text: str) -> ParseResult | None:
    """Return a structured ParseResult or None if no key / disabled.

    Cached to disk by sha256(text) so repeated calls don't burn API credits.
    """
    if not text or not text.strip():
        return None
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None  # not enabled

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = _cache_path(text)
    if cache.exists():
        cached = json.loads(cache.read_text(encoding="utf-8"))
        return ParseResult(
            kind=PrereqKind(cached["kind"]),
            groups=[tuple(g) for g in cached["groups"]],
            notes=cached.get("notes", ""),
            confident=True,
            raw=text,
        )

    # Real call goes here — left as a clear TODO so it's a one-liner to enable.
    # The schema we want back from Claude:
    #   {"kind": "PREREQ"|"COREQ"|"RECOMMENDED",
    #    "groups": [["MATH 20A", "MATH 20B"], ["MATH 10A", "MATH 10B"]],
    #    "notes": "..."}
    # See docs/parsing-strategy.md for the full prompt; the current stub
    # intentionally avoids importing the SDK so installs stay light.
    return None


__all__ = ["fallback"]
