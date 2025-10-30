"""
Temporal Drift Validator.

Detects mismatched or directionally inconsistent temporal expressions
between claims and evidence.
"""
import re
from typing import List
from .base import Validator
from .registry import register_validator
from ..types import Claim, EvidenceSpan, Disposition


@register_validator("temporal_drift_validator")
class TemporalDriftValidator(Validator):
    """
    Detects temporal mismatches between claims and evidence.
    
    Refutes claims with significant temporal drift (e.g., "yesterday" vs "last week").
    """

    @property
    def name(self):
        return "temporal_drift_validator"

    def __init__(self, config=None, debug=False):
        super().__init__(config, debug)
        self.drift_threshold = self.config.get("drift_threshold", 7)  # days
        
        # Relative temporal expressions mapped to days offset
        self.relative_map = {
            "today": 0,
            "this morning": 0,
            "this afternoon": 0,
            "tonight": 0,
            "yesterday": -1,
            "last night": -1,
            "last week": -7,
            "last month": -30,
            "tomorrow": 1,
            "next week": 7,
            "next month": 30,
        }
        
        # Pattern for numeric temporal expressions (e.g., "3 days ago")
        self.numeric_pattern = re.compile(r"(\d+)\s*(day|week|month|year)s?\b", re.I)

    def validate(self, claim: Claim, evidence: List[EvidenceSpan], transcript: str) -> Disposition:
        """
        Validate temporal consistency between claim and evidence.
        
        Args:
            claim: Claim to validate
            evidence: Retrieved evidence spans
            transcript: Full transcript (not used)
        
        Returns:
            Disposition with verdict and temporal drift metrics
        """
        if not evidence:
            return Disposition(
                claim=claim,
                verdict="insufficient_evidence",
                evidence=[],
                validator=self.name,
                explanation="No evidence available"
            )
        
        claim_times = self._extract_temporal(claim.text)
        evidence_text = " ".join(e.text for e in evidence)
        evidence_times = self._extract_temporal(evidence_text)

        # Case 1: No temporal expressions in either
        if not claim_times and not evidence_times:
            return Disposition(
                claim=claim,
                verdict="supported",
                evidence=evidence,
                validator=self.name,
                explanation="No temporal expressions found"
            )

        # Case 2: Temporal in claim but not evidence
        if claim_times and not evidence_times:
            # Check lexical overlap - if high, likely same event despite missing temporal
            overlap = self._lexical_overlap(claim.text, evidence_text)
            if overlap > 0.4:
                return Disposition(
                    claim=claim,
                    verdict="supported",
                    evidence=evidence,
                    validator=self.name,
                    explanation=(
                        f"Temporal reference in claim ({claim_times}) "
                        f"but absent from evidence; lexical overlap ({overlap:.0%}) suggests same event."
                    )
                )
            else:
                return Disposition(
                    claim=claim,
                    verdict="insufficient_evidence",
                    evidence=evidence,
                    validator=self.name,
                    explanation=f"Temporal reference in claim ({claim_times}) but absent from evidence"
                )
        
        # Case 3: Different symbolic anchors (no numeric values)
        if (set(claim_times) != set(evidence_times) and 
            not any(isinstance(x, (int, float)) for x in claim_times + evidence_times)):
            return Disposition(
                claim=claim,
                verdict="refuted",
                evidence=evidence,
                validator=self.name,
                explanation=f"Different temporal anchors: claim={claim_times}, evidence={evidence_times}",
                metadata={"drift_days": None, "symbolic_mismatch": True}
            )

        # Case 4: Calculate drift
        drift_score = self._compare_temporal_sets(claim_times, evidence_times)
        diff = abs(drift_score)
        unit = "day" if diff == 1 else "days"
        
        if diff > self.drift_threshold:
            verdict = "refuted"
            explanation = (
                f"Temporal drift detected ({diff:.0f} {unit} difference). "
                f"Claim expressions={claim_times}, evidence={evidence_times}"
            )
        else:
            verdict = "supported"
            explanation = f"Temporal alignment OK ({diff:.0f} {unit} difference)"

        return Disposition(
            claim=claim,
            verdict=verdict,
            evidence=evidence,
            validator=self.name,
            explanation=explanation,
            metadata={"drift_days": drift_score}
        )

    def _extract_temporal(self, text: str) -> List[int]:
        """
        Extract temporal expressions and convert to days offset.
        
        Handles:
        - Relative expressions ("yesterday", "last week")
        - Numeric expressions ("3 days ago", "in 2 weeks")
        - Polarity detection ("ago" vs "in X days")
        
        Args:
            text: Text to extract from
        
        Returns:
            List of days offsets (negative = past, positive = future)
        """
        text_lower = text.lower()
        times = []
        
        # Extract relative expressions with word boundary matching
        for key, days in self.relative_map.items():
            if re.search(rf"\b{re.escape(key)}\b", text_lower):
                times.append(days)
        
        # Extract numeric expressions with polarity detection
        for m in self.numeric_pattern.finditer(text_lower):
            n = int(m.group(1))
            unit = m.group(2).lower()
            
            # Convert to days
            multiplier = {"day": 1, "week": 7, "month": 30, "year": 365}[unit]
            days = -n * multiplier  # default = past
            
            # Check context window for polarity
            window_start = max(0, m.start() - 10)
            window_end = min(len(text_lower), m.end() + 10)
            window = text_lower[window_start:window_end]
            
            # "in X days" = future
            if "in " in window or "next " in window:
                days = n * multiplier
            
            times.append(days)
        
        return times

    def _lexical_overlap(self, a: str, b: str) -> float:
        """
        Calculate lexical overlap between two texts.
        
        Used to determine if claim and evidence refer to the same event
        even when temporal expressions differ or are missing.
        
        Args:
            a: First text
            b: Second text
        
        Returns:
            Overlap ratio between 0.0 and 1.0
        """
        a_words = set(a.lower().split())
        b_words = set(b.lower().split())
        
        # Remove stopwords
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'is', 'was', 'were', 'this', 'that', 'these', 'those'
        }
        content_a = a_words - stopwords
        content_b = b_words - stopwords
        
        if not content_a:
            return 0.0
        
        # Calculate overlap ratio
        overlap = len(content_a & content_b) / len(content_a)
        return overlap
    
    def _compare_temporal_sets(self, claim_times: List[int], evidence_times: List[int]) -> float:
        """
        Compare temporal expressions between claim and evidence.
        
        Uses averaging to handle multiple expressions robustly.
        Optionally limits evidence to nearest expression to avoid skew.
        
        Args:
            claim_times: Days offsets from claim
            evidence_times: Days offsets from evidence
        
        Returns:
            Difference in days (positive = claim is later than evidence)
        """
        if not claim_times or not evidence_times:
            return 0.0
        
        # Limit evidence to nearest expression if multiple (avoid skew)
        if len(evidence_times) > 1:
            evidence_times = evidence_times[:1]
        
        # Use average for robust comparison
        claim_avg = sum(claim_times) / len(claim_times)
        evidence_avg = sum(evidence_times) / len(evidence_times)
        
        return claim_avg - evidence_avg
