"""
Chart Checker - A library for verifying clinical summaries.
"""
from .checker import Checker
from .types import Claim, EvidenceSpan, Disposition, Report
from .config import Config

__version__ = "0.1.0"

__all__ = [
    'Checker',
    'Claim',
    'EvidenceSpan',
    'Disposition',
    'Report',
    'Config',
]
