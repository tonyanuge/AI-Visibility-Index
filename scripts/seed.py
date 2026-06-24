"""Load SYNTHETIC demo data (two verticals) so the app runs and smoke-tests green.
All businesses are clearly fake. Replace with real captures via ingest.manual."""
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from avix.store import db
from avix.store import repository as repo
from avix.core.models import Mention

PHYSIO = "Physiotherapists", "Dublin"
ESTATE = "Estate Agents", "Dublin"

def seed(conn):
    rows = [
        # (business, cat, area, engine, archetype, rank, accuracy, sentiment)
        ("Riverside Physio (DEMO)", *PHYSIO, "ChatGPT", "Discovery", 1, "Correct", "Positive"),
        ("Riverside Physio (DEMO)", *PHYSIO, "Gemini", "Shortlist", 2, "Wrong", "Positive"),
        ("Riverside Physio (DEMO)", *PHYSIO, "Perplexity", "Discovery", 1, "Correct", "Positive"),
        ("Riverside Physio (DEMO)", *PHYSIO, "ChatGPT", "Attribute", 1, "Correct", "Positive"),
        ("Riverside Physio (DEMO)", *PHYSIO, "Gemini", "Need-based", 2, "Correct", "Neutral"),
        ("City Sports Clinic (DEMO)", *PHYSIO, "ChatGPT", "Discovery", 2, "N/A", "Neutral"),
        ("City Sports Clinic (DEMO)", *PHYSIO, "Perplexity", "Need-based", 1, "Correct", "Positive"),
        ("Quayside Physio (DEMO)", *PHYSIO, "Gemini", "Shortlist", 4, "Partial", "Neutral"),
        ("Harbour Estates (DEMO)", *ESTATE, "ChatGPT", "Discovery", 1, "Correct", "Positive"),
        ("Harbour Estates (DEMO)", *ESTATE, "Perplexity", "Shortlist", 2, "Correct", "Neutral"),
    ]
    for b, cat, area, eng, arch, rank, acc, sent in rows:
        repo.add_mention(conn, Mention(business=b, category=cat, area=area, engine=eng,
            archetype=arch, rank=rank, accuracy=acc, sentiment=sent, source="Demo",
            prompt_text="(demo)", date="2026-06-24"))
        repo.add_business(conn, b, cat, area)
    # roster entries that were NEVER mentioned -> these are the INVISIBLE businesses
    for inv in ["Northside Physiotherapy (DEMO)", "Docklands Physio (DEMO)"]:
        repo.add_business(conn, inv, *PHYSIO)
    repo.add_business(conn, "Liffey Lettings (DEMO)", *ESTATE)

if __name__ == "__main__":
    with db.connect() as c:
        seed(c)
        print("Seeded demo data.")
