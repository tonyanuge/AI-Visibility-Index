"""Public checker: business name + cell -> verdict (Invisible / Beaten / Strong / Not covered).

Sample-data guardrail (Layer 1, server-side): in a guarded (demo/ambiguous) cell, a name that
is not in the seeded roster returns a neutral NOT_IN_SAMPLE note — never a fabricated verdict
about a real business. Roster names still get a verdict, tagged sample + banner."""
from ..core import index
from ..audit import audit_log
from . import index_service, sample_guard


def check(conn, business, category, area) -> dict:
    cell = index_service.get_cell(conn, category, area)
    guarded = sample_guard.is_guarded(conn, category, area)

    if guarded and not sample_guard.in_roster(conn, category, area, business):
        # content-free: log the cell only, never the searched (possibly real) business name
        audit_log.record(conn, "checker.not_in_sample", f"{category}|{area}")
        return sample_guard.not_in_sample(business, sample_guard.roster_names(conn, category, area))

    verdict = index.verdict_for(cell, business)
    # content-free: log the cell + verdict state only, never the business contact data
    audit_log.record(conn, "checker.run", f"{category}|{area}|{verdict['state']}")
    if guarded:
        verdict["sample"] = True
        verdict["sample_banner"] = sample_guard.banner()
    return verdict
