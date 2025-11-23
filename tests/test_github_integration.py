"""
Integration tests for GitHub flow with mock API responses.

Tests complete flow with GitHub URL input, error scenarios, and cache behavior.

**Requirements: 3.1, 3.3, 5.1, 5.3, 5.5**
"""

import os
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path

import pytest
import requests

from agentic_code_review.main import PRCodeReviewFlow, ReviewState
from agentic_code_review.providers import PRData
from agentic_code_review.providers.github_provider import GitHubProvider, _pr_cache
from agentic_code_review.providers.base import (
    ProviderAPIError,
    NetworkError,
    RateLimitError,
    AuthenticationError,
)


# Test fixtures
@pytest.fixture
def mock_github_pr_metadata():
    """Mock GitHub API PR metadata response."""
    return {
        "title": "Add new feature",
        "body": "This PR adds a new feature to the codebase",
        "user": {"login": "testuser"},
        "number": 123,
        "html_url": "https://github.com/owner/repo/pull/123",
    }


@pytest.fixture
def mock_github_pr_diff():
    """Mock GitHub API PR diff response."""
    return """diff --git a/file.py b/file.py
index 1234567..abcdefg 100644
--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
 def hello():
+    # New comment
     print("Hello, World!")
"""


@pytest.fixture
def mock_github_files():
    """Mock GitHub API files response."""
    return [
        {"filename": "file.py", "status": "modified"},
        {"filename": "test.py", "status": "added"},
    ]


@pytest.fixture
def setup_github_token():
    """Set up GitHub token for tests."""
    original_token = os.environ.get("GITHUB_TOKEN")
    os.environ["GITHUB_TOKEN"] = "test_token_12345"
    yield
    # Cleanup
    if original_token:
        os.environ["GITHUB_TOKEN"] = original_token
    elif "GITHUB_TOKEN" in os.environ:
        del os.environ["GITHUB_TOKEN"]


@pytest.fixture
def clear_cache():
    """Clear the PR cache before and after tests."""
    _pr_cache.clear()
    yield
    _pr_cache.clear()


