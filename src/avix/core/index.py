"""Verdict logic for the public checker — the four states, derived from a scored cell."""
from .models import IndexCell

INVISIBLE, BEATEN, STRONG, NOT_COVERED = "INVISIBLE", "VISIBLE_BEATEN", "STRONG", "NOT_COVERED"

def verdict_for(cell: IndexCell | None, business: str, top_n: int = 3) -> dict:
    if cell is None or not cell.scores:
        return {"state": NOT_COVERED, "business": business,
                "message": "This category/area has not been mapped yet."}

    competitors_ahead = []
    target = None
    for s in cell.scores:  # already sorted best-first
        if s.business.strip().lower() == business.strip().lower():
            target = s
            break
        if s.total_mentions > 0:
            competitors_ahead.append(s.business)

    if target is None or target.total_mentions == 0:
        return {
            "state": INVISIBLE, "business": business,
            "recommended_instead": [s.business for s in cell.scores if s.total_mentions > 0][:top_n],
            "message": "AI never recommended you in this market.",
        }

    rank_position = [s.business for s in cell.scores if s.total_mentions > 0].index(target.business) + 1
    if rank_position == 1 and target.status == "Strong":
        return {"state": STRONG, "business": business, "share": target.share_of_recs,
                "message": "You are the top AI recommendation right now."}
    return {
        "state": BEATEN, "business": business,
        "rank": rank_position, "share": round(target.share_of_recs, 4),
        "ahead_of_you": competitors_ahead[:top_n],
        "accuracy_pct": target.accuracy_pct,
        "message": "You are recommended, but behind competitors.",
    }
