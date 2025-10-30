"""
Retriever registry for managing and accessing retrievers.
"""
from typing import Dict, Type, Optional
from .base import Retriever


class RetrieverRegistry:
    """
    Registry for managing retriever classes.
    
    Retrievers can be registered using the @register_retriever decorator
    or by calling register() directly.
    """
    
    def __init__(self):
        self._retrievers: Dict[str, Type[Retriever]] = {}
    
    def register(self, name: str, retriever_class: Type[Retriever]) -> None:
        """
        Register a retriever class with a given name.
        
        Args:
            name: Unique name for the retriever
            retriever_class: Retriever class to register
        """
        if name in self._retrievers:
            raise ValueError(f"Retriever '{name}' is already registered")
        
        if not issubclass(retriever_class, Retriever):
            raise TypeError(f"{retriever_class} must be a subclass of Retriever")
        
        self._retrievers[name] = retriever_class
    
    def get(self, name: str) -> Optional[Type[Retriever]]:
        """
        Get a retriever class by name.
        
        Args:
            name: Name of the retriever
        
        Returns:
            Retriever class or None if not found
        """
        return self._retrievers.get(name)
    
    def create(
        self,
        name: str,
        transcript: str,
        config: dict = None
    ) -> Retriever:
        """
        Create an instance of a retriever by name.
        
        Args:
            name: Name of the retriever
            transcript: Transcript text to search
            config: Optional configuration dictionary
        
        Returns:
            Retriever instance
        
        Raises:
            ValueError: If retriever name is not registered
        """
        retriever_class = self.get(name)
        if retriever_class is None:
            raise ValueError(f"Retriever '{name}' not found in registry")
        
        return retriever_class(transcript=transcript, config=config)
    
    def list_retrievers(self) -> list:
        """Return list of all registered retriever names."""
        return list(self._retrievers.keys())
    
    def __contains__(self, name: str) -> bool:
        """Check if a retriever is registered."""
        return name in self._retrievers


# Global registry instance
_registry = RetrieverRegistry()


def register_retriever(name: str):
    """
    Decorator to register a retriever class.
    
    Usage:
        @register_retriever("my_retriever")
        class MyRetriever(Retriever):
            ...
    
    Args:
        name: Unique name for the retriever
    """
    def decorator(retriever_class: Type[Retriever]):
        _registry.register(name, retriever_class)
        return retriever_class
    return decorator


def get_retriever(name: str) -> Optional[Type[Retriever]]:
    """Get a retriever class by name from the global registry."""
    return _registry.get(name)


def create_retriever(
    name: str,
    transcript: str,
    config: dict = None
) -> Retriever:
    """Create a retriever instance by name from the global registry."""
    return _registry.create(name, transcript, config)


def list_retrievers() -> list:
    """List all registered retriever names."""
    return _registry.list_retrievers()
