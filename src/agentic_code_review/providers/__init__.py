"""Provider abstraction layer for PR data retrieval."""

from typing import Type

from .base import (
    PRData,
    PRProvider,
    ProviderError,
    ProviderAPIError,
    NetworkError,
    RateLimitError,
    AuthenticationError,
)
from .file_provider import FileProvider
from .github_provider import GitHubProvider


class ProviderFactory:
    """Factory for creating appropriate PR data provider."""
    
    # Registry of available providers (extensible)
    _providers: list[Type[PRProvider]] = [
        GitHubProvider,  # Check GitHub URLs first
        FileProvider,    # Backward compatibility - check last
    ]
    
    @classmethod
    def get_provider(cls, input_str: str, **config) -> PRProvider:
        """
        Detect and instantiate appropriate provider for input.
        
        Args:
            input_str: URL or file path
            **config: Provider-specific configuration (e.g., tokens)
        
        Returns:
            Instantiated provider ready to fetch data
        
        Raises:
            ValueError: If no provider can handle the input
        """
        for provider_class in cls._providers:
            if provider_class.can_handle(input_str):
                return provider_class(**config)
        
        raise ValueError(
            f"No provider found for input: {input_str}. "
            f"Supported providers: {[p.__name__ for p in cls._providers]}"
        )
    
    @classmethod
    def register_provider(cls, provider_class: Type[PRProvider]):
        """
        Register a new provider (for future extensibility).
        
        Args:
            provider_class: Provider class to register
        """
        # New providers take precedence (inserted at beginning)
        cls._providers.insert(0, provider_class)


__all__ = [
    "PRData",
    "PRProvider",
    "ProviderError",
    "ProviderAPIError",
    "NetworkError",
    "RateLimitError",
    "AuthenticationError",
    "ProviderFactory",
    "FileProvider",
    "GitHubProvider",
]
