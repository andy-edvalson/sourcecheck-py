"""
Negation-based entity refuter using scispaCy and negspacy.
"""

from typing import List
import spacy
import re
from negspacy.negation import Negex
from scispacy.abbreviation import AbbreviationDetector
from sentence_transformers import SentenceTransformer, util
from .base import Validator
from .registry import register_validator
from ..types import Claim, EvidenceSpan, Disposition

@register_validator("negation_refuter")
class NegationEntityRefuter(Validator):
    """
    Validator that refutes claims contradicted by negated medical entities in the transcript.
    Uses spaCy + scispaCy + negspacy for entity/negation detection.
    """

    def __init__(self, config: dict = None, debug: bool = False):
        super().__init__(config, debug)

        self.match_threshold = (self.config or {}).get("match_threshold", 0.7)
        self.semantic_threshold = (self.config or {}).get("semantic_threshold", 0.6)
        self.boost_terms = set((self.config or {}).get("boost_words", []))

        if self.debug:
            print(f"DEBUG negation_refuter __init__: match_threshold={self.match_threshold}, config={self.config}")

        self.nlp = spacy.load("en_core_sci_md")
        self.nlp.add_pipe("abbreviation_detector")
        self.nlp.add_pipe("negex", config={"chunk_prefix": ["no", "denies", "without", "never", "negative"]})

        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')

    @property
    def name(self) -> str:
        return "negation_refuter"

    def _extract_sentence_with_entity(self, transcript: str, entity_text: str) -> str:
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', transcript)
        for sentence in sentences:
            if entity_text in sentence:
                return sentence.strip()

        idx = transcript.find(entity_text)
        if idx == -1:
            return entity_text

        start = max(0, idx - 50)
        end = min(len(transcript), idx + len(entity_text) + 50)
        return transcript[start:end].strip()

    def _is_claim_negated(self, claim_text: str) -> bool:
        """Check if claim contains negation"""
        doc = self.nlp(claim_text)
        for ent in doc.ents:
            if hasattr(ent._, "negex") and ent._.negex:
                return True
        for token in doc:
            if token.dep_ == "neg":
                return True
        return False

    def _entity_match_score(self, claim_text: str, entity_text: str) -> float:
        claim_emb = self.embedder.encode(claim_text, convert_to_tensor=True)
        entity_emb = self.embedder.encode(entity_text, convert_to_tensor=True)
        similarity = util.cos_sim(claim_emb, entity_emb).item()

        entity_text_lower = entity_text.lower()
        if self.boost_terms and any(term in entity_text_lower for term in self.boost_terms):
            similarity = min(1.0, similarity + 0.3)
            if self.debug:
                print(f"DEBUG negation_refuter: Boosted similarity due to term match (new score={similarity:.3f})")

        if self.debug:
            print(f"DEBUG negation_refuter: Semantic similarity between '{claim_text[:30]}...' and '{entity_text}' = {similarity:.3f}")
        return similarity

    def validate(self, claim: Claim, evidence: List[EvidenceSpan], transcript: str) -> Disposition:
        if self.debug:
            print(f"DEBUG negation_refuter: Processing claim '{claim.text[:50]}...'")
        
        claim_is_negated = self._is_claim_negated(claim.text)
        if self.debug:
            print(f"DEBUG negation_refuter: Claim negation status: {claim_is_negated}")
        
        doc = self.nlp(transcript)
        if self.debug:
            print(f"DEBUG negation_refuter: Found {len(doc.ents)} entities in transcript")

        best_score = 0.0
        best_entity = None
        negated_count = 0

        for ent in doc.ents:
            if not hasattr(ent._, "negex") or not ent._.negex:
                continue

            sentence = self._extract_sentence_with_entity(transcript, ent.text)
            if '?' in sentence:
                if self.debug:
                    print(f"DEBUG negation_refuter: Skipping question: '{sentence}'")
                continue

            negated_count += 1
            if self.debug:
                print(f"DEBUG negation_refuter: Negated entity #{negated_count}: '{ent.text}' in sentence: '{sentence}'")

            score = self._entity_match_score(claim.text, sentence)

            if score > 0.1 and self.debug:
                print(f"DEBUG negation_refuter: Negated entity '{ent.text}' vs claim, score={score:.3f}")

            if score > best_score:
                best_score = score
                best_entity = ent.text

        if self.debug:
            print(f"DEBUG negation_refuter: Found {negated_count} negated entities, best_score={best_score:.3f}, threshold={self.match_threshold}")

        if best_score >= self.match_threshold:
            if claim_is_negated:
                return Disposition(
                    claim=claim,
                    verdict="supported",
                    evidence=[],
                    validator=self.name,
                    explanation=f"Double negative: both claim and transcript express negation, indicating agreement (score={best_score:.2f})"
                )
            else:
                return Disposition(
                    claim=claim,
                    verdict="refuted",
                    evidence=[],
                    validator=self.name,
                    explanation=f"Claim contradicts negated entity in transcript: '{best_entity}' (score={best_score:.2f})"
                )

        return Disposition(
            claim=claim,
            verdict="insufficient_evidence",
            evidence=[],
            validator=self.name,
            explanation="No negated entities matched claim"
        )
