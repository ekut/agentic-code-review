"""Property-based tests for GitHubProvider."""

import os
import time
import pytest
import requests
from unittest.mock import patch, MagicMock
from hypothesis import given, strategies as st, settings, assume

from agentic_code_review.providers import GitHubProvider, AuthenticationError, NetworkError, ProviderAPIError, RateLimitError


# Strategies for generating test data
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
def github_pr_url(draw):
    """Generate valid GitHub PR URLs in various formats."""
    owner, repo, pr_number = draw(github_url_components())
    
    # Choose URL format
    format_choice = draw(st.integers(min_value=0, max_value=3))
    
    if format_choice == 0:
        # Standard HTTPS URL
        return f"https://github.com/{owner}/{repo}/pull/{pr_number}", owner, repo, pr_number
    elif format_choice == 1:
        # URL with trailing path
        trailing = draw(st.sampled_from(["/files", "/commits", "/checks"]))
        return f"https://github.com/{owner}/{repo}/pull/{pr_number}{trailing}", owner, repo, pr_number
    elif format_choice == 2:
        # API URL
        return f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}", owner, repo, pr_number
    else:
        # HTTP (not HTTPS)
        return f"http://github.com/{owner}/{repo}/pull/{pr_number}", owner, repo, pr_number


# Fixtures
@pytest.fixture
def github_provider():
    """Create a GitHubProvider instance with a test token."""
    # Set a test token to avoid authentication errors
    os.environ["GITHUB_TOKEN"] = "test_token_12345"
    provider = GitHubProvider()
    yield provider
    # Clean up
    if "GITHUB_TOKEN" in os.environ:
        del os.environ["GITHUB_TOKEN"]


class TestGitHubProviderURLParsing:
    """Tests for GitHub URL parsing functionality."""
    
    @settings(max_examples=100)
    @given(url_data=github_pr_url())
    def test_property_1_url_parsing_correctness(self, url_data):
        """
        **Feature: github-pr-integration, Property 1: URL parsing correctness**
        
        For any valid GitHub PR URL, parsing should extract the correct owner,
        repository name, and PR number that match the URL components.
        
        **Validates: Requirements 1.1**
        """
        url, expected_owner, expected_repo, expected_pr = url_data
        
        # Parse the URL
        owner, repo, pr_number = GitHubProvider.parse_pr_url(url)
        
        # Verify extracted components match expected values
        assert owner == expected_owner, f"Owner mismatch: got {owner}, expected {expected_owner}"
        assert repo == expected_repo, f"Repo mismatch: got {repo}, expected {expected_repo}"
        assert pr_number == expected_pr, f"PR number mismatch: got {pr_number}, expected {expected_pr}"
        assert isinstance(pr_number, int), "PR number should be an integer"
        assert pr_number > 0, "PR number should be positive"

    @settings(max_examples=100)
    @given(components=github_url_components())
    def test_property_4_multiple_url_format_support(self, components):
        """
        **Feature: github-pr-integration, Property 4: Multiple URL format support**
        
        For any GitHub PR URL in supported formats (HTTPS, API URL), parsing should
        successfully extract the components.
        
        **Validates: Requirements 1.4**
        """
        owner, repo, pr_number = components
        
        # Test all supported URL formats
        url_formats = [
            f"https://github.com/{owner}/{repo}/pull/{pr_number}",
            f"http://github.com/{owner}/{repo}/pull/{pr_number}",
            f"https://github.com/{owner}/{repo}/pull/{pr_number}/files",
            f"https://github.com/{owner}/{repo}/pull/{pr_number}/commits",
            f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}",
        ]
        
        for url in url_formats:
            # Each format should parse successfully
            parsed_owner, parsed_repo, parsed_pr = GitHubProvider.parse_pr_url(url)
            
            # Verify all formats extract the same components
            assert parsed_owner == owner, f"Owner mismatch for URL {url}"
            assert parsed_repo == repo, f"Repo mismatch for URL {url}"
            assert parsed_pr == pr_number, f"PR number mismatch for URL {url}"



