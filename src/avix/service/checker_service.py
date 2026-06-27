"""Public checker: business name + cell -> verdict (Invisible / Beaten / Strong / Not covered).

Two separated guardrail behaviours (server-side):
  - ROSTER RESTRICTION applies to ALL mapped markets (real + demo): only roster firms get a
    verdict; an off-roster name returns an honest no-verdict note (no competitors).
  - SAMPLE banner is DEMO-only; REAL markets instead carry a dated-snapshot provenance note."""
from ..core import index
from ..audit import audit_log
from . import index_service, sample_guard


def check(conn, business, category, area) -> dict:
    cell = index_service.get_cell(conn, category, area)
    demo = sample_guard.is_guarded(conn, category, area)   # all-demo-source cell -> SAMPLE banner
    mapped = cell is not None                              # has captured data -> roster restriction

    # Roster restriction (all mapped markets): an off-roster name never gets a fabricated verdict.
    if mapped and not sample_guard.in_roster(conn, category, area, business):
        event = "checker.not_in_sample" if demo else "checker.not_in_dataset"
        audit_log.record(conn, event, f"{category}|{area}")   # content-free: cell only, never the name
        examples = sample_guard.roster_names(conn, category, area)
        return (sample_guard.not_in_sample(business, examples) if demo
                else sample_guard.not_in_dataset(business, examples))

    verdict = index.verdict_for(cell, business)
    audit_log.record(conn, "checker.run", f"{category}|{area}|{verdict['state']}")
    if demo:                                  # DEMO market -> SAMPLE banner
        verdict["sample"] = True
        verdict["sample_banner"] = sample_guard.banner()
    elif mapped:                              # REAL market -> dated-snapshot provenance note
        verdict["provenance"] = sample_guard.provenance(conn, category, area)
    return verdict
