"""
Temporal and Numeric Drift Quality Module.

Detects discrepancies in numbers, dates, durations, and temporal
context between claims and evidence using regex-based comparison.
"""
import re
from typing import List, Tuple, Set
from .base import QualityModule
from .registry import register_quality_module
from ..types import Disposition, QualityIssue


@register_quality_module("temporal_numeric_drift")
class TemporalNumericDriftModule(QualityModule):
    """
    Detects temporal and numeric drift between claims and evidence.
    
    Flags changes like:
    - "this morning" vs no time context
    - "6 years" → "4 years"
    - "10mg" → "5mg"
    - Dates that don't match
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize temporal/numeric drift module.
        
        Config options:
            min_quality_score: Analyze if quality_score < this (default: 0.95)
            tolerance_percent: Allow X% numeric difference (default: 10)
            check_temporal: Check temporal adverbs (default: True)
            check_numeric: Check numeric values (default: True)
            max_issues: Maximum issues to report (default: 3)
        """
        super().__init__(config)
        self.min_quality_score = self.config.get("min_quality_score", 0.95)
        self.tolerance_percent = self.config.get("tolerance_percent", 10)
        self.check_temporal = self.config.get("check_temporal", True)
        self.check_numeric = self.config.get("check_numeric", True)
        self.max_issues = self.config.get("max_issues", 3)
        
        # Temporal adverbs and phrases
        self.temporal_patterns = [
            r'\bthis morning\b',
            r'\bthis afternoon\b',
            r'\bthis evening\b',
            r'\btonight\b',
            r'\byesterday\b',
            r'\blast night\b',
            r'\blast week\b',
            r'\blast month\b',
            r'\blast year\b',
            r'\btoday\b',
            r'\btomorrow\b',
            r'\brecently\b',
            r'\bearlier today\b',
        ]
    
    @property
    def name(self) -> str:
        return "temporal_numeric_drift"
    
    def should_analyze(self, disposition: Disposition) -> bool:
        """Only analyze if quality score indicates potential issues."""
        if disposition.quality_score is None:
            return True
        return disposition.quality_score < self.min_quality_score
    
    def analyze(
        self,
        disposition: Disposition,
        transcript: str
    ) -> dict:
        """
        Analyze for temporal and numeric drift.
        
        Args:
            disposition: Validation result with claim and evidence
            transcript: Full transcript (not used)
        
        Returns:
            Dict with 'issues' (List[QualityIssue]) and 'quality_score' (float)
        """
        if not self.should_analyze(disposition):
            return {"issues": [], "quality_score": 1.0}
        
        if not disposition.evidence:
            return {"issues": [], "quality_score": 1.0}
        
        claim_text = disposition.claim.text
        evidence_text = disposition.evidence[0].text
        
        issues = []
        
        # Check temporal drift
        if self.check_temporal:
            issues.extend(self._detect_temporal_drift(claim_text, evidence_text))
        
        # Check numeric drift
        if self.check_numeric:
            issues.extend(self._detect_numeric_drift(claim_text, evidence_text))
        
        # Calculate quality_score based on issue severity
        quality_score = 1.0
        for issue in issues[:self.max_issues]:
            if issue.severity == "high":
                quality_score *= 0.5  # 50% penalty for high severity
            elif issue.severity == "medium":
                quality_score *= 0.8  # 20% penalty for medium severity
            elif issue.severity == "low":
                quality_score *= 0.9  # 10% penalty for low severity
        
        return {
            "issues": issues[:self.max_issues],
            "quality_score": quality_score
        }
    
    def _detect_temporal_drift(
        self,
        claim: str,
        evidence: str
    ) -> List[QualityIssue]:
        """
        Detect temporal context drift.
        
        Flags when evidence has temporal context but claim doesn't.
        """
        issues = []
        
        # Find temporal phrases in evidence
        evidence_temporal = set()
        for pattern in self.temporal_patterns:
            matches = re.finditer(pattern, evidence, re.IGNORECASE)
            for match in matches:
                evidence_temporal.add(match.group(0).lower())
        
        # Check if claim has these temporal phrases
        claim_lower = claim.lower()
        for temporal in evidence_temporal:
            if temporal not in claim_lower:
                issues.append(QualityIssue(
                    type="temporal_drift",
                    severity="medium",
                    detail=f"Evidence specifies temporal context '{temporal}' but claim omits it",
                    evidence_snippet=self._get_context(evidence, temporal),
                    claim_snippet=claim[:100],
                    suggestion=f"Consider adding temporal context: '{temporal}'"
                ))
        
        return issues
    
    def _detect_numeric_drift(
        self,
        claim: str,
        evidence: str
    ) -> List[QualityIssue]:
        """
        Detect numeric value drift.
        
        Flags when numbers differ between claim and evidence.
        """
        issues = []
        
        # Extract numeric values with units from evidence
        evidence_nums = self._extract_numeric_values(evidence)
        claim_nums = self._extract_numeric_values(claim)
        
        # Check for mismatches
        for e_value, e_unit in evidence_nums:
            # Look for same unit in claim
            matching_claims = [(c_value, c_unit) for c_value, c_unit in claim_nums if c_unit == e_unit]
            
            if not matching_claims:
                # Unit exists in evidence but not in claim
                issues.append(QualityIssue(
                    type="numeric_drift",
                    severity="medium",
                    detail=f"Evidence specifies '{e_value} {e_unit}' but claim omits this measurement",
                    evidence_snippet=self._get_context(evidence, f"{e_value} {e_unit}"),
                    claim_snippet=claim[:100],
                    suggestion=f"Consider including: '{e_value} {e_unit}'"
                ))
            else:
                # Check if values differ significantly
                for c_value, c_unit in matching_claims:
                    if not self._values_match(e_value, c_value):
                        issues.append(QualityIssue(
                            type="numeric_drift",
                            severity="high",
                            detail=f"Numeric mismatch: evidence says '{e_value} {e_unit}' but claim says '{c_value} {c_unit}'",
                            evidence_snippet=self._get_context(evidence, f"{e_value} {e_unit}"),
                            claim_snippet=self._get_context(claim, f"{c_value} {c_unit}"),
                            suggestion=f"Verify the correct value: '{e_value} {e_unit}' or '{c_value} {c_unit}'"
                        ))
        
        return issues
    
    def _extract_numeric_values(self, text: str) -> List[Tuple[str, str]]:
        """
        Extract numeric values with units.
        
        Returns list of (value, unit) tuples.
        """
        # Pattern for numbers with units
        pattern = r'(\d+(?:\.\d+)?)\s*(cm|mm|mg|kg|lb|g|ml|years?|months?|days?|hours?|minutes?|weeks?)'
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        # Normalize units (e.g., "year" → "years")
        normalized = []
        for value, unit in matches:
            unit_lower = unit.lower()
            # Normalize to plural
            if unit_lower in ['year', 'month', 'day', 'hour', 'minute', 'week']:
                unit_lower += 's'
            normalized.append((value, unit_lower))
        
        return normalized
    
    def _values_match(self, val1: str, val2: str) -> bool:
        """
        Check if two numeric values match within tolerance.
        
        Args:
            val1: First value as string
            val2: Second value as string
        
        Returns:
            True if values match within tolerance
        """
        try:
            v1 = float(val1)
            v2 = float(val2)
            
            # Check if within tolerance percentage
            if v1 == 0 and v2 == 0:
                return True
            
            max_val = max(abs(v1), abs(v2))
            diff_percent = abs(v1 - v2) / max_val * 100
            
            return diff_percent <= self.tolerance_percent
        except ValueError:
            # If can't convert to float, do string comparison
            return val1 == val2
    
    def _get_context(self, text: str, phrase: str, context: int = 40) -> str:
        """
        Get context around a phrase.
        
        Args:
            text: Full text
            phrase: Phrase to find
            context: Characters of context
        
        Returns:
            Snippet with context
        """
        pos = text.lower().find(phrase.lower())
        
        if pos == -1:
            return text[:min(100, len(text))] + ("..." if len(text) > 100 else "")
        
        start = max(0, pos - context)
        end = min(len(text), pos + len(phrase) + context)
        
        snippet = text[start:end]
        
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        
        return snippet
