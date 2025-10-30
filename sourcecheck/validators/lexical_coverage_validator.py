"""
Lexical Coverage Validator.

Detects hallucinations by measuring lexical overlap between claims and evidence.
Uses tokenization, stopword filtering, and n-gram analysis.
"""
import re
from typing import List
from .base import Validator
from .registry import register_validator
from ..types import Claim, EvidenceSpan, Disposition


@register_validator("lexical_coverage_validator")
class LexicalCoverageValidator(Validator):
    """
    Detects hallucinations via lexical coverage and fabricated n-grams.
    
    Refutes claims with low lexical overlap or significant fabricated phrases.
    """
    
    def __init__(self, config=None, debug=False):
        """
        Initialize lexical coverage validator.
        
        Config options:
            min_coverage: Minimum lexical overlap required (default: 0.35)
            min_phrase_words: Minimum words in fabricated phrase (default: 2)
            fabrication_penalty: Weight for fabricated phrases (default: 0.5)
        """
        super().__init__(config, debug)
        self.min_coverage = self.config.get("min_coverage", 0.20)  # Lowered from 0.35 to handle paraphrasing
        self.min_phrase_words = self.config.get("min_phrase_words", 2)
        self.fabrication_penalty = self.config.get("fabrication_penalty", 0.5)
        self.max_penalty = self.config.get("max_penalty", 0.5)  # Cap penalty to avoid over-penalization
        self.entity_boost = self.config.get("entity_boost", 0.20)  # Boost for matching core entities
        self.use_char_ngrams = self.config.get("use_char_ngrams", False)  # Enable character n-gram fallback
        self.char_ngram_size = self.config.get("char_ngram_size", 3)  # Trigrams by default
        self.char_ngram_weight = self.config.get("char_ngram_weight", 0.3)  # 30% weight for char n-grams
        
        # Stopwords - initialized once for performance
        self.stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 
            'for', 'is', 'was', 'were', 'are', 'been', 'be', 'have', 'has',
            'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'may', 'might', 'must', 'can', 'of', 'with', 'from', 'by', 'as'
        }
    
    @property
    def name(self) -> str:
        """Return validator name."""
        return "lexical_coverage_validator"
    
    def validate(
        self,
        claim: Claim,
        evidence: List[EvidenceSpan],
        transcript: str
    ) -> Disposition:
        """
        Validate claim using lexical coverage analysis.
        
        Args:
            claim: Claim to validate
            evidence: Retrieved evidence spans
            transcript: Full transcript (not used)
        
        Returns:
            Disposition with verdict and coverage metrics
        """
        if not evidence:
            return Disposition(
                claim=claim,
                verdict="insufficient_evidence",
                evidence=[],
                validator=self.name,
                explanation="No evidence available for lexical coverage analysis"
            )
        
        claim_text = claim.text
        # Aggregate all evidence spans with proper whitespace handling
        evidence_text = " ".join(e.text.strip() for e in evidence if e.text)
        
        # Check for empty evidence text
        if not evidence_text.strip():
            return Disposition(
                claim=claim,
                verdict="insufficient_evidence",
                evidence=evidence,
                validator=self.name,
                explanation="Evidence provided but contains no text content"
            )
        
        # Calculate base coverage
        coverage = self._calculate_coverage(claim_text, evidence_text)
        
        # Find fabricated phrases
        fabricated = self._find_fabricated_phrases(claim_text, evidence_text)
        
        # Apply fabrication penalty with cap to avoid over-penalization
        if fabricated:
            fabricated_ratio = len(fabricated) / max(len(claim_text.split()) - 1, 1)
            penalty = min(self.fabrication_penalty * fabricated_ratio, self.max_penalty)
            adjusted_coverage = coverage * (1 - penalty)
        else:
            adjusted_coverage = coverage
        
        # Determine verdict
        if adjusted_coverage < self.min_coverage:
            verdict = "refuted"
            explanation = (
                f"Low lexical coverage ({coverage:.2f}, adjusted: {adjusted_coverage:.2f}). "
                f"Fabricated phrases: {', '.join(fabricated[:3]) if fabricated else 'none'}"
            )
        else:
            verdict = "supported"
            explanation = (
                f"Adequate lexical coverage ({coverage:.2f}). "
                f"Fabricated phrases: {', '.join(fabricated[:3]) if fabricated else 'none'}"
            )
        
        # Return disposition with metadata for arbitration
        return Disposition(
            claim=claim,
            verdict=verdict,
            evidence=evidence,
            validator=self.name,
            explanation=explanation,
            metadata={
                "coverage": coverage,
                "adjusted_coverage": adjusted_coverage,
                "fabricated_phrases": fabricated,
                "fabricated_count": len(fabricated)
            }
        )
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text with proper normalization.
        
        - Lowercase
        - Extract alphanumeric tokens
        - Remove stopwords
        - Handle contractions (e.g., "don't")
        
        Args:
            text: Text to tokenize
        
        Returns:
            List of normalized tokens
        """
        # Extract words (alphanumeric + apostrophes for contractions)
        words = re.findall(r"\b[a-z0-9']+\b", text.lower())
        
        # Filter stopwords
        return [w for w in words if w not in self.stopwords]
    
    def _calculate_coverage(self, claim: str, evidence: str) -> float:
        """
        Calculate lexical coverage (Jaccard similarity of content words).
        
        Optionally uses hybrid word + character n-gram approach for robustness
        to morphological variations and paraphrasing.
        
        Args:
            claim: Claim text
            evidence: Evidence text (aggregated)
        
        Returns:
            Coverage score between 0.0 and 1.0
        """
        claim_words = set(self._tokenize(claim))
        evidence_words = set(self._tokenize(evidence))
        
        if not claim_words:
            return 1.0  # Empty claim = perfect coverage
        
        # Calculate word-level coverage
        overlap = claim_words & evidence_words
        word_coverage = len(overlap) / len(claim_words)
        
        # Optionally blend with character n-gram coverage
        if self.use_char_ngrams:
            char_coverage = self._char_ngram_coverage(claim, evidence)
            # Weighted blend: word coverage gets more weight
            coverage = (1 - self.char_ngram_weight) * word_coverage + self.char_ngram_weight * char_coverage
        else:
            coverage = word_coverage
        
        # Boost for core entity matches (handles paraphrasing)
        entities = self._extract_core_entities(claim, evidence)
        if entities['age_match'] and entities['gender_match']:
            coverage = min(coverage + self.entity_boost, 1.0)
        
        return coverage
    
    def _char_ngram_coverage(self, claim: str, evidence: str) -> float:
        """
        Calculate character n-gram coverage for morphological robustness.
        
        Handles variations like:
        - "tripped" vs "tripping" vs "trip"
        - "woman" vs "women"
        - Minor typos
        
        Args:
            claim: Claim text
            evidence: Evidence text
        
        Returns:
            Coverage score between 0.0 and 1.0
        """
        # Defensive: if text is too short for n-grams, fall back to 0
        if len(claim) < self.char_ngram_size or len(evidence) < self.char_ngram_size:
            return 0.0
        
        def char_ngrams(text: str, n: int) -> set:
            """Extract character n-grams from text."""
            # Normalize: lowercase, remove non-alphanumeric
            normalized = re.sub(r'[^a-z0-9]+', ' ', text.lower())
            ngrams = set()
            for word in normalized.split():
                if len(word) >= n:
                    for i in range(len(word) - n + 1):
                        ngrams.add(word[i:i+n])
            return ngrams
        
        claim_ngrams = char_ngrams(claim, self.char_ngram_size)
        evidence_ngrams = char_ngrams(evidence, self.char_ngram_size)
        
        if not claim_ngrams:
            return 1.0
        if not evidence_ngrams:
            return 0.0
        
        overlap = claim_ngrams & evidence_ngrams
        return len(overlap) / len(claim_ngrams)
    
    def _extract_core_entities(self, claim: str, evidence: str) -> dict:
        """
        Extract and match core entities (age, gender) between claim and evidence.
        
        Handles paraphrasing like:
        - "56-year-old woman" vs "56 female"
        - "elderly man" vs "male"
        
        Args:
            claim: Claim text
            evidence: Evidence text
        
        Returns:
            Dict with age_match and gender_match booleans
        """
        claim_lower = claim.lower()
        evidence_lower = evidence.lower()
        
        # Check for age match (numbers 1-120)
        claim_ages = set(re.findall(r'\b(\d{1,3})\b', claim))
        evidence_ages = set(re.findall(r'\b(\d{1,3})\b', evidence))
        # Filter to reasonable ages
        claim_ages = {int(a) for a in claim_ages if 1 <= int(a) <= 120}
        evidence_ages = {int(a) for a in evidence_ages if 1 <= int(a) <= 120}
        age_match = bool(claim_ages & evidence_ages)
        
        # Check for gender match (with synonyms)
        gender_terms = {
            'male': ['male', 'man', 'men', 'boy', 'gentleman', 'he', 'his', 'him'],
            'female': ['female', 'woman', 'women', 'girl', 'lady', 'she', 'her', 'hers']
        }
        
        gender_match = False
        for gender, terms in gender_terms.items():
            claim_has = any(term in claim_lower for term in terms)
            evidence_has = any(term in evidence_lower for term in terms)
            if claim_has and evidence_has:
                gender_match = True
                break
        
        return {
            'age_match': age_match,
            'gender_match': gender_match
        }
    
    def _find_fabricated_phrases(self, claim: str, evidence: str) -> List[str]:
        """
        Find 2-word phrases in claim that don't appear in evidence.
        
        A phrase is considered fabricated if:
        1. The exact phrase doesn't appear in evidence
        2. BOTH individual words are missing from evidence
        
        Args:
            claim: Claim text
            evidence: Evidence text (aggregated)
        
        Returns:
            List of fabricated phrases
        """
        fabricated = []
        words = self._tokenize(claim)
        evidence_lower = evidence.lower()
        
        # Check 2-word phrases
        for i in range(len(words) - 1):
            phrase = f"{words[i]} {words[i+1]}"
            
            # Check if phrase appears in evidence
            if phrase not in evidence_lower:
                # Check if BOTH words are missing (strong signal of fabrication)
                if words[i] not in evidence_lower and words[i+1] not in evidence_lower:
                    fabricated.append(phrase)
        
        return fabricated
