"""
Quality analysis modules for detecting issues in validated claims.

Quality modules run after validation and arbitration to detect
issues like omissions, vagueness, or contradictions, even when
claims are ultimately accepted.

Pipeline: Retriever → Validators → Arbitration → QualityModules → Report
"""
from .base import QualityModule
from .registry import (
    register_quality_module,
    create_quality_module,
    list_quality_modules,
    get_quality_module_class
)

# Import modules to trigger registration
from .semantic_quality import SemanticQualityModule
from .temporal_numeric_drift import TemporalNumericDriftModule

__all__ = [
    "QualityModule",
    "register_quality_module",
    "create_quality_module",
    "list_quality_modules",
    "get_quality_module_class",
    "SemanticQualityModule",
    "TemporalNumericDriftModule",
]
