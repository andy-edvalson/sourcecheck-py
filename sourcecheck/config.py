"""
Configuration manager for schema and policy dictionaries.
"""
from typing import Dict, Any, Optional


class Config:
    """Manages schema and policy configurations (as dicts)."""
    
    def __init__(self, schema: Dict[str, Any], policies: Dict[str, Any]):
        """
        Initialize configuration with schema and policies dicts.
        
        Args:
            schema: Schema configuration dict
            policies: Policies configuration dict
        """
        if not isinstance(schema, dict):
            raise TypeError(f"schema must be dict, got {type(schema)}")
        if not isinstance(policies, dict):
            raise TypeError(f"policies must be dict, got {type(policies)}")
        
        self.schema = schema
        self.policies = policies
        
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate that required configuration keys exist."""
        # Validate schema
        if 'version' not in self.schema:
            raise ValueError("schema.yaml missing 'version' field")
        if 'fields' not in self.schema:
            raise ValueError("schema.yaml missing 'fields' section")
        
        # Validate policies
        if 'version' not in self.policies:
            raise ValueError("policies.yaml missing 'version' field")
        if 'validators' not in self.policies:
            raise ValueError("policies.yaml missing 'validators' section")
    
    def get_field_config(self, field_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific field."""
        return self.schema.get('fields', {}).get(field_name)
    
    def get_validators_for_field(self, field_name: str) -> list:
        """Get list of validator names for a specific field."""
        return self.policies.get('validators', {}).get(field_name, [])
    
    def get_required_fields(self) -> list:
        """Get list of required field names."""
        fields = self.schema.get('fields', {})
        return [
            name for name, config in fields.items()
            if config.get('required', False)
        ]
    
    def get_criticality_weight(self, criticality: str) -> float:
        """Get weight for a criticality level."""
        weights = self.schema.get('criticality_weights', {})
        return weights.get(criticality, 0.5)
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a policy setting value."""
        return self.policies.get('settings', {}).get(key, default)
    
    def get_policy(self, key: str, default: Any = None) -> Any:
        """Get a top-level policy value (e.g., retriever, retriever_config)."""
        return self.policies.get(key, default)
    
    def get_all_fields(self) -> Dict[str, Dict[str, Any]]:
        """Get all field configurations."""
        return self.schema.get('fields', {})
