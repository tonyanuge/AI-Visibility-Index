"""Real (non-demo) market behaviour: roster-restriction applies, but SAMPLE banner does NOT —
real markets carry a dated-snapshot provenance note. Uses in-memory source="Manual" data with
placeholder names (no real firm names, no dependency on the gitignored CSVs)."""
import io, zipfile, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from avix.store import db, repository as repo
from avix.core.models import Mention
from avix.service import checker_service, report_service, sample_guard

CAT, AREA = "Estate Agents", "Testville"
TOP = "Alpha Realty (LISTED)"
ZERO = "Gamma Property (LISTED)"      # on roster, 0 mentions -> INVISIBLE
OFF = "Some Other Agency"            # not on roster -> honest no-data


def _conn():
    c = db.connect(Path(tempfile.mkdtemp()) / "real.db")
    rows = [
        (TOP, "ChatGPT", "Discovery", 1), (TOP, "Perplexity", "Shortlist", 1),
        (TOP, "ChatGPT", "Need-based", 2), (TOP, "Perplexity", "Discovery", 1),
        (TOP, "ChatGPT", "Attribute", 2),                 # 5 -> Strong -> STRONG
        ("Beta Homes (LISTED)", "ChatGPT", "Discovery", 3),
    ]
    for b, eng, arch, rank in rows:
        repo.add_mention(c, Mention(business=b, category=CAT, area=AREA, engine=eng,
            archetype=arch, rank=rank, source="Manual", prompt_text=f"q-{arch}", date="2026-06-27"))
        repo.add_business(c, b, CAT, AREA)
    repo.add_business(c, ZERO, CAT, AREA)                  # roster firm, never captured
    return c


def test_real_market_is_not_demo():
    c = _conn()
    assert sample_guard.is_guarded(c, CAT, AREA) is False   # Manual source -> not a SAMPLE market
    assert sample_guard.is_mapped(c, CAT, AREA) is True


def test_listed_firm_gets_real_verdict_no_sample_banner():
    c = _conn()
    v = checker_service.check(c, TOP, CAT, AREA)
    assert v["state"] == "STRONG"
    assert not v.get("sample") and "sample_banner" not in v   # NO sample banner on a real market
    assert v.get("provenance") and "Dated snapshot" in v["provenance"]


def test_zero_mention_roster_firm_is_invisible():
    c = _conn()
    v = checker_service.check(c, ZERO, CAT, AREA)
    assert v["state"] == "INVISIBLE"                          # true, evidenced (never captured)
    assert not v.get("sample") and v.get("provenance")


def test_off_roster_real_name_honest_no_data():
    c = _conn()
    v = checker_service.check(c, OFF, CAT, AREA)
    assert v["state"] == "NOT_IN_SAMPLE"                      # reused state, real wording
    assert v.get("sample") is False and "sample_banner" not in v
    assert OFF in v["message"] and "haven't captured" in v["message"].lower()
    assert "recommended_instead" not in v and "ahead_of_you" not in v   # names no competitors


def test_off_roster_report_refused_real_market():
    c = _conn()
    assert report_service.report_data(c, OFF, CAT, AREA) is None
    assert report_service.build_docx(c, OFF, CAT, AREA) is None


def test_real_report_has_provenance_not_sample_strip():
    c = _conn()
    blob = report_service.build_docx(c, TOP, CAT, AREA)
    assert blob and blob[:2] == b"PK"
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    assert "Dated snapshot" in text          # provenance present
    assert "SAMPLE DATA" not in text         # NO sample strip on a real report


def test_on_screen_real_market_carries_provenance():
    c = _conn()
    v = checker_service.check(c, TOP, CAT, AREA)
    p = report_service.on_screen(c, TOP, CAT, AREA, v)
    assert p.get("provenance") and not p.get("sample")
