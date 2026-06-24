"""Pure domain models. No I/O."""
from dataclasses import dataclass, field
from typing import Optional

ACCURACY = {"Correct", "Wrong", "Partial", "N/A"}
SENTIMENT = {"Positive", "Neutral", "Negative"}

@dataclass(frozen=True)
class Mention:
    business: str
    category: str
    area: str
    engine: str
    archetype: str
    rank: Optional[int] = None
    accuracy: str = "N/A"
    sentiment: str = "Neutral"
    source: str = "Unclear"
    prompt_text: str = ""
    date: str = ""

@dataclass
class BusinessScore:
    business: str
    total_mentions: int
    visibility_mentions: int
    share_of_recs: float
    avg_rank: Optional[float]
    accuracy_pct: Optional[float]
    pos: int
    neu: int
    neg: int
    status: str

@dataclass
class IndexCell:
    category: str
    area: str
    scores: list[BusinessScore] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

@dataclass
class Lead:
    business: str
    email: str
    category: str
    area: str
    verdict: str
    ts: str = ""
