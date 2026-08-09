#!/usr/bin/env python
"""Dump the FastAPI OpenAPI schema to a file.

Runs without a server, so CI can regenerate the client types deterministically
and fail when the committed output has drifted from the API.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from kiku.api.main import create_app


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "frontend/openapi.json")
    spec = create_app().openapi()
    out.parent.mkdir(parents=True, exist_ok=True)
    # Stable formatting: the file is diffed in CI, so key order and spacing must
    # not wobble between runs.
    out.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n")
    schemas = len(spec.get("components", {}).get("schemas", {}))
    print(f"wrote {out} — {len(spec['paths'])} paths, {schemas} schemas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
