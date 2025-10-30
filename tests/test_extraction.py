"""
Tests for claim extraction functionality.
"""
import pytest
from sourcecheck.claimextractor.configurable import extract_claims_configurable
from sourcecheck.config import Config


@pytest.fixture
def sample_schema():
    """Sample schema for testing."""
    return {
        'fields': {
            'chief_complaint': {
                'type': 'string',
                'required': True,
                'criticality': 'critical',
                'extraction_method': 'single_value'
            },
            'medications': {
                'type': 'list',
                'required': False,
                'criticality': 'high',
                'extraction_method': 'delimited',
                'delimiter': '|'
            },
            'history': {
                'type': 'string',
                'required': False,
                'criticality': 'medium',
                'extraction_method': 'bullet_list'
            }
        }
    }


@pytest.fixture
def sample_summary():
    """Sample summary for testing."""
    return {
        'chief_complaint': 'Chest pain for 2 days',
        'medications': 'Aspirin 81mg daily | Lisinopril 10mg daily',
        'history': '- No significant medical history\n- No known allergies'
    }


def test_extract_single_value_claim(sample_schema, sample_summary):
    """Test extraction of single value claim."""
    claims = extract_claims_configurable(
        summary=sample_summary,
        schema=sample_schema
    )
    
    # Should extract chief_complaint as single claim
    cc_claims = [c for c in claims if c.field == 'chief_complaint']
    assert len(cc_claims) == 1
    assert cc_claims[0].text == 'Chest pain for 2 days'
    assert cc_claims[0].criticality == 'critical'


def test_extract_delimited_claims(sample_schema, sample_summary):
    """Test extraction of delimited claims."""
    claims = extract_claims_configurable(
        summary=sample_summary,
        schema=sample_schema
    )
    
    # Should extract 2 medication claims
    med_claims = [c for c in claims if c.field == 'medications']
    assert len(med_claims) == 2
    assert any('Aspirin' in c.text for c in med_claims)
    assert any('Lisinopril' in c.text for c in med_claims)


def test_extract_bullet_list_claims(sample_schema, sample_summary):
    """Test extraction of bullet list claims."""
    claims = extract_claims_configurable(
        summary=sample_summary,
        schema=sample_schema
    )
    
    # Should extract 2 history claims
    hist_claims = [c for c in claims if c.field == 'history']
    assert len(hist_claims) == 2
    assert any('medical history' in c.text for c in hist_claims)
    assert any('allergies' in c.text for c in hist_claims)


def test_extract_empty_field(sample_schema):
    """Test extraction with empty field."""
    summary = {
        'chief_complaint': 'Chest pain',
        'medications': '',
        'history': ''
    }
    
    claims = extract_claims_configurable(
        summary=summary,
        schema=sample_schema
    )
    
    # Should only extract chief_complaint
    assert len(claims) == 1
    assert claims[0].field == 'chief_complaint'


def test_extract_missing_field(sample_schema):
    """Test extraction with missing field."""
    summary = {
        'chief_complaint': 'Chest pain'
    }
    
    claims = extract_claims_configurable(
        summary=summary,
        schema=sample_schema
    )
    
    # Should only extract chief_complaint
    assert len(claims) == 1
    assert claims[0].field == 'chief_complaint'


def test_extract_with_metadata(sample_schema, sample_summary):
    """Test extraction with metadata."""
    meta = {'patient_id': '12345', 'encounter_date': '2024-01-01'}
    
    claims = extract_claims_configurable(
        summary=sample_summary,
        schema=sample_schema,
        meta=meta
    )
    
    # All claims should have metadata
    assert all(c.metadata is not None for c in claims)
    assert all(c.metadata.get('patient_id') == '12345' for c in claims)
