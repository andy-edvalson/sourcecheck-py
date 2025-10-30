"""
Path resolution utility for navigating nested data structures.

Supports dot notation, array indexing, and fallback paths for flexible
data extraction from various input formats.
"""
from typing import Any, List, Optional
import re


class PathResolver:
    """
    Resolve paths in nested dictionaries using dot notation.
    
    Supports:
    - Dot notation: "history_section.identifiers"
    - Array indexing: "sections[0].value"
    - Wildcards: "medications[*].name"
    - Fallback paths: Try multiple locations in order
    """
    
    @staticmethod
    def get_value(data: Any, path: str, default: Any = None) -> Any:
        """
        Get value from nested dict using dot notation.
        
        Args:
            data: Dictionary or string to search
            path: Dot-notation path (e.g., "section.field" or "items[0].name")
                  Use "." for root value
            default: Value to return if path not found
        
        Returns:
            Value at path, or default if not found
        
        Examples:
            >>> data = {"history": {"age": 56}}
            >>> PathResolver.get_value(data, "history.age")
            56
            >>> PathResolver.get_value(data, "history.missing", "N/A")
            'N/A'
            >>> data = {"sections": [{"label": "Name", "value": "John"}]}
            >>> PathResolver.get_value(data, "sections[?label='Name'].value")
            'John'
            >>> PathResolver.get_value("raw text", ".")
            'raw text'
        """
        if not path:
            return default
        
        # Handle root path "." - return data as-is
        if path == ".":
            return data
        
        # Handle string data - can only return root
        if isinstance(data, str):
            return data if path == "." else default
        
        # Handle dict data
        if not isinstance(data, dict):
            return default
        
        # Handle simple dot notation (most common case)
        if '[' not in path:
            return PathResolver._get_nested(data, path.split('.'), default)
        
        # Check for query syntax: array[?field='value']
        if '[?' in path:
            return PathResolver._get_with_query(data, path, default)
        
        # Handle array indexing: "sections[0].value"
        return PathResolver._get_with_arrays(data, path, default)
    
    @staticmethod
    def _get_nested(data: dict, keys: List[str], default: Any) -> Any:
        """Navigate nested dict with list of keys."""
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
    
    @staticmethod
    def _get_with_arrays(data: dict, path: str, default: Any) -> Any:
        """
        Handle paths with array indexing.
        
        Examples:
            "sections[0].value" -> Get first section's value
            "items[*].name" -> Get all item names (returns list)
        """
        # Parse path like "sections[0].value" or "items[*].name"
        # Split on . [ ] but keep the parts
        parts = re.split(r'\.|\[|\]', path)
        parts = [p for p in parts if p]  # Remove empty strings
        
        current = data
        for part in parts:
            if part.isdigit():
                # Array index
                idx = int(part)
                if isinstance(current, list) and 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return default
            elif part == '*':
                # Wildcard - return list of all items
                if isinstance(current, list):
                    return current
                else:
                    return default
            else:
                # Dict key
                if isinstance(current, dict) and part in current:
                    current = current[part]
                elif isinstance(current, list):
                    # Try to get this key from all items in list
                    result = []
                    for item in current:
                        if isinstance(item, dict) and part in item:
                            result.append(item[part])
                    return result if result else default
                else:
                    return default
        return current
    
    @staticmethod
    def resolve_with_fallbacks(
        data: dict,
        paths: List[str],
        default: Any = None
    ) -> Any:
        """
        Try multiple paths in order, return first found value.
        
        Args:
            data: Dictionary to search
            paths: List of paths to try in order
            default: Value to return if none found
        
        Returns:
            First non-None value found, or default
        
        Examples:
            >>> data = {"alt_name": "John"}
            >>> paths = ["name", "alt_name", "full_name"]
            >>> PathResolver.resolve_with_fallbacks(data, paths)
            'John'
        """
        for path in paths:
            value = PathResolver.get_value(data, path)
            if value is not None and value != "":
                return value
        return default
    
    @staticmethod
    def _get_with_query(data: dict, path: str, default: Any) -> Any:
        """
        Handle query syntax: array[?field='value'].property
        
        Examples:
            "sections[?label='Name'].value" -> Find item where label='Name', return value
            "items[?id='123'].name" -> Find item where id='123', return name
        """
        # Parse: array_path[?field='value'].remaining_path
        match = re.match(r"([^\[]+)\[\?([^=]+)='([^']+)'\]\.?(.*)", path)
        if not match:
            return default
        
        array_path, match_field, match_value, remaining_path = match.groups()
        
        # Get the array
        array = PathResolver.get_value(data, array_path, [])
        if not isinstance(array, list):
            return default
        
        # Find matching item (case-insensitive)
        match_value_lower = match_value.lower().strip()
        for item in array:
            if not isinstance(item, dict):
                continue
            
            item_value = item.get(match_field, "")
            if isinstance(item_value, str):
                if item_value.lower().strip() == match_value_lower:
                    # Found match, get remaining path
                    if remaining_path:
                        return PathResolver.get_value(item, remaining_path, default)
                    else:
                        return item
        
        return default
