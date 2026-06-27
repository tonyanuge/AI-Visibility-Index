import csv, io, hmac, re
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse, FileResponse, Response
from .. import config
from ..store import db
from ..service import index_service, checker_service, lead_service, report_service, sample_guard
from ..audit import audit_log
from ..ingest.runners.llm import available_runners
from .schemas import CheckRequest, LeadRequest
from .ratelimit import rate_limit

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

settings = config.load_settings()
app = FastAPI(title=settings.get("app_name", "AI Visibility Index"), version="0.1.0")
WEB = config.ROOT / "web"
LANDING_PAGE = WEB / "landing" / "index.html"
CHECKER_PAGE = WEB / "checker" / "index.html"
PRICING_PAGE = WEB / "pricing" / "index.html"

def _conn():
    return db.connect()

# Admin-only guard for lead export (emails are PII). Token comes from the environment;
# the client sends it in the X-Admin-Export-Token header. Never exposed to the frontend.
def _require_export_token(token: str | None):
    server = config.env("AVIX_ADMIN_EXPORT_TOKEN")
    if not server:  # fail closed: export stays disabled until an admin token is configured
        raise HTTPException(503, "Lead export is disabled: no admin export token configured.")
    if not token or not hmac.compare_digest(token, server):  # constant-time compare
        # 401: the caller is unauthenticated (no/invalid credentials), not forbidden.
        raise HTTPException(401, "Invalid or missing admin export token.",
                            headers={"WWW-Authenticate": 'Token realm="lead-export"'})

@app.get("/health")
def health():
    runners = [r.name for r in available_runners()]
    return {"status": "ok", "live_engines_enabled": runners,
            "mode": "automated" if runners else "manual"}

@app.get("/api/index/cells")
def cells():
    with _conn() as c:
        return index_service.list_cells(c)

@app.get("/api/index/{category}/{area}")
def index_cell(category: str, area: str):
    with _conn() as c:
        cell = index_service.get_cell(c, category, area)
    if cell is None:
        raise HTTPException(404, "Cell not mapped yet")
    return {"category": cell.category, "area": cell.area,
            "summary": cell.summary,
            "scores": [vars(s) for s in cell.scores]}

@app.post("/api/checker", dependencies=[Depends(rate_limit("checker"))])
def checker(req: CheckRequest):
    with _conn() as c:
        v = checker_service.check(c, req.business, req.category, req.area)
        # on-screen report payload only for real verdicts — never for a refused (NOT_IN_SAMPLE)
        # name, so a real business gets no fabricated stat/findings.
        if v.get("state") != "NOT_IN_SAMPLE":
            v["report"] = report_service.on_screen(c, req.business, req.category, req.area, v)
    v["config"] = {"audit_url": settings.get("audit_url"),
                   "monitoring_url": settings.get("monitoring_url"),
                   "audit_price_eur": settings.get("audit_price_eur")}
    return v

@app.post("/api/leads", dependencies=[Depends(rate_limit("leads"))])
def leads(req: LeadRequest):
    with _conn() as c:
        return lead_service.capture(c, req.business, req.email, req.category,
                                    req.area, req.verdict)

@app.get("/api/leads/export", dependencies=[Depends(rate_limit("export"))])
def leads_export(x_admin_export_token: str | None = Header(default=None)):
    _require_export_token(x_admin_export_token)
    with _conn() as c:
        rows = lead_service.export_rows(c)
        # content-free audit on SUCCESS only (200) — event + non-PII ref, never token or IP
        audit_log.record(c, "export.accessed", "leads")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["ts", "business", "email", "category", "area", "verdict"])
    for r in rows:
        w.writerow([r["ts"], r["business"], r["email"], r["category"], r["area"], r["verdict"]])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"})

@app.get("/api/report", dependencies=[Depends(rate_limit("report"))])
def report_download(business: str, category: str, area: str):
    """Branded .docx for business+market, generated in-memory (never written to a repo path)."""
    with _conn() as c:
        blob = report_service.build_docx(c, business, category, area)
    if blob is None:
        raise HTTPException(404, "This category/area has not been mapped yet.")
    safe = re.sub(r"[^A-Za-z0-9]+", "_", business).strip("_") or "report"
    return Response(content=blob, media_type=_DOCX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{safe}_AI_Visibility_Check.docx"'})

@app.get("/api/sample/roster", dependencies=[Depends(rate_limit("checker"))])
def sample_roster(category: str, area: str):
    """Layer 2 source: roster (example DEMO firm) names for a guarded market, so the UI can
    restrict the business field to sample firms. Empty + sample=false for real markets."""
    with _conn() as c:
        guarded = sample_guard.is_guarded(c, category, area)
        names = sample_guard.roster_names(c, category, area) if guarded else []
    return {"sample": guarded, "businesses": sorted(names)}

@app.get("/")
def home():
    return FileResponse(LANDING_PAGE) if LANDING_PAGE.exists() else {"app": app.title}

@app.get("/checker")
def checker_page():
    return FileResponse(CHECKER_PAGE) if CHECKER_PAGE.exists() else {"app": app.title}

@app.get("/pricing")
def pricing_page():
    return FileResponse(PRICING_PAGE) if PRICING_PAGE.exists() else {"app": app.title}
