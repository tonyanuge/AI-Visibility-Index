"""Import the REAL Dublin 6 / Ranelagh estate-agent market from captured CSVs.

The CSVs live under data/imports/ (gitignored) and hold real firm names + captures — they are
NEVER committed, and this script embeds no firm names. Run after placing the files:

  PYTHONPATH=src python scripts/seed_dublin6.py

Forces category="Estate Agents", area="Dublin 6 / Ranelagh", source="Manual" (a REAL source —
NOT "Demo"), so this market gets real, evidence-backed verdicts (roster-restricted) rather than
the synthetic-demo guardrail. Prints a verification summary to eyeball before trusting it."""
import csv
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from avix.store import db
from avix.store import repository as repo
from avix.core.models import Mention

ROOT = Path(__file__).resolve().parents[1]
CAPTURES = ROOT / "data" / "imports" / "captures.csv"
ROSTER = ROOT / "data" / "imports" / "roster.csv"
ALIASES = ROOT / "data" / "imports" / "aliases.csv"   # gitignored: variant -> canonical roster name

CATEGORY = "Estate Agents"
AREA = "Dublin 6 / Ranelagh"
SOURCE = "Manual"
EXCLUDE = "__EXCLUDE__"   # sentinel canonical -> drop from scoring/roster (no firm names in code)


def _load_aliases() -> dict:
    if not ALIASES.exists():
        return {}
    with open(ALIASES, newline="", encoding="utf-8-sig") as f:
        return {(r.get("variant") or "").strip(): (r.get("canonical") or "").strip()
                for r in csv.DictReader(f) if (r.get("variant") or "").strip()}


def _canonical(name: str, aliases: dict) -> str | None:
    """Map a captured/roster name to its canonical roster name. None => drop (excluded)."""
    name = (name or "").strip()
    canon = aliases.get(name, name)
    return None if canon == EXCLUDE else canon


def _rank(v):
    try:
        return int(v) if str(v).strip() not in ("", "-", "None") else None
    except (TypeError, ValueError):
        return None


def _row_to_mention(row: dict) -> Mention:
    return Mention(
        business=(row.get("business_name") or "").strip(),
        category=CATEGORY, area=AREA, source=SOURCE,       # forced
        engine=(row.get("engine") or "").strip(),
        archetype=(row.get("archetype") or "Discovery").strip(),
        rank=_rank(row.get("rank")),                        # blank -> None, still counts as presence
        accuracy="N/A", sentiment="Neutral",
        prompt_text=(row.get("prompt") or "").strip(),
        date=(row.get("capture_date") or "").strip(),
    )


def seed(conn) -> dict:
    aliases = _load_aliases()
    imported = excluded = 0
    with open(CAPTURES, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            m = _row_to_mention(row)
            if not m.business:
                continue
            canon = _canonical(m.business, aliases)   # variant -> canonical roster name
            if canon is None:                          # excluded (e.g. a directory, not an agency)
                excluded += 1
                continue
            m = replace(m, business=canon)             # frozen Mention -> new instance
            repo.add_mention(conn, m)
            repo.add_business(conn, canon, CATEGORY, AREA)
            imported += 1
    roster = 0
    with open(ROSTER, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            canon = _canonical(row.get("business_name"), aliases)
            if canon:
                repo.add_business(conn, canon, CATEGORY, AREA)  # 0-mention firms -> INVISIBLE
                roster += 1
    return {"imported": imported, "excluded": excluded, "roster_rows": roster}


def _summary(conn) -> str:
    from avix.service import index_service
    ms = repo.mentions_for_cell(conn, CATEGORY, AREA)
    cell = index_service.get_cell(conn, CATEGORY, AREA)
    firms = {m.business for m in ms}
    prompts = {m.prompt_text for m in ms}
    engines = sorted({m.engine for m in ms})
    counts = {}
    for m in ms:
        counts[m.business] = counts.get(m.business, 0) + 1
    top = max(counts.items(), key=lambda kv: kv[1]) if counts else ("-", 0)
    roster = repo.roster(conn, CATEGORY, AREA)
    zero = [r for r in roster if r not in firms]
    out = [
        f"  mention rows imported : {len(ms)}",
        f"  distinct firms named  : {len(firms)}",
        f"  distinct prompts      : {len(prompts)}",
        f"  distinct engines      : {', '.join(engines)}",
        f"  top firm + count      : {top[0]}  ({top[1]})",
        f"  roster size           : {len(roster)}",
        f"  roster firms w/ 0 mentions : {len(zero)}",
    ]
    if cell and cell.scores:
        out.append(f"  top scored business   : {cell.scores[0].business}  "
                   f"(status {cell.scores[0].status})")
    return "\n".join(out)


if __name__ == "__main__":
    if not (CAPTURES.exists() and ROSTER.exists()):
        print(f"Missing CSVs. Expected:\n  {CAPTURES}\n  {ROSTER}")
        sys.exit(1)
    with db.connect() as c:
        res = seed(c)
        print(f"Seeded REAL market '{CATEGORY} — {AREA}': "
              f"{res['imported']} mentions, {res['roster_rows']} roster rows.")
        print("Verification summary:")
        print(_summary(c))
