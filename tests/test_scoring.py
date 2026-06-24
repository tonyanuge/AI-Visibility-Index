import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from avix.core.models import Mention
from avix.core import scoring

VIZ = {"Discovery", "Shortlist", "Need-based", "Attribute"}
TH = {"strong": 5, "visible": 2}

def m(b, arch="Discovery", rank=1, acc="N/A", sent="Neutral"):
    return Mention(business=b, category="C", area="A", engine="ChatGPT",
                   archetype=arch, rank=rank, accuracy=acc, sentiment=sent)

def test_invisible_is_null_safe():
    ms = [m("A")]
    assert scoring.total_mentions(ms, "Ghost") == 0
    assert scoring.avg_rank(ms, "Ghost", VIZ) is None
    assert scoring.accuracy_pct(ms, "Ghost") is None
    assert scoring.share_of_recs(ms, "Ghost", VIZ) == 0.0
    assert scoring.status(0, TH) == "INVISIBLE"

def test_vetting_excluded_from_visibility():
    ms = [m("A", "Discovery"), m("A", "Vetting", rank=9)]
    assert scoring.visibility_mentions(ms, "A", VIZ) == 1
    assert scoring.avg_rank(ms, "A", VIZ) == 1  # vetting rank ignored

def test_status_thresholds_config_driven():
    assert scoring.status(5, {"strong": 5, "visible": 2}) == "Strong"
    assert scoring.status(5, {"strong": 9, "visible": 2}) == "Visible"  # flips with config

def test_accuracy_ratio():
    ms = [m("A", acc="Correct"), m("A", acc="Wrong"), m("A", acc="N/A")]
    assert scoring.accuracy_pct(ms, "A") == 0.5

def test_status_keys_off_total_not_visibility():
    ms = [m("A", "Vetting") for _ in range(3)]  # 3 total, 0 visibility
    s = scoring.score_business(ms, "A", VIZ, TH)
    assert s.visibility_mentions == 0 and s.status == "Visible"  # total=3 -> Visible
