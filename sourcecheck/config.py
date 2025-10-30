"""
Configuration loader for schema and policy files.
"""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Manages loading and accessing schema and policy configurations."""
    
    def __init__(self, schema_path: str, policies_path: str):
        """
        Initialize configuration loader.
        
        Args:
            schema_path: Path to schema.yaml file
            policies_path: Path to policies.yaml file
        """
        self.schema_path = Path(schema_path)
        self.policies_path = Path(policies_path)
        
        self.schema = self._load_yaml(self.schema_path)
        self.policies = self._load_yaml(self.policies_path)
        
        self._validate_config()
    
    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load YAML file and return parsed content."""
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        with open(path, 'r') as f:
            content = yaml.safe_load(f)
        
        if content is None:
            raise ValueError(f"Empty configuration file: {path}")
        
        return content
    
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
