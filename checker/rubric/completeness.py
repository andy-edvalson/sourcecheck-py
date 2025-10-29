"""
Completeness checker for required fields.
"""
from typing import List, Dict, Any


def check_completeness(
    summary: Dict[str, Any],
    schema: Dict[str, Any]
) -> List[str]:
    """
    Check if all required fields are present and non-empty in the summary.
    
    Args:
        summary: Summary dictionary with field values
        schema: Schema configuration defining required fields
    
    Returns:
        List of missing or empty required field names
    """
    missing_fields = []
    
    fields = schema.get('fields', {})
    
    for field_name, field_config in fields.items():
        is_required = field_config.get('required', False)
        
        if is_required:
            # Check if field exists and is non-empty
            if field_name not in summary:
                missing_fields.append(field_name)
            elif not summary[field_name]:
                # Field exists but is empty/None/False
                missing_fields.append(field_name)
            elif isinstance(summary[field_name], str) and not summary[field_name].strip():
                # Field is whitespace-only string
                missing_fields.append(field_name)
    
    return missing_fields


def calculate_completeness_score(
    summary: Dict[str, Any],
    schema: Dict[str, Any]
) -> float:
    """
    Calculate a completeness score based on required fields.
    
    Args:
        summary: Summary dictionary with field values
        schema: Schema configuration
    
    Returns:
        Score between 0.0 and 1.0, where 1.0 is fully complete
    """
    fields = schema.get('fields', {})
    required_fields = [
        name for name, config in fields.items()
        if config.get('required', False)
    ]
    
    if not required_fields:
        return 1.0
    
    missing = check_completeness(summary, schema)
    present_count = len(required_fields) - len(missing)
    
    return present_count / len(required_fields)
