"""
Semantic retriever using sentence-level embeddings.
"""
import re
from typing import List
from .base import Retriever
from .registry import register_retriever
from ..types import EvidenceSpan
from ..utils import EmbeddingService


@register_retriever("semantic")
class SemanticRetriever(Retriever):
    """
    Semantic retriever using sentence-level embeddings.
    
    Key properties:
    - Sentence-level granularity (no overlap)
    - Optional claim contextualization
    - In-memory only (no vector store)
    - Fast for small transcripts (< 200 sentences)
    """
    
    def __init__(self, transcript: str, config: dict = None):
        """
        Initialize semantic retriever.
        
        Args:
            transcript: Full transcript text
            config: Configuration dictionary
        """
        super().__init__(transcript, config)
        self.embedding_service = EmbeddingService()
        
        # Configuration
        self.contextualize = self.config.get('contextualize_claims', True)
        self.claim_prefixes = self.config.get('claim_prefixes', {})
        
        # Build sentence-level chunks (no overlap)
        self.sentences = []
        self.sentence_positions = []
        self._split_into_sentences()
    
    @property
    def name(self) -> str:
        return "semantic"
    
    def _split_into_sentences(self):
        """
        Split transcript into sentences with no overlap.
        
        Uses regex to split on sentence boundaries for clean,
        precise sentence-level retrieval.
        """
        if not self.transcript:
            return
        
        # Split on sentence boundaries
        # Pattern: period/question/exclamation followed by space and capital/newline
        pattern = r'(?<=[.!?])\s+(?=[A-Z\n])'
        sentences = re.split(pattern, self.transcript)
        
        current_pos = 0
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 10:  # Skip very short fragments
                continue
            
            # Find sentence position in transcript
            pos = self.transcript.find(sentence, current_pos)
            if pos != -1:
                self.sentences.append(sentence)
                self.sentence_positions.append(pos)
                current_pos = pos + len(sentence)
        
        print(f"Semantic retriever: Split transcript into {len(self.sentences)} sentences")
    
    def _contextualize_claim(self, claim: str, metadata: dict = None) -> str:
        """
        Optionally add context prefix to claim for better semantic matching.
        
        Args:
            claim: Original claim text
            metadata: Metadata containing 'field' key
        
        Returns:
            Contextualized claim or original if no prefix configured
        """
        if not self.contextualize or not metadata:
            return claim
        
        field = metadata.get('field')
        if not field:
            return claim
        
        prefix = self.claim_prefixes.get(field, '')
        return prefix + claim if prefix else claim
    
    def retrieve(
        self,
        claim: str,
        top_k: int = 5,
        metadata: dict = None
    ) -> List[EvidenceSpan]:
        """
        Retrieve evidence using semantic similarity.
        
        Computes cosine similarity between claim and all sentences,
        returns top-k most similar sentences.
        
        Args:
            claim: Claim text to find evidence for
            top_k: Number of evidence spans to return
            metadata: Optional metadata for claim contextualization
        
        Returns:
            List of top-k most semantically similar sentences
        """
        if not self.sentences:
            return []
        
        # Contextualize claim if configured
        query = self._contextualize_claim(claim, metadata)
        
        # Get claim embedding
        claim_embedding = self.embedding_service.get_embedding(query)
        
        # Score all sentences
        scored_sentences = []
        for i, sentence in enumerate(self.sentences):
            # Get sentence embedding
            sent_embedding = self.embedding_service.get_embedding(sentence)
            
            # Compute cosine similarity
            similarity = self.embedding_service.cosine_similarity(
                claim_embedding,
                sent_embedding
            )
            
            scored_sentences.append((i, similarity))
        
        # Sort by similarity (highest first)
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        
        # Build evidence spans from top-k sentences
        evidence = []
        for i, score in scored_sentences[:top_k]:
            pos = self.sentence_positions[i]
            text = self.sentences[i]
            
            evidence.append(EvidenceSpan(
                text=text,
                start_idx=pos,
                end_idx=pos + len(text),
                score=score
            ))
        
        return evidence
