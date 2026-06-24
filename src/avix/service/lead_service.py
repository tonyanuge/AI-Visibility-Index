"""Lead capture. The email lives in the leads table (the product), never in the audit trail."""
from datetime import datetime, timezone
from ..core.models import Lead
from ..store import repository as repo
from ..audit import audit_log

def capture(conn, business, email, category, area, verdict_state) -> dict:
    lead = Lead(business=business, email=email, category=category, area=area,
                verdict=verdict_state,
                ts=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    repo.add_lead(conn, lead)
    audit_log.record(conn, "lead.captured", f"{category}|{area}|{verdict_state}")
    return {"ok": True}

def export_rows(conn):
    return repo.all_leads(conn)
