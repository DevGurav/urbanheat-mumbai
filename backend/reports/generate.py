"""Renders `template.html` (Jinja2) to a PDF via WeasyPrint (Phase 7, `api-reference.md`).

Never computes a number itself — both sections of the report come from
`backend/services.py`'s `explain_ward`/`scenario`, the same functions `GET /explain/{cell_id}`
and `POST /scenario` already serve, so a PDF can never disagree with the live dashboard.

WeasyPrint needs native Pango/cairo/gdk-pixbuf libraries at import time, not just the Python
package — present in the deployed Docker image (`Dockerfile`'s apt-get step) and GitHub
Actions' `ubuntu-latest` runner (`ci.yml`'s equivalent step), absent on a bare Windows dev
machine. `generate_ward_report`'s caller is expected to handle `OSError` from that import
failing (`backend/routers/reports.py` does).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Template

from backend.schemas import ScenarioResponse, WardExplainResponse

_TEMPLATE_PATH = Path(__file__).parent / "template.html"


def generate_ward_report(
    ward: WardExplainResponse, scenario: ScenarioResponse | None = None
) -> bytes:
    """Renders the ward explanation, and a scenario comparison if given, to PDF bytes."""
    # Imported here, not at module level: the native library load (WeasyPrint's own `ffi`
    # module) happens at import time, and this module docstring's OSError contract depends
    # on that failure surfacing inside this function, not at `backend.routers.reports`'
    # own import of this module.
    from weasyprint import HTML

    template = Template(_TEMPLATE_PATH.read_text(encoding="utf-8"))
    html = template.render(
        ward=ward,
        scenario=scenario,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d"),
    )
    return HTML(string=html).write_pdf()
