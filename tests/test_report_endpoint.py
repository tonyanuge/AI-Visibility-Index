"""HTTP tests for the report endpoint + the enriched checker (FastAPI TestClient, temp DB)."""
import io, zipfile, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

CAT, AREA = "Accountants / Chartered Accountants", "Dublin"


def _client():
    tmp = Path(tempfile.mkdtemp()) / "ep.db"
    from avix.store import db as dbmod
    dbmod.DB_PATH = tmp                       # point the app at the temp DB
    from avix.store import db
    from scripts.seed import seed as seed_demo
    from scripts.seed_accountants import seed as seed_acc
    c = db.connect(tmp); seed_demo(c); seed_acc(c)
    from avix.api.main import app
    from avix.api import ratelimit
    ratelimit.configure(None)                 # file-backed limits
    ratelimit.reset()
    from fastapi.testclient import TestClient
    return TestClient(app)


def test_report_endpoint_returns_valid_docx():
    client = _client()
    r = client.get("/api/report", params={"business": "Liffey & Quay Accountants (DEMO)",
                                           "category": CAT, "area": AREA})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert "attachment" in r.headers.get("content-disposition", "")
    assert r.content[:2] == b"PK"
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        z.read("word/document.xml")


def test_report_endpoint_unmapped_404():
    client = _client()
    r = client.get("/api/report", params={"business": "X", "category": "Dentists", "area": "Cork"})
    assert r.status_code == 404


def test_checker_carries_onscreen_report():
    client = _client()
    r = client.post("/api/checker", json={"business": "Northside Accounting Co (DEMO)",
                                          "category": CAT, "area": AREA})
    j = r.json()
    assert j["state"] == "INVISIBLE"
    assert j.get("report", {}).get("key_findings")
    assert j["report"]["competitors"]


def test_report_endpoint_rate_limited():
    client = _client()
    from avix.api import ratelimit
    ratelimit.configure({"trust_forwarded_for": False,
                         "limits": {"report": {"limit": 2, "window_seconds": 60}}})
    p = {"business": "Liffey & Quay Accountants (DEMO)", "category": CAT, "area": AREA}
    codes = [client.get("/api/report", params=p).status_code for _ in range(3)]
    ratelimit.configure(None)
    assert codes[0] == 200 and codes[1] == 200 and codes[2] == 429