class TestGitHubFlowIntegration:
    """Integration tests for complete GitHub flow."""
    
    def test_complete_flow_with_github_url(
        self,
        setup_github_token,
        clear_cache,
        mock_github_pr_metadata,
        mock_github_pr_diff,
        mock_github_files,
    ):
        """
        Test complete flow with GitHub URL input.
        
        **Validates: Requirements 3.1**
        
        Verifies that:
        - GitHub URL is correctly parsed
        - API requests are made with authentication
        - PR data is fetched and stored in state
        - Flow completes successfully
        """
        url = "https://github.com/owner/repo/pull/123"
        
        # Mock the requests.get to return our test data
        with patch('requests.get') as mock_get:
            # Set up mock responses for different API calls
            mock_metadata_response = Mock()
            mock_metadata_response.status_code = 200
            mock_metadata_response.json.return_value = mock_github_pr_metadata
            mock_metadata_response.headers = {
                'X-RateLimit-Remaining': '5000',
                'X-RateLimit-Limit': '5000',
                'X-RateLimit-Reset': str(int((datetime.now() + timedelta(hours=1)).timestamp())),
            }
            
            mock_diff_response = Mock()
            mock_diff_response.status_code = 200
            mock_diff_response.text = mock_github_pr_diff
            mock_diff_response.headers = mock_metadata_response.headers
            
            mock_files_response = Mock()
            mock_files_response.status_code = 200
            mock_files_response.json.return_value = mock_github_files
            mock_files_response.headers = mock_metadata_response.headers
            
            # Configure mock to return different responses based on headers
            def side_effect(*args, **kwargs):
                headers = kwargs.get('headers', {})
                if 'application/vnd.github.v3.diff' in headers.get('Accept', ''):
                    return mock_diff_response
                elif '/files' in args[0]:
                    return mock_files_response
                else:
                    return mock_metadata_response
            
            mock_get.side_effect = side_effect
            
            # Create flow and execute
            with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                flow = PRCodeReviewFlow()
                flow._state = ReviewState(pr_input=url)
                
                # Execute read_pr_data
                flow.read_pr_data()
                
                # Verify state is updated correctly
                assert flow.state.pr_content == mock_github_pr_diff
                assert flow.state.pr_metadata["title"] == "Add new feature"
                assert flow.state.pr_metadata["author"] == "testuser"
                assert flow.state.pr_metadata["provider"] == "github"
                assert flow.state.pr_metadata["pr_number"] == 123
                assert flow.state.pr_metadata["repository"] == "owner/repo"
                assert len(flow.state.errors) == 0
                
                # Verify API was called with correct authentication
                calls = mock_get.call_args_list
                assert len(calls) == 3  # metadata, diff, files
                
                # Check that all calls included the token
                for call in calls:
                    headers = call[1]['headers']
                    assert 'Authorization' in headers
                    assert headers['Authorization'] == 'Bearer test_token_12345'
    
    def test_github_flow_with_404_error(self, setup_github_token, clear_cache):
        """
        Test flow with 404 error (PR not found).
        
        **Validates: Requirements 3.3**
        
        Verifies that:
        - 404 errors are properly handled
        - Error message indicates PR not found
        - State contains error information
        """
        url = "https://github.com/owner/repo/pull/999"
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.headers = {
                'X-RateLimit-Remaining': '5000',
                'X-RateLimit-Limit': '5000',
            }
            mock_get.return_value = mock_response
            
            with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                flow = PRCodeReviewFlow()
                flow._state = ReviewState(pr_input=url)
                
                # Execute read_pr_data
                flow.read_pr_data()
                
                # Verify error is captured
                assert len(flow.state.errors) > 0
                assert "Error fetching PR data" in flow.state.errors[0]
                assert "404" in flow.state.final_answer or "not found" in flow.state.final_answer.lower()
    
    def test_github_flow_with_403_error(self, setup_github_token, clear_cache):
        """
        Test flow with 403 error (access denied).
        
        **Validates: Requirements 3.3**
        
        Verifies that:
        - 403 errors are properly handled
        - Error message indicates access denied
        - State contains error information
        """
        url = "https://github.com/private/repo/pull/123"
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 403
            mock_response.headers = {
                'X-RateLimit-Remaining': '5000',
                'X-RateLimit-Limit': '5000',
            }
            mock_get.return_value = mock_response
            
            with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                flow = PRCodeReviewFlow()
                flow._state = ReviewState(pr_input=url)
                
                # Execute read_pr_data
                flow.read_pr_data()
                
                # Verify error is captured
                assert len(flow.state.errors) > 0
                assert "Error fetching PR data" in flow.state.errors[0]
                assert "403" in flow.state.final_answer or "access denied" in flow.state.final_answer.lower()
    
    def test_github_flow_with_rate_limit_error(self, setup_github_token, clear_cache):
        """
        Test flow with rate limit error (429).
        
        **Validates: Requirements 5.3**
        
        Verifies that:
        - Rate limit errors are properly handled
        - System waits for rate limit reset (or raises error)
        - Error message includes rate limit information
        """
        url = "https://github.com/owner/repo/pull/123"
        
        with patch('requests.get') as mock_get:
            # First call returns 429, subsequent calls should not happen
            # because we're not actually waiting
            reset_time = datetime.now() + timedelta(hours=1)
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.headers = {
                'X-RateLimit-Remaining': '0',
                'X-RateLimit-Limit': '5000',
                'X-RateLimit-Reset': str(int(reset_time.timestamp())),
            }
            mock_get.return_value = mock_response
            
            # Mock time.sleep to avoid actually waiting
            with patch('time.sleep'):
                with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                    flow = PRCodeReviewFlow()
                    flow._state = ReviewState(pr_input=url)
                    
                    # Execute read_pr_data
                    flow.read_pr_data()
                    
                    # Verify error is captured
                    assert len(flow.state.errors) > 0
                    assert "Error fetching PR data" in flow.state.errors[0]
    
    def test_github_flow_with_network_timeout(self, setup_github_token, clear_cache):
        """
        Test flow with network timeout error.
        
        **Validates: Requirements 3.3**
        
        Verifies that:
        - Timeout errors trigger retry logic
        - After max retries, error is properly reported
        - Error message indicates timeout
        """
        url = "https://github.com/owner/repo/pull/123"
        
        with patch('requests.get') as mock_get:
            # Simulate timeout on all attempts
            mock_get.side_effect = requests.exceptions.Timeout("Request timed out")
            
            # Mock time.sleep to avoid actually waiting during retries
            with patch('time.sleep'):
                with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                    flow = PRCodeReviewFlow()
                    flow._state = ReviewState(pr_input=url)
                    
                    # Execute read_pr_data
                    flow.read_pr_data()
                    
                    # Verify error is captured
                    assert len(flow.state.errors) > 0
                    assert "Error fetching PR data" in flow.state.errors[0]
                    assert "timeout" in flow.state.final_answer.lower() or "timed out" in flow.state.final_answer.lower()
                    
                    # Verify retry logic was triggered (3 attempts)
                    assert mock_get.call_count == 3
    
    def test_github_flow_with_connection_error(self, setup_github_token, clear_cache):
        """
        Test flow with connection error.
        
        **Validates: Requirements 3.3**
        
        Verifies that:
        - Connection errors trigger retry logic
        - After max retries, error is properly reported
        - Error message indicates connection issue
        """
        url = "https://github.com/owner/repo/pull/123"
        
        with patch('requests.get') as mock_get:
            # Simulate connection error on all attempts
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
            
            # Mock time.sleep to avoid actually waiting during retries
            with patch('time.sleep'):
                with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                    flow = PRCodeReviewFlow()
                    flow._state = ReviewState(pr_input=url)
                    
                    # Execute read_pr_data
                    flow.read_pr_data()
                    
                    # Verify error is captured
                    assert len(flow.state.errors) > 0
                    assert "Error fetching PR data" in flow.state.errors[0]
                    assert "connection" in flow.state.final_answer.lower()
                    
                    # Verify retry logic was triggered (3 attempts)
                    assert mock_get.call_count == 3
    
    def test_github_flow_cache_behavior(
        self,
        setup_github_token,
        clear_cache,
        mock_github_pr_metadata,
        mock_github_pr_diff,
        mock_github_files,
    ):
        """
        Test cache behavior across multiple requests.
        
        **Validates: Requirements 5.5**
        
        Verifies that:
        - First request fetches from API
        - Second request within TTL uses cache
        - API is only called once for cached requests
        - Cache key is correctly generated
        """
        url = "https://github.com/owner/repo/pull/123"
        
        with patch('requests.get') as mock_get:
            # Set up mock responses
            mock_metadata_response = Mock()
            mock_metadata_response.status_code = 200
            mock_metadata_response.json.return_value = mock_github_pr_metadata
            mock_metadata_response.headers = {
                'X-RateLimit-Remaining': '5000',
                'X-RateLimit-Limit': '5000',
                'X-RateLimit-Reset': str(int((datetime.now() + timedelta(hours=1)).timestamp())),
            }
            
            mock_diff_response = Mock()
            mock_diff_response.status_code = 200
            mock_diff_response.text = mock_github_pr_diff
            mock_diff_response.headers = mock_metadata_response.headers
            
            mock_files_response = Mock()
            mock_files_response.status_code = 200
            mock_files_response.json.return_value = mock_github_files
            mock_files_response.headers = mock_metadata_response.headers
            
            def side_effect(*args, **kwargs):
                headers = kwargs.get('headers', {})
                if 'application/vnd.github.v3.diff' in headers.get('Accept', ''):
                    return mock_diff_response
                elif '/files' in args[0]:
                    return mock_files_response
                else:
                    return mock_metadata_response
            
            mock_get.side_effect = side_effect
            
            with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                # First request - should fetch from API
                flow1 = PRCodeReviewFlow()
                flow1._state = ReviewState(pr_input=url)
                flow1.read_pr_data()
                
                # Verify data was fetched
                assert flow1.state.pr_content == mock_github_pr_diff
                assert len(flow1.state.errors) == 0
                
                # Record number of API calls
                first_call_count = mock_get.call_count
                assert first_call_count == 3  # metadata, diff, files
                
                # Second request - should use cache
                flow2 = PRCodeReviewFlow()
                flow2._state = ReviewState(pr_input=url)
                flow2.read_pr_data()
                
                # Verify data was retrieved (from cache)
                assert flow2.state.pr_content == mock_github_pr_diff
                assert len(flow2.state.errors) == 0
                
                # Verify no additional API calls were made
                assert mock_get.call_count == first_call_count, "Cache should prevent additional API calls"
    
    def test_github_flow_rate_limit_header_inspection(
        self,
        setup_github_token,
        clear_cache,
        mock_github_pr_metadata,
        mock_github_pr_diff,
        mock_github_files,
    ):
        """
        Test that rate limit headers are inspected and logged.
        
        **Validates: Requirements 5.1**
        
        Verifies that:
        - Rate limit headers are extracted from responses
        - Low rate limit triggers warning
        - Rate limit info is stored in provider
        """
        url = "https://github.com/owner/repo/pull/123"
        
        with patch('requests.get') as mock_get:
            # Set up mock responses with low rate limit
            mock_metadata_response = Mock()
            mock_metadata_response.status_code = 200
            mock_metadata_response.json.return_value = mock_github_pr_metadata
            mock_metadata_response.headers = {
                'X-RateLimit-Remaining': '5',  # Low rate limit
                'X-RateLimit-Limit': '5000',
                'X-RateLimit-Reset': str(int((datetime.now() + timedelta(hours=1)).timestamp())),
            }
            
            mock_diff_response = Mock()
            mock_diff_response.status_code = 200
            mock_diff_response.text = mock_github_pr_diff
            mock_diff_response.headers = mock_metadata_response.headers
            
            mock_files_response = Mock()
            mock_files_response.status_code = 200
            mock_files_response.json.return_value = mock_github_files
            mock_files_response.headers = mock_metadata_response.headers
            
            def side_effect(*args, **kwargs):
                headers = kwargs.get('headers', {})
                if 'application/vnd.github.v3.diff' in headers.get('Accept', ''):
                    return mock_diff_response
                elif '/files' in args[0]:
                    return mock_files_response
                else:
                    return mock_metadata_response
            
            mock_get.side_effect = side_effect
            
            # Capture log output
            with patch('agentic_code_review.providers.github_provider.logger') as mock_logger:
                with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                    flow = PRCodeReviewFlow()
                    flow._state = ReviewState(pr_input=url)
                    
                    # Execute read_pr_data
                    flow.read_pr_data()
                    
                    # Verify data was fetched successfully
                    assert len(flow.state.errors) == 0
                    
                    # Verify warning was logged for low rate limit
                    warning_calls = [call for call in mock_logger.warning.call_args_list 
                                   if 'rate limit low' in str(call).lower()]
                    assert len(warning_calls) > 0, "Should log warning for low rate limit"


