"""
Base retriever class and interfaces.
"""
from abc import ABC, abstractmethod
from typing import List
from ..types import EvidenceSpan


class Retriever(ABC):
    """
    Abstract base class for all evidence retrievers.
    
    Retrievers search transcripts to find evidence spans that may support
    or refute claims extracted from summaries.
    """
    
    def __init__(self, transcript: str, config: dict = None):
        """
        Initialize retriever with transcript and optional configuration.
        
        Args:
            transcript: Full transcript text to search
            config: Optional configuration dictionary
        """
        self.transcript = transcript
        self.config = config or {}
    
    @abstractmethod
    def retrieve(
        self,
        claim: str,
        top_k: int = 5,
        metadata: dict = None
    ) -> List[EvidenceSpan]:
        """
        Retrieve evidence spans for a claim.
        
        Args:
            claim: Claim text to find evidence for
            top_k: Maximum number of evidence spans to return
            metadata: Optional metadata about the claim (field, summary, etc.)
        
        Returns:
            List of EvidenceSpan objects, sorted by relevance score (highest first)
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the retriever's unique name."""
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
