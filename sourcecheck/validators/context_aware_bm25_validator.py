"""
Context-aware BM25 validator that validates evidence against HPI narrative.
"""
import re
from typing import List, Set
from .base import Validator
from .registry import register_validator
from ..types import Claim, EvidenceSpan, Disposition


@register_validator("context_aware_bm25_validator")
class ContextAwareBM25Validator(Validator):
    """
    BM25 validator that uses HPI context to validate terse claims.
    
    For short claims (e.g., "Fall"), this validator checks if the evidence
    aligns with the HPI narrative rather than just checking BM25 scores.
    """
    
    # Configuration for context-aware validation
    CONTEXT_RELATIONSHIPS = {
        'chief_complaint': 'hpi',
        'dx': 'hpi',
    }
    
    @property
    def name(self) -> str:
        return "context_aware_bm25_validator"
    
    def _extract_keywords(self, text: str) -> Set[str]:
        """
        Extract meaningful keywords from text.
        
        Args:
            text: Text to extract keywords from
        
        Returns:
            Set of lowercase keywords
        """
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'my', 'your',
            'his', 'her', 'its', 'our', 'their'
        }
        
        # Extract words (alphanumeric sequences)
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out stop words and short words
        keywords = {w for w in words if len(w) > 2 and w not in stop_words}
        
        return keywords
    
    def _calculate_context_alignment(
        self,
        evidence_text: str,
        context_keywords: Set[str]
    ) -> float:
        """
        Calculate how well evidence aligns with context keywords.
        
        Args:
            evidence_text: Evidence text to check
            context_keywords: Keywords from HPI context
        
        Returns:
            Alignment score between 0.0 and 1.0
        """
        if not context_keywords:
            return 0.0
        
        # Extract keywords from evidence
        evidence_keywords = self._extract_keywords(evidence_text)
        
        if not evidence_keywords:
            return 0.0
        
        # Calculate overlap
        overlap = len(evidence_keywords & context_keywords)
        
        # Score based on percentage of context keywords found
        alignment_score = overlap / len(context_keywords)
        
        return min(1.0, alignment_score)
    
    def _is_terse_claim(self, claim: Claim) -> bool:
        """
        Check if claim is terse (3 words or less).
        
        Args:
            claim: Claim to check
        
        Returns:
            True if claim is terse
        """
        word_count = len(claim.text.split())
        return word_count <= 3
    
    def _get_context_field(self, claim: Claim) -> str:
        """
        Get the context field name for this claim's field.
        
        Args:
            claim: Claim to get context for
        
        Returns:
            Context field name (e.g., 'hpi') or empty string
        """
        return self.CONTEXT_RELATIONSHIPS.get(claim.field, '')
    
    def validate(
        self,
        claim: Claim,
        evidence: List[EvidenceSpan],
        transcript: str
    ) -> Disposition:
        """
        Validate claim using context-aware scoring.
        
        For terse claims, validates evidence against HPI narrative.
        For other claims, uses standard BM25 validation.
        
        Args:
            claim: The claim to validate
            evidence: List of evidence spans from retriever
            transcript: Full transcript text
        
        Returns:
            Disposition with verdict and explanation
        """
        # Get thresholds from config
        min_evidence_score = self.config.get('min_evidence_score', 0.3)
        min_evidence_count = self.config.get('min_evidence_count', 1)
        context_boost = self.config.get('context_boost', 0.3)
        
        # Check if we should use context-aware validation
        use_context = False
        context_keywords = set()
        
        if self._is_terse_claim(claim):
            context_field = self._get_context_field(claim)
            if context_field and claim.metadata:
                summary = claim.metadata.get('summary', {})
                context_text = summary.get(context_field, '')
                if context_text:
                    use_context = True
                    context_keywords = self._extract_keywords(context_text)
        
        # Check if we have any evidence
        if not evidence:
            explanation = "No evidence found in transcript for this claim"
            if use_context:
                explanation += f" (validated with {context_field} context)"
            
            return Disposition(
                claim=claim,
                verdict="insufficient_evidence",
                evidence=[],
                validator=self.name,
                explanation=explanation
            )
        
        # Score evidence (with context boost if applicable)
        scored_evidence = []
        for ev in evidence:
            score = ev.score
            
            # Apply context boost if using context-aware validation
            if use_context and context_keywords:
                alignment = self._calculate_context_alignment(
                    ev.text,
                    context_keywords
                )
                # Boost score based on context alignment
                score = score + (alignment * context_boost)
                score = min(1.0, score)  # Cap at 1.0
            
            # Create new evidence span with adjusted score
            scored_evidence.append(EvidenceSpan(
                text=ev.text,
                start_idx=ev.start_idx,
                end_idx=ev.end_idx,
                score=score
            ))
        
        # Sort by score
        scored_evidence.sort(key=lambda e: e.score, reverse=True)
        
        # Filter evidence by minimum score threshold
        strong_evidence = [
            e for e in scored_evidence
            if e.score >= min_evidence_score
        ]
        
        # Determine verdict
        if len(strong_evidence) >= min_evidence_count:
            avg_score = sum(e.score for e in strong_evidence) / len(strong_evidence)
            verdict = "supported"
            
            explanation = (
                f"Found {len(strong_evidence)} evidence span(s) with "
                f"average score of {avg_score:.3f}. "
            )
            
            if use_context:
                explanation += f"Evidence aligns with {context_field} narrative. "
            
            explanation += "Claim appears to be supported by transcript."
        else:
            if scored_evidence:
                max_score = max(e.score for e in scored_evidence)
                verdict = "insufficient_evidence"
                explanation = (
                    f"Found {len(scored_evidence)} evidence span(s) but highest "
                    f"score is {max_score:.3f}, below threshold of "
                    f"{min_evidence_score:.3f}. "
                )
                
                if use_context:
                    explanation += f"Evidence does not sufficiently align with {context_field} narrative. "
                
                explanation += "Cannot confirm claim."
            else:
                verdict = "insufficient_evidence"
                explanation = "No evidence found in transcript for this claim."
        
        return Disposition(
            claim=claim,
            verdict=verdict,
            evidence=scored_evidence[:5],  # Top 5 evidence spans
            validator=self.name,
            explanation=explanation
        )
