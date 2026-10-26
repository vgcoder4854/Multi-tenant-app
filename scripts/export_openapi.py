"""Export the OpenAPI schema to docs/openapi.json.

Usage (from the backend directory):
    python ../scripts/export_openapi.py
"""
from __future__ import annotations

import json
import pathlib

from app.main import app

DOCS = pathlib.Path(__file__).resolve().parent.parent / "docs"
DOCS.mkdir(exist_ok=True)
out = DOCS / "openapi.json"
out.write_text(json.dumps(app.openapi(), indent=2), encoding="utf-8")
print(f"wrote {out} ({out.stat().st_size} bytes)")
