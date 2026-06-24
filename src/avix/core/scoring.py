"""Validated scoring engine — mirrors the AI Mystery Shopping tracker workbook exactly.

Status keys off TOTAL mentions (not visibility mentions). The visibility exclusion is
driven by a config-supplied set of archetypes, never a hard-coded 'Vetting' literal.
All ratios are null-safe (no division errors; None on empty denominators).
"""
from .models import Mention, BusinessScore, IndexCell

def _for(mentions, business):
    return [m for m in mentions if m.business == business]

def total_mentions(mentions, business) -> int:
    return len(_for(mentions, business))

def visibility_mentions(mentions, business, viz: set[str]) -> int:
    return len([m for m in _for(mentions, business) if m.archetype in viz])

def share_of_recs(mentions, business, viz: set[str]) -> float:
    denom = len([m for m in mentions if m.archetype in viz])
    if denom == 0:
        return 0.0
    return visibility_mentions(mentions, business, viz) / denom

def avg_rank(mentions, business, viz: set[str]):
    ranks = [m.rank for m in _for(mentions, business)
             if m.archetype in viz and m.rank is not None]
    return sum(ranks) / len(ranks) if ranks else None

def accuracy_pct(mentions, business):
    rows = _for(mentions, business)
    c = sum(1 for m in rows if m.accuracy == "Correct")
    w = sum(1 for m in rows if m.accuracy == "Wrong")
    p = sum(1 for m in rows if m.accuracy == "Partial")
    denom = c + w + p
    return (c / denom) if denom else None

def sentiment_counts(mentions, business):
    rows = _for(mentions, business)
    return (
        sum(1 for m in rows if m.sentiment == "Positive"),
        sum(1 for m in rows if m.sentiment == "Neutral"),
        sum(1 for m in rows if m.sentiment == "Negative"),
    )

def status(total: int, thresholds: dict) -> str:
    if total == 0:
        return "INVISIBLE"
    if total >= thresholds.get("strong", 5):
        return "Strong"
    if total >= thresholds.get("visible", 2):
        return "Visible"
    return "Barely"

def score_business(mentions, business, viz, thresholds) -> BusinessScore:
    total = total_mentions(mentions, business)
    pos, neu, neg = sentiment_counts(mentions, business)
    return BusinessScore(
        business=business,
        total_mentions=total,
        visibility_mentions=visibility_mentions(mentions, business, viz),
        share_of_recs=share_of_recs(mentions, business, viz),
        avg_rank=avg_rank(mentions, business, viz),
        accuracy_pct=accuracy_pct(mentions, business),
        pos=pos, neu=neu, neg=neg,
        status=status(total, thresholds),
    )

def score_cell(mentions, roster, category, area, viz, thresholds) -> IndexCell:
    """roster = every known business in the cell (incl. ones never mentioned)."""
    named = {m.business for m in mentions}
    universe = sorted(set(roster) | named)
    scores = [score_business(mentions, b, viz, thresholds) for b in universe]
    scores.sort(key=lambda s: (s.share_of_recs, s.total_mentions), reverse=True)

    total_in_roster = len(universe)
    invisible = [s for s in scores if s.total_mentions == 0]
    correct = sum(1 for m in mentions if m.accuracy == "Correct")
    wrong = sum(1 for m in mentions if m.accuracy == "Wrong")
    partial = sum(1 for m in mentions if m.accuracy == "Partial")
    acc_den = correct + wrong + partial
    summary = {
        "businesses_in_roster": total_in_roster,
        "ever_recommended": sum(1 for s in scores if s.total_mentions > 0),
        "invisible_count": len(invisible),
        "pct_invisible": round(len(invisible) / total_in_roster, 4) if total_in_roster else 0.0,
        "overall_accuracy": round(correct / acc_den, 4) if acc_den else None,
        "total_recommendation_rows": len(mentions),
    }
    return IndexCell(category=category, area=area, scores=scores, summary=summary)
