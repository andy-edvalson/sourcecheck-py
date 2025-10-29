"""
Base validator class and interfaces.
"""
from abc import ABC, abstractmethod
from typing import List
from ..types import Claim, EvidenceSpan, Disposition


class Validator(ABC):
    """
    Abstract base class for all validators.
    
    Validators examine claims and evidence to determine if a claim is supported,
    refuted, or has insufficient evidence.
    """
    
    def __init__(self, config: dict = None, debug: bool = False):
        """
        Initialize validator with optional configuration.
        
        Args:
            config: Optional configuration dictionary
            debug: Enable debug output (default: False)
        """
        self.config = config or {}
        self.debug = debug
    
    @abstractmethod
    def validate(
        self,
        claim: Claim,
        evidence: List[EvidenceSpan],
        transcript: str
    ) -> Disposition:
        """
        Validate a claim against retrieved evidence.
        
        Args:
            claim: The claim to validate
            evidence: List of evidence spans retrieved from transcript
            transcript: Full transcript text for context
        
        Returns:
            Disposition with verdict and explanation
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the validator's unique name."""
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
