"""Vercel serverless entrypoint. Imports the FastAPI app from `backend.api`."""

from __future__ import annotations

import os
import sys

# Make `backend/` importable when running on Vercel's Python runtime.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api import app  # noqa: E402

# Vercel's Python runtime detects an ASGI app exported as `app`.
__all__ = ["app"]
