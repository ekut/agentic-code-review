"""Base classes and interfaces for PR data providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class PRData:
    """Unified PR data structure returned by all providers."""
    
    diff: str
    title: str
    description: str
    author: str
    files_changed: list[str]
    pr_number: int
    repository: str
    url: str
    provider: str  # "github", "gitlab", "bitbucket", "file", etc.
    metadata: Optional[dict] = None  # Provider-specific metadata (e.g., commit SHAs, timestamps)


@dataclass
class RateLimitInfo:
    """Rate limit information from API provider."""
    
    remaining: int
    limit: int
    reset_time: datetime


@dataclass
class CacheEntry:
    """Cache entry for PR data with TTL."""
    
    data: PRData
    timestamp: datetime
    ttl_seconds: int = 300  # 5 minutes default
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return (datetime.now() - self.timestamp).total_seconds() > self.ttl_seconds


class ProviderError(Exception):
    """Base exception for provider-related errors."""
    pass


class ProviderAPIError(ProviderError):
    """API request failed (4xx, 5xx errors)."""
    
    def __init__(self, provider: str, status_code: int, message: str):
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"{provider} API error {status_code}: {message}")


class NetworkError(ProviderError):
    """Network connectivity issues."""
    pass


class RateLimitError(ProviderError):
    """Rate limit exceeded."""
    
    def __init__(self, provider: str, reset_time: datetime):
        self.provider = provider
        self.reset_time = reset_time
        super().__init__(
            f"{provider} rate limit exceeded. Resets at {reset_time}"
        )


class AuthenticationError(ProviderError):
    """Authentication failed."""
    
    def __init__(self, provider: str, message: str):
        self.provider = provider
        super().__init__(f"{provider} authentication error: {message}")


class PRProvider(ABC):
    """Abstract base class for PR data providers."""
    
    @abstractmethod
    def fetch_pr_data(self, **kwargs) -> PRData:
        """
        Fetch PR data from the provider.
        
        Args:
            **kwargs: Provider-specific parameters
        
        Returns:
            PRData object with unified structure
        
        Raises:
            ProviderError: For provider-specific errors
        """
        pass
    
    @abstractmethod
    def validate_input(self, **kwargs) -> bool:
        """
        Validate that the input parameters are correct for this provider.
        
        Returns:
            True if valid, False otherwise
        """
        pass
    
    @staticmethod
    @abstractmethod
    def can_handle(input_str: str) -> bool:
        """
        Determine if this provider can handle the given input string.
        
        Args:
            input_str: URL or file path
        
        Returns:
            True if this provider can handle the input
        """
        pass
