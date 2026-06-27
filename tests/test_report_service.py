"""Unit tests for the report adapter: scored cell -> on-screen payload + ReportData -> .docx."""
import io, zipfile, sys, tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))   # so `scripts.*` (namespace package) is importable

from avix.store import db
from avix.core import index
from avix.service import index_service, report_service
from scripts.seed_accountants import seed as seed_acc, MARKET

CAT, AREA = MARKET


def _conn():
    tmp = Path(tempfile.mkdtemp()) / "rs.db"
    c = db.connect(tmp)
    seed_acc(c)
    return c


def _cell_verdict(c, business):
    cell = index_service.get_cell(c, CAT, AREA)
    return cell, index.verdict_for(cell, business)


def test_on_screen_recommended_firm():
    c = _conn()
    cell, v = _cell_verdict(c, "Liffey & Quay Accountants (DEMO)")
    p = report_service.on_screen(c, "Liffey & Quay Accountants (DEMO)", CAT, AREA, v, cell)
    assert p["stat"]                       # non-empty mention-rate stat
    assert len(p["key_findings"]) >= 1


def test_on_screen_invisible_firm():
    c = _conn()
    cell, v = _cell_verdict(c, "Northside Accounting Co (DEMO)")
    assert v["state"] == index.INVISIBLE
    p = report_service.on_screen(c, "Northside Accounting Co (DEMO)", CAT, AREA, v, cell)
    assert "0 ai recommendations" in p["stat"].lower()
    assert p["competitors"]                # recommended_instead surfaced


def test_report_data_shape_and_internal_consistency():
    c = _conn()
    d = report_service.report_data(c, "Grafton Tax Advisers (DEMO)", CAT, AREA)
    assert d is not None
    assert d.client == "Grafton Tax Advisers (DEMO)" and d.market == CAT and d.area == AREA
    assert len(d.competitor_counts) >= 1
    assert d.total_checks == sum(r.checks for r in d.sample_rows) >= 1
    assert d.recommended_actions          # fixed generic omission line (not tailored)


def test_report_data_unmapped_returns_none():
    c = _conn()
    assert report_service.report_data(c, "Whoever", "Dentists", "Cork") is None


def test_build_docx_valid_carries_disclaimer_no_overclaims():
    c = _conn()
    blob = report_service.build_docx(c, "Liffey & Quay Accountants (DEMO)", CAT, AREA)
    assert blob and blob[:2] == b"PK"      # zip magic -> a real .docx
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        ET.fromstring(z.read("word/document.xml"))     # valid OOXML
        text = z.read("word/document.xml").decode("utf-8").lower()
    assert "not a guarantee of future ranking" in text
    for banned in ["guaranteed ranking", "we guarantee", "guaranteed results", "ai-powered"]:
        assert banned not in text
    # recommendation-based framing, same as the on-screen stat; never "checks"/"queries"/"mention rate"
    assert "captured ai recommendations" in text
    assert "checks" not in text and "queries" not in text and "mention rate" not in text
    # section retitled; data-only scope sentence retained (no tailored advice)
    assert "scope of this report" in text and "recommended actions" not in text
