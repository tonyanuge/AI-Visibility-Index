"""CLI: render a branded AI Visibility Check .docx from a structured JSON input.

Usage:
  PYTHONPATH=src python scripts/generate_report.py tests/fixtures/sample_report.json
  PYTHONPATH=src python scripts/generate_report.py input.json --out data/exports/custom.docx

Output defaults to data/exports/ (gitignored). The generator renders analyst-supplied
narrative + evidence; it does not write findings."""
import sys, json, argparse, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from avix.report import ReportData, build_report, load_branding
from avix import config


def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_") or "report"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render a branded AI Visibility Check .docx.")
    ap.add_argument("input", help="Path to the structured report JSON.")
    ap.add_argument("--out", help="Output .docx path (default: data/exports/<client>_AI_Visibility_Check.docx)")
    args = ap.parse_args(argv)

    with open(args.input, "r", encoding="utf-8") as f:
        data = ReportData.from_dict(json.load(f))

    out = Path(args.out) if args.out else (
        config.ROOT / "data" / "exports" / f"{_slug(data.client)}_AI_Visibility_Check.docx")
    out.parent.mkdir(parents=True, exist_ok=True)

    out.write_bytes(build_report(data, load_branding()))
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
