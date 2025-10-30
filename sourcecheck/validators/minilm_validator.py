"""
MiniLM embedding-based semantic similarity validator.
"""
from typing import List
from .base import Validator
from .registry import register_validator
from ..types import Claim, EvidenceSpan, Disposition
from ..utils import EmbeddingService


@register_validator("minilm_validator")
class MiniLMValidator(Validator):
    """
    Validates claims using pure semantic similarity via MiniLM embeddings.
    
    Computes cosine similarity between claim and evidence embeddings.
    No lexical matching - purely semantic understanding.
    """
    
    def __init__(self, config: dict = None, debug: bool = False):
        """
        Initialize validator with embedding service.
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config, debug)
        self.embedding_service = EmbeddingService()
    
    @property
    def name(self) -> str:
        return "minilm_validator"
    
    def validate(
        self,
        claim: Claim,
        evidence: List[EvidenceSpan],
        transcript: str
    ) -> Disposition:
        """
        Validate claim using semantic similarity.
        
        Args:
            claim: The claim to validate
            evidence: List of evidence spans from retriever
            transcript: Full transcript text
        
        Returns:
            Disposition with verdict and explanation
        """
        # Get threshold from config
        threshold = self.config.get('embedding_threshold', 0.7)
        
        # Check if we have evidence
        if not evidence:
            return Disposition(
                claim=claim,
                verdict="insufficient_evidence",
                evidence=[],
                validator=self.name,
                explanation="No evidence spans found in transcript"
            )
        
        # Get claim embedding
        claim_embedding = self.embedding_service.get_embedding(claim.text)
        
        # Score each evidence span with semantic similarity
        scored_evidence = []
        for ev in evidence:
            # Get evidence embedding
            ev_embedding = self.embedding_service.get_embedding(ev.text)
            
            # Compute cosine similarity
            similarity = self.embedding_service.cosine_similarity(
                claim_embedding,
                ev_embedding
            )
            
            # Create new evidence span with similarity score
            scored_evidence.append(EvidenceSpan(
                text=ev.text,
                start_idx=ev.start_idx,
                end_idx=ev.end_idx,
                score=similarity
            ))
        
        # Sort by similarity score (highest first)
        scored_evidence.sort(key=lambda e: e.score, reverse=True)
        
        # Get best score
        best_score = scored_evidence[0].score if scored_evidence else 0.0
        
        # Determine verdict based on threshold
        if best_score >= threshold:
            verdict = "supported"
            explanation = (
                f"Semantic similarity {best_score:.3f} exceeds threshold {threshold:.3f}. "
                f"Claim semantically matches evidence."
            )
        else:
            verdict = "insufficient_evidence"
            explanation = (
                f"Best semantic similarity {best_score:.3f} below threshold {threshold:.3f}. "
                f"No evidence with sufficient semantic match found."
            )
        
        return Disposition(
            claim=claim,
            verdict=verdict,
            evidence=scored_evidence[:5],  # Top 5 evidence spans
            validator=self.name,
            explanation=explanation
        )
