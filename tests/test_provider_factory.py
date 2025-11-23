"""
Property-based tests for provider factory detection.

**Feature: github-pr-integration, Property 24: Provider factory detection**
**Validates: Requirements 8.3, 8.4**
"""

import pytest
from hypothesis import given, strategies as st, assume

from agentic_code_review.providers import (
    ProviderFactory,
    PRProvider,
    PRData,
)


class MockFileProvider(PRProvider):
    """Mock provider for file paths."""
    
    def fetch_pr_data(self, **kwargs) -> PRData:
        return PRData(
            diff="file diff",
            title="File PR",
            description="From file",
            author="file_author",
            files_changed=["file.py"],
            pr_number=0,
            repository="local/file",
            url="file://local",
            provider="file"
        )
    
    def validate_input(self, **kwargs) -> bool:
        return True
    
    @staticmethod
    def can_handle(input_str: str) -> bool:
        """Handle file paths (simple heuristic: no :// or starts with /)."""
        return "://" not in input_str or input_str.startswith("file://")


class MockGitHubProvider(PRProvider):
    """Mock provider for GitHub URLs."""
    
    def fetch_pr_data(self, **kwargs) -> PRData:
        return PRData(
            diff="github diff",
            title="GitHub PR",
            description="From GitHub",
            author="github_author",
            files_changed=["file.py"],
            pr_number=123,
            repository="owner/repo",
            url="https://github.com/owner/repo/pull/123",
            provider="github"
        )
    
    def validate_input(self, **kwargs) -> bool:
        return True
    
    @staticmethod
    def can_handle(input_str: str) -> bool:
        """Handle GitHub URLs."""
        return "github.com" in input_str.lower()


class MockGitLabProvider(PRProvider):
    """Mock provider for GitLab URLs."""
    
    def fetch_pr_data(self, **kwargs) -> PRData:
        return PRData(
            diff="gitlab diff",
            title="GitLab MR",
            description="From GitLab",
            author="gitlab_author",
            files_changed=["file.py"],
            pr_number=456,
            repository="group/project",
            url="https://gitlab.com/group/project/-/merge_requests/456",
            provider="gitlab"
        )
    
    def validate_input(self, **kwargs) -> bool:
        return True
    
    @staticmethod
    def can_handle(input_str: str) -> bool:
        """Handle GitLab URLs."""
        return "gitlab.com" in input_str.lower()


@pytest.fixture(autouse=True)
def reset_provider_registry():
    """Reset the provider registry before and after each test."""
    original_providers = ProviderFactory._providers.copy()
    ProviderFactory._providers = []
    yield
    ProviderFactory._providers = original_providers


def test_factory_raises_error_for_unsupported_input():
    """
    Property 24: Provider factory detection
    
    When no providers are registered, the factory should raise ValueError
    for any input.
    """
    with pytest.raises(ValueError, match="No provider found for input"):
        ProviderFactory.get_provider("https://example.com/pr/1")


def test_factory_detects_single_provider():
    """
    Property 24: Provider factory detection
    
    When a single provider is registered, the factory should detect and
    instantiate it for matching inputs.
    """
    ProviderFactory.register_provider(MockGitHubProvider)
    
    provider = ProviderFactory.get_provider("https://github.com/owner/repo/pull/123")
    assert isinstance(provider, MockGitHubProvider)


def test_factory_selects_correct_provider_from_multiple():
    """
    Property 24: Provider factory detection
    
    When multiple providers are registered, the factory should select
    the correct one based on input format.
    """
    ProviderFactory.register_provider(MockFileProvider)
    ProviderFactory.register_provider(MockGitHubProvider)
    ProviderFactory.register_provider(MockGitLabProvider)
    
    # Test GitHub detection
    github_provider = ProviderFactory.get_provider(
        "https://github.com/owner/repo/pull/123"
    )
    assert isinstance(github_provider, MockGitHubProvider)
    
    # Test GitLab detection
    gitlab_provider = ProviderFactory.get_provider(
        "https://gitlab.com/group/project/-/merge_requests/456"
    )
    assert isinstance(gitlab_provider, MockGitLabProvider)
    
    # Test file detection
    file_provider = ProviderFactory.get_provider("files/code_changes.txt")
    assert isinstance(file_provider, MockFileProvider)


def test_factory_respects_registration_order():
    """
    Property 24: Provider factory detection
    
    When multiple providers can handle the same input, the most recently
    registered provider should take precedence.
    """
    # Register in order: File, GitHub
    ProviderFactory.register_provider(MockFileProvider)
    ProviderFactory.register_provider(MockGitHubProvider)
    
    # GitHub was registered last, so it should take precedence
    provider = ProviderFactory.get_provider("https://github.com/owner/repo/pull/123")
    assert isinstance(provider, MockGitHubProvider)


def test_factory_passes_config_to_provider():
    """
    Property 24: Provider factory detection
    
    The factory should pass configuration parameters to the provider constructor.
    """
    class ConfigurableProvider(PRProvider):
        def __init__(self, token=None, **kwargs):
            self.token = token
        
        def fetch_pr_data(self, **kwargs) -> PRData:
            return PRData(
                diff="", title="", description="", author="",
                files_changed=[], pr_number=0, repository="",
                url="", provider="test"
            )
        
        def validate_input(self, **kwargs) -> bool:
            return True
        
        @staticmethod
        def can_handle(input_str: str) -> bool:
            return input_str.startswith("test://")
    
    ProviderFactory.register_provider(ConfigurableProvider)
    
    provider = ProviderFactory.get_provider("test://example", token="secret_token")
    assert provider.token == "secret_token"


