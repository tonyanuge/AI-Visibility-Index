"""Pure data model for the branded report renderer. No I/O, no findings logic.

The analyst supplies narrative + structured evidence; the builder renders it. Headline
figures (totals, mention rate) are DERIVED here from the structured data so the cover
stat, key findings, and verdict table can never disagree (requirement R7)."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CompetitorCount:
    """One competitor row: how often it was recommended ahead, and on which assistants."""
    firm: str
    times_ahead: int
    assistants: str = ""


@dataclass(frozen=True)
class SampleRow:
    """One row of the What-We-Tested structure (a search theme + its captures)."""
    theme: str
    prompt: str
    assistants: str
    checks: int


@dataclass
class ReportData:
    # identity / cover
    client: str
    market: str
    area: str
    snapshot_date: str
    prepared_by: str
    overall_verdict_label: str          # e.g. "Weak / inconsistent AI visibility"
    overall_verdict_state: str          # e.g. "WEAK_INCONSISTENT" (keys into verdict_colors)
    # structured evidence
    verdicts: dict                      # {section label: STATE}, ordered for the verdict table
    competitor_counts: list             # list[CompetitorCount]
    sample_rows: list                   # list[SampleRow] -> total checks = sum(.checks)
    mentioned_count: int                # times the client was recommended
    invisible_count: int                # rows judged invisible
    beaten_count: int                   # rows judged visible-but-beaten
    # narrative (analyst-written)
    executive_summary: list             # list[str] paragraphs
    what_we_tested_prompts: list        # list[str]
    what_we_tested_assistants: list     # list[str]
    key_findings: list                  # list[str] bullets
    what_this_means: list               # list[str] paragraphs
    recommended_actions: list           # list[str] bullets

    # ---- derived (single source of truth = the structured data) ----
    @property
    def total_checks(self) -> int:
        return sum(r.checks for r in self.sample_rows)

    @property
    def mention_rate_pct(self) -> int:
        total = self.total_checks
        return round(100 * self.mentioned_count / total) if total else 0

    @classmethod
    def from_dict(cls, d: dict) -> "ReportData":
        return cls(
            client=d["client"],
            market=d["market"],
            area=d["area"],
            snapshot_date=d["snapshot_date"],
            prepared_by=d["prepared_by"],
            overall_verdict_label=d["overall_verdict_label"],
            overall_verdict_state=d["overall_verdict_state"],
            verdicts=dict(d.get("verdicts", {})),
            competitor_counts=[CompetitorCount(**c) for c in d.get("competitor_counts", [])],
            sample_rows=[SampleRow(**r) for r in d.get("sample_rows", [])],
            mentioned_count=int(d.get("mentioned_count", 0)),
            invisible_count=int(d.get("invisible_count", 0)),
            beaten_count=int(d.get("beaten_count", 0)),
            executive_summary=list(d.get("executive_summary", [])),
            what_we_tested_prompts=list(d.get("what_we_tested_prompts", [])),
            what_we_tested_assistants=list(d.get("what_we_tested_assistants", [])),
            key_findings=list(d.get("key_findings", [])),
            what_this_means=list(d.get("what_this_means", [])),
            recommended_actions=list(d.get("recommended_actions", [])),
        )
