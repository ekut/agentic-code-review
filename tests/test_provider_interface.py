"""
Property-based tests for provider interface compliance.

**Feature: github-pr-integration, Property 23: Provider interface compliance**
**Validates: Requirements 8.1**
"""

import inspect
from abc import ABC
from typing import get_type_hints

import pytest
from hypothesis import given, strategies as st

from agentic_code_review.providers.base import PRProvider, PRData


class ConcreteTestProvider(PRProvider):
    """A concrete test implementation of PRProvider for testing."""
    
    def fetch_pr_data(self, **kwargs) -> PRData:
        """Test implementation of fetch_pr_data."""
        return PRData(
            diff="test diff",
            title="Test PR",
            description="Test description",
            author="test_author",
            files_changed=["file1.py"],
            pr_number=1,
            repository="owner/repo",
            url="https://example.com/pr/1",
            provider="test"
        )
    
    def validate_input(self, **kwargs) -> bool:
        """Test implementation of validate_input."""
        return True
    
    @staticmethod
    def can_handle(input_str: str) -> bool:
        """Test implementation of can_handle."""
        return input_str.startswith("test://")


class IncompleteProvider(PRProvider):
    """A provider that doesn't implement all required methods."""
    
    def fetch_pr_data(self, **kwargs) -> PRData:
        return PRData(
            diff="", title="", description="", author="",
            files_changed=[], pr_number=0, repository="",
            url="", provider=""
        )
    
    # Missing validate_input and can_handle implementations


def test_provider_is_abstract():
    """
    Property 23: Provider interface compliance
    
    Verify that PRProvider is an abstract base class that cannot be instantiated.
    """
    with pytest.raises(TypeError):
        PRProvider()


def test_provider_has_required_methods():
    """
    Property 23: Provider interface compliance
    
    Verify that PRProvider defines all required abstract methods.
    """
    required_methods = {'fetch_pr_data', 'validate_input', 'can_handle'}
    
    # Get all abstract methods from PRProvider
    abstract_methods = {
        name for name, method in inspect.getmembers(PRProvider)
        if getattr(method, '__isabstractmethod__', False)
    }
    
    assert required_methods == abstract_methods, (
        f"PRProvider must define exactly these abstract methods: {required_methods}, "
        f"but found: {abstract_methods}"
    )


def test_concrete_provider_can_be_instantiated():
    """
    Property 23: Provider interface compliance
    
    Verify that a concrete implementation of PRProvider can be instantiated.
    """
    provider = ConcreteTestProvider()
    assert isinstance(provider, PRProvider)


def test_incomplete_provider_cannot_be_instantiated():
    """
    Property 23: Provider interface compliance
    
    Verify that incomplete implementations cannot be instantiated.
    """
    with pytest.raises(TypeError):
        IncompleteProvider()


def test_fetch_pr_data_returns_prdata():
    """
    Property 23: Provider interface compliance
    
    Verify that fetch_pr_data returns a PRData object.
    """
    provider = ConcreteTestProvider()
    result = provider.fetch_pr_data()
    assert isinstance(result, PRData)


def test_validate_input_returns_bool():
    """
    Property 23: Provider interface compliance
    
    Verify that validate_input returns a boolean.
    """
    provider = ConcreteTestProvider()
    result = provider.validate_input()
    assert isinstance(result, bool)


def test_can_handle_returns_bool():
    """
    Property 23: Provider interface compliance
    
    Verify that can_handle returns a boolean.
    """
    result = ConcreteTestProvider.can_handle("test://example")
    assert isinstance(result, bool)


def test_can_handle_is_static():
    """
    Property 23: Provider interface compliance
    
    Verify that can_handle is a static method.
    """
    assert isinstance(
        inspect.getattr_static(PRProvider, 'can_handle'),
        staticmethod
    )


@given(st.text())
def test_can_handle_accepts_string_input(input_str: str):
    """
    Property 23: Provider interface compliance
    
    For any string input, can_handle should accept it and return a boolean.
    This property runs 100 iterations with random strings.
    """
    result = ConcreteTestProvider.can_handle(input_str)
    assert isinstance(result, bool)


@given(
    diff=st.text(),
    title=st.text(),
    description=st.text(),
    author=st.text(),
    files_changed=st.lists(st.text()),
    pr_number=st.integers(min_value=1),
    repository=st.text(min_size=1),
    url=st.text(min_size=1),
    provider=st.text(min_size=1)
)
def test_fetch_pr_data_returns_valid_prdata(
    diff: str,
    title: str,
    description: str,
    author: str,
    files_changed: list[str],
    pr_number: int,
    repository: str,
    url: str,
    provider: str
):
    """
    Property 23: Provider interface compliance
    
    For any valid PRData fields, a provider implementation should be able to
    return a properly structured PRData object.
    This property runs 100 iterations with random data.
    """
    class DynamicProvider(PRProvider):
        def fetch_pr_data(self, **kwargs) -> PRData:
            return PRData(
                diff=diff,
                title=title,
                description=description,
                author=author,
                files_changed=files_changed,
                pr_number=pr_number,
                repository=repository,
                url=url,
                provider=provider
            )
        
        def validate_input(self, **kwargs) -> bool:
            return True
        
        @staticmethod
        def can_handle(input_str: str) -> bool:
            return True
    
    provider_instance = DynamicProvider()
    result = provider_instance.fetch_pr_data()
    
    # Verify the result is a PRData instance with correct fields
    assert isinstance(result, PRData)
    assert result.diff == diff
    assert result.title == title
    assert result.description == description
    assert result.author == author
    assert result.files_changed == files_changed
    assert result.pr_number == pr_number
    assert result.repository == repository
    assert result.url == url
    assert result.provider == provider


def test_provider_method_signatures():
    """
    Property 23: Provider interface compliance
    
    Verify that all required methods have the correct signatures.
    """
    # Check fetch_pr_data signature
    fetch_sig = inspect.signature(PRProvider.fetch_pr_data)
    assert 'kwargs' in fetch_sig.parameters
    assert fetch_sig.return_annotation == PRData
    
    # Check validate_input signature
    validate_sig = inspect.signature(PRProvider.validate_input)
    assert 'kwargs' in validate_sig.parameters
    assert validate_sig.return_annotation == bool
    
    # Check can_handle signature
    can_handle_sig = inspect.signature(PRProvider.can_handle)
    assert 'input_str' in can_handle_sig.parameters
    assert can_handle_sig.return_annotation == bool