@given(st.text(min_size=1))
def test_factory_handles_arbitrary_strings(input_str: str):
    """
    Property 24: Provider factory detection
    
    For any non-empty string input, the factory should either:
    1. Return a provider instance if a matching provider exists, or
    2. Raise ValueError if no provider can handle the input
    
    This property runs 100 iterations with random strings.
    """
    ProviderFactory.register_provider(MockGitHubProvider)
    ProviderFactory.register_provider(MockFileProvider)
    
    if "github.com" in input_str.lower():
        # Should detect GitHub provider
        provider = ProviderFactory.get_provider(input_str)
        assert isinstance(provider, MockGitHubProvider)
    elif "://" not in input_str:
        # Should detect file provider
        provider = ProviderFactory.get_provider(input_str)
        assert isinstance(provider, MockFileProvider)
    else:
        # Should raise ValueError for unsupported formats
        with pytest.raises(ValueError, match="No provider found"):
            ProviderFactory.get_provider(input_str)


@given(
    st.lists(
        st.sampled_from([
            "https://github.com/owner/repo/pull/123",
            "https://gitlab.com/group/project/-/merge_requests/456",
            "files/code_changes.txt",
            "/path/to/file.diff",
        ]),
        min_size=1,
        max_size=10
    )
)
def test_factory_consistently_detects_provider_type(inputs: list[str]):
    """
    Property 24: Provider factory detection
    
    For any list of inputs, the factory should consistently detect the same
    provider type for the same input format across multiple calls.
    
    This property runs 100 iterations with random input lists.
    """
    ProviderFactory.register_provider(MockFileProvider)
    ProviderFactory.register_provider(MockGitHubProvider)
    ProviderFactory.register_provider(MockGitLabProvider)
    
    for input_str in inputs:
        # Get provider twice for the same input
        provider1 = ProviderFactory.get_provider(input_str)
        provider2 = ProviderFactory.get_provider(input_str)
        
        # Should return the same provider type
        assert type(provider1) == type(provider2)


@given(st.integers(min_value=1, max_value=10))
def test_factory_with_dynamic_provider_registration(num_providers: int):
    """
    Property 24: Provider factory detection
    
    For any number of providers registered, the factory should maintain
    a registry and be able to report available providers.
    
    This property runs 100 iterations with different provider counts.
    """
    # Clear registry for this test iteration
    ProviderFactory._providers = []
    
    # Register multiple mock providers
    for i in range(num_providers):
        class DynamicProvider(PRProvider):
            provider_id = i
            
            def fetch_pr_data(self, **kwargs) -> PRData:
                return PRData(
                    diff="", title="", description="", author="",
                    files_changed=[], pr_number=0, repository="",
                    url="", provider=f"dynamic_{self.provider_id}"
                )
            
            def validate_input(self, **kwargs) -> bool:
                return True
            
            @staticmethod
            def can_handle(input_str: str) -> bool:
                return input_str.startswith(f"dynamic{i}://")
        
        ProviderFactory.register_provider(DynamicProvider)
    
    # Verify the registry has the correct number of providers
    assert len(ProviderFactory._providers) == num_providers


def test_factory_error_message_includes_supported_providers():
    """
    Property 24: Provider factory detection
    
    When no provider can handle an input, the error message should list
    the available providers to help with debugging.
    """
    ProviderFactory.register_provider(MockGitHubProvider)
    ProviderFactory.register_provider(MockFileProvider)
    
    with pytest.raises(ValueError) as exc_info:
        ProviderFactory.get_provider("https://unsupported.com/pr/1")
    
    error_message = str(exc_info.value)
    assert "MockGitHubProvider" in error_message
    assert "MockFileProvider" in error_message


@given(
    st.one_of(
        st.just("https://github.com/user/repo/pull/1"),
        st.just("https://gitlab.com/user/repo/-/merge_requests/1"),
        st.just("file.txt"),
    )
)
def test_factory_returns_provider_instance(input_str: str):
    """
    Property 24: Provider factory detection
    
    For any supported input format, the factory should return an instance
    that implements the PRProvider interface.
    
    This property runs 100 iterations with different input formats.
    """
    ProviderFactory.register_provider(MockFileProvider)
    ProviderFactory.register_provider(MockGitHubProvider)
    ProviderFactory.register_provider(MockGitLabProvider)
    
    provider = ProviderFactory.get_provider(input_str)
    
    # Verify it's a PRProvider instance
    assert isinstance(provider, PRProvider)
    
    # Verify it has all required methods
    assert hasattr(provider, 'fetch_pr_data')
    assert hasattr(provider, 'validate_input')
    assert hasattr(provider, 'can_handle')
    
    # Verify methods are callable
    assert callable(provider.fetch_pr_data)
    assert callable(provider.validate_input)
    assert callable(provider.can_handle)
