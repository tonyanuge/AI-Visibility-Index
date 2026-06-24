"""Application layer for the Index. The API/UI call ONLY this, never the store directly."""
from .. import config
from ..core import scoring
from ..store import repository as repo
from ..audit import audit_log

def get_cell(conn, category, area):
    mentions = repo.mentions_for_cell(conn, category, area)
    if not mentions:
        return None
    roster = repo.roster(conn, category, area)
    cell = scoring.score_cell(
        mentions, roster, category, area,
        viz=config.visibility_archetypes(),
        thresholds=config.load_scoring().get("status_thresholds", {}),
    )
    audit_log.record(conn, "index.viewed", f"{category}|{area}")
    return cell

def list_cells(conn):
    return repo.list_cells(conn)