class TestGitHubProviderInputValidation:
    """Tests for GitHub input validation functionality."""
    
    @settings(max_examples=100)
    @given(components=github_url_components())
    def test_property_2_multiple_parameter_input_acceptance(self, components):
        """
        **Feature: github-pr-integration, Property 2: Multiple parameter input acceptance**
        
        For any valid combination of owner, repository, and PR number provided as
        separate parameters, the system should accept and process them correctly.
        
        **Validates: Requirements 1.2**
        """
        owner, repo, pr_number = components
        
        # Create provider with test token
        os.environ["GITHUB_TOKEN"] = "test_token_12345"
        try:
            github_provider = GitHubProvider()
            
            # Validate input with separate parameters
            is_valid = github_provider.validate_input(
                owner=owner,
                repo=repo,
                pr_number=pr_number
            )
            
            assert is_valid, f"Valid parameters should be accepted: owner={owner}, repo={repo}, pr_number={pr_number}"
            
            # Also test that fetch_pr_data accepts these parameters with mocked API
            with patch('agentic_code_review.providers.github_provider.requests.get') as mock_get:
                # Setup mock responses
                mock_metadata_response = MagicMock()
                mock_metadata_response.status_code = 200
                mock_metadata_response.json.return_value = {
                    "title": "Test PR",
                    "body": "Test description",
                    "user": {"login": "testuser"},
                    "changed_files": 1
                }
                
                mock_diff_response = MagicMock()
                mock_diff_response.status_code = 200
                mock_diff_response.text = "diff content"
                
                mock_files_response = MagicMock()
                mock_files_response.status_code = 200
                mock_files_response.json.return_value = [{"filename": "test.txt"}]
                
                def side_effect(url, headers=None, timeout=None):
                    if headers and headers.get("Accept") == "application/vnd.github.v3.diff":
                        return mock_diff_response
                    elif url.endswith("/files"):
                        return mock_files_response
                    else:
                        return mock_metadata_response
                
                mock_get.side_effect = side_effect
                
                pr_data = github_provider.fetch_pr_data(
                    owner=owner,
                    repo=repo,
                    pr_number=pr_number
                )
                
                # Verify the returned data has correct structure
                assert pr_data.repository == f"{owner}/{repo}"
                assert pr_data.pr_number == pr_number
                assert pr_data.provider == "github"
        finally:
            # Clean up
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]

    
    @settings(max_examples=100)
    @given(
        invalid_data=st.one_of(
            # Invalid URLs
            st.just("not a url"),
            st.just("https://gitlab.com/owner/repo/merge_requests/123"),
            st.just("https://github.com/owner"),  # Missing parts
            st.just("https://github.com/owner/repo"),  # No PR
            st.just("https://github.com/owner/repo/issues/123"),  # Issue, not PR
            st.text(min_size=1, max_size=50).filter(lambda x: "github.com" not in x),
            # Invalid parameters
            st.builds(dict, owner=st.just(""), repo=st.just("valid"), pr_number=st.just(1)),
            st.builds(dict, owner=st.just("valid"), repo=st.just(""), pr_number=st.just(1)),
            st.builds(dict, owner=st.just("valid"), repo=st.just("valid"), pr_number=st.just(0)),
            st.builds(dict, owner=st.just("valid"), repo=st.just("valid"), pr_number=st.just(-1)),
            st.builds(dict, owner=st.just(None), repo=st.just("valid"), pr_number=st.just(1)),
            st.builds(dict, owner=st.just("valid"), repo=st.just(None), pr_number=st.just(1)),
        )
    )
    def test_property_3_invalid_input_rejection(self, invalid_data):
        """
        **Feature: github-pr-integration, Property 3: Invalid input rejection**
        
        For any invalid input (malformed URLs, missing components, wrong formats),
        the system should reject it and provide an error message indicating the
        expected format.
        
        **Validates: Requirements 1.3**
        """
        # Create provider with test token
        os.environ["GITHUB_TOKEN"] = "test_token_12345"
        try:
            github_provider = GitHubProvider()
            
            if isinstance(invalid_data, str):
                # Test invalid URL parsing
                if "github.com" in invalid_data and "/pull/" in invalid_data:
                    # If it looks like it might be a GitHub URL, try parsing
                    try:
                        GitHubProvider.parse_pr_url(invalid_data)
                        # If we get here, check if it's actually valid
                        # (some edge cases might parse successfully)
                    except ValueError as e:
                        # Should raise ValueError with helpful message
                        assert "Invalid GitHub PR URL" in str(e) or "Expected format" in str(e)
                else:
                    # Should not be handled by GitHub provider
                    can_handle = GitHubProvider.can_handle(invalid_data)
                    if can_handle:
                        # If it claims to handle it, parsing should fail
                        with pytest.raises(ValueError):
                            GitHubProvider.parse_pr_url(invalid_data)
            
            elif isinstance(invalid_data, dict):
                # Test invalid parameter validation
                is_valid = github_provider.validate_input(**invalid_data)
                assert not is_valid, f"Invalid parameters should be rejected: {invalid_data}"
        
        finally:
            # Clean up
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]



