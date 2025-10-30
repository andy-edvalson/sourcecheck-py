"""
Validator registry for managing and accessing validators.
"""
from typing import Dict, Type, Optional
from .base import Validator


class ValidatorRegistry:
    """
    Registry for managing validator classes.
    
    Validators can be registered using the @register_validator decorator
    or by calling register() directly.
    """
    
    def __init__(self):
        self._validators: Dict[str, Type[Validator]] = {}
    
    def register(self, name: str, validator_class: Type[Validator]) -> None:
        """
        Register a validator class with a given name.
        
        Args:
            name: Unique name for the validator
            validator_class: Validator class to register
        """
        if name in self._validators:
            raise ValueError(f"Validator '{name}' is already registered")
        
        if not issubclass(validator_class, Validator):
            raise TypeError(f"{validator_class} must be a subclass of Validator")
        
        self._validators[name] = validator_class
    
    def get(self, name: str) -> Optional[Type[Validator]]:
        """
        Get a validator class by name.
        
        Args:
            name: Name of the validator
        
        Returns:
            Validator class or None if not found
        """
        return self._validators.get(name)
    
    def create(self, name: str, config: dict = None, debug: bool = False) -> Validator:
        """
        Create an instance of a validator by name.
        
        Args:
            name: Name of the validator
            config: Optional configuration dictionary
            debug: Enable debug output (default: False)
        
        Returns:
            Validator instance
        
        Raises:
            ValueError: If validator name is not registered
        """
        validator_class = self.get(name)
        if validator_class is None:
            raise ValueError(f"Validator '{name}' not found in registry")
        
        return validator_class(config=config, debug=debug)
    
    def list_validators(self) -> list:
        """Return list of all registered validator names."""
        return list(self._validators.keys())
    
    def __contains__(self, name: str) -> bool:
        """Check if a validator is registered."""
        return name in self._validators


# Global registry instance
_registry = ValidatorRegistry()


def register_validator(name: str):
    """
    Decorator to register a validator class.
    
    Usage:
        @register_validator("my_validator")
        class MyValidator(Validator):
            ...
    
    Args:
        name: Unique name for the validator
    """
    def decorator(validator_class: Type[Validator]):
        _registry.register(name, validator_class)
        return validator_class
    return decorator


def get_validator(name: str) -> Optional[Type[Validator]]:
    """Get a validator class by name from the global registry."""
    return _registry.get(name)


def create_validator(name: str, config: dict = None, debug: bool = False) -> Validator:
    """Create a validator instance by name from the global registry."""
    return _registry.create(name, config, debug)


def list_validators() -> list:
    """List all registered validator names."""
    return _registry.list_validators()
