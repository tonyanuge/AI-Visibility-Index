"""Branded client report renderer. Renders analyst-supplied data into a .docx — it owns
structure, branding, colour, tables, dates and pagination, not the findings themselves."""
from .models import ReportData, CompetitorCount, SampleRow
from .builder import build_report, load_branding

__all__ = ["ReportData", "CompetitorCount", "SampleRow", "build_report", "load_branding"]