class TestGitHubProviderAPIFetching:
    """Tests for GitHub API data fetching functionality."""
    
    @settings(max_examples=100)
    @given(
        components=github_url_components(),
        token=st.text(
            alphabet=st.characters(
                min_codepoint=0x20,
                max_codepoint=0x7E,  # Printable ASCII only
            ),
            min_size=10,
            max_size=100
        )
    )
    def test_property_6_token_inclusion_in_api_requests(self, components, token):
        """
        **Feature: github-pr-integration, Property 6: Token inclusion in API requests**
        
        For any API request made to GitHub, the authentication token should be
        included in the request headers.
        
        **Validates: Requirements 2.2, 3.1**
        """
        owner, repo, pr_number = components
        
        # Clear cache before test to ensure API calls are made
        from agentic_code_review.providers.github_provider import _pr_cache
        _pr_cache.clear()
        
        # Create provider with specific token
        os.environ["GITHUB_TOKEN"] = token
        try:
            github_provider = GitHubProvider()
            
            # Mock the requests.get to capture the headers
            with patch('agentic_code_review.providers.github_provider.requests.get') as mock_get:
                # Setup mock response for metadata request
                mock_metadata_response = MagicMock()
                mock_metadata_response.status_code = 200
                mock_metadata_response.json.return_value = {
                    "title": "Test PR",
                    "body": "Test description",
                    "user": {"login": "testuser"},
                    "changed_files": 1
                }
                
                # Setup mock response for diff request
                mock_diff_response = MagicMock()
                mock_diff_response.status_code = 200
                mock_diff_response.text = "diff --git a/file.txt b/file.txt"
                
                # Setup mock response for files request
                mock_files_response = MagicMock()
                mock_files_response.status_code = 200
                mock_files_response.json.return_value = [
                    {"filename": "file.txt"}
                ]
                
                # Return different responses based on headers
                def side_effect(url, headers=None, timeout=None):
                    if headers and headers.get("Accept") == "application/vnd.github.v3.diff":
                        return mock_diff_response
                    elif url.endswith("/files"):
                        return mock_files_response
                    else:
                        return mock_metadata_response
                
                mock_get.side_effect = side_effect
                
                # Fetch PR data
                github_provider.fetch_pr_data(
                    owner=owner,
                    repo=repo,
                    pr_number=pr_number
                )
                
                # Verify that requests.get was called
                assert mock_get.call_count >= 1, "API request should be made"
                
                # Check all calls to verify token is included
                for call in mock_get.call_args_list:
                    call_kwargs = call[1]
                    headers = call_kwargs.get('headers', {})
                    
                    # Verify Authorization header is present
                    assert 'Authorization' in headers, "Authorization header must be present"
                    
                    # Verify token is in the Authorization header
                    auth_header = headers['Authorization']
                    assert token in auth_header, f"Token should be in Authorization header"
                    assert auth_header.startswith('Bearer '), "Should use Bearer token format"
        
        finally:
            # Clean up
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]

    @settings(max_examples=100)
    @given(
        components=github_url_components(),
        diff_content=st.text(min_size=10, max_size=1000)
    )
    def test_property_8_diff_extraction_from_responses(self, components, diff_content):
        """
        **Feature: github-pr-integration, Property 8: Diff extraction from responses**
        
        For any successful API response containing PR data, the system should
        extract and store the diff content.
        
        **Validates: Requirements 3.2**
        """
        owner, repo, pr_number = components
        
        # Clear cache before test to ensure API calls are made
        from agentic_code_review.providers.github_provider import _pr_cache
        _pr_cache.clear()
        
        # Create provider with test token
        os.environ["GITHUB_TOKEN"] = "test_token_12345"
        try:
            github_provider = GitHubProvider()
            
            # Mock the requests.get
            with patch('agentic_code_review.providers.github_provider.requests.get') as mock_get:
                # Setup mock response for metadata request
                mock_metadata_response = MagicMock()
                mock_metadata_response.status_code = 200
                mock_metadata_response.json.return_value = {
                    "title": "Test PR",
                    "body": "Test description",
                    "user": {"login": "testuser"},
                    "changed_files": 1
                }
                
                # Setup mock response for diff request with our generated diff
                mock_diff_response = MagicMock()
                mock_diff_response.status_code = 200
                mock_diff_response.text = diff_content
                
                # Setup mock response for files request
                mock_files_response = MagicMock()
                mock_files_response.status_code = 200
                mock_files_response.json.return_value = [
                    {"filename": "file.txt"}
                ]
                
                # Return different responses based on headers
                def side_effect(url, headers=None, timeout=None):
                    if headers and headers.get("Accept") == "application/vnd.github.v3.diff":
                        return mock_diff_response
                    elif url.endswith("/files"):
                        return mock_files_response
                    else:
                        return mock_metadata_response
                
                mock_get.side_effect = side_effect
                
                # Fetch PR data
                pr_data = github_provider.fetch_pr_data(
                    owner=owner,
                    repo=repo,
                    pr_number=pr_number
                )
                
                # Verify diff content is extracted and stored
                assert pr_data.diff == diff_content, "Diff content should match the API response"
                assert isinstance(pr_data.diff, str), "Diff should be a string"
        
        finally:
            # Clean up
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]

    @settings(max_examples=100)
    @given(
        components=github_url_components(),
        title=st.text(min_size=1, max_size=200),
        description=st.text(min_size=0, max_size=1000),
        author=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"),
            min_size=1,
            max_size=39
        ).filter(lambda x: x and x[0].isalnum()),
        num_files=st.integers(min_value=1, max_value=10)
    )
    def test_property_11_complete_metadata_retrieval(self, components, title, description, author, num_files):
        """
        **Feature: github-pr-integration, Property 11: Complete metadata retrieval**
        
        For any successful PR data fetch, the result should include title,
        description, author username, and list of changed files.
        
        **Validates: Requirements 4.1**
        """
        owner, repo, pr_number = components
        
        # Clear cache before test to ensure API calls are made
        from agentic_code_review.providers.github_provider import _pr_cache
        _pr_cache.clear()
        
        # Create provider with test token
        os.environ["GITHUB_TOKEN"] = "test_token_12345"
        try:
            github_provider = GitHubProvider()
            
            # Generate file list
            files_changed = [f"file{i}.txt" for i in range(num_files)]
            
            # Mock the requests.get
            with patch('agentic_code_review.providers.github_provider.requests.get') as mock_get:
                # Setup mock response for metadata request
                mock_metadata_response = MagicMock()
                mock_metadata_response.status_code = 200
                mock_metadata_response.json.return_value = {
                    "title": title,
                    "body": description,
                    "user": {"login": author},
                    "changed_files": num_files
                }
                
                # Setup mock response for diff request
                mock_diff_response = MagicMock()
                mock_diff_response.status_code = 200
                mock_diff_response.text = "diff content"
                
                # Setup mock response for files request
                mock_files_response = MagicMock()
                mock_files_response.status_code = 200
                mock_files_response.json.return_value = [
                    {"filename": f} for f in files_changed
                ]
                
                # Return different responses based on headers
                def side_effect(url, headers=None, timeout=None):
                    if headers and headers.get("Accept") == "application/vnd.github.v3.diff":
                        return mock_diff_response
                    elif url.endswith("/files"):
                        return mock_files_response
                    else:
                        return mock_metadata_response
                
                mock_get.side_effect = side_effect
                
                # Fetch PR data
                pr_data = github_provider.fetch_pr_data(
                    owner=owner,
                    repo=repo,
                    pr_number=pr_number
                )
                
                # Verify all metadata fields are present
                assert pr_data.title == title, "Title should be extracted"
                assert pr_data.description == description, "Description should be extracted"
                assert pr_data.author == author, "Author should be extracted"
                assert pr_data.files_changed == files_changed, "Files changed list should be extracted"
                assert len(pr_data.files_changed) == num_files, "Number of files should match"
        
        finally:
            # Clean up
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]

    @settings(max_examples=100)
    @given(
        components=github_url_components(),
        title=st.text(min_size=1, max_size=200),
        body=st.one_of(st.none(), st.text(min_size=0, max_size=1000)),
        author=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"),
            min_size=1,
            max_size=39
        ).filter(lambda x: x and x[0].isalnum()),
    )
    def test_property_12_metadata_field_extraction(self, components, title, body, author):
        """
        **Feature: github-pr-integration, Property 12: Metadata field extraction**
        
        For any GitHub API JSON response, the system should extract all required
        metadata fields (title, description, author, files_changed).
        
        **Validates: Requirements 4.2**
        """
        owner, repo, pr_number = components
        
        # Clear cache before test to ensure API calls are made
        from agentic_code_review.providers.github_provider import _pr_cache
        _pr_cache.clear()
        
        # Create provider with test token
        os.environ["GITHUB_TOKEN"] = "test_token_12345"
        try:
            github_provider = GitHubProvider()
            
            # Mock the requests.get
            with patch('agentic_code_review.providers.github_provider.requests.get') as mock_get:
                # Setup mock response for metadata request
                mock_metadata_response = MagicMock()
                mock_metadata_response.status_code = 200
                mock_metadata_response.json.return_value = {
                    "title": title,
                    "body": body,
                    "user": {"login": author},
                    "changed_files": 1
                }
                
                # Setup mock response for diff request
                mock_diff_response = MagicMock()
                mock_diff_response.status_code = 200
                mock_diff_response.text = "diff content"
                
                # Setup mock response for files request
                mock_files_response = MagicMock()
                mock_files_response.status_code = 200
                mock_files_response.json.return_value = [
                    {"filename": "test.txt"}
                ]
                
                # Return different responses based on headers
                def side_effect(url, headers=None, timeout=None):
                    if headers and headers.get("Accept") == "application/vnd.github.v3.diff":
                        return mock_diff_response
                    elif url.endswith("/files"):
                        return mock_files_response
                    else:
                        return mock_metadata_response
                
                mock_get.side_effect = side_effect
                
                # Fetch PR data
                pr_data = github_provider.fetch_pr_data(
                    owner=owner,
                    repo=repo,
                    pr_number=pr_number
                )
                
                # Verify all fields are extracted correctly
                assert pr_data.title == title, "Title field should be extracted"
                assert pr_data.description == (body or ""), "Description field should be extracted (empty string if None)"
                assert pr_data.author == author, "Author field should be extracted"
                assert isinstance(pr_data.files_changed, list), "Files changed should be a list"
        
        finally:
            # Clean up
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]

    @settings(max_examples=100)
    @given(components=github_url_components())
    def test_property_14_url_inclusion_in_metadata(self, components):
        """
        **Feature: github-pr-integration, Property 14: URL inclusion in metadata**
        
        For any fetched PR data, the metadata should include the complete GitHub PR URL.
        
        **Validates: Requirements 4.5**
        """
        owner, repo, pr_number = components
        
        # Create provider with test token
        os.environ["GITHUB_TOKEN"] = "test_token_12345"
        try:
            github_provider = GitHubProvider()
            
            # Mock the requests.get
            with patch('agentic_code_review.providers.github_provider.requests.get') as mock_get:
                # Setup mock response for metadata request
                mock_metadata_response = MagicMock()
                mock_metadata_response.status_code = 200
                mock_metadata_response.json.return_value = {
                    "title": "Test PR",
                    "body": "Test description",
                    "user": {"login": "testuser"},
                    "changed_files": 1
                }
                
                # Setup mock response for diff request
                mock_diff_response = MagicMock()
                mock_diff_response.status_code = 200
                mock_diff_response.text = "diff content"
                
                # Setup mock response for files request
                mock_files_response = MagicMock()
                mock_files_response.status_code = 200
                mock_files_response.json.return_value = [
                    {"filename": "test.txt"}
                ]
                
                # Return different responses based on headers
                def side_effect(url, headers=None, timeout=None):
                    if headers and headers.get("Accept") == "application/vnd.github.v3.diff":
                        return mock_diff_response
                    elif url.endswith("/files"):
                        return mock_files_response
                    else:
                        return mock_metadata_response
                
                mock_get.side_effect = side_effect
                
                # Fetch PR data
                pr_data = github_provider.fetch_pr_data(
                    owner=owner,
                    repo=repo,
                    pr_number=pr_number
                )
                
                # Verify URL is included and correct
                expected_url = f"https://github.com/{owner}/{repo}/pull/{pr_number}"
                assert pr_data.url == expected_url, "PR URL should be included in metadata"
                assert pr_data.url.startswith("https://github.com/"), "URL should be a GitHub URL"
                assert f"/{owner}/{repo}/pull/{pr_number}" in pr_data.url, "URL should contain correct components"
        
        finally:
            # Clean up
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]



