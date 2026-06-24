"""Config-driven settings + taxonomy loading. No org/category/area logic is hard-coded."""
import os
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"

def _load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def load_settings() -> dict:
    # Prefer a local (gitignored) settings.yaml; fall back to the committed example.
    local = CONFIG_DIR / "settings.yaml"
    example = CONFIG_DIR / "settings.example.yaml"
    return _load_yaml(local if local.exists() else example)

def load_scoring() -> dict:
    return _load_yaml(CONFIG_DIR / "scoring.yaml")

def load_archetypes() -> list[dict]:
    return _load_yaml(CONFIG_DIR / "taxonomy" / "archetypes.yaml").get("archetypes", [])

def visibility_archetypes() -> set[str]:
    """Archetypes that count toward share-of-voice, resolved from config (no string literal)."""
    return {a["name"] for a in load_archetypes() if a.get("counts_to_share_of_voice", True)}

def env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)
