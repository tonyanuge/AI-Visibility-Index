import csv, io
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from .. import config
from ..store import db
from ..service import index_service, checker_service, lead_service
from ..ingest.runners.llm import available_runners
from .schemas import CheckRequest, LeadRequest

settings = config.load_settings()
app = FastAPI(title=settings.get("app_name", "AI Visibility Index"), version="0.1.0")
WEB = config.ROOT / "web" / "checker"

def _conn():
    return db.connect()

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

@app.post("/api/checker")
def checker(req: CheckRequest):
    with _conn() as c:
        v = checker_service.check(c, req.business, req.category, req.area)
    v["config"] = {"audit_url": settings.get("audit_url"),
                   "monitoring_url": settings.get("monitoring_url"),
                   "audit_price_eur": settings.get("audit_price_eur")}
    return v

@app.post("/api/leads")
def leads(req: LeadRequest):
    with _conn() as c:
        return lead_service.capture(c, req.business, req.email, req.category,
                                    req.area, req.verdict)

@app.get("/api/leads/export")
def leads_export():
    with _conn() as c:
        rows = lead_service.export_rows(c)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["ts", "business", "email", "category", "area", "verdict"])
    for r in rows:
        w.writerow([r["ts"], r["business"], r["email"], r["category"], r["area"], r["verdict"]])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"})

@app.get("/")
def home():
    idx = WEB / "index.html"
    return FileResponse(idx) if idx.exists() else {"app": app.title}