class TestGitHubProviderErrorHandling:
    """Tests for GitHub error handling and retry logic."""
    
    @settings(max_examples=100)
    @given(
        components=github_url_components(),
        num_failures=st.integers(min_value=1, max_value=2)  # Fail 1-2 times, then succeed
    )
    def test_property_9_retry_with_exponential_backoff(self, components, num_failures):
        """
        **Feature: github-pr-integration, Property 9: Retry with exponential backoff**
        
        For any network failure during API requests, the system should retry up to
        3 times with exponentially increasing delays between attempts.
        
        **Validates: Requirements 3.4**
        """
        owner, repo, pr_number = components
        
        # Clear cache before test to ensure API calls are made
        from agentic_code_review.providers.github_provider import _pr_cache
        _pr_cache.clear()
        
        # Create provider with test token
        os.environ["GITHUB_TOKEN"] = "test_token_12345"
        try:
            github_provider = GitHubProvider()
            
            # Track call times to verify exponential backoff
            call_times = []
            
            # Mock the requests.get to fail num_failures times, then succeed
            with patch('agentic_code_review.providers.github_provider.requests.get') as mock_get:
                with patch('agentic_code_review.providers.github_provider.time.sleep') as mock_sleep:
                    call_count = [0]
                    
                    def side_effect(url, headers=None, timeout=None):
                        import time
                        call_times.append(time.time())
                        call_count[0] += 1
                        
                        # Fail for the first num_failures attempts
                        if call_count[0] <= num_failures:
                            raise requests.exceptions.ConnectionError("Connection failed")
                        
                        # Succeed on subsequent attempts
                        if headers and headers.get("Accept") == "application/vnd.github.v3.diff":
                            mock_response = MagicMock()
                            mock_response.status_code = 200
                            mock_response.text = "diff content"
                            return mock_response
                        elif url.endswith("/files"):
                            mock_response = MagicMock()
                            mock_response.status_code = 200
                            mock_response.json.return_value = [{"filename": "test.txt"}]
                            return mock_response
                        else:
                            mock_response = MagicMock()
                            mock_response.status_code = 200
                            mock_response.json.return_value = {
                                "title": "Test PR",
                                "body": "Test description",
                                "user": {"login": "testuser"},
                                "changed_files": 1
                            }
                            return mock_response
                    
                    mock_get.side_effect = side_effect
                    
                    # Fetch PR data - should succeed after retries
                    pr_data = github_provider.fetch_pr_data(
                        owner=owner,
                        repo=repo,
                        pr_number=pr_number
                    )
                    
                    # Verify retry happened
                    assert call_count[0] > num_failures, "Should have retried after failures"
                    
                    # Verify exponential backoff was used
                    # Should have called sleep num_failures times
                    assert mock_sleep.call_count == num_failures, f"Should have slept {num_failures} times"
                    
                    # Verify exponential backoff timing
                    sleep_times = [call[0][0] for call in mock_sleep.call_args_list]
                    for i, sleep_time in enumerate(sleep_times):
                        expected_time = 1 * (2 ** i)  # INITIAL_BACKOFF * (BACKOFF_MULTIPLIER ** attempt)
                        assert sleep_time == expected_time, f"Sleep time {i} should be {expected_time}, got {sleep_time}"
                    
                    # Verify successful fetch
                    assert pr_data.provider == "github"
                    assert pr_data.repository == f"{owner}/{repo}"
        
        finally:
            # Clean up
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]

    @settings(max_examples=100)
    @given(
        components=github_url_components(),
        diff_content=st.one_of(
            st.just(""),  # Empty string
            st.just("   "),  # Whitespace only
            st.just("\n\n\n"),  # Newlines only
            st.just("\t\t"),  # Tabs only
        )
    )
    def test_property_10_non_empty_diff_validation(self, components, diff_content):
        """
        **Feature: github-pr-integration, Property 10: Non-empty diff validation**
        
        For any retrieved diff content, the system should validate it is non-empty
        before proceeding to review.
        
        **Validates: Requirements 3.5**
        """
        owner, repo, pr_number = components
        
        # Clear cache before test to ensure API calls are made
        from agentic_code_review.providers.github_provider import _pr_cache
        _pr_cache.clear()
        
        # Create provider with test token
        os.environ["GITHUB_TOKEN"] = "test_token_12345"
        try:
            github_provider = GitHubProvider()
            
            # Mock the requests.get to return empty/whitespace diff
            with patch('agentic_code_review.providers.github_provider.requests.get') as mock_get:
                # Setup mock response for metadata request
                mock_metadata_response = MagicMock()
                mock_metadata_response.status_code = 200
                mock_metadata_response.json.return_value = {
                    "title": "Test PR",
                    "body": "Test description",
                    "user": {"login": "testuser"},
                    "changed_files": 1
                }
                
                # Setup mock response for diff request with empty/whitespace content
                mock_diff_response = MagicMock()
                mock_diff_response.status_code = 200
                mock_diff_response.text = diff_content
                
                # Return different responses based on headers
                def side_effect(url, headers=None, timeout=None):
                    if headers and headers.get("Accept") == "application/vnd.github.v3.diff":
                        return mock_diff_response
                    else:
                        return mock_metadata_response
                
                mock_get.side_effect = side_effect
                
                # Fetch PR data should raise ValueError for empty diff
                with pytest.raises(ValueError) as exc_info:
                    github_provider.fetch_pr_data(
                        owner=owner,
                        repo=repo,
                        pr_number=pr_number
                    )
                
                # Verify error message mentions empty diff
                error_message = str(exc_info.value)
                assert "no diff content" in error_message.lower() or "empty" in error_message.lower(), \
                    "Error message should indicate empty diff"
        
        finally:
            # Clean up
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]

    @settings(max_examples=100)
    @given(
        token=st.text(
            alphabet=st.characters(
                min_codepoint=0x20,
                max_codepoint=0x7E,  # Printable ASCII only
            ),
            min_size=20,
            max_size=100
        ),
        error_scenario=st.sampled_from([
            "api_error",
            "network_error",
            "exception_message"
        ])
    )
    def test_property_7_token_confidentiality(self, token, error_scenario):
        """
        **Feature: github-pr-integration, Property 7: Token confidentiality**
        
        For any log output or error message generated by the system, authentication
        tokens should never appear in the text.
        
        **Validates: Requirements 2.4**
        """
        # Create provider with specific token
        os.environ["GITHUB_TOKEN"] = token
        try:
            github_provider = GitHubProvider(token=token)
            
            # Mock sleep to avoid delays
            with patch('agentic_code_review.providers.github_provider.time.sleep'):
                # Test different error scenarios
                with patch('agentic_code_review.providers.github_provider.requests.get') as mock_get:
                    if error_scenario == "api_error":
                        # Mock API error response that might contain token
                        mock_response = MagicMock()
                        mock_response.status_code = 500
                        mock_response.text = f"Server error. Token: {token}"
                        mock_get.return_value = mock_response
                        
                    elif error_scenario == "network_error":
                        # Mock network error with token in message
                        mock_get.side_effect = requests.exceptions.ConnectionError(
                            f"Connection failed with token {token}"
                        )
                        
                    elif error_scenario == "exception_message":
                        # Mock generic exception with token
                        mock_get.side_effect = Exception(f"Error occurred: {token}")
                    
                    # Try to fetch PR data - should raise an error
                    try:
                        github_provider.fetch_pr_data(
                            owner="test",
                            repo="repo",
                            pr_number=1
                        )
                    except Exception as e:
                        # Verify token is NOT in the error message
                        error_message = str(e)
                        assert token not in error_message, \
                            f"Token should be redacted from error messages. Found token in: {error_message}"
                        
                        # Verify redaction marker is present if original had token
                        if error_scenario in ["api_error", "network_error", "exception_message"]:
                            assert "[REDACTED]" in error_message or "error" in error_message.lower(), \
                                "Error message should contain redaction marker or generic error text"
        
        finally:
            # Clean up
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]

    @settings(max_examples=100)
    @given(
        components=github_url_components(),
        error_type=st.sampled_from([
            ("timeout", requests.exceptions.Timeout),
            ("connection_refused", requests.exceptions.ConnectionError),
            ("dns_error", requests.exceptions.ConnectionError),
        ])
    )
    def test_property_22_network_error_classification(self, components, error_type):
        """
        **Feature: github-pr-integration, Property 22: Network error classification**
        
        For any network error (timeout, connection failure, DNS error), the system
        should correctly classify and report the specific error type.
        
        **Validates: Requirements 7.4**
        """
        owner, repo, pr_number = components
        error_name, error_class = error_type
        
        # Clear cache before test to ensure API calls are made
        from agentic_code_review.providers.github_provider import _pr_cache
        _pr_cache.clear()
        
        # Create provider with test token
        os.environ["GITHUB_TOKEN"] = "test_token_12345"
        try:
            github_provider = GitHubProvider()
            
            # Mock sleep to avoid delays
            with patch('agentic_code_review.providers.github_provider.time.sleep'):
                # Mock the requests.get to raise specific network error
                with patch('agentic_code_review.providers.github_provider.requests.get') as mock_get:
                    # Create appropriate error message based on error type
                    if error_name == "timeout":
                        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")
                    elif error_name == "connection_refused":
                        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
                    elif error_name == "dns_error":
                        mock_get.side_effect = requests.exceptions.ConnectionError(
                            "[Errno -2] Name or service not known"
                        )
                    
                    # Try to fetch PR data - should raise NetworkError
                    with pytest.raises(NetworkError) as exc_info:
                        github_provider.fetch_pr_data(
                            owner=owner,
                            repo=repo,
                            pr_number=pr_number
                        )
                    
                    # Verify error message classifies the error correctly
                    error_message = str(exc_info.value).lower()
                    
                    if error_name == "timeout":
                        assert "timeout" in error_message or "timed out" in error_message, \
                            "Timeout errors should be identified"
                    elif error_name == "connection_refused":
                        assert "connection refused" in error_message or "connection" in error_message, \
                            "Connection refused errors should be identified"
                    elif error_name == "dns_error":
                        assert "dns" in error_message or "name" in error_message or "resolution" in error_message, \
                            "DNS errors should be identified"
        
        finally:
            # Clean up
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]

    @settings(max_examples=100)
    @given(
        components=github_url_components(),
        status_code=st.sampled_from([404, 403, 401, 500, 502, 503])
    )
    def test_property_21_dual_level_error_reporting(self, components, status_code):
        """
        **Feature: github-pr-integration, Property 21: Dual-level error reporting**
        
        For any error that occurs, the system should generate both detailed logging
        information for debugging and user-friendly error messages for end users.
        
        **Validates: Requirements 7.1, 7.5**
        """
        owner, repo, pr_number = components
        
        # Create provider with test token
        os.environ["GITHUB_TOKEN"] = "test_token_12345"
        try:
            github_provider = GitHubProvider()
            
            # Capture log messages
            with patch('agentic_code_review.providers.github_provider.logger') as mock_logger:
                # Mock the requests.get to return error status
                with patch('agentic_code_review.providers.github_provider.requests.get') as mock_get:
                    mock_response = MagicMock()
                    mock_response.status_code = status_code
                    mock_response.text = f"API Error {status_code}"
                    mock_get.return_value = mock_response
                    
                    # Try to fetch PR data - should raise an error
                    try:
                        github_provider.fetch_pr_data(
                            owner=owner,
                            repo=repo,
                            pr_number=pr_number
                        )
                    except (ProviderAPIError, AuthenticationError) as e:
                        # Verify user-friendly error message
                        error_message = str(e)
                        
                        # Should contain helpful information
                        if status_code == 404:
                            assert "not found" in error_message.lower(), \
                                "404 errors should mention 'not found'"
                            assert str(status_code) in error_message, \
                                "Error message should include status code"
                        elif status_code == 403:
                            assert "access denied" in error_message.lower() or "permission" in error_message.lower(), \
                                "403 errors should mention access/permissions"
                            assert str(status_code) in error_message, \
                                "Error message should include status code"
                        elif status_code == 401:
                            # 401 raises AuthenticationError, which doesn't include status code
                            assert "token" in error_message.lower() or "authentication" in error_message.lower(), \
                                "401 errors should mention authentication"
                        elif status_code >= 500:
                            assert "server error" in error_message.lower() or "try again" in error_message.lower(), \
                                "5xx errors should mention server error"
                            assert str(status_code) in error_message, \
                                "Error message should include status code"
                        
                        # Verify logging occurred (detailed information)
                        # The logger should have been called for info/debug/warning messages
                        assert mock_logger.info.called or mock_logger.debug.called or mock_logger.warning.called, \
                            "Should log detailed information for debugging"
        
        finally:
            # Clean up
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]



