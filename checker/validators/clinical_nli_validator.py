"""
Clinical NLI Validator using DeBERTa-base MNLI.
Detects entailment, neutral, or contradiction between claim and evidence.
"""

from typing import List, Tuple
from .base import Validator
from .registry import register_validator
from ..types import Claim, EvidenceSpan, Disposition

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import spacy
from negspacy.negation import Negex


@register_validator("clinical_nli_validator")
class ClinicalNLIValidator(Validator):
    """
    Lightweight entailment-based validator using DeBERTa-v3 MNLI.
    Determines if evidence contradicts or supports the claim.
    
    Key features:
    - Detects contradictions to refute false claims
    - Detects entailment to support true claims
    - Uses confidence thresholds to avoid false refutations
    - Singleton model loading for performance
    """
    
    # Class-level model cache (singleton pattern)
    _model = None
    _tokenizer = None
    _device = None
    _nlp = None

    def __init__(self, config: dict = None, debug: bool = False):
        super().__init__(config, debug)
        
        # Configuration
        cfg = self.config or {}
        self.model_name = cfg.get("model_name", "microsoft/deberta-v3-base")
        self.confidence_threshold = cfg.get("confidence_threshold", 0.3)
        self.use_gpu = cfg.get("use_gpu", torch.cuda.is_available())
        self.max_evidence_spans = cfg.get("max_evidence_spans", 5)
        
        # Load models (cached at class level)
        self._ensure_model_loaded()
        self._ensure_negation_model_loaded()

    @classmethod
    def _ensure_model_loaded(cls):
        """Load NLI model once and cache at class level."""
        if cls._model is None:
            print(f"Loading NLI model: microsoft/deberta-base-mnli")
            cls._tokenizer = AutoTokenizer.from_pretrained("microsoft/deberta-base-mnli")
            cls._model = AutoModelForSequenceClassification.from_pretrained("microsoft/deberta-base-mnli")
            cls._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            cls._model.to(cls._device)
            cls._model.eval()
            print(f"NLI model loaded on {cls._device}")

    @classmethod
    def _ensure_negation_model_loaded(cls):
        """Load negation detection model once and cache at class level."""
        if cls._nlp is None:
            print(f"Loading negation detection model for clinical_nli_validator")
            cls._nlp = spacy.load("en_core_sci_md")
            cls._nlp.add_pipe("negex", config={"chunk_prefix": ["no", "denies", "without", "never", "negative"]})

    @property
    def name(self) -> str:
        return "clinical_nli_validator"

    def _is_negated(self, text: str) -> bool:
        """Check if text contains negation"""
        doc = self._nlp(text)
        for ent in doc.ents:
            if hasattr(ent._, "negex") and ent._.negex:
                return True
        for token in doc:
            if token.dep_ == "neg":
                return True
        return False

    def _classify_pair(self, premise: str, hypothesis: str) -> Tuple[str, float]:
        """
        Classify relationship between premise and hypothesis.
        
        Returns:
            Tuple of (label, confidence) where label is one of:
            - "entailment": hypothesis follows from premise
            - "neutral": no clear relationship
            - "contradiction": hypothesis contradicts premise
        """
        inputs = self._tokenizer(
            premise, hypothesis,
            return_tensors="pt",
            truncation=True,
            max_length=512
        )
        
        # Move to device
        inputs = {k: v.to(self._device) for k, v in inputs.items()}
        
        with torch.no_grad():
            logits = self._model(**inputs).logits
        
        # Get probabilities and prediction
        probs = torch.softmax(logits, dim=1)[0]
        label_id = torch.argmax(probs).item()
        confidence = probs[label_id].item()
        
        label = ["entailment", "neutral", "contradiction"][label_id]
        return label, confidence

    def validate(
        self,
        claim: Claim,
        evidence: List[EvidenceSpan],
        transcript: str
    ) -> Disposition:
        """
        Validate claim using NLI to detect entailment or contradiction.
        Handles double negatives before NLI classification.
        
        Args:
            claim: Claim to validate
            evidence: Evidence spans from retriever
            transcript: Full transcript (not used directly)
        
        Returns:
            Disposition with verdict: supported, refuted, or insufficient_evidence
        """
        if not evidence:
            return Disposition(
                claim=claim,
                verdict="insufficient_evidence",
                evidence=[],
                validator=self.name,
                explanation="No evidence spans to validate claim against."
            )

        claim_is_negated = self._is_negated(claim.text)

        verdict = "insufficient_evidence"
        explanation = ""
        best_evidence = None
        best_confidence = 0.0
        
        # Check up to max_evidence_spans
        for ev in evidence[:self.max_evidence_spans]:
            evidence_is_negated = self._is_negated(ev.text)
            
            # Handle double negative case before NLI
            if claim_is_negated and evidence_is_negated:
                verdict = "supported"
                explanation = f"Double negative: both claim and evidence express negation, indicating agreement"
                best_evidence = ev
                best_confidence = 1.0
                break
            
            relation, confidence = self._classify_pair(ev.text, claim.text)
            
            # High-confidence contradiction = refute claim
            if relation == "contradiction" and confidence >= self.confidence_threshold:
                verdict = "refuted"
                explanation = f"Claim contradicts evidence (confidence={confidence:.2f}): \"{ev.text[:100]}...\""
                best_evidence = ev
                best_confidence = confidence
                break  # Stop at first high-confidence contradiction
            
            # High-confidence entailment = support claim
            elif relation == "entailment" and confidence >= self.confidence_threshold:
                if confidence > best_confidence:
                    verdict = "supported"
                    explanation = f"Claim supported by evidence (confidence={confidence:.2f}): \"{ev.text[:100]}...\""
                    best_evidence = ev
                    best_confidence = confidence
                # Continue checking for contradictions
            
            # Neutral or low confidence - keep checking
            else:
                continue

        if not explanation:
            explanation = f"No strong entailment or contradiction found (threshold={self.confidence_threshold})"

        return Disposition(
            claim=claim,
            verdict=verdict,
            evidence=[best_evidence] if best_evidence else evidence[:1],
            validator=self.name,
            explanation=explanation
        )