class TestGitHubProviderDirectIntegration:
    """Direct integration tests for GitHubProvider class."""
    
    def test_provider_retry_with_exponential_backoff(self, setup_github_token, clear_cache):
        """
        Test that provider retries with exponential backoff on network errors.
        
        **Validates: Requirements 3.3**
        
        Verifies that:
        - Network errors trigger retry
        - Backoff time increases exponentially
        - Max retries is respected
        """
        provider = GitHubProvider()
        
        with patch('requests.get') as mock_get:
            # Fail first 2 times, succeed on 3rd
            mock_get.side_effect = [
                requests.exceptions.ConnectionError("Connection failed"),
                requests.exceptions.ConnectionError("Connection failed"),
                Mock(status_code=200, json=lambda: {"title": "Test"}, headers={
                    'X-RateLimit-Remaining': '5000',
                    'X-RateLimit-Limit': '5000',
                }),
            ]
            
            # Track sleep calls to verify exponential backoff
            sleep_times = []
            
            def mock_sleep(seconds):
                sleep_times.append(seconds)
            
            with patch('time.sleep', side_effect=mock_sleep):
                # This should succeed after retries
                response = provider._make_request_with_retry(
                    "https://api.github.com/repos/owner/repo/pulls/123",
                    {"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                assert len(sleep_times) == 2  # Slept twice before success
                
                # Verify exponential backoff: 1s, 2s
                assert sleep_times[0] == 1
                assert sleep_times[1] == 2
    
    def test_provider_cache_expiration(
        self,
        setup_github_token,
        clear_cache,
        mock_github_pr_metadata,
        mock_github_pr_diff,
        mock_github_files,
    ):
        """
        Test that cache expires after TTL.
        
        **Validates: Requirements 5.5**
        
        Verifies that:
        - Cached data is used within TTL
        - Expired cache entries are removed
        - New API call is made after expiration
        """
        provider = GitHubProvider()
        
        with patch('requests.get') as mock_get:
            # Set up mock responses
            mock_metadata_response = Mock()
            mock_metadata_response.status_code = 200
            mock_metadata_response.json.return_value = mock_github_pr_metadata
            mock_metadata_response.headers = {
                'X-RateLimit-Remaining': '5000',
                'X-RateLimit-Limit': '5000',
                'X-RateLimit-Reset': str(int((datetime.now() + timedelta(hours=1)).timestamp())),
            }
            
            mock_diff_response = Mock()
            mock_diff_response.status_code = 200
            mock_diff_response.text = mock_github_pr_diff
            mock_diff_response.headers = mock_metadata_response.headers
            
            mock_files_response = Mock()
            mock_files_response.status_code = 200
            mock_files_response.json.return_value = mock_github_files
            mock_files_response.headers = mock_metadata_response.headers
            
            def side_effect(*args, **kwargs):
                headers = kwargs.get('headers', {})
                if 'application/vnd.github.v3.diff' in headers.get('Accept', ''):
                    return mock_diff_response
                elif '/files' in args[0]:
                    return mock_files_response
                else:
                    return mock_metadata_response
            
            mock_get.side_effect = side_effect
            
            # First fetch - should call API
            pr_data1 = provider.fetch_pr_data(owner="owner", repo="repo", pr_number=123)
            first_call_count = mock_get.call_count
            assert first_call_count == 3
            
            # Second fetch immediately - should use cache
            pr_data2 = provider.fetch_pr_data(owner="owner", repo="repo", pr_number=123)
            assert mock_get.call_count == first_call_count  # No new calls
            assert pr_data1.diff == pr_data2.diff
            
            # Simulate cache expiration by modifying timestamp
            cache_key = provider._create_cache_key("owner", "repo", 123)
            if cache_key in _pr_cache:
                _pr_cache[cache_key].timestamp = datetime.now() - timedelta(seconds=301)
            
            # Third fetch after expiration - should call API again
            pr_data3 = provider.fetch_pr_data(owner="owner", repo="repo", pr_number=123)
            assert mock_get.call_count > first_call_count  # New calls made
    
    def test_provider_handles_empty_diff(self, setup_github_token, clear_cache):
        """
        Test that provider validates non-empty diff content.
        
        **Validates: Requirements 3.3**
        
        Verifies that:
        - Empty diff content is detected
        - Appropriate error is raised
        - Error message is descriptive
        """
        provider = GitHubProvider()
        
        with patch('requests.get') as mock_get:
            # Set up mock responses with empty diff
            mock_metadata_response = Mock()
            mock_metadata_response.status_code = 200
            mock_metadata_response.json.return_value = {
                "title": "Empty PR",
                "body": "This PR has no changes",
                "user": {"login": "testuser"},
            }
            mock_metadata_response.headers = {
                'X-RateLimit-Remaining': '5000',
                'X-RateLimit-Limit': '5000',
            }
            
            mock_diff_response = Mock()
            mock_diff_response.status_code = 200
            mock_diff_response.text = ""  # Empty diff
            mock_diff_response.headers = mock_metadata_response.headers
            
            def side_effect(*args, **kwargs):
                headers = kwargs.get('headers', {})
                if 'application/vnd.github.v3.diff' in headers.get('Accept', ''):
                    return mock_diff_response
                else:
                    return mock_metadata_response
            
            mock_get.side_effect = side_effect
            
            # Should raise ValueError for empty diff
            with pytest.raises(ValueError) as exc_info:
                provider.fetch_pr_data(owner="owner", repo="repo", pr_number=123)
            
            assert "no diff content" in str(exc_info.value).lower()
    
    def test_provider_token_redaction_in_errors(self, setup_github_token, clear_cache):
        """
        Test that authentication tokens are redacted from error messages.
        
        **Validates: Requirements 3.1**
        
        Verifies that:
        - Tokens do not appear in error messages
        - Error messages are still informative
        - Redaction works for various error types
        """
        provider = GitHubProvider(token="secret_token_12345")
        
        # Test redaction in network error
        test_text = "Error with token secret_token_12345 in message"
        redacted = provider._redact_token(test_text)
        assert "secret_token_12345" not in redacted
        assert "[REDACTED]" in redacted
        
        # Test redaction in Bearer format
        test_text2 = "Authorization: Bearer secret_token_12345"
        redacted2 = provider._redact_token(test_text2)
        assert "secret_token_12345" not in redacted2
        assert "Bearer [REDACTED]" in redacted2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
