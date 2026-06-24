"""Public checker: business name + cell -> verdict (Invisible / Beaten / Strong / Not covered)."""
from ..core import index
from ..audit import audit_log
from . import index_service

def check(conn, business, category, area) -> dict:
    cell = index_service.get_cell(conn, category, area)
    verdict = index.verdict_for(cell, business)
    # content-free: log the cell + verdict state only, never the business contact data
    audit_log.record(conn, "checker.run", f"{category}|{area}|{verdict['state']}")
    return verdict
