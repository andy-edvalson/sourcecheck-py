"""
Shared data types for the checker package.

Domain-agnostic types for validating structured documents against source material.
"""
from typing import List, Literal, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, computed_field


# Type aliases for common literals
VerdictType = Literal["supported", "refuted", "insufficient_evidence"]
SeverityType = Literal["critical", "high", "medium", "low"]


class Claim(BaseModel):
    """
    A statement extracted from a structured document.
    
    Claims are extracted from structured documents (e.g., summaries, reports)
    and validated against source material (e.g., transcripts, documents).
    """
    field: str = Field(..., description="Source field name")
    text: str = Field(..., min_length=1, description="Claim text")
    value: Optional[str] = Field(None, description="Extracted value")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    model_config = {"frozen": False}  # Allow metadata updates


class EvidenceSpan(BaseModel):
    """
    A span of text from source material that serves as evidence.
    
    Evidence spans are retrieved from source material to support or refute claims.
    """
    text: str = Field(..., min_length=1, description="Evidence text")
    start_idx: int = Field(..., ge=0, description="Start index in source")
    end_idx: int = Field(..., gt=0, description="End index in source")
    score: float = Field(default=1.0, ge=0.0, le=1.0, description="Relevance score")
    
    @field_validator('end_idx')
    @classmethod
    def validate_indices(cls, v, info):
        """Ensure end_idx is greater than start_idx."""
        if 'start_idx' in info.data and v <= info.data['start_idx']:
            raise ValueError('end_idx must be greater than start_idx')
        return v


class ValidatorResult(BaseModel):
    """
    Result from a single validator.
    
    Each validator produces a verdict with explanation and optional score.
    """
    validator: str = Field(..., min_length=1, description="Validator name")
    verdict: VerdictType = Field(..., description="Validation verdict")
    explanation: str = Field(default="", description="Explanation of verdict")
    score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class Disposition(BaseModel):
    """
    Validation result for a single claim.
    
    A disposition represents the final verdict for a claim after running
    one or more validators and examining evidence.
    
    Verdict meanings:
    - "supported": Evidence supports the claim
    - "refuted": Evidence contradicts the claim
    - "insufficient_evidence": Not enough evidence to determine
    """
    claim: Claim = Field(..., description="The claim being validated")
    verdict: VerdictType = Field(..., description="Final verdict")
    evidence: List[EvidenceSpan] = Field(default_factory=list, description="Supporting evidence")
    validator: str = Field(default="unknown", description="Primary validator used")
    explanation: str = Field(default="", description="Explanation of verdict")
    validator_results: List[ValidatorResult] = Field(
        default_factory=list,
        description="Results from all validators"
    )
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Overall confidence")
    quality_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Quality score (1.0 = all validators agree, lower = disagreement/issues)"
    )
    
    @computed_field
    @property
    def has_evidence(self) -> bool:
        """Check if any evidence was found."""
        return len(self.evidence) > 0
    
    @computed_field
    @property
    def evidence_count(self) -> int:
        """Count of evidence spans."""
        return len(self.evidence)


class Issue(BaseModel):
    """
    Represents a detected issue in the verification process.
    
    Issues can represent omissions, gaps, errors, or other problems
    detected during validation. The category and severity are domain-specific.
    """
    category: str = Field(..., description="Issue category/type")
    severity: SeverityType = Field(..., description="Issue severity level")
    detail: str = Field(..., description="Detailed description")
    field: Optional[str] = Field(None, description="Related field name")
    suggestion: Optional[str] = Field(None, description="Suggested resolution")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class VerificationReport(BaseModel):
    """
    Complete verification report for a structured document.
    
    The report contains all dispositions (claim validations), detected issues,
    and overall statistics about the verification process.
    """
    dispositions: List[Disposition] = Field(
        default_factory=list,
        description="Validation results for all claims"
    )
    source_fields: Union[Dict[str, Any], str] = Field(
        default_factory=dict,
        description="Original structured document fields or raw text"
    )
    overall_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall verification score (pass/fail)"
    )
    quality_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Overall quality score (validator agreement, completeness)"
    )
    missing_claims: List[str] = Field(
        default_factory=list,
        description="Claims that should exist but are missing"
    )
    issues: List[Issue] = Field(
        default_factory=list,
        description="Detected issues (omissions, gaps, errors)"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @computed_field
    @property
    def total_claims(self) -> int:
        """Total number of claims validated."""
        return len(self.dispositions)
    
    @computed_field
    @property
    def supported_count(self) -> int:
        """Number of supported claims."""
        return sum(1 for d in self.dispositions if d.verdict == "supported")
    
    @computed_field
    @property
    def refuted_count(self) -> int:
        """Number of refuted claims."""
        return sum(1 for d in self.dispositions if d.verdict == "refuted")
    
    @computed_field
    @property
    def insufficient_count(self) -> int:
        """Number of claims with insufficient evidence."""
        return sum(1 for d in self.dispositions if d.verdict == "insufficient_evidence")
    
    @computed_field
    @property
    def support_rate(self) -> float:
        """Percentage of claims that are supported (0.0 to 1.0)."""
        if self.total_claims == 0:
            return 0.0
        return round(self.supported_count / self.total_claims, 3)
    
    @computed_field
    @property
    def critical_issues(self) -> List[Issue]:
        """Filter issues by critical severity."""
        return [i for i in self.issues if i.severity == "critical"]
    
    @computed_field
    @property
    def high_issues(self) -> List[Issue]:
        """Filter issues by high severity."""
        return [i for i in self.issues if i.severity == "high"]
    
    def model_dump_dict(self) -> Dict[str, Any]:
        """
        Convert report to dictionary format (backward compatibility).
        
        This method provides compatibility with the old to_dict() method.
        """
        return self.model_dump()
