"""
Shared data types for the checker package.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class Claim:
    """Represents a single claim extracted from a summary field."""
    text: str
    field: str
    confidence: float = 1.0
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EvidenceSpan:
    """Represents a span of text from the transcript that serves as evidence."""
    text: str
    start_idx: int
    end_idx: int
    score: float = 1.0


@dataclass
class ValidatorResult:
    """Result from a single validator."""
    validator: str
    verdict: str
    explanation: Optional[str] = None
    score: Optional[float] = None


@dataclass
class Disposition:
    """
    Represents the validation result for a single claim.
    
    Verdict can be:
    - "supported": Evidence supports the claim
    - "refuted": Evidence contradicts the claim
    - "insufficient_evidence": Not enough evidence to determine
    """
    claim: Claim
    verdict: str
    evidence: List[EvidenceSpan] = field(default_factory=list)
    validator: str = "unknown"
    explanation: Optional[str] = None
    validator_results: List[ValidatorResult] = field(default_factory=list)


@dataclass
class Report:
    """
    Complete verification report for a summary.
    """
    dispositions: List[Disposition] = field(default_factory=list)
    summary_fields: Dict[str, Any] = field(default_factory=dict)
    overall_score: float = 0.0
    missing_claims: List[str] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary format."""
        return {
            "dispositions": [
                {
                    "claim": {
                        "text": d.claim.text,
                        "field": d.claim.field,
                        "confidence": d.claim.confidence
                    },
                    "verdict": d.verdict,
                    "evidence": [
                        {
                            "text": e.text,
                            "start_idx": e.start_idx,
                            "end_idx": e.end_idx,
                            "score": e.score
                        }
                        for e in d.evidence
                    ],
                    "validator": d.validator,
                    "explanation": d.explanation,
                    "validator_results": [
                        {
                            "validator": vr.validator,
                            "verdict": vr.verdict,
                            "explanation": vr.explanation,
                            "score": vr.score
                        }
                        for vr in d.validator_results
                    ]
                }
                for d in self.dispositions
            ],
            "summary_fields": self.summary_fields,
            "overall_score": self.overall_score,
            "missing_claims": self.missing_claims,
            "metadata": self.metadata
        }
