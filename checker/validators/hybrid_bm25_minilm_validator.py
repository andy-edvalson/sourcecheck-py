from typing import List
from .base import Validator
from .registry import register_validator
from ..types import Claim, EvidenceSpan, Disposition
from ..utils import EmbeddingService


@register_validator("hybrid_bm25_minilm_validator")
class HybridBM25MiniLMValidator(Validator):
    """
    Validates claims using a weighted combination of BM25 and MiniLM scores.
    Boosts literal matches and configured boost terms optionally via config.
    """

    def __init__(self, config: dict = None, debug: bool = False):
        super().__init__(config, debug)
        self.embedding_service = EmbeddingService()
        self.literal_boost = (self.config or {}).get("literal_boost", 0.2)
        self.boost_terms = set((self.config or {}).get("boost_terms", []))

        if self.debug:
            print(f"DEBUG hybrid_bm25_minilm_validator: Configured literal_boost={self.literal_boost}, boost_terms={self.boost_terms}")

    @property
    def name(self) -> str:
        return "hybrid_bm25_minilm_validator"

    def validate(
        self,
        claim: Claim,
        evidence: List[EvidenceSpan],
        transcript: str
    ) -> Disposition:
        threshold = self.config.get('min_evidence_score', 0.3)
        bm25_weight = self.config.get('bm25_weight', 0.5)
        minilm_weight = 1.0 - bm25_weight

        if not evidence:
            return Disposition(
                claim=claim,
                verdict="insufficient_evidence",
                evidence=[],
                validator=self.name,
                explanation="No evidence spans found in transcript"
            )

        claim_embedding = self.embedding_service.get_embedding(claim.text)

        scored_evidence = []
        for ev in evidence:
            bm25_score = ev.score
            ev_embedding = self.embedding_service.get_embedding(ev.text)
            minilm_score = self.embedding_service.cosine_similarity(
                claim_embedding,
                ev_embedding
            )

            hybrid_score = (bm25_weight * bm25_score) + (minilm_weight * minilm_score)

            # Apply literal match boost
            boosted = False
            if claim.text.lower() in ev.text.lower():
                hybrid_score = min(1.0, hybrid_score + self.literal_boost)
                boosted = True

            # Apply boost terms if present
            if hasattr(self, "boost_terms") and self.boost_terms:
                text_lower = ev.text.lower()
                if any(term in text_lower for term in self.boost_terms):
                    hybrid_score = min(1.0, hybrid_score + self.literal_boost)
                    boosted = True

            if boosted and self.debug:
                print(f"DEBUG hybrid_validator: Boosted hybrid score applied to '{ev.text[:30]}...' (new score: {hybrid_score:.3f})")

            scored_evidence.append(EvidenceSpan(
                text=ev.text,
                start_idx=ev.start_idx,
                end_idx=ev.end_idx,
                score=hybrid_score
            ))

        scored_evidence.sort(key=lambda e: e.score, reverse=True)
        best_score = scored_evidence[0].score if scored_evidence else 0.0

        if best_score >= threshold:
            verdict = "supported"
            explanation = (
                f"Hybrid score {best_score:.3f} "
                f"(BM25 weight={bm25_weight:.1f}, MiniLM weight={minilm_weight:.1f}) "
                f"exceeds threshold {threshold:.3f}. "
                f"Claim supported by combined lexical and semantic matching."
            )
        else:
            verdict = "insufficient_evidence"
            explanation = (
                f"Best hybrid score {best_score:.3f} "
                f"(BM25 weight={bm25_weight:.1f}, MiniLM weight={minilm_weight:.1f}) "
                f"below threshold {threshold:.3f}. "
                f"Insufficient combined evidence."
            )

        return Disposition(
            claim=claim,
            verdict=verdict,
            evidence=scored_evidence[:5],  # Ensure boosted scores are returned
            validator=self.name,
            explanation=explanation
        )
