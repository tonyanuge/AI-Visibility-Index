"""Turn a scored cell + verdict into (a) the on-screen result payload and (b) a ReportData
for the branded .docx — by REUSING the scoring engine, verdict logic, and report renderer.

Strictly deterministic and DATA-DERIVED: every sentence states what the captured data shows.
No advice, no predictions, no tailored fix-recommendations (that would cross into automated
consulting). The auto-report's recommended-actions slot carries a fixed generic omission line,
not tailored advice. The dated-snapshot disclaimer + "not a guarantee of future ranking"
sentence are carried verbatim by the report renderer (config/report.yaml)."""
from datetime import date

from ..core import index
from ..store import repository as repo
from ..report import ReportData, CompetitorCount, SampleRow, build_report, load_branding
from . import index_service, sample_guard

# Fixed, generic, non-tailored line for the auto-report's recommended-actions slot.
_AUTO_ACTIONS = ["This automated summary states what the captured data shows; "
                 "it does not include tailored recommendations."]

_OVERALL_LABEL = {
    index.INVISIBLE: "Invisible",
    index.BEATEN: "Visible but beaten",
    index.STRONG: "Top recommendation",
    index.NOT_COVERED: "Not covered",
}


def _mention_stat(cell, verdict: dict) -> str:
    """Share-of-recommendations / count + % invisible — wording approved in the plan."""
    pct_inv = round(cell.summary.get("pct_invisible", 0) * 100)
    state = verdict["state"]
    if state == index.INVISIBLE:
        return f"0 AI recommendations in this market · {pct_inv}% of local firms are never recommended."
    share = round((verdict.get("share") or 0) * 100)
    if state == index.STRONG:
        return f"{share}% share of AI recommendations · top-ranked in the captured answers."
    if state == index.BEATEN:
        return f"{share}% share of AI recommendations · ranked #{verdict.get('rank')}."
    return ""


def _key_findings(cell, verdict: dict) -> list:
    s = cell.summary
    state = verdict["state"]
    out = []
    if state == index.INVISIBLE:
        out.append("Never recommended in the captured AI answers for this market.")
        if verdict.get("recommended_instead"):
            out.append("AI recommended instead: " + ", ".join(verdict["recommended_instead"]) + ".")
    elif state == index.BEATEN:
        out.append(f"Recommended, but ranked #{verdict.get('rank')} by share of AI recommendations.")
        if verdict.get("ahead_of_you"):
            out.append("Recommended ahead of it: " + ", ".join(verdict["ahead_of_you"]) + ".")
    elif state == index.STRONG:
        out.append("The top AI recommendation in the captured answers for this market.")
    out.append(f"{s.get('ever_recommended', 0)} of {s.get('businesses_in_roster', 0)} local firms "
               f"are recommended at least once; {s.get('invisible_count', 0)} are never recommended.")
    if s.get("overall_accuracy") is not None:
        out.append(f"Where AI stated facts about firms, {round(s['overall_accuracy'] * 100)}% "
                   f"were captured as correct.")
    return out


def on_screen(conn, business, category, area, verdict: dict, cell=None) -> dict:
    """Payload for the browser result: mention stat + key findings + competitors recommended."""
    cell = cell if cell is not None else index_service.get_cell(conn, category, area)
    if cell is None:
        return {"stat": "", "key_findings": [], "competitors": []}
    competitors = verdict.get("recommended_instead") or verdict.get("ahead_of_you") or []
    payload = {
        "stat": _mention_stat(cell, verdict),
        "key_findings": _key_findings(cell, verdict),
        "competitors": competitors,
    }
    if sample_guard.is_guarded(conn, category, area):       # DEMO -> SAMPLE banner
        payload["sample"] = True
        payload["sample_banner"] = sample_guard.banner()
    elif sample_guard.is_mapped(conn, category, area):      # REAL -> provenance note
        payload["provenance"] = sample_guard.provenance(conn, category, area)
    return payload


