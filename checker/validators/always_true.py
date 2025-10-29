"""
Dummy validator that always returns 'supported' verdict.
"""
from typing import List
from .base import Validator
from .registry import register_validator
from ..types import Claim, EvidenceSpan, Disposition


@register_validator("always_true")
class AlwaysTrueValidator(Validator):
    """
    A pass-through validator that always marks claims as supported.
    
    Useful for testing and as a placeholder during development.
    """
    
    @property
    def name(self) -> str:
        return "always_true"
    
    def validate(
        self,
        claim: Claim,
        evidence: List[EvidenceSpan],
        transcript: str
    ) -> Disposition:
        """
        Always return 'supported' verdict regardless of evidence.
        
        Args:
            claim: The claim to validate
            evidence: List of evidence spans (ignored)
            transcript: Full transcript text (ignored)
        
        Returns:
            Disposition with 'supported' verdict
        """
        return Disposition(
            claim=claim,
            verdict="supported",
            evidence=evidence,
            validator=self.name,
            explanation="AlwaysTrueValidator always returns 'supported'"
        )