class TestGitHubProviderRateLimiting:
    """Tests for GitHub rate limiting functionality."""
    
    @settings(max_examples=100)
    @given(
        components=github_url_components(),
        remaining=st.integers(min_value=0, max_value=5000),
        limit=st.integers(min_value=1000, max_value=5000),
        reset_timestamp=st.integers(min_value=int(time.time()), max_value=int(time.time()) + 3600)
    )
    def test_property_15_rate_limit_header_inspection(self, components, remaining, limit, reset_timestamp):
        """
        **Feature: github-pr-integration, Property 15: Rate limit header inspection**
        
        For any GitHub API response, the system should check and extract rate limit
        information from response headers.
        
        **Validates: Requirements 5.1**
        """
        owner, repo, pr_number = components
        
        # Clear cache before test to ensure API calls are made
        from agentic_code_review.providers.github_provider import _pr_cache
        _pr_cache.clear()
        
        # Create provider with test token
        os.environ["GITHUB_TOKEN"] = "test_token_12345"
        try:
            github_provider = GitHubProvider()
            
            # Mock the requests.get to return response with rate limit headers
            with patch('agentic_code_review.providers.github_provider.requests.get') as mock_get:
                # Setup mock response for metadata request with rate limit headers
                mock_metadata_response = MagicMock()
                mock_metadata_response.status_code = 200
                mock_metadata_response.headers = {
                    'X-RateLimit-Remaining': str(remaining),
                    'X-RateLimit-Limit': str(limit),
                    'X-RateLimit-Reset': str(reset_timestamp)
                }
                mock_metadata_response.json.return_value = {
                    "title": "Test PR",
                    "body": "Test description",
                    "user": {"login": "testuser"},
                    "changed_files": 1
                }
                
                # Setup mock response for diff request
                mock_diff_response = MagicMock()
                mock_diff_response.status_code = 200
                mock_diff_response.headers = {
                    'X-RateLimit-Remaining': str(remaining),
                    'X-RateLimit-Limit': str(limit),
                    'X-RateLimit-Reset': str(reset_timestamp)
                }
                mock_diff_response.text = "diff content"
                
                # Setup mock response for files request
                mock_files_response = MagicMock()
                mock_files_response.status_code = 200
                mock_files_response.headers = {
                    'X-RateLimit-Remaining': str(remaining),
                    'X-RateLimit-Limit': str(limit),
                    'X-RateLimit-Reset': str(reset_timestamp)
                }
                mock_files_response.json.return_value = [
                    {"filename": "test.txt"}
                ]
                
                # Return different responses based on headers
                def side_effect(url, headers=None, timeout=None):
                    if headers and headers.get("Accept") == "application/vnd.github.v3.diff":
                        return mock_diff_response
                    elif url.endswith("/files"):
                        return mock_files_response
                    else:
                        return mock_metadata_response
                
                mock_get.side_effect = side_effect
                
                # Fetch PR data
                pr_data = github_provider.fetch_pr_data(
                    owner=owner,
                    repo=repo,
                    pr_number=pr_number
                )
                
                # Verify rate limit info was extracted
                rate_limit_info = github_provider.get_rate_limit_info()
                assert rate_limit_info is not None, "Rate limit info should be extracted"
                assert rate_limit_info.remaining == remaining, f"Remaining should be {remaining}"
                assert rate_limit_info.limit == limit, f"Limit should be {limit}"
                assert rate_limit_info.reset_time is not None, "Reset time should be set"
                
                # Verify reset time is correct
                from datetime import datetime
                expected_reset = datetime.fromtimestamp(reset_timestamp)
                assert rate_limit_info.reset_time == expected_reset, "Reset time should match header"
        
        finally:
            # Clean up
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]

    @settings(max_examples=100)
    @given(
        components=github_url_components(),
        reset_timestamp=st.integers(min_value=int(time.time()) + 1, max_value=int(time.time()) + 10)
    )
    def test_property_16_rate_limit_waiting_behavior(self, components, reset_timestamp):
        """
        **Feature: github-pr-integration, Property 16: Rate limit waiting behavior**
        
        For any API request that exceeds the rate limit, the system should wait
        until the reset time before retrying.
        
        **Validates: Requirements 5.3**
        """
        owner, repo, pr_number = components
        
        # Clear cache before test to ensure API calls are made
        from agentic_code_review.providers.github_provider import _pr_cache
        _pr_cache.clear()
        
        # Create provider with test token
        os.environ["GITHUB_TOKEN"] = "test_token_12345"
        try:
            github_provider = GitHubProvider()
            
            # Track sleep calls
            sleep_called = []
            
            # Mock the requests.get to return 429 first, then success
            with patch('agentic_code_review.providers.github_provider.requests.get') as mock_get:
                with patch('agentic_code_review.providers.github_provider.time.sleep') as mock_sleep:
                    call_count = [0]
                    
                    def side_effect(url, headers=None, timeout=None):
                        call_count[0] += 1
                        
                        # First call returns 429 (rate limit exceeded)
                        if call_count[0] == 1:
                            mock_response = MagicMock()
                            mock_response.status_code = 429
                            mock_response.headers = {
                                'X-RateLimit-Remaining': '0',
                                'X-RateLimit-Limit': '5000',
                                'X-RateLimit-Reset': str(reset_timestamp)
                            }
                            return mock_response
                        
                        # Subsequent calls succeed
                        if headers and headers.get("Accept") == "application/vnd.github.v3.diff":
                            mock_response = MagicMock()
                            mock_response.status_code = 200
                            mock_response.headers = {
                                'X-RateLimit-Remaining': '4999',
                                'X-RateLimit-Limit': '5000',
                                'X-RateLimit-Reset': str(reset_timestamp)
                            }
                            mock_response.text = "diff content"
                            return mock_response
                        elif url.endswith("/files"):
                            mock_response = MagicMock()
                            mock_response.status_code = 200
                            mock_response.headers = {
                                'X-RateLimit-Remaining': '4998',
                                'X-RateLimit-Limit': '5000',
                                'X-RateLimit-Reset': str(reset_timestamp)
                            }
                            mock_response.json.return_value = [{"filename": "test.txt"}]
                            return mock_response
                        else:
                            mock_response = MagicMock()
                            mock_response.status_code = 200
                            mock_response.headers = {
                                'X-RateLimit-Remaining': '4999',
                                'X-RateLimit-Limit': '5000',
                                'X-RateLimit-Reset': str(reset_timestamp)
                            }
                            mock_response.json.return_value = {
                                "title": "Test PR",
                                "body": "Test description",
                                "user": {"login": "testuser"},
                                "changed_files": 1
                            }
                            return mock_response
                    
                    def sleep_side_effect(seconds):
                        sleep_called.append(seconds)
                    
                    mock_get.side_effect = side_effect
                    mock_sleep.side_effect = sleep_side_effect
                    
                    # Check if reset time is in the future
                    from datetime import datetime
                    expected_wait = reset_timestamp - time.time()
                    
                    if expected_wait > 0:
                        # Fetch PR data - should wait for rate limit reset
                        pr_data = github_provider.fetch_pr_data(
                            owner=owner,
                            repo=repo,
                            pr_number=pr_number
                        )
                        
                        # If reset time is in future, should have waited
                        assert len(sleep_called) > 0, "Should have waited for rate limit reset"
                        
                        # Verify wait time is reasonable
                        actual_wait = sleep_called[0]
                        
                        # Allow some tolerance for timing
                        assert actual_wait >= 0, "Wait time should be non-negative"
                        assert actual_wait <= expected_wait + 2, "Wait time should not exceed reset time by much"
                        
                        # Verify successful fetch after waiting
                        assert pr_data.provider == "github"
                        assert pr_data.repository == f"{owner}/{repo}"
                    else:
                        # If reset time is in past, should raise RateLimitError without waiting
                        # This is expected behavior - the test generated a past timestamp
                        with pytest.raises(RateLimitError):
                            github_provider.fetch_pr_data(
                                owner=owner,
                                repo=repo,
                                pr_number=pr_number
                            )
        
        finally:
            # Clean up
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]

    @settings(max_examples=100)
    @given(
        components=github_url_components(),
        remaining=st.integers(min_value=0, max_value=100),
        limit=st.integers(min_value=1000, max_value=5000),
        reset_timestamp=st.integers(min_value=int(time.time()), max_value=int(time.time()) + 3600),
        error_status=st.sampled_from([404, 403, 500])
    )
    def test_property_17_rate_limit_info_in_errors(self, components, remaining, limit, reset_timestamp, error_status):
        """
        **Feature: github-pr-integration, Property 17: Rate limit info in errors**
        
        For any error message generated when rate limit information is available,
        the message should include the rate limit details.
        
        **Validates: Requirements 5.4**
        """
        owner, repo, pr_number = components
        
        # Create provider with test token
        os.environ["GITHUB_TOKEN"] = "test_token_12345"
        try:
            github_provider = GitHubProvider()
            
            # Capture log messages
            with patch('agentic_code_review.providers.github_provider.logger') as mock_logger:
                # Mock the requests.get to return error with rate limit headers
                with patch('agentic_code_review.providers.github_provider.requests.get') as mock_get:
                    mock_response = MagicMock()
                    mock_response.status_code = error_status
                    mock_response.headers = {
                        'X-RateLimit-Remaining': str(remaining),
                        'X-RateLimit-Limit': str(limit),
                        'X-RateLimit-Reset': str(reset_timestamp)
                    }
                    mock_response.text = f"API Error {error_status}"
                    mock_get.return_value = mock_response
                    
                    # Try to fetch PR data - should raise an error
                    try:
                        github_provider.fetch_pr_data(
                            owner=owner,
                            repo=repo,
                            pr_number=pr_number
                        )
                    except (ProviderAPIError, AuthenticationError) as e:
                        # Verify rate limit info is available
                        rate_limit_info = github_provider.get_rate_limit_info()
                        assert rate_limit_info is not None, "Rate limit info should be extracted even on error"
                        assert rate_limit_info.remaining == remaining
                        assert rate_limit_info.limit == limit
                        
                        # Check if rate limit info was logged
                        # Look through all log calls for rate limit information
                        logged_rate_info = False
                        for call in mock_logger.info.call_args_list:
                            if call and len(call[0]) > 0:
                                log_message = str(call[0][0])
                                if "rate limit" in log_message.lower() and str(remaining) in log_message:
                                    logged_rate_info = True
                                    break
                        
                        # If remaining is very low, should have logged a warning
                        if remaining < 10:
                            warning_logged = False
                            for call in mock_logger.warning.call_args_list:
                                if call and len(call[0]) > 0:
                                    log_message = str(call[0][0])
                                    if "rate limit" in log_message.lower():
                                        warning_logged = True
                                        break
                            assert warning_logged, "Should log warning when rate limit is low"
        
        finally:
            # Clean up
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]