def _competitor_counts(mentions, cell, business) -> list:
    engines_by_firm = {}
    for m in mentions:
        engines_by_firm.setdefault(m.business, set()).add(m.engine)
    out = []
    for sc in cell.scores:  # sorted best-first
        if sc.total_mentions <= 0:
            continue
        if sc.business.strip().lower() == business.strip().lower():
            continue
        out.append(CompetitorCount(firm=sc.business, times_ahead=sc.total_mentions,
                                   assistants="; ".join(sorted(engines_by_firm.get(sc.business, [])))))
    return out


def _sample_rows(mentions) -> list:
    """Captured-answer structure, grouped by archetype (theme) -> count."""
    by_theme = {}
    engines_by_theme = {}
    for m in mentions:
        by_theme[m.archetype] = by_theme.get(m.archetype, 0) + 1
        engines_by_theme.setdefault(m.archetype, set()).add(m.engine)
    return [SampleRow(theme=theme, prompt=f"{theme}-style buying-intent prompts",
                      assistants="; ".join(sorted(engines_by_theme[theme])), checks=n)
            for theme, n in sorted(by_theme.items(), key=lambda kv: kv[1], reverse=True)]


def report_data(conn, business, category, area) -> ReportData | None:
    """Map the scored cell + verdict into a ReportData (None if the market isn't mapped)."""
    cell = index_service.get_cell(conn, category, area)
    if cell is None:
        return None
    # Roster restriction (all mapped markets): never generate a report for an out-of-roster name —
    # a firm we didn't capture must not receive a fabricated report. Returning None -> the API 404s.
    demo = sample_guard.is_guarded(conn, category, area)
    if not sample_guard.in_roster(conn, category, area, business):
        return None
    verdict = index.verdict_for(cell, business)
    mentions = repo.mentions_for_cell(conn, category, area)
    s = cell.summary
    state = verdict["state"]

    snapshot = max((m.date for m in mentions if m.date), default="") or date.today().isoformat()
    target_mentions = next((sc.total_mentions for sc in cell.scores
                            if sc.business.strip().lower() == business.strip().lower()), 0)
    beaten = sum(1 for sc in cell.scores if sc.total_mentions > 0 and sc.status != "Strong")

    branding = load_branding()
    data_kind = "demo data" if demo else "data"
    exec_summary = [
        f'This automated summary reports what AI assistants returned for "{business}" in '
        f'{category} — {area}, from the captured {data_kind} on {snapshot}.',
        _mention_stat(cell, verdict) or "This market has captured AI recommendation data.",
    ]
    what_this_means = [
        "These figures describe what the captured AI answers showed for this market on the "
        "snapshot date. AI answers vary by date, model, location, browsing context, and prompt wording.",
    ]
    if not demo:   # REAL market: lead with the dated-snapshot provenance note
        what_this_means.insert(0, sample_guard.provenance(conn, category, area))
    return ReportData(
        client=business, market=category, area=area, snapshot_date=snapshot,
        prepared_by=branding.get("company", ""),
        overall_verdict_label=_OVERALL_LABEL.get(state, state),
        overall_verdict_state=state if state != index.BEATEN else "VISIBLE_BEATEN",
        verdicts={f"{category} — {area}": state},
        competitor_counts=_competitor_counts(mentions, cell, business),
        sample_rows=_sample_rows(mentions),
        mentioned_count=target_mentions,
        invisible_count=s.get("invisible_count", 0),
        beaten_count=beaten,
        executive_summary=exec_summary,
        what_we_tested_prompts=sorted({f"{m.archetype}-style buying-intent prompts" for m in mentions}),
        what_we_tested_assistants=sorted({m.engine for m in mentions}),
        key_findings=_key_findings(cell, verdict),
        what_this_means=what_this_means,
        recommended_actions=_AUTO_ACTIONS,
        sample_banner=sample_guard.banner() if demo else "",   # SAMPLE strip on demo reports only
    )


def build_docx(conn, business, category, area) -> bytes | None:
    """Full pipeline: scored cell -> ReportData -> branded .docx bytes (in-memory; None if unmapped)."""
    data = report_data(conn, business, category, area)
    if data is None:
        return None
    return build_report(data, load_branding())
