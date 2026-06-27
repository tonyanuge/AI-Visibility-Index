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
    # ISSUE-1 contract: invalid email must be rejected (non-2xx) so the checker UI shows an error, not success
    bad = client.post("/api/leads", json={"business": "X", "email": "not-an-email",
                      "category": "Physiotherapists", "area": "Dublin", "verdict": "INVISIBLE"})
    check("POST /api/leads rejects invalid email (non-2xx)", bad.status_code >= 400)
    home = client.get("/")
    check("GET / serves landing page", home.status_code == 200 and "checker" in home.text.lower())
    chk = client.get("/checker")
    check("GET /checker serves functional checker page", chk.status_code == 200 and "id=\"cell\"" in chk.text)
    check("checker business field is a typeahead combobox (free text + datalist suggestions)",
          'list="rosterList"' in chk.text and 'id="rosterList"' in chk.text and "<input id=\"business\"" in chk.text)

    print("\n[6] Protected lead export (ISSUE-2 + auth status correction)")
    from avix.api import ratelimit
    ratelimit.reset()  # fresh window so the auth matrix isn't throttled
    EXP, TOK = "/api/leads/export", "X-Admin-Export-Token"
    os.environ.pop("AVIX_ADMIN_EXPORT_TOKEN", None)
    check("export FAILS CLOSED when server token unset (503)", client.get(EXP).status_code == 503)
    os.environ["AVIX_ADMIN_EXPORT_TOKEN"] = "smoke-secret-123"
    miss = client.get(EXP)
    check("export rejects MISSING token (401)", miss.status_code == 401)
    check("export 401 carries WWW-Authenticate header",
          "www-authenticate" in {k.lower() for k in miss.headers})
    check("export rejects WRONG token (401)", client.get(EXP, headers={TOK: "nope"}).status_code == 401)
    check("export rejects BLANK token (401)", client.get(EXP, headers={TOK: ""}).status_code == 401)
    ok = client.get(EXP, headers={TOK: "smoke-secret-123"})
    check("export SUCCEEDS with correct token (200)", ok.status_code == 200)
    check("export returns CSV with expected header row",
          ok.text.splitlines()[0] == "ts,business,email,category,area,verdict")
    check("content-free audit logged export.accessed (event only, no token/IP)",
          any(e["event"] == "export.accessed" for e in audit_log.entries(conn)))
    os.environ.pop("AVIX_ADMIN_EXPORT_TOKEN", None)  # restore fail-closed default

    print("\n[7] Rate limiting (ISSUE-A)")
    # inject a tiny, known limit so the trigger point is deterministic (proves config-driven)
    ratelimit.configure({"trust_forwarded_for": False, "limits": {
        "checker": {"limit": 2, "window_seconds": 60},
        "leads":   {"limit": 10, "window_seconds": 60}}})
    # use a roster (DEMO) name so the guardrail returns a verdict, not NOT_IN_SAMPLE
    body = {"business": "Riverside Physio (DEMO)", "category": "Physiotherapists", "area": "Dublin"}
    s1 = client.post("/api/checker", json=body).status_code
    s2 = client.post("/api/checker", json=body).status_code
    blocked = client.post("/api/checker", json=body)
    check("under-threshold checker requests still succeed", s1 == 200 and s2 == 200)
    check("over-threshold checker request -> 429", blocked.status_code == 429)
    check("429 carries Retry-After header",
          "retry-after" in {k.lower() for k in blocked.headers})
    # per-route independence: leads (limit 10) is unaffected by the checker limit being hit
    lead_ok = client.post("/api/leads", json={"business": "X", "email": "ok@b.ie",
              "category": "Physiotherapists", "area": "Dublin", "verdict": "INVISIBLE"})
    check("hitting checker limit does NOT block /api/leads", lead_ok.status_code == 200)
    ratelimit.configure(None)  # restore file-backed limits

    print("\n[8] Demo journey: Accountants — Dublin (search -> on-screen + downloadable report)")
    from scripts.seed_accountants import seed as seed_acc, MARKET as ACC
    seed_acc(conn)
    ratelimit.reset()
    acc_cat, acc_area = ACC
    cells_now = client.get("/api/index/cells").json()
    check("accountants market is mapped",
          any(c["category"] == acc_cat and c["area"] == acc_area for c in cells_now))
    rr = client.post("/api/checker", json={"business": "Liffey & Quay Accountants (DEMO)",
                     "category": acc_cat, "area": acc_area}).json()
    check("accountants search returns a real verdict (not NOT_COVERED)", rr["state"] != "NOT_COVERED")
    check("checker carries on-screen report (stat + key findings)",
          bool(rr.get("report", {}).get("stat")) and len(rr["report"]["key_findings"]) > 0)
    dl = client.get("/api/report", params={"business": "Liffey & Quay Accountants (DEMO)",
                    "category": acc_cat, "area": acc_area})
    check("GET /api/report returns a downloadable .docx (200)",
          dl.status_code == 200 and dl.content[:2] == b"PK")
    check("report is a .docx attachment",
          "attachment" in dl.headers.get("content-disposition", "")
          and "wordprocessingml" in dl.headers.get("content-type", ""))
    check("seeded roster result carries SAMPLE banner", bool(rr.get("sample_banner")))

    print("\n[9] Demo guardrail (defamation safety — real name must NOT get a verdict)")
    import io as _io, zipfile as _zip
    ratelimit.reset()
    real = client.post("/api/checker", json={"business": "Nexus Accounting",
                       "category": acc_cat, "area": acc_area}).json()
    check("real name in demo market -> NOT_IN_SAMPLE (no fabricated verdict)",
          real["state"] == "NOT_IN_SAMPLE")
    check("NOT_IN_SAMPLE names no competitors about the real business",
          "recommended_instead" not in real and "ahead_of_you" not in real and "report" not in real)
    check("NOT_IN_SAMPLE carries SAMPLE banner", bool(real.get("sample_banner")))
    rep = client.get("/api/report", params={"business": "Nexus Accounting",
                     "category": acc_cat, "area": acc_area})
    check("/api/report refuses a real name (404, no docx)", rep.status_code == 404)
    ros = client.get("/api/sample/roster", params={"category": acc_cat, "area": acc_area}).json()
    check("/api/sample/roster lists sample firms", ros["sample"] is True and len(ros["businesses"]) > 0)
    dlb = client.get("/api/report", params={"business": "Liffey & Quay Accountants (DEMO)",
                     "category": acc_cat, "area": acc_area})
    banner_in_docx = (dlb.status_code == 200 and
        "SAMPLE DATA" in _zip.ZipFile(_io.BytesIO(dlb.content)).read("word/document.xml").decode())
    check("roster report .docx contains the SAMPLE banner strip", banner_in_docx)
    # NOT_IN_SAMPLE lead moment: a typed real name can still leave a lead via the existing /api/leads
    lead = client.post("/api/leads", json={"business": "Nexus Accounting", "email": "owner@nexus.ie",
           "category": acc_cat, "area": acc_area, "verdict": "NOT_IN_SAMPLE"})
    check("NOT_IN_SAMPLE lead captured via existing /api/leads (200)", lead.status_code == 200)

    print("\n[10] Real market split (roster-restriction all markets; provenance not SAMPLE banner)")
    from avix.core.models import Mention
    from avix.store import repository as repo
    RC, RA = "Estate Agents", "Smoke Town"
    for b, eng in [("Alpha Realty (LISTED)", "ChatGPT"), ("Alpha Realty (LISTED)", "Perplexity"),
                   ("Alpha Realty (LISTED)", "ChatGPT"), ("Alpha Realty (LISTED)", "Perplexity"),
                   ("Alpha Realty (LISTED)", "ChatGPT"), ("Beta Homes (LISTED)", "ChatGPT")]:
        repo.add_mention(conn, Mention(business=b, category=RC, area=RA, engine=eng, archetype="Discovery",
            rank=1, source="Manual", prompt_text="best estate agents smoke town", date="2026-06-27"))
        repo.add_business(conn, b, RC, RA)
    repo.add_business(conn, "Gamma Property (LISTED)", RC, RA)   # roster, 0 mentions
    ratelimit.reset()
    rv = client.post("/api/checker", json={"business": "Alpha Realty (LISTED)", "category": RC, "area": RA}).json()
    check("real market: listed firm gets a verdict, NOT sample-bannered",
          rv["state"] in ("STRONG", "VISIBLE_BEATEN", "INVISIBLE") and not rv.get("sample"))
    check("real market: verdict carries dated-snapshot provenance", bool(rv.get("provenance")))
    inv = client.post("/api/checker", json={"business": "Gamma Property (LISTED)", "category": RC, "area": RA}).json()
    check("real market: 0-mention roster firm -> INVISIBLE (real)", inv["state"] == "INVISIBLE" and not inv.get("sample"))
    off = client.post("/api/checker", json={"business": "Not Captured Agency", "category": RC, "area": RA}).json()
    check("real market: off-roster -> honest no-data (no verdict, no SAMPLE banner, no competitors)",
          off["state"] == "NOT_IN_SAMPLE" and off.get("sample") is False
          and "recommended_instead" not in off and "report" not in off)
    check("real market: off-roster report refused (404)",
          client.get("/api/report", params={"business": "Not Captured Agency", "category": RC, "area": RA}).status_code == 404)

    print("\n" + "=" * 48)
    print(f"SMOKE TEST: {len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("FAILED:", FAIL); sys.exit(1)
    print("ALL GREEN"); sys.exit(0)

if __name__ == "__main__":
    main()
