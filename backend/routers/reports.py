"""POST /reports/generate — a downloadable PDF for a ward, optionally with a scenario
comparison (Phase 7, `api-reference.md`).

Returns the PDF directly (`application/pdf`, `Content-Disposition: attachment`), not a
separate stored-file URL as `api-reference.md`'s original stub sketched — the same kind of
correction Phase 3 already made to that file's draft contracts (`ward_name` → `ward_code`,
`tree_planting` → `greening`/`cool_roof`). Storing the file somewhere would mean adding blob
storage this project has never needed anywhere else (ADR-0004's whole framing); streaming the
bytes back on the same request needs nothing new.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from backend import services
from backend.errors import api_error
from backend.reports.generate import generate_ward_report
from backend.schemas import ReportRequest

router = APIRouter(tags=["reports"])


@router.post("/reports/generate")
def generate_report(req: ReportRequest, request: Request) -> Response:
    store = request.app.state.store
    ward = services.explain_ward(store, req.ward_code)
    scenario = (
        services.scenario(store, req.ward_code, req.intervention, req.coverage)
        if req.intervention
        else None
    )

    try:
        pdf_bytes = generate_ward_report(ward, scenario)
    except OSError as exc:
        # WeasyPrint needs native Pango/cairo/gdk-pixbuf libraries at import time, present in
        # the deployed image (Dockerfile) and CI (ci.yml) but not guaranteed on every dev
        # machine (backend/reports/generate.py's module docstring has the detail) — a missing
        # native library degrades this one endpoint, not the whole app.
        raise api_error(503, "reports_unavailable", str(exc)) from exc

    filename = f"urbanheat-ward-{req.ward_code}-report.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
