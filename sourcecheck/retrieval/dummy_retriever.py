"""
Dummy retriever for testing and always_true validator.
"""
from typing import List
from .base import Retriever
from .registry import register_retriever
from ..types import EvidenceSpan


@register_retriever("dummy")
class DummyRetriever(Retriever):
    """
    A no-op retriever that returns empty evidence.
    
    Useful for testing and for validators that don't need evidence
    (like always_true).
    """
    
    @property
    def name(self) -> str:
        return "dummy"
    
    def retrieve(
        self,
        claim: str,
        top_k: int = 5
    ) -> List[EvidenceSpan]:
        """
        Return empty evidence list.
        
        Args:
            claim: Claim text (ignored)
            top_k: Maximum spans (ignored)
        
        Returns:
            Empty list
        """
        return []
