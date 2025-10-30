"""
Rubric package for completeness and missing claim detection.
"""
from .auditor import detect_missing_claims
from .completeness import check_completeness, calculate_completeness_score

__all__ = [
    'detect_missing_claims',
    'check_completeness',
    'calculate_completeness_score',
]
