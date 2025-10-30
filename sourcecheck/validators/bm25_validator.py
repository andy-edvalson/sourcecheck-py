"""
BM25-based validator for claim verification.
"""
from typing import List
from .base import Validator
from .registry import register_validator
from ..types import Claim, EvidenceSpan, Disposition


@register_validator("bm25_validator")
class BM25Validator(Validator):
    """
    Validator that uses BM25 retrieval to verify claims.
    
    This validator checks if sufficient evidence exists in the transcript
    to support a claim, using BM25 scoring to rank evidence quality.
    """
    
    @property
    def name(self) -> str:
        return "bm25_validator"
    
    def validate(
        self,
        claim: Claim,
        evidence: List[EvidenceSpan],
        transcript: str
    ) -> Disposition:
        """
        Validate a claim using BM25-retrieved evidence.
        
        Args:
            claim: The claim to validate
            evidence: List of evidence spans retrieved via BM25
            transcript: Full transcript text
        
        Returns:
            Disposition with verdict and explanation
        """
        # Get thresholds from config
        min_evidence_score = self.config.get('min_evidence_score', 0.3)
        min_evidence_count = self.config.get('min_evidence_count', 1)
        
        # Check if we have any evidence
        if not evidence:
            return Disposition(
                claim=claim,
                verdict="insufficient_evidence",
                evidence=[],
                validator=self.name,
                explanation="No evidence found in transcript for this claim"
            )
        
        # Filter evidence by minimum score threshold
        strong_evidence = [
            e for e in evidence
            if e.score >= min_evidence_score
        ]
        
        # Determine verdict based on evidence quality and quantity
        if len(strong_evidence) >= min_evidence_count:
            # Calculate average score of strong evidence
            avg_score = sum(e.score for e in strong_evidence) / len(strong_evidence)
            
            verdict = "supported"
            explanation = (
                f"Found {len(strong_evidence)} evidence span(s) with "
                f"average BM25 score of {avg_score:.3f}. "
                f"Claim appears to be supported by transcript."
            )
        else:
            # Have some evidence but not strong enough
            if evidence:
                max_score = max(e.score for e in evidence)
                verdict = "insufficient_evidence"
                explanation = (
                    f"Found {len(evidence)} evidence span(s) but highest "
                    f"BM25 score is {max_score:.3f}, below threshold of "
                    f"{min_evidence_score:.3f}. Cannot confirm claim."
                )
            else:
                verdict = "insufficient_evidence"
                explanation = "No evidence found in transcript for this claim"
        
        return Disposition(
            claim=claim,
            verdict=verdict,
            evidence=evidence[:5],  # Include top 5 evidence spans
            validator=self.name,
            explanation=explanation
        )
