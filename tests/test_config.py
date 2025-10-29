"""
Tests for configuration loading.
"""
import pytest
from pathlib import Path
from checker.config import Config


def test_config_loads_successfully():
    """Test that config files load without errors."""
    config = Config(
        schema_path="checker/schema.yaml",
        policies_path="checker/policies.yaml"
    )
    
    assert config.schema is not None
    assert config.policies is not None
    assert 'version' in config.schema
    assert 'version' in config.policies


def test_get_field_config():
    """Test retrieving field configuration."""
    config = Config(
        schema_path="checker/schema.yaml",
        policies_path="checker/policies.yaml"
    )
    
    field_config = config.get_field_config('chief_complaint')
    assert field_config is not None
    assert field_config['type'] == 'string'
    assert field_config['required'] is True
    assert field_config['criticality'] == 'high'


def test_get_validators_for_field():
    """Test retrieving validators for a field."""
    config = Config(
        schema_path="checker/schema.yaml",
        policies_path="checker/policies.yaml"
    )
    
    validators = config.get_validators_for_field('chief_complaint')
    assert isinstance(validators, list)
    assert 'always_true' in validators


def test_get_required_fields():
    """Test retrieving required fields."""
    config = Config(
        schema_path="checker/schema.yaml",
        policies_path="checker/policies.yaml"
    )
    
    required = config.get_required_fields()
    assert isinstance(required, list)
    assert 'chief_complaint' in required
    assert 'assessment' in required


def test_get_criticality_weight():
    """Test retrieving criticality weights."""
    config = Config(
        schema_path="checker/schema.yaml",
        policies_path="checker/policies.yaml"
    )
    
    high_weight = config.get_criticality_weight('high')
    assert high_weight == 1.0
    
    medium_weight = config.get_criticality_weight('medium')
    assert medium_weight == 0.6


def test_get_setting():
    """Test retrieving policy settings."""
    config = Config(
        schema_path="checker/schema.yaml",
        policies_path="checker/policies.yaml"
    )
    
    fail_fast = config.get_setting('fail_fast')
    assert fail_fast is False
    
    max_spans = config.get_setting('max_evidence_spans')
    assert max_spans == 5
    
    # Test default value
    unknown = config.get_setting('unknown_setting', 'default')
    assert unknown == 'default'
