"""
Property-based tests for flow integration with provider abstraction.

**Feature: github-pr-integration, Property 5: State update after parsing**
**Validates: Requirements 1.5**

**Feature: github-pr-integration, Property 13: Metadata availability to crew**
**Validates: Requirements 4.3**
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from hypothesis import given, strategies as st, settings, assume

from agentic_code_review.main import PRCodeReviewFlow, ReviewState
from agentic_code_review.providers import PRData


# Test data strategies
@st.composite
def github_url_components(draw):
    """Generate valid GitHub URL components (owner, repo, pr_number)."""
    # Owner: alphanumeric, hyphens, underscores (GitHub username rules)
    owner = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"),
        min_size=1,
        max_size=39  # GitHub username max length
    ).filter(lambda x: x and x[0].isalnum() and x[-1].isalnum()))
    
    # Repo: similar to owner but can have dots
    repo = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_."),
        min_size=1,
        max_size=100
    ).filter(lambda x: x and x[0].isalnum() and x[-1].isalnum()))
    
    # PR number: positive integer
    pr_number = draw(st.integers(min_value=1, max_value=999999))
    
    return owner, repo, pr_number


@st.composite
def pr_metadata_strategy(draw):
    """Generate random PR metadata."""
    title = draw(st.text(min_size=1, max_size=200))
    description = draw(st.text(min_size=0, max_size=1000))
    author = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"),
        min_size=1,
        max_size=39
    ).filter(lambda x: x and x[0].isalnum()))
    num_files = draw(st.integers(min_value=1, max_value=10))
    files_changed = [f"file{i}.txt" for i in range(num_files)]
    
    return {
        "title": title,
        "description": description,
        "author": author,
        "files_changed": files_changed,
    }


@st.composite
def file_content_strategy(draw):
    """Generate random file content for testing."""
    # Generate realistic diff-like content
    lines = draw(st.lists(st.text(min_size=0, max_size=100), min_size=1, max_size=50))
    return "\n".join(lines)


class TestStateUpdateAfterParsing:
    """
    Property 5: State update after parsing
    
    For any successfully parsed PR identifier, the system state should contain
    the extracted owner, repo, and PR number.
    """
    
    @settings(max_examples=100)
    @given(
        components=github_url_components(),
        metadata=pr_metadata_strategy(),
        diff_content=file_content_strategy()
    )
    def test_property_5_state_update_after_github_url_parsing(
        self, components, metadata, diff_content
    ):
        """
        **Feature: github-pr-integration, Property 5: State update after parsing**
        
        For any successfully parsed GitHub PR URL, the system state should be
        updated with the PR content and metadata including owner, repo, and PR number.
        
        **Validates: Requirements 1.5**
        
        This property runs 100 iterations with random GitHub URLs and metadata.
        """
        owner, repo, pr_number = components
        url = f"https://github.com/{owner}/{repo}/pull/{pr_number}"
        
        # Set up environment
        os.environ["GITHUB_TOKEN"] = "test_token_12345"
        
        try:
            # Mock the provider to return our test data
            mock_pr_data = PRData(
                diff=diff_content,
                title=metadata["title"],
                description=metadata["description"],
                author=metadata["author"],
                files_changed=metadata["files_changed"],
                pr_number=pr_number,
                repository=f"{owner}/{repo}",
                url=url,
                provider="github"
            )
            
            with patch('agentic_code_review.main.ProviderFactory.get_provider') as mock_factory:
                mock_provider = MagicMock()
                mock_provider.fetch_pr_data.return_value = mock_pr_data
                mock_factory.return_value = mock_provider
                
                # Create flow and patch the persistence mechanism
                with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                    flow = PRCodeReviewFlow()
                    # Manually initialize state
                    test_state = ReviewState(pr_input=url)
                    flow._state = test_state
                    
                    # Execute the read_pr_data method directly
                    flow.read_pr_data()
                    
                    # Verify state is updated correctly
                    assert flow.state.pr_content == diff_content, "PR content should be in state"
                    assert flow.state.pr_metadata is not None, "PR metadata should be in state"
                    
                    # Verify metadata contains all required fields
                    assert flow.state.pr_metadata["title"] == metadata["title"]
                    assert flow.state.pr_metadata["description"] == metadata["description"]
                    assert flow.state.pr_metadata["author"] == metadata["author"]
                    assert flow.state.pr_metadata["files_changed"] == metadata["files_changed"]
                    assert flow.state.pr_metadata["pr_number"] == pr_number
                    assert flow.state.pr_metadata["repository"] == f"{owner}/{repo}"
                    assert flow.state.pr_metadata["url"] == url
                    assert flow.state.pr_metadata["provider"] == "github"
                    
                    # Verify no errors were added
                    assert len(flow.state.errors) == 0, "No errors should be present after successful parsing"
        
        finally:
            # Clean up
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]
    
    @settings(max_examples=100)
    @given(
        file_content=file_content_strategy()
    )
    def test_property_5_state_update_after_file_path_parsing(self, file_content):
        """
        **Feature: github-pr-integration, Property 5: State update after parsing**
        
        For any successfully parsed file path, the system state should be
        updated with the PR content and minimal metadata.
        
        **Validates: Requirements 1.5**
        
        This property runs 100 iterations with random file content.
        """
        # Create a temporary file with the content
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', newline='') as f:
            f.write(file_content)
            temp_path = f.name
        
        try:
            # Read back what was actually written (to handle platform line ending normalization)
            with open(temp_path, 'r', encoding='utf-8') as f:
                actual_written_content = f.read()
            
            # Create flow with initial state
            with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                flow = PRCodeReviewFlow()
                flow._state = ReviewState(pr_input=temp_path)
                
                # Execute the read_pr_data method
                flow.read_pr_data()
                
                # Verify state is updated correctly
                assert flow.state.pr_content == actual_written_content, "PR content should match file content"
                assert flow.state.pr_metadata is not None, "PR metadata should be in state"
                
                # Verify metadata contains required fields for file provider
                assert flow.state.pr_metadata["provider"] == "file"
                assert flow.state.pr_metadata["repository"] == "local"
                assert flow.state.pr_metadata["pr_number"] == 0
                assert flow.state.pr_metadata["url"] == temp_path
                
                # Verify no errors were added
                assert len(flow.state.errors) == 0, "No errors should be present after successful file read"
        
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_property_5_state_contains_errors_on_invalid_input(self):
        """
        **Feature: github-pr-integration, Property 5: State update after parsing**
        
        For any invalid input that cannot be parsed, the system state should
        contain error information.
        
        **Validates: Requirements 1.5**
        """
        # Create flow with invalid input
        with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
            flow = PRCodeReviewFlow()
            flow._state = ReviewState(pr_input="https://invalid-site.com/not-a-pr")
            
            # Execute the read_pr_data method
            flow.read_pr_data()
            
            # Verify errors were added to state
            assert len(flow.state.errors) > 0, "Errors should be present for invalid input"
            assert flow.state.final_answer != "", "Final answer should contain error message"
            assert "Error fetching PR data" in flow.state.errors[0]
    
    def test_property_5_state_handles_missing_input(self):
        """
        **Feature: github-pr-integration, Property 5: State update after parsing**
        
        When no input is provided, the system state should contain appropriate
        error information.
        
        **Validates: Requirements 1.5**
        """
        # Create flow with empty input
        with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
            flow = PRCodeReviewFlow()
            flow._state = ReviewState(pr_input="")
            
            # Execute the read_pr_data method
            flow.read_pr_data()
            
            # Verify errors were added to state
            assert len(flow.state.errors) > 0, "Errors should be present for missing input"
            assert "Missing 'pr_input' in state" in flow.state.errors[0]
            assert "No input provided" in flow.state.final_answer


class TestMetadataAvailabilityToCrew:
    """
    Property 13: Metadata availability to crew
    
    For any successfully fetched PR metadata, it should be accessible in the
    ReviewState for use by the review crew.
    """
    
    @settings(max_examples=100)
    @given(
        components=github_url_components(),
        metadata=pr_metadata_strategy(),
        diff_content=file_content_strategy()
    )
    def test_property_13_metadata_available_in_state_for_crew(
        self, components, metadata, diff_content
    ):
        """
        **Feature: github-pr-integration, Property 13: Metadata availability to crew**
        
        For any successfully fetched PR metadata, it should be stored in the
        ReviewState and accessible for the review crew to use as context.
        
        **Validates: Requirements 4.3**
        
        This property runs 100 iterations with random PR data.
        """
        owner, repo, pr_number = components
        url = f"https://github.com/{owner}/{repo}/pull/{pr_number}"
        
        # Set up environment
        os.environ["GITHUB_TOKEN"] = "test_token_12345"
        
        try:
            # Mock the provider to return our test data
            mock_pr_data = PRData(
                diff=diff_content,
                title=metadata["title"],
                description=metadata["description"],
                author=metadata["author"],
                files_changed=metadata["files_changed"],
                pr_number=pr_number,
                repository=f"{owner}/{repo}",
                url=url,
                provider="github"
            )
            
            with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                with patch('agentic_code_review.main.ProviderFactory.get_provider') as mock_factory:
                    mock_provider = MagicMock()
                    mock_provider.fetch_pr_data.return_value = mock_pr_data
                    mock_factory.return_value = mock_provider
                    
                    # Create flow with initial state
                    flow = PRCodeReviewFlow()
                    flow._state = ReviewState(pr_input=url)
                    
                    # Execute the read_pr_data method
                    flow.read_pr_data()
                    
                    # Verify metadata is accessible in state
                    assert hasattr(flow.state, 'pr_metadata'), "State should have pr_metadata attribute"
                    assert isinstance(flow.state.pr_metadata, dict), "pr_metadata should be a dictionary"
                    
                    # Verify all metadata fields are accessible
                    assert "title" in flow.state.pr_metadata, "Title should be in metadata"
                    assert "description" in flow.state.pr_metadata, "Description should be in metadata"
                    assert "author" in flow.state.pr_metadata, "Author should be in metadata"
                    assert "files_changed" in flow.state.pr_metadata, "Files changed should be in metadata"
                    assert "pr_number" in flow.state.pr_metadata, "PR number should be in metadata"
                    assert "repository" in flow.state.pr_metadata, "Repository should be in metadata"
                    assert "url" in flow.state.pr_metadata, "URL should be in metadata"
                    assert "provider" in flow.state.pr_metadata, "Provider should be in metadata"
                    
                    # Verify metadata values are correct
                    assert flow.state.pr_metadata["title"] == metadata["title"]
                    assert flow.state.pr_metadata["description"] == metadata["description"]
                    assert flow.state.pr_metadata["author"] == metadata["author"]
                    assert flow.state.pr_metadata["files_changed"] == metadata["files_changed"]
                    assert flow.state.pr_metadata["pr_number"] == pr_number
                    assert flow.state.pr_metadata["repository"] == f"{owner}/{repo}"
                    
                    # Verify the crew can access this metadata through the state
                    # (simulating what the crew would do)
                    crew_accessible_metadata = flow.state.pr_metadata
                    assert crew_accessible_metadata is not None
                    assert len(crew_accessible_metadata) > 0
        
        finally:
            # Clean up
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]
    
    @settings(max_examples=100)
    @given(
        metadata=pr_metadata_strategy(),
        diff_content=file_content_strategy()
    )
    def test_property_13_metadata_structure_is_consistent(self, metadata, diff_content):
        """
        **Feature: github-pr-integration, Property 13: Metadata availability to crew**
        
        For any PR data source (GitHub or file), the metadata structure in
        ReviewState should be consistent and predictable for the crew.
        
        **Validates: Requirements 4.3**
        
        This property runs 100 iterations with random metadata.
        """
        # Test with file provider
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', newline='') as f:
            f.write(diff_content)
            temp_path = f.name
        
        try:
            # Create flow with file input
            with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                flow = PRCodeReviewFlow()
                flow._state = ReviewState(pr_input=temp_path)
                
                # Execute the read_pr_data method
                flow.read_pr_data()
                
                # Verify metadata structure is consistent
                assert isinstance(flow.state.pr_metadata, dict), "Metadata should be a dictionary"
                
                # Verify required keys are present (even if values differ by provider)
                required_keys = ["provider", "repository", "pr_number", "url"]
                for key in required_keys:
                    assert key in flow.state.pr_metadata, f"Key '{key}' should be in metadata"
                
                # Verify metadata is not empty
                assert len(flow.state.pr_metadata) > 0, "Metadata should not be empty"
        
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_property_13_metadata_persists_through_flow(self):
        """
        **Feature: github-pr-integration, Property 13: Metadata availability to crew**
        
        Metadata should persist in the state throughout the flow execution,
        remaining accessible to all subsequent steps including the crew.
        
        **Validates: Requirements 4.3**
        """
        # Create a test file
        test_content = "test diff content"
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(test_content)
            temp_path = f.name
        
        try:
            # Create flow
            with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                flow = PRCodeReviewFlow()
                flow._state = ReviewState(pr_input=temp_path)
                
                # Execute read_pr_data
                flow.read_pr_data()
                
                # Store initial metadata
                initial_metadata = flow.state.pr_metadata.copy()
                
                # Simulate flow progression (without actually running the crew)
                # The metadata should still be accessible
                assert flow.state.pr_metadata == initial_metadata, "Metadata should persist"
                
                # Verify metadata is still accessible after state operations
                flow._state.crew_needed = True
                assert flow.state.pr_metadata == initial_metadata, "Metadata should persist after state changes"
                
                flow._state.review_result = {"test": "result"}
                assert flow.state.pr_metadata == initial_metadata, "Metadata should persist after adding review results"
        
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @settings(max_examples=100)
    @given(
        components=github_url_components(),
        metadata=pr_metadata_strategy()
    )
    def test_property_13_metadata_contains_context_for_review(self, components, metadata):
        """
        **Feature: github-pr-integration, Property 13: Metadata availability to crew**
        
        For any PR, the metadata should contain sufficient context information
        (title, description, author, files) that the crew can use for review.
        
        **Validates: Requirements 4.3**
        
        This property runs 100 iterations with random PR metadata.
        """
        owner, repo, pr_number = components
        url = f"https://github.com/{owner}/{repo}/pull/{pr_number}"
        
        # Set up environment
        os.environ["GITHUB_TOKEN"] = "test_token_12345"
        
        try:
            # Mock the provider
            mock_pr_data = PRData(
                diff="test diff",
                title=metadata["title"],
                description=metadata["description"],
                author=metadata["author"],
                files_changed=metadata["files_changed"],
                pr_number=pr_number,
                repository=f"{owner}/{repo}",
                url=url,
                provider="github"
            )
            
            with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                with patch('agentic_code_review.main.ProviderFactory.get_provider') as mock_factory:
                    mock_provider = MagicMock()
                    mock_provider.fetch_pr_data.return_value = mock_pr_data
                    mock_factory.return_value = mock_provider
                    
                    # Create flow
                    flow = PRCodeReviewFlow()
                    flow._state = ReviewState(pr_input=url)
                    
                    # Execute read_pr_data
                    flow.read_pr_data()
                    
                    # Verify metadata contains context information
                    context_fields = ["title", "description", "author", "files_changed"]
                    for field in context_fields:
                        assert field in flow.state.pr_metadata, f"Context field '{field}' should be available"
                        assert flow.state.pr_metadata[field] is not None, f"Context field '{field}' should not be None"
                    
                    # Verify the context is meaningful (not empty for required fields)
                    assert flow.state.pr_metadata["title"] != "", "Title should not be empty"
                    assert flow.state.pr_metadata["author"] != "", "Author should not be empty"
                    assert isinstance(flow.state.pr_metadata["files_changed"], list), "Files changed should be a list"
        
        finally:
            # Clean up
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]
