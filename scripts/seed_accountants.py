"""Load SYNTHETIC demo capture data for the "Accountants / Chartered Accountants" — "Dublin"
market so the public journey (search -> verdict -> report) returns a real result.

All businesses are clearly fake (suffixed "(DEMO)"). This is NOT a real client's data and
must not be treated as a publishable Index. Replace with real captures via ingest.manual."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from avix.store import db
from avix.store import repository as repo
from avix.core.models import Mention

MARKET = ("Accountants / Chartered Accountants", "Dublin")
DATE = "2026-06-26"


def seed(conn):
    # (business, engine, archetype, rank, accuracy, sentiment)
    rows = [
        # Top firm -> 5 captured recommendations -> "Strong" -> STRONG verdict
        ("Liffey & Quay Accountants (DEMO)", "ChatGPT", "Discovery", 1, "Correct", "Positive"),
        ("Liffey & Quay Accountants (DEMO)", "Gemini", "Shortlist", 1, "Correct", "Positive"),
        ("Liffey & Quay Accountants (DEMO)", "Perplexity", "Discovery", 2, "Correct", "Neutral"),
        ("Liffey & Quay Accountants (DEMO)", "ChatGPT", "Need-based", 1, "Correct", "Positive"),
        ("Liffey & Quay Accountants (DEMO)", "Gemini", "Attribute", 2, "Partial", "Neutral"),
        # Mid firm -> 3 recommendations -> "Visible" -> VISIBLE_BEATEN verdict
        ("Grafton Tax Advisers (DEMO)", "ChatGPT", "Discovery", 3, "Correct", "Neutral"),
        ("Grafton Tax Advisers (DEMO)", "Perplexity", "Shortlist", 2, "Wrong", "Neutral"),
        ("Grafton Tax Advisers (DEMO)", "Gemini", "Need-based", 4, "Correct", "Positive"),
        # Lower firms -> a couple of recommendations each
        ("Docklands Chartered (DEMO)", "ChatGPT", "Shortlist", 4, "N/A", "Neutral"),
        ("Docklands Chartered (DEMO)", "Perplexity", "Discovery", 3, "Correct", "Neutral"),
        ("Sandyford Accounting (DEMO)", "Gemini", "Discovery", 5, "Partial", "Neutral"),
    ]
    for business, engine, archetype, rank, accuracy, sentiment in rows:
        repo.add_mention(conn, Mention(
            business=business, category=MARKET[0], area=MARKET[1], engine=engine,
            archetype=archetype, rank=rank, accuracy=accuracy, sentiment=sentiment,
            source="Demo", prompt_text="(demo)", date=DATE))
        repo.add_business(conn, business, *MARKET)
    # roster firms that were NEVER recommended -> these are the INVISIBLE businesses
    for invisible in ["Northside Accounting Co (DEMO)", "Rathmines Tax & Co (DEMO)"]:
        repo.add_business(conn, invisible, *MARKET)


if __name__ == "__main__":
    with db.connect() as c:
        seed(c)
        print("Seeded synthetic Accountants — Dublin demo data.")
