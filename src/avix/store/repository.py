from ..core.models import Mention, Lead

def add_business(conn, name, category, area):
    conn.execute("INSERT OR IGNORE INTO businesses(name,category,area) VALUES(?,?,?)",
                 (name, category, area))
    conn.commit()

def roster(conn, category, area) -> list[str]:
    rows = conn.execute("SELECT name FROM businesses WHERE category=? AND area=?",
                        (category, area)).fetchall()
    return [r["name"] for r in rows]

def add_mention(conn, m: Mention):
    conn.execute(
        """INSERT INTO mentions(date,area,category,engine,archetype,business,rank,
           accuracy,sentiment,source,prompt_text) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (m.date, m.area, m.category, m.engine, m.archetype, m.business, m.rank,
         m.accuracy, m.sentiment, m.source, m.prompt_text))
    conn.commit()

def mentions_for_cell(conn, category, area) -> list[Mention]:
    rows = conn.execute("SELECT * FROM mentions WHERE category=? AND area=?",
                        (category, area)).fetchall()
    return [Mention(business=r["business"], category=r["category"], area=r["area"],
                    engine=r["engine"], archetype=r["archetype"], rank=r["rank"],
                    accuracy=r["accuracy"], sentiment=r["sentiment"], source=r["source"],
                    prompt_text=r["prompt_text"], date=r["date"]) for r in rows]

def list_cells(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT DISTINCT category, area FROM mentions ORDER BY category, area").fetchall()
    return [{"category": r["category"], "area": r["area"]} for r in rows]

def add_lead(conn, lead: Lead):
    conn.execute("INSERT INTO leads(ts,business,email,category,area,verdict) VALUES(?,?,?,?,?,?)",
                 (lead.ts, lead.business, lead.email, lead.category, lead.area, lead.verdict))
    conn.commit()

def all_leads(conn) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM leads ORDER BY id DESC").fetchall()]
