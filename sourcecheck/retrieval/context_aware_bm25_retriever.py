"""
Context-aware BM25 retriever with query expansion.
"""
from typing import List
from .bm25_retriever import BM25Retriever
from .registry import register_retriever
from ..types import EvidenceSpan


@register_retriever("context_aware_bm25")
class ContextAwareBM25Retriever(BM25Retriever):
    """
    BM25 retriever that expands terse queries with context from related fields.
    
    For short claims (e.g., "Fall"), this retriever can automatically expand
    the query with context from related fields (e.g., HPI) to improve evidence
    retrieval. Configuration is driven by YAML settings.
    """
    
    def __init__(self, transcript: str, config: dict = None):
        """
        Initialize context-aware BM25 retriever.
        
        Args:
            transcript: Full transcript text to search
            config: Configuration dictionary with context_expansion settings
        """
        super().__init__(transcript, config)
        
        # Load context expansion configuration
        self.context_config = self.config.get('context_expansion', {})
        self.context_enabled = self.context_config.get('enabled', False)
        self.max_context_length = self.context_config.get('max_context_length', 200)
        self.terse_threshold = self.context_config.get('terse_threshold', 3)
        self.field_relationships = self.context_config.get('field_relationships', {})
    
    @property
    def name(self) -> str:
        return "context_aware_bm25"
    
    def retrieve(
        self,
        claim: str,
        top_k: int = 5,
        metadata: dict = None
    ) -> List[EvidenceSpan]:
        """
        Retrieve evidence spans with optional context expansion.
        
        If context expansion is enabled and the claim is terse, expands
        the query with context from related fields before retrieval.
        
        Args:
            claim: Claim text to find evidence for
            top_k: Maximum number of evidence spans to return
            metadata: Metadata containing field name and summary
        
        Returns:
            List of EvidenceSpan objects, sorted by BM25 score
        """
        # Expand query with context if applicable
        query = claim
        if self.context_enabled and metadata:
            query = self._expand_query_with_context(claim, metadata)
        
        # Use parent's retrieve method with expanded query
        return super().retrieve(query, top_k, metadata)
    
    def _expand_query_with_context(self, claim: str, metadata: dict) -> str:
        """
        Expand a terse claim with context from related fields.
        
        Args:
            claim: Original claim text
            metadata: Metadata containing 'field' and 'summary'
        
        Returns:
            Expanded query string, or original claim if no expansion needed
        """
        # Check if claim is terse (word count <= threshold)
        word_count = len(claim.split())
        if word_count > self.terse_threshold:
            return claim
        
        # Get field and summary from metadata
        field = metadata.get('field')
        summary = metadata.get('summary')
        
        if not field or not summary:
            return claim
        
        # Check if this field has context relationships configured
        if field not in self.field_relationships:
            return claim
        
        # Get context configuration for this field
        relationship = self.field_relationships[field]
        context_fields = relationship.get('context_fields', [])
        
        if not context_fields:
            return claim
        
        # Build context from specified fields
        context_parts = []
        for context_field in context_fields:
            if context_field in summary:
                context_value = summary[context_field]
                if isinstance(context_value, str) and context_value:
                    # Take first N characters of context
                    truncated = context_value[:self.max_context_length]
                    context_parts.append(truncated)
        
        # If we found context, expand the query
        if context_parts:
            context = " ".join(context_parts)
            expanded_query = f"{claim}. {context}"
            return expanded_query
        
        return claim
