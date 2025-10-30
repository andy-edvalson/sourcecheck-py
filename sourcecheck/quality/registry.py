"""
Registry for quality analysis modules.

Provides decorator-based registration and factory functions
for creating quality modules.
"""
from typing import Dict, Type, List
from .base import QualityModule


# Global registry of quality modules
_quality_modules: Dict[str, Type[QualityModule]] = {}


def register_quality_module(name: str):
    """
    Decorator to register a quality module.
    
    Usage:
        @register_quality_module("semantic_quality")
        class SemanticQualityModule(QualityModule):
            ...
    
    Args:
        name: Unique identifier for the module
    
    Returns:
        Decorator function
    """
    def decorator(cls: Type[QualityModule]) -> Type[QualityModule]:
        if name in _quality_modules:
            raise ValueError(f"Quality module '{name}' is already registered")
        _quality_modules[name] = cls
        return cls
    return decorator


def create_quality_module(name: str, config: dict = None) -> QualityModule:
    """
    Create a quality module instance by name.
    
    Args:
        name: Module identifier (e.g., "semantic_quality")
        config: Module-specific configuration
    
    Returns:
        Initialized quality module instance
    
    Raises:
        ValueError: If module name is not registered
    """
    if name not in _quality_modules:
        available = list_quality_modules()
        raise ValueError(
            f"Unknown quality module: '{name}'. "
            f"Available modules: {available}"
        )
    
    module_class = _quality_modules[name]
    return module_class(config or {})


def list_quality_modules() -> List[str]:
    """
    List all registered quality module names.
    
    Returns:
        List of module identifiers
    """
    return list(_quality_modules.keys())


def get_quality_module_class(name: str) -> Type[QualityModule]:
    """
    Get the class for a registered quality module.
    
    Args:
        name: Module identifier
    
    Returns:
        Quality module class
    
    Raises:
        ValueError: If module name is not registered
    """
    if name not in _quality_modules:
        raise ValueError(f"Unknown quality module: '{name}'")
    return _quality_modules[name]
