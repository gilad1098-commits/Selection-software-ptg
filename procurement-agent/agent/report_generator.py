from __future__ import annotations

from agent.draft_generator import generate_engineer_report
from agent.models import RFQRecord

# Re-export for backwards compatibility with the spec's module layout
__all__ = ["generate_engineer_report"]
