"""Demo sample-data guardrail — server-side enforcement (defamation safety).

Proves a REAL business name can never receive a fabricated verdict/report against synthetic
demo data, at the service layer AND through the API."""
import io, zipfile, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

CAT, AREA = "Accountants / Chartered Accountants", "Dublin"
REAL = "Nexus Accounting"            # a real firm — must NOT get a verdict
ROSTER = "Northside Accounting Co (DEMO)"   # invisible roster firm
TOP = "Liffey & Quay Accountants (DEMO)"


def _conn():
    from avix.store import db
    from scripts.seed_accountants import seed
    c = db.connect(Path(tempfile.mkdtemp()) / "g.db")
    seed(c)
    return c


def _client():
    tmp = Path(tempfile.mkdtemp()) / "ge.db"
    from avix.store import db as dbmod
    dbmod.DB_PATH = tmp
    from avix.store import db
    from scripts.seed_accountants import seed as seed_acc
    c = db.connect(tmp); seed_acc(c)
    from avix.api.main import app
    from avix.api import ratelimit
    ratelimit.configure(None); ratelimit.reset()
    from fastapi.testclient import TestClient
    return TestClient(app)


# ---- service layer (enforcement is below the API) ----

def test_service_real_name_never_gets_verdict():
    from avix.service import checker_service
    c = _conn()
    v = checker_service.check(c, REAL, CAT, AREA)
    assert v["state"] == "NOT_IN_SAMPLE"
    assert v["state"] not in ("INVISIBLE", "VISIBLE_BEATEN", "STRONG")
    assert "recommended_instead" not in v and "ahead_of_you" not in v   # names no competitors
    assert v.get("sample") is True and v.get("sample_banner")


def test_service_roster_name_gets_verdict_with_banner():
    from avix.service import checker_service
    c = _conn()
    v = checker_service.check(c, ROSTER, CAT, AREA)
    assert v["state"] == "INVISIBLE"        # roster firm, genuinely never recommended
    assert v.get("sample") is True and v.get("sample_banner")


def test_service_report_refuses_real_name():
    from avix.service import report_service
    c = _conn()
    assert report_service.report_data(c, REAL, CAT, AREA) is None
    assert report_service.build_docx(c, REAL, CAT, AREA) is None   # never a docx for a real name


def test_fail_toward_guarded_on_unknown_source():
    """A cell with a missing/unknown mention source must be treated as guarded (not real)."""
    from avix.store import db, repository as repo
    from avix.core.models import Mention
    from avix.service import sample_guard
    c = db.connect(Path(tempfile.mkdtemp()) / "u.db")
    repo.add_mention(c, Mention(business="A (DEMO)", category="C", area="A", engine="ChatGPT",
                                archetype="Discovery", rank=1, source="", date="2026-06-26"))
    repo.add_business(c, "A (DEMO)", "C", "A")
    assert sample_guard.is_guarded(c, "C", "A") is True   # blank source -> guarded


# ---- API layer ----

def test_api_real_name_not_in_sample():
    client = _client()
    j = client.post("/api/checker", json={"business": REAL, "category": CAT, "area": AREA}).json()
    assert j["state"] == "NOT_IN_SAMPLE"
    assert "report" not in j               # no fabricated stat/findings for a real name
    assert j.get("sample_banner")


def test_api_report_real_name_404():
    client = _client()
    r = client.get("/api/report", params={"business": REAL, "category": CAT, "area": AREA})
    assert r.status_code == 404


def test_api_sample_roster_lists_firms():
    client = _client()
    j = client.get("/api/sample/roster", params={"category": CAT, "area": AREA}).json()
    assert j["sample"] is True
    assert ROSTER in j["businesses"] and TOP in j["businesses"]


def test_api_roster_report_has_banner():
    client = _client()
    r = client.get("/api/report", params={"business": TOP, "category": CAT, "area": AREA})
    assert r.status_code == 200
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    assert "SAMPLE DATA" in text
