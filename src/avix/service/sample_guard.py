"""Demo sample-data guardrail (server-side, defamation safety).

A cell is GUARDED unless it is provably all-real (has mentions and every mention has a known
non-demo source). Uncertainty fails toward guarded — a cell with any demo-source row, any
missing/blank/unknown source, is treated as SAMPLE. In a guarded cell, only roster (example)
names resolve to a verdict; any other name gets a neutral not-in-sample note (never a
fabricated verdict about a real business). Reuses the store + config; no business names in code."""
from pathlib import Path
import yaml

from .. import config
from ..store import repository as repo

_CFG = None


def _cfg() -> dict:
    global _CFG
    if _CFG is None:
        with open(config.CONFIG_DIR / "demo.yaml", "r", encoding="utf-8") as f:
            _CFG = yaml.safe_load(f) or {}
    return _CFG


def demo_sources() -> set:
    return {str(s) for s in _cfg().get("demo_sources", ["Demo"])}


def banner() -> str:
    return _cfg().get("sample_banner", "SAMPLE DATA — illustrative only, not a real measurement.")


def not_in_sample_message() -> str:
    return _cfg().get("not_in_sample_message",
                      "Not in this sample — this demo covers a fixed set of example firms.")


def is_guarded(conn, category, area) -> bool:
    """True unless the cell is provably all-real. Fails toward guarded on any uncertainty."""
    mentions = repo.mentions_for_cell(conn, category, area)
    if not mentions:
        return False  # no cell -> handled as NOT_COVERED elsewhere; nothing to fabricate
    ds = demo_sources()
    provably_all_real = all((m.source or "").strip() and (m.source or "").strip() not in ds
                            for m in mentions)
    return not provably_all_real


def roster_names(conn, category, area) -> list:
    return repo.roster(conn, category, area)


def in_roster(conn, category, area, business) -> bool:
    b = (business or "").strip().lower()
    return any((r or "").strip().lower() == b for r in repo.roster(conn, category, area))


def not_in_sample(business, examples) -> dict:
    """Neutral response for an out-of-roster name in a guarded cell. Names no competitors,
    makes no evaluative claim about the searched (possibly real) business."""
    return {
        "state": "NOT_IN_SAMPLE",
        "business": business,
        "sample": True,
        "sample_banner": banner(),
        "message": not_in_sample_message(),
        "examples": list(examples)[:5],
    }
