"""
BM25-based evidence retriever.
"""
import re
from typing import List
from rank_bm25 import BM25Okapi
from .base import Retriever
from .registry import register_retriever
from ..types import EvidenceSpan


@register_retriever("bm25")
class BM25Retriever(Retriever):
    """
    BM25-based retriever for evidence extraction.
    
    Uses the BM25 ranking algorithm to find relevant passages in the transcript
    that may support or refute claims. BM25 is a probabilistic retrieval model
    that accounts for term frequency, document length, and inverse document frequency.
    """
    
    def __init__(self, transcript: str, config: dict = None):
        """
        Initialize BM25 retriever and build index.
        
        Args:
            transcript: Full transcript text to search
            config: Optional configuration with:
                - chunk_size: Target size for text chunks (default: 200)
                - overlap: Overlap between chunks (default: 50)
                - context_window: Extra context around matches (default: 150)
        """
        super().__init__(transcript, config)
        
        # Configuration
        self.chunk_size = self.config.get('chunk_size', 200)
        self.overlap = self.config.get('overlap', 50)
        self.context_window = self.config.get('context_window', 150)
        
        # Build index
        self.chunks = []
        self.chunk_positions = []
        self._build_index()
    
    @property
    def name(self) -> str:
        return "bm25"
    
    def _build_index(self):
        """
        Build BM25 index by chunking transcript with sliding window.
        
        Uses a sliding window approach with overlap to create chunks that
        cover the entire transcript. Each chunk is tokenized for BM25 indexing.
        """
        if not self.transcript:
            self.bm25 = None
            return
        
        # Calculate step size (chunk_size - overlap)
        step_size = max(1, self.chunk_size - self.overlap)
        
        # Create sliding window chunks
        pos = 0
        while pos < len(self.transcript):
            # Extract chunk
            chunk_end = min(pos + self.chunk_size, len(self.transcript))
            chunk_text = self.transcript[pos:chunk_end].strip()
            
            if chunk_text:
                self.chunks.append(chunk_text)
                self.chunk_positions.append(pos)
            
            # Move to next position
            pos += step_size
            
            # Stop if we've covered the whole transcript
            if chunk_end >= len(self.transcript):
                break
        
        # Tokenize chunks for BM25
        tokenized_chunks = [self._tokenize(chunk) for chunk in self.chunks]
        
        # Build BM25 index
        if tokenized_chunks:
            self.bm25 = BM25Okapi(tokenized_chunks)
        else:
            self.bm25 = None
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into lowercase words.
        
        Args:
            text: Text to tokenize
        
        Returns:
            List of lowercase tokens
        """
        # Simple whitespace tokenization with lowercase
        # Medical terms often multi-word, so keep it simple
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens
    
    def retrieve(
        self,
        claim: str,
        top_k: int = 5,
        metadata: dict = None
    ) -> List[EvidenceSpan]:
        """
        Retrieve evidence spans using BM25 ranking.
        
        Args:
            claim: Claim text to find evidence for
            top_k: Maximum number of evidence spans to return
            metadata: Optional metadata (ignored by base BM25)
        
        Returns:
            List of EvidenceSpan objects, sorted by BM25 score (highest first)
        """
        if not self.bm25 or not claim:
            return []
        
        # Tokenize claim
        claim_tokens = self._tokenize(claim)
        
        if not claim_tokens:
            return []
        
        # Get BM25 scores for all chunks
        scores = self.bm25.get_scores(claim_tokens)
        
        # Get top-k chunk indices
        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:top_k]
        
        # Build evidence spans with context
        evidence_spans = []
        
        for idx in top_indices:
            score = scores[idx]
            
            # Skip chunks with very low scores
            if score < 0.1:
                continue
            
            chunk_text = self.chunks[idx]
            chunk_pos = self.chunk_positions[idx]
            
            # Add context window around chunk
            start_idx = max(0, chunk_pos - self.context_window)
            end_idx = min(
                len(self.transcript),
                chunk_pos + len(chunk_text) + self.context_window
            )
            
            # Extract span with context
            span_text = self.transcript[start_idx:end_idx].strip()
            
            # Normalize score to 0-1 range (BM25 scores are unbounded)
            # Use sigmoid-like transformation
            normalized_score = min(1.0, score / 10.0)
            
            evidence_spans.append(EvidenceSpan(
                text=span_text,
                start_idx=start_idx,
                end_idx=end_idx,
                score=normalized_score
            ))
        
        return evidence_spans
