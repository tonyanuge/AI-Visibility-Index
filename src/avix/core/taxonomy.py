"""Loads prompt packs (config-driven). Unknown archetypes route to a safe default."""
from pathlib import Path
import yaml
from .. import config

def load_pack(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        pack = yaml.safe_load(f) or {}
    known = {a["name"] for a in config.load_archetypes()}
    for p in pack.get("prompts", []):
        if p.get("archetype") not in known:
            p["archetype"] = "Discovery"  # safe default, never crash
    return pack
