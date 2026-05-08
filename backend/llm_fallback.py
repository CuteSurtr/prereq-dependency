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
    if not text or not text.strip():
        return None
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

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

    return None


__all__ = ["fallback"]
