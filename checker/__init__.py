"""
Chart Checker - A library for verifying structured documents against source material.
"""
from .checker import Checker
from .types import Claim, EvidenceSpan, Disposition, VerificationReport
from .config import Config

__version__ = "0.1.0"

__all__ = [
    'Checker',
    'Claim',
    'EvidenceSpan',
    'Disposition',
    'VerificationReport',
    'Config',
]
