"""
Configurable claim extractor that uses schema to determine extraction method.
"""
import re
from typing import List, Dict, Any, Optional
from ..types import Claim
from ..utils.path_resolver import PathResolver


def extract_claims_configurable(
    summary,  # Can be Dict[str, Any] or str
    schema: Dict[str, Any],
    meta: Optional[Dict[str, Any]] = None,
    debug: bool = False
) -> List[Claim]:
    """
    Extract claims from summary using schema-defined extraction methods.
    
    Supports path-based field resolution for nested structures and raw text.
    
    Args:
        summary: Summary dictionary with field values (may be nested) or raw string
        schema: Schema dict with extraction configuration per field
        meta: Optional metadata
        debug: Enable debug output (default: False)
    
    Returns:
        List of Claim objects
    """
    claims = []
    fields_config = schema.get('fields', {})
    
    if debug:
        print(f"DEBUG extract_claims_configurable: Processing {len(fields_config)} configured fields")
        print(f"DEBUG: Summary type: {type(summary).__name__}")
    
    for field_name, field_config in fields_config.items():
        # Use path resolution or direct access
        path = field_config.get('path')
        fallback_paths = field_config.get('fallback_paths', [])
        
        if path:
            # Use path resolution (handles all formats via path syntax)
            all_paths = [path] + fallback_paths
            field_value = PathResolver.resolve_with_fallbacks(summary, all_paths)
            if debug and field_value:
                print(f"DEBUG: Resolved '{field_name}' from path '{path}'")
        else:
            # Backward compatibility: direct field access
            if isinstance(summary, dict):
                field_value = summary.get(field_name)
            else:
                field_value = None
            if debug and field_value:
                print(f"DEBUG: Got '{field_name}' via direct access")
        
        if not field_value or not isinstance(field_value, str):
            continue
        
        # Skip empty or whitespace-only fields
        if not field_value.strip():
            continue
        
        # Get extraction method
        method = field_config.get('extraction_method', 'single_value')
        
        # Skip fields marked as 'skip'
        if method == 'skip':
            if debug:
                print(f"DEBUG: Skipping field '{field_name}' (extraction_method=skip)")
            continue
        
        if debug:
            value_preview = field_value[:50] if len(field_value) > 50 else field_value
            print(f"DEBUG: Extracting from '{field_name}' using method '{method}': '{value_preview}...'")
        
        # Extract claims based on method
        field_claims = extract_by_method(
            field_value=field_value,
            field_name=field_name,
            method=method,
            config=field_config
        )
        
        claims.extend(field_claims)
    
    return claims


def get_field_config(schema: Dict[str, Any], field_name: str) -> Optional[Dict[str, Any]]:
    """Get field configuration from schema (handles both flat and nested)."""
    # Try flat structure first
    if 'fields' in schema:
        return schema['fields'].get(field_name)
    
    # Try nested sections
    if 'sections' in schema:
        for section_name, section_config in schema['sections'].items():
            fields = section_config.get('fields', {})
            if field_name in fields:
                return fields[field_name]
    
    return None


def extract_by_method(
    field_value: str,
    field_name: str,
    method: str,
    config: Dict[str, Any]
) -> List[Claim]:
    """
    Extract claims using specified method.
    
    Args:
        field_value: The field's text value
        field_name: Name of the field
        method: Extraction method (single_value, delimited, bullet_list, etc.)
        config: Field configuration dict (contains delimiter, pattern, etc.)
    
    Returns:
        List of extracted claims
    """
    claims = []
    
    if method == 'single_value':
        # Entire field is one claim
        claims.append(Claim(
            text=field_value.strip(),
            field=field_name,
            metadata={"extraction_method": "single_value"}
        ))
    
    elif method == 'delimited':
        # Split on delimiter
        delimiter = config.get('delimiter', ',')
        trim = True
        fallback = 'single_value'
        
        parts = field_value.split(delimiter)
        
        if len(parts) > 1:
            # Successfully split
            for part in parts:
                if trim:
                    part = part.strip()
                if part:  # Skip empty parts
                    claims.append(Claim(
                        text=part,
                        field=field_name,
                        metadata={
                            "extraction_method": "delimited",
                            "delimiter": delimiter
                        }
                    ))
        else:
            # Delimiter not found, use fallback
            if fallback == 'single_value':
                claims.append(Claim(
                    text=field_value.strip(),
                    field=field_name,
                    metadata={
                        "extraction_method": "delimited_fallback",
                        "fallback": "single_value"
                    }
                ))
    
    elif method == 'bullet_list':
        # Extract bullet points
        delimiter = config.get('delimiter', '\n-')
        trim = True
        fallback = 'single_value'
        
        # Check if field has bullet format
        if has_bullet_format(field_value, delimiter):
            # Split on delimiter
            parts = re.split(r'\n-\s*', field_value)
            
            for part in parts:
                if trim:
                    part = part.strip()
                # Remove leading dash if present
                part = part.lstrip('- ')
                if part:
                    claims.append(Claim(
                        text=part,
                        field=field_name,
                        metadata={
                            "extraction_method": "bullet_list",
                            "delimiter": delimiter
                        }
                    ))
        else:
            # No bullets found, use fallback
            if fallback == 'single_value':
                claims.append(Claim(
                    text=field_value.strip(),
                    field=field_name,
                    metadata={
                        "extraction_method": "bullet_list_fallback",
                        "fallback": "single_value",
                        "format_warning": "Expected bullet list, found plain text"
                    }
                ))
            elif fallback == 'sentence_split':
                # Split into sentences
                sentences = split_into_sentences(field_value)
                for sentence in sentences:
                    if sentence.strip():
                        claims.append(Claim(
                            text=sentence.strip(),
                            field=field_name,
                            metadata={
                                "extraction_method": "bullet_list_fallback",
                                "fallback": "sentence_split"
                            }
                        ))
    
    elif method == 'structured':
        # Extract using regex pattern
        pattern = config.get('pattern')
        if pattern:
            match = re.search(pattern, field_value)
            if match:
                # Use matched groups or full match
                text = match.group(0) if not match.groups() else ' '.join(match.groups())
                claims.append(Claim(
                    text=text,
                    field=field_name,
                    metadata={
                        "extraction_method": "structured",
                        "pattern": pattern
                    }
                ))
            else:
                # Pattern didn't match, fallback to single value
                claims.append(Claim(
                    text=field_value.strip(),
                    field=field_name,
                    metadata={
                        "extraction_method": "structured_fallback",
                        "pattern_failed": True
                    }
                ))
        else:
            # No pattern provided, treat as single value
            claims.append(Claim(
                text=field_value.strip(),
                field=field_name,
                metadata={"extraction_method": "structured_no_pattern"}
            ))
    
    elif method == 'sentence_split':
        # Split text into sentences
        sentences = split_into_sentences(field_value)
        for sentence in sentences:
            if sentence.strip():
                claims.append(Claim(
                    text=sentence.strip(),
                    field=field_name,
                    metadata={"extraction_method": "sentence_split"}
                ))
    
    else:
        # Unknown method, treat as single value
        claims.append(Claim(
            text=field_value.strip(),
            field=field_name,
            metadata={"extraction_method": f"unknown_{method}"}
        ))
    
    return claims


def has_bullet_format(text: str, delimiter: str = '\n-') -> bool:
    """Check if text has bullet list format."""
    # Check for newline followed by dash
    return '\n-' in text or text.strip().startswith('-')


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences using simple regex."""
    pattern = r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])$'
    sentences = re.split(pattern, text)
    return [s.strip() for s in sentences if s.strip()]
