"""Import your real captures into the app.
Usage:
  python scripts/import_tracker.py path/to/ai_mystery_shopping_tracker.xlsx
  python scripts/import_tracker.py path/to/run_log.csv
"""
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from avix.store import db
from avix.ingest import manual

def main(path):
    p = Path(path)
    with db.connect() as conn:
        if p.suffix.lower() in (".xlsx", ".xlsm"):
            n = manual.import_tracker_xlsx(conn, p)
        else:
            n = manual.import_csv(conn, p)
    print(f"Imported {n} mention rows from {p.name}.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    main(sys.argv[1])
