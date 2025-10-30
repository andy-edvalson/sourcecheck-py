"""
Tests for main Checker orchestrator.
"""
import pytest
from sourcecheck import Checker
from sourcecheck.types import Report


def test_checker_initialization():
    """Test that Checker initializes successfully."""
    checker = Checker(
        schema_path="sourcecheck/schema.yaml",
        policies_path="sourcecheck/policies.yaml"
    )
    
    assert checker.config is not None


def test_verify_summary_returns_report():
    """Test that verify_summary returns a Report object."""
    checker = Checker(
        schema_path="sourcecheck/schema.yaml",
        policies_path="sourcecheck/policies.yaml"
    )
    
    transcript = "Patient reports chest pain for 2 days. No fever or chills."
    summary = {
        "chief_complaint": "Chest pain for 2 days",
        "history_of_present_illness": "Patient has chest pain",
        "assessment": "Possible costochondritis",
        "plan": "Prescribe ibuprofen and follow up"
    }
    
    report = checker.verify_summary(transcript, summary)
    
    assert isinstance(report, Report)
    assert report.dispositions is not None
    assert report.summary_fields == summary
    assert isinstance(report.overall_score, float)
    assert 0.0 <= report.overall_score <= 1.0


def test_verify_summary_extracts_claims():
    """Test that claims are extracted from summary."""
    checker = Checker(
        schema_path="sourcecheck/schema.yaml",
        policies_path="sourcecheck/policies.yaml"
    )
    
    transcript = "Patient has hypertension and takes lisinopril."
    summary = {
        "chief_complaint": "High blood pressure",
        "medications": "Lisinopril 10mg daily"
    }
    
    report = checker.verify_summary(transcript, summary)
    
    # Should have extracted claims from both fields
    assert len(report.dispositions) > 0
    
    # Check that claims are from the correct fields
    fields = {d.claim.field for d in report.dispositions}
    assert 'chief_complaint' in fields or 'medications' in fields


def test_verify_summary_with_empty_summary():
    """Test verify_summary with empty summary."""
    checker = Checker(
        schema_path="sourcecheck/schema.yaml",
        policies_path="sourcecheck/policies.yaml"
    )
    
    transcript = "Patient has chest pain."
    summary = {}
    
    report = checker.verify_summary(transcript, summary)
    
    assert isinstance(report, Report)
    assert len(report.dispositions) == 0
    assert report.overall_score >= 0.0


def test_verify_summary_with_metadata():
    """Test verify_summary with metadata."""
    checker = Checker(
        schema_path="sourcecheck/schema.yaml",
        policies_path="sourcecheck/policies.yaml"
    )
    
    transcript = "Patient has chest pain."
    summary = {
        "chief_complaint": "Chest pain"
    }
    meta = {
        "patient_id": "12345",
        "encounter_date": "2025-10-28"
    }
    
    report = checker.verify_summary(transcript, summary, meta)
    
    assert report.metadata == meta


def test_report_to_dict():
    """Test that Report can be converted to dictionary."""
    checker = Checker(
        schema_path="sourcecheck/schema.yaml",
        policies_path="sourcecheck/policies.yaml"
    )
    
    transcript = "Patient has chest pain."
    summary = {
        "chief_complaint": "Chest pain"
    }
    
    report = checker.verify_summary(transcript, summary)
    report_dict = report.to_dict()
    
    assert isinstance(report_dict, dict)
    assert 'dispositions' in report_dict
    assert 'summary_fields' in report_dict
    assert 'overall_score' in report_dict
    assert 'missing_claims' in report_dict


def test_verify_summary_calculates_score():
    """Test that overall score is calculated."""
    checker = Checker(
        schema_path="sourcecheck/schema.yaml",
        policies_path="sourcecheck/policies.yaml"
    )
    
    transcript = "Patient has chest pain and hypertension."
    summary = {
        "chief_complaint": "Chest pain",
        "past_medical_history": "Hypertension",
        "assessment": "Chest pain evaluation",
        "plan": "Follow up in one week"
    }
    
    report = checker.verify_summary(transcript, summary)
    
    # With always_true validator, score should be high
    assert report.overall_score > 0.5
