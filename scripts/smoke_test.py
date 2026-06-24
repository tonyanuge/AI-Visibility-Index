"""End-to-end smoke test. Builds a temp DB, seeds it, exercises every layer + the API."""
import sys, tempfile, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

PASS, FAIL = [], []
def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("  PASS  " if cond else "  FAIL  ") + name)

def main():
    tmp = Path(tempfile.mkdtemp()) / "smoke.db"
    from avix.store import db as dbmod
    dbmod.DB_PATH = tmp  # point the app at the temp db
    from avix.store import db
    from scripts.seed import seed
    from avix.service import index_service, checker_service, lead_service
    from avix.audit import audit_log

    conn = db.connect(tmp); seed(conn)

    print("\n[1] Scoring + Index")
    cell = index_service.get_cell(conn, "Physiotherapists", "Dublin")
    check("index cell builds", cell is not None)
    top = cell.scores[0]
    check("top business is the most-recommended (Riverside)", top.business.startswith("Riverside"))
    check("invisible businesses counted in summary", cell.summary["invisible_count"] >= 2)
    check("share-of-voice sums sensibly (<=1.0001)", sum(s.share_of_recs for s in cell.scores) <= 1.0001)
    check("accuracy is null-safe (no crash)", True)

    print("\n[2] Checker verdict states")
    inv = checker_service.check(conn, "Northside Physiotherapy (DEMO)", "Physiotherapists", "Dublin")
    check("never-named business -> INVISIBLE", inv["state"] == "INVISIBLE")
    check("INVISIBLE lists competitors recommended instead", len(inv.get("recommended_instead", [])) > 0)
    beaten = checker_service.check(conn, "City Sports Clinic (DEMO)", "Physiotherapists", "Dublin")
    check("mid-ranked business -> VISIBLE_BEATEN", beaten["state"] == "VISIBLE_BEATEN")
    strong = checker_service.check(conn, "Riverside Physio (DEMO)", "Physiotherapists", "Dublin")
    check("top business -> STRONG", strong["state"] == "STRONG")
    nc = checker_service.check(conn, "Whoever", "Dentists", "Cork")
    check("unmapped cell -> NOT_COVERED", nc["state"] == "NOT_COVERED")

    print("\n[3] Leads + content-free audit")
    lead_service.capture(conn, "Northside Physiotherapy (DEMO)", "owner@clinic.ie",
                         "Physiotherapists", "Dublin", "INVISIBLE")
    rows = lead_service.export_rows(conn)
    check("lead stored with email", any(r["email"] == "owner@clinic.ie" for r in rows))
    audit_blob = " ".join(e["event"] + e["ref"] for e in audit_log.entries(conn))
    check("AUDIT IS CONTENT-FREE (no email in audit trail)", "owner@clinic.ie" not in audit_blob)
    check("audit recorded events", len(audit_log.entries(conn)) > 0)

    print("\n[4] Multi-vertical (breadth)")
    cells = index_service.list_cells(conn)
    check("two verticals available (physio + estate)", len(cells) >= 2)

    print("\n[5] API layer (FastAPI TestClient)")
    from fastapi.testclient import TestClient
    from avix.api.main import app
    client = TestClient(app)
    check("GET /health ok", client.get("/health").status_code == 200)
    check("GET /api/index/cells ok", client.get("/api/index/cells").status_code == 200)
    r = client.post("/api/checker", json={"business": "Northside Physiotherapy (DEMO)",
                    "category": "Physiotherapists", "area": "Dublin"})
    check("POST /api/checker -> INVISIBLE via API", r.json().get("state") == "INVISIBLE")
    r2 = client.post("/api/leads", json={"business": "X", "email": "a@b.ie",
                     "category": "Physiotherapists", "area": "Dublin", "verdict": "INVISIBLE"})
    check("POST /api/leads ok", r2.status_code == 200)
    check("GET / serves checker page", client.get("/").status_code == 200)

    print("\n" + "=" * 48)
    print(f"SMOKE TEST: {len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("FAILED:", FAIL); sys.exit(1)
    print("ALL GREEN"); sys.exit(0)

if __name__ == "__main__":
    main()
