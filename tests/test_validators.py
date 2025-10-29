"""
Tests for validator system.
"""
import pytest
from checker.types import Claim, EvidenceSpan, Disposition
from checker.validators import (
    create_validator,
    list_validators,
    get_validator
)
from checker.validators.always_true import AlwaysTrueValidator


def test_always_true_validator_registered():
    """Test that always_true validator is registered."""
    validators = list_validators()
    assert 'always_true' in validators


def test_create_always_true_validator():
    """Test creating an always_true validator instance."""
    validator = create_validator('always_true')
    assert validator is not None
    assert isinstance(validator, AlwaysTrueValidator)
    assert validator.name == 'always_true'


def test_always_true_validator_always_supports():
    """Test that always_true validator always returns supported."""
    validator = create_validator('always_true')
    
    claim = Claim(
        text="Patient has chest pain",
        field="chief_complaint"
    )
    
    evidence = [
        EvidenceSpan(
            text="Patient reports chest pain",
            start_idx=0,
            end_idx=27,
            score=0.9
        )
    ]
    
    disposition = validator.validate(
        claim=claim,
        evidence=evidence,
        transcript="Patient reports chest pain for 2 days"
    )
    
    assert disposition.verdict == "supported"
    assert disposition.claim == claim
    assert disposition.validator == "always_true"


def test_always_true_validator_with_no_evidence():
    """Test always_true validator with no evidence."""
    validator = create_validator('always_true')
    
    claim = Claim(
        text="Patient has diabetes",
        field="past_medical_history"
    )
    
    disposition = validator.validate(
        claim=claim,
        evidence=[],
        transcript="Patient has hypertension"
    )
    
    # Should still return supported even with no evidence
    assert disposition.verdict == "supported"


def test_get_validator():
    """Test getting validator class."""
    validator_class = get_validator('always_true')
    assert validator_class is not None
    assert validator_class == AlwaysTrueValidator


def test_create_validator_with_invalid_name():
    """Test creating validator with invalid name raises error."""
    with pytest.raises(ValueError, match="not found in registry"):
        create_validator('nonexistent_validator')
