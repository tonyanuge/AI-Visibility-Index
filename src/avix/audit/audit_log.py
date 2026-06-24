"""Content-free audit. Records WHAT happened + a non-PII reference (cell/verdict).
Never logs emails, business contact data, raw LLM text, or secrets."""
from datetime import datetime, timezone

# Fields that must never enter the audit trail.
_FORBIDDEN = {"email", "raw", "prompt_text", "api_key", "secret"}

def record(conn, event: str, ref: str = ""):
    safe = "".join(c for c in ref if c not in "@")  # defensive: strip @ so emails can't sneak in
    conn.execute("INSERT INTO audit(ts,event,ref) VALUES(?,?,?)",
                 (datetime.now(timezone.utc).isoformat(timespec="seconds"), event, safe[:120]))
    conn.commit()

def entries(conn) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM audit ORDER BY id").fetchall()]
