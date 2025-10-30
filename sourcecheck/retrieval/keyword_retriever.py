"""
Keyword-based evidence retriever.
"""
import re
from typing import List
from .base import Retriever
from .registry import register_retriever
from ..types import EvidenceSpan


@register_retriever("keyword")
class KeywordRetriever(Retriever):
    """
    Simple keyword-based retriever.
    
    Extracts keywords from claims and searches for them in the transcript,
    returning surrounding context as evidence spans.
    """
    
    @property
    def name(self) -> str:
        return "keyword"
    
    def retrieve(
        self,
        claim: str,
        top_k: int = 5
    ) -> List[EvidenceSpan]:
        """
        Retrieve evidence spans using keyword matching.
        
        Args:
            claim: Claim text to find evidence for
            top_k: Maximum number of evidence spans to return
        
        Returns:
            List of EvidenceSpan objects, sorted by score
        """
        if not self.transcript or not claim:
            return []
        
        context_window = self.config.get('context_window', 100)
        min_keyword_length = self.config.get('min_keyword_length', 4)
        
        # Extract keywords from claim (words longer than min_keyword_length)
        keywords = [
            word.lower()
            for word in re.findall(r'\b\w+\b', claim)
            if len(word) > min_keyword_length
        ]
        
        if not keywords:
            return []
        
        evidence_spans = []
        transcript_lower = self.transcript.lower()
        
        # Find spans containing keywords
        for keyword in keywords[:5]:  # Limit to first 5 keywords
            # Find all occurrences of the keyword
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            for match in pattern.finditer(self.transcript):
                start_idx = max(0, match.start() - context_window)
                end_idx = min(len(self.transcript), match.end() + context_window)
                
                # Extract the span
                span_text = self.transcript[start_idx:end_idx].strip()
                
                # Simple scoring based on keyword density
                score = sum(
                    1 for kw in keywords
                    if kw in span_text.lower()
                ) / len(keywords)
                
                evidence_spans.append(EvidenceSpan(
                    text=span_text,
                    start_idx=start_idx,
                    end_idx=end_idx,
                    score=score
                ))
                
                if len(evidence_spans) >= top_k:
                    break
            
            if len(evidence_spans) >= top_k:
                break
        
        # Sort by score and return top spans
        evidence_spans.sort(key=lambda x: x.score, reverse=True)
        return evidence_spans[:top_k]