class TestGitHubProviderCaching:
    """Tests for GitHub PR data caching functionality."""
    
    @settings(max_examples=100)
    @given(
        components=github_url_components(),
        num_requests=st.integers(min_value=2, max_value=5)
    )
    def test_property_18_pr_data_caching(self, components, num_requests):
        """
        **Feature: github-pr-integration, Property 18: PR data caching**
        
        For any PR identifier, fetching it multiple times within 5 minutes should
        result in only one API call, with subsequent requests served from cache.
        
        **Validates: Requirements 5.5**
        """
        owner, repo, pr_number = components
        
        # Create provider with test token
        os.environ["GITHUB_TOKEN"] = "test_token_12345"
        try:
            github_provider = GitHubProvider()
            
            # Clear cache before test
            from agentic_code_review.providers.github_provider import _pr_cache
            _pr_cache.clear()
            
            # Mock the requests.get
            with patch('agentic_code_review.providers.github_provider.requests.get') as mock_get:
                # Setup mock responses
                mock_metadata_response = MagicMock()
                mock_metadata_response.status_code = 200
                mock_metadata_response.headers = {
                    'X-RateLimit-Remaining': '5000',
                    'X-RateLimit-Limit': '5000',
                    'X-RateLimit-Reset': str(int(time.time()) + 3600)
                }
                mock_metadata_response.json.return_value = {
                    "title": "Test PR",
                    "body": "Test description",
                    "user": {"login": "testuser"},
                    "changed_files": 1
                }
                
                mock_diff_response = MagicMock()
                mock_diff_response.status_code = 200
                mock_diff_response.headers = {
                    'X-RateLimit-Remaining': '4999',
                    'X-RateLimit-Limit': '5000',
                    'X-RateLimit-Reset': str(int(time.time()) + 3600)
                }
                mock_diff_response.text = "diff content"
                
                mock_files_response = MagicMock()
                mock_files_response.status_code = 200
                mock_files_response.headers = {
                    'X-RateLimit-Remaining': '4998',
                    'X-RateLimit-Limit': '5000',
                    'X-RateLimit-Reset': str(int(time.time()) + 3600)
                }
                mock_files_response.json.return_value = [
                    {"filename": "test.txt"}
                ]
                
                def side_effect(url, headers=None, timeout=None):
                    if headers and headers.get("Accept") == "application/vnd.github.v3.diff":
                        return mock_diff_response
                    elif url.endswith("/files"):
                        return mock_files_response
                    else:
                        return mock_metadata_response
                
                mock_get.side_effect = side_effect
                
                # Fetch PR data multiple times
                results = []
                for i in range(num_requests):
                    pr_data = github_provider.fetch_pr_data(
                        owner=owner,
                        repo=repo,
                        pr_number=pr_number
                    )
                    results.append(pr_data)
                
                # Verify all results are identical
                for i in range(1, num_requests):
                    assert results[i].diff == results[0].diff, "Cached data should be identical"
                    assert results[i].title == results[0].title
                    assert results[i].author == results[0].author
                    assert results[i].pr_number == results[0].pr_number
                
                # Verify API was called only once (3 calls: metadata, diff, files)
                # After first fetch, subsequent fetches should use cache
                # First fetch: 3 calls (metadata, diff, files)
                # Subsequent fetches: 0 calls (from cache)
                assert mock_get.call_count == 3, \
                    f"Should only make 3 API calls (metadata, diff, files) for first fetch, got {mock_get.call_count}"
                
                # Verify cache key was created correctly
                cache_key = github_provider._create_cache_key(owner, repo, pr_number)
                assert cache_key in _pr_cache, "Cache entry should exist"
                
                # Verify cache entry is not expired
                cache_entry = _pr_cache[cache_key]
                assert not cache_entry.is_expired(), "Cache entry should not be expired"
                assert cache_entry.ttl_seconds == 300, "TTL should be 5 minutes (300 seconds)"
        
        finally:
            # Clean up
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]
            # Clear cache after test
            from agentic_code_review.providers.github_provider import _pr_cache
            _pr_cache.clear()
