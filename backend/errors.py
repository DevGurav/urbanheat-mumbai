"""A single place to raise API errors, so every failure has the same shape.

`docs/api-reference.md` promises an RFC-7807-ish body: `{detail, error_code}` with a real
HTTP status, never a 200 wrapping an error. `main.py` registers an exception handler that
flattens this into the top-level response body.
"""

from __future__ import annotations

from fastapi import HTTPException


def api_error(status_code: int, error_code: str, detail: str) -> HTTPException:
    return HTTPException(
        status_code=status_code, detail={"detail": detail, "error_code": error_code}
    )
