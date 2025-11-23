"""
Integration tests for backward compatibility with file-based input.

Tests complete flow with file path input, verifies existing behavior is maintained,
and tests switching between file and GitHub inputs.

**Requirements: 6.1, 6.3, 6.4**
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

import pytest

from agentic_code_review.main import PRCodeReviewFlow, ReviewState


# Test fixtures
@pytest.fixture
def sample_diff_content():
    """Sample diff content for testing."""
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
def simple_diff_content():
    """Simple diff content that should trigger simple review."""
    return """diff --git a/README.md b/README.md
index abc123..def456 100644
--- a/README.md
+++ b/README.md
@@ -1,2 +1,2 @@
 # Project Title
-Old description
+New description
"""


@pytest.fixture
def complex_diff_content():
    """Complex diff content that should trigger crew review."""
    return """diff --git a/auth.py b/auth.py
index 111222..333444 100644
--- a/auth.py
+++ b/auth.py
@@ -10,5 +10,8 @@
 def authenticate(user, password):
-    return user == "admin" and password == "secret"
+    # New authentication logic with database
+    db_user = database.get_user(user)
+    return db_user and check_password(password, db_user.password_hash)
"""


@pytest.fixture
def existing_test_files():
    """Paths to existing test files in the project."""
    return [
        "files/code_changes.txt",
        "files/code_changes_simple.txt"
    ]


class TestFileInputBackwardCompatibilityIntegration:
    """
    Integration tests for backward compatibility with file-based input.
    
    **Validates: Requirements 6.1, 6.3, 6.4**
    """
    
    def test_complete_flow_with_file_path_input(self, sample_diff_content):
        """
        Test complete flow with file path input.
        
        **Validates: Requirements 6.1, 6.3**
        
        Verifies that:
        - File path input is correctly detected
        - File content is read and stored in state
        - Flow completes successfully with file input
        - Existing behavior is maintained
        """
        # Create a temporary file with diff content
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(sample_diff_content)
            temp_path = f.name
        
        try:
            # Create flow with file input
            with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                flow = PRCodeReviewFlow()
                flow._state = ReviewState(pr_input=temp_path)
                
                # Execute read_pr_data
                flow.read_pr_data()
                
                # Verify state is updated correctly
                assert flow.state.pr_content != "", "PR content should be loaded"
                assert sample_diff_content in flow.state.pr_content, "Content should match file content"
                assert len(flow.state.errors) == 0, "No errors should occur"
                
                # Verify metadata is present
                assert flow.state.pr_metadata is not None
                assert flow.state.pr_metadata["provider"] == "file"
                assert flow.state.pr_metadata["repository"] == "local"
                assert flow.state.pr_metadata["url"] == temp_path
                
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_existing_test_files_still_work(self, existing_test_files):
        """
        Test that existing test files in the project still work.
        
        **Validates: Requirements 6.3**
        
        Verifies that:
        - Existing test files can be read
        - Content is correctly loaded into state
        - No errors occur with existing files
        """
        for file_path in existing_test_files:
            # Skip if file doesn't exist
            if not Path(file_path).exists():
                pytest.skip(f"Test file {file_path} not found")
            
            # Read expected content directly
            with open(file_path, 'r') as f:
                expected_content = f.read()
            
            # Create flow with file input
            with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                flow = PRCodeReviewFlow()
                flow._state = ReviewState(pr_input=file_path)
                
                # Execute read_pr_data
                flow.read_pr_data()
                
                # Verify content matches
                assert flow.state.pr_content == expected_content
                assert len(flow.state.errors) == 0
                assert flow.state.pr_metadata["provider"] == "file"
    
    def test_file_input_with_simple_review_flow(self, simple_diff_content):
        """
        Test complete flow with file input triggering simple review.
        
        **Validates: Requirements 6.1, 6.3**
        
        Verifies that:
        - File input works with simple review path
        - Flow routing works correctly with file input
        - Simple review completes successfully
        """
        # Create a temporary file with simple diff
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.diff') as f:
            f.write(simple_diff_content)
            temp_path = f.name
        
        try:
            # Mock LLM calls to control flow
            with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                with patch('agentic_code_review.main.LLM') as mock_llm_class:
                    # Mock LLM instance
                    mock_llm = Mock()
                    mock_llm_class.return_value = mock_llm
                    
                    # First call: analyze_changes returns SIMPLE
                    # Second call: simple_review returns review result
                    mock_llm.call.side_effect = [
                        "SIMPLE",  # analyze_changes decision
                        "The changes look good. Minor documentation update. APPROVE."  # simple_review result
                    ]
                    
                    flow = PRCodeReviewFlow()
                    flow._state = ReviewState(pr_input=temp_path)
                    
                    # Execute read_pr_data
                    flow.read_pr_data()
                    
                    # Verify file was read
                    assert len(flow.state.errors) == 0
                    assert flow.state.pr_content != ""
                    
                    # Execute analyze_changes
                    result = flow.analyze_changes(None)
                    
                    # Verify SIMPLE path was chosen
                    assert result == 'SIMPLE'
                    assert flow.state.crew_needed is False
                    
                    # Execute simple_review
                    flow.simple_review()
                    
                    # Verify review was completed
                    assert flow.state.review_result is not None
                    assert "APPROVE" in str(flow.state.review_result)
        
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_file_input_error_handling(self):
        """
        Test error handling with file input.
        
        **Validates: Requirements 6.3**
        
        Verifies that:
        - Missing files are handled gracefully
        - Error messages are clear and helpful
        - State contains error information
        """
        # Test with non-existent file
        with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
            flow = PRCodeReviewFlow()
            flow._state = ReviewState(pr_input="nonexistent_file.txt")
            
            # Execute read_pr_data
            flow.read_pr_data()
            
            # Verify error is captured
            assert len(flow.state.errors) > 0
            assert "Error fetching PR data" in flow.state.errors[0]
            assert flow.state.final_answer != ""
    
    def test_file_input_with_relative_paths(self, sample_diff_content):
        """
        Test file input with various relative path formats.
        
        **Validates: Requirements 6.1, 6.3**
        
        Verifies that:
        - Relative paths work correctly
        - Different path formats are handled
        - Content is correctly loaded
        """
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', dir='.') as f:
            f.write(sample_diff_content)
            temp_name = Path(f.name).name
        
        try:
            # Test with relative path
            relative_path = f"./{temp_name}"
            
            with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                flow = PRCodeReviewFlow()
                flow._state = ReviewState(pr_input=relative_path)
                
                # Execute read_pr_data
                flow.read_pr_data()
                
                # Verify content was loaded
                assert len(flow.state.errors) == 0
                assert flow.state.pr_content != ""
                assert sample_diff_content in flow.state.pr_content
        
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)


class TestSwitchingBetweenFileAndGitHubInputs:
    """
    Integration tests for switching between file and GitHub inputs.
    
    **Validates: Requirements 6.1, 6.4**
    """
    
    def test_switch_from_file_to_github_input(self, sample_diff_content):
        """
        Test switching from file input to GitHub input.
        
        **Validates: Requirements 6.1, 6.4**
        
        Verifies that:
        - System can handle file input first
        - Then switch to GitHub input
        - Both inputs work correctly
        - No state pollution between inputs
        """
        # Set up GitHub token
        os.environ["GITHUB_TOKEN"] = "test_token_12345"
        
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write(sample_diff_content)
                temp_path = f.name
            
            try:
                # First: Test with file input
                with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                    flow1 = PRCodeReviewFlow()
                    flow1._state = ReviewState(pr_input=temp_path)
                    
                    # Execute read_pr_data
                    flow1.read_pr_data()
                    
                    # Verify file input worked
                    assert len(flow1.state.errors) == 0
                    assert flow1.state.pr_metadata["provider"] == "file"
                    file_content = flow1.state.pr_content
                
                # Second: Test with GitHub input
                github_url = "https://github.com/owner/repo/pull/123"
                
                with patch('requests.get') as mock_get:
                    # Mock GitHub API responses
                    mock_metadata = Mock()
                    mock_metadata.status_code = 200
                    mock_metadata.json.return_value = {
                        "title": "Test PR",
                        "body": "Test description",
                        "user": {"login": "testuser"},
                    }
                    mock_metadata.headers = {
                        'X-RateLimit-Remaining': '5000',
                        'X-RateLimit-Limit': '5000',
                    }
                    
                    mock_diff = Mock()
                    mock_diff.status_code = 200
                    mock_diff.text = "diff --git a/test.py b/test.py\n+new line"
                    mock_diff.headers = mock_metadata.headers
                    
                    mock_files = Mock()
                    mock_files.status_code = 200
                    mock_files.json.return_value = [{"filename": "test.py"}]
                    mock_files.headers = mock_metadata.headers
                    
                    def side_effect(*args, **kwargs):
                        headers = kwargs.get('headers', {})
                        if 'application/vnd.github.v3.diff' in headers.get('Accept', ''):
                            return mock_diff
                        elif '/files' in args[0]:
                            return mock_files
                        else:
                            return mock_metadata
                    
                    mock_get.side_effect = side_effect
                    
                    with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                        flow2 = PRCodeReviewFlow()
                        flow2._state = ReviewState(pr_input=github_url)
                        
                        # Execute read_pr_data
                        flow2.read_pr_data()
                        
                        # Verify GitHub input worked
                        assert len(flow2.state.errors) == 0
                        assert flow2.state.pr_metadata["provider"] == "github"
                        github_content = flow2.state.pr_content
                        
                        # Verify contents are different (no state pollution)
                        assert file_content != github_content
            
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        
        finally:
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]
    
    def test_switch_from_github_to_file_input(self, sample_diff_content):
        """
        Test switching from GitHub input to file input.
        
        **Validates: Requirements 6.1, 6.4**
        
        Verifies that:
        - System can handle GitHub input first
        - Then switch to file input
        - Both inputs work correctly
        - No state pollution between inputs
        """
        # Set up GitHub token
        os.environ["GITHUB_TOKEN"] = "test_token_12345"
        
        try:
            # First: Test with GitHub input
            github_url = "https://github.com/owner/repo/pull/456"
            
            with patch('requests.get') as mock_get:
                # Mock GitHub API responses
                mock_metadata = Mock()
                mock_metadata.status_code = 200
                mock_metadata.json.return_value = {
                    "title": "GitHub PR",
                    "body": "GitHub description",
                    "user": {"login": "githubuser"},
                }
                mock_metadata.headers = {
                    'X-RateLimit-Remaining': '5000',
                    'X-RateLimit-Limit': '5000',
                }
                
                mock_diff = Mock()
                mock_diff.status_code = 200
                mock_diff.text = "diff --git a/github.py b/github.py\n+github line"
                mock_diff.headers = mock_metadata.headers
                
                mock_files = Mock()
                mock_files.status_code = 200
                mock_files.json.return_value = [{"filename": "github.py"}]
                mock_files.headers = mock_metadata.headers
                
                def side_effect(*args, **kwargs):
                    headers = kwargs.get('headers', {})
                    if 'application/vnd.github.v3.diff' in headers.get('Accept', ''):
                        return mock_diff
                    elif '/files' in args[0]:
                        return mock_files
                    else:
                        return mock_metadata
                
                mock_get.side_effect = side_effect
                
                with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                    flow1 = PRCodeReviewFlow()
                    flow1._state = ReviewState(pr_input=github_url)
                    
                    # Execute read_pr_data
                    flow1.read_pr_data()
                    
                    # Verify GitHub input worked
                    assert len(flow1.state.errors) == 0
                    assert flow1.state.pr_metadata["provider"] == "github"
                    github_content = flow1.state.pr_content
            
            # Second: Test with file input
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write(sample_diff_content)
                temp_path = f.name
            
            try:
                with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                    flow2 = PRCodeReviewFlow()
                    flow2._state = ReviewState(pr_input=temp_path)
                    
                    # Execute read_pr_data
                    flow2.read_pr_data()
                    
                    # Verify file input worked
                    assert len(flow2.state.errors) == 0
                    assert flow2.state.pr_metadata["provider"] == "file"
                    file_content = flow2.state.pr_content
                    
                    # Verify contents are different (no state pollution)
                    assert github_content != file_content
            
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        
        finally:
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]
    
    def test_multiple_switches_between_inputs(self, sample_diff_content):
        """
        Test multiple switches between file and GitHub inputs.
        
        **Validates: Requirements 6.1, 6.4**
        
        Verifies that:
        - System can handle multiple switches
        - Each input type works correctly every time
        - No state pollution across multiple switches
        """
        # Set up GitHub token
        os.environ["GITHUB_TOKEN"] = "test_token_12345"
        
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write(sample_diff_content)
                temp_path = f.name
            
            try:
                github_url = "https://github.com/owner/repo/pull/789"
                
                # Mock GitHub API
                with patch('requests.get') as mock_get:
                    mock_metadata = Mock()
                    mock_metadata.status_code = 200
                    mock_metadata.json.return_value = {
                        "title": "Multi-switch PR",
                        "body": "Testing multiple switches",
                        "user": {"login": "switchuser"},
                    }
                    mock_metadata.headers = {
                        'X-RateLimit-Remaining': '5000',
                        'X-RateLimit-Limit': '5000',
                    }
                    
                    mock_diff = Mock()
                    mock_diff.status_code = 200
                    mock_diff.text = "diff --git a/switch.py b/switch.py\n+switch line"
                    mock_diff.headers = mock_metadata.headers
                    
                    mock_files = Mock()
                    mock_files.status_code = 200
                    mock_files.json.return_value = [{"filename": "switch.py"}]
                    mock_files.headers = mock_metadata.headers
                    
                    def side_effect(*args, **kwargs):
                        headers = kwargs.get('headers', {})
                        if 'application/vnd.github.v3.diff' in headers.get('Accept', ''):
                            return mock_diff
                        elif '/files' in args[0]:
                            return mock_files
                        else:
                            return mock_metadata
                    
                    mock_get.side_effect = side_effect
                    
                    # Perform multiple switches
                    for i in range(3):
                        # File input
                        with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                            flow_file = PRCodeReviewFlow()
                            flow_file._state = ReviewState(pr_input=temp_path)
                            flow_file.read_pr_data()
                            
                            assert len(flow_file.state.errors) == 0
                            assert flow_file.state.pr_metadata["provider"] == "file"
                            assert sample_diff_content in flow_file.state.pr_content
                        
                        # GitHub input
                        with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                            flow_github = PRCodeReviewFlow()
                            flow_github._state = ReviewState(pr_input=github_url)
                            flow_github.read_pr_data()
                            
                            assert len(flow_github.state.errors) == 0
                            assert flow_github.state.pr_metadata["provider"] == "github"
                            assert "switch line" in flow_github.state.pr_content
            
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        
        finally:
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]
    
    def test_concurrent_file_and_github_flows(self, sample_diff_content):
        """
        Test that file and GitHub flows can work concurrently without interference.
        
        **Validates: Requirements 6.1, 6.4**
        
        Verifies that:
        - Multiple flow instances can run simultaneously
        - File and GitHub inputs don't interfere with each other
        - Each flow maintains its own state correctly
        """
        # Set up GitHub token
        os.environ["GITHUB_TOKEN"] = "test_token_12345"
        
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write(sample_diff_content)
                temp_path = f.name
            
            try:
                github_url = "https://github.com/owner/repo/pull/999"
                
                # Mock GitHub API
                with patch('requests.get') as mock_get:
                    mock_metadata = Mock()
                    mock_metadata.status_code = 200
                    mock_metadata.json.return_value = {
                        "title": "Concurrent PR",
                        "body": "Testing concurrent flows",
                        "user": {"login": "concurrentuser"},
                    }
                    mock_metadata.headers = {
                        'X-RateLimit-Remaining': '5000',
                        'X-RateLimit-Limit': '5000',
                    }
                    
                    mock_diff = Mock()
                    mock_diff.status_code = 200
                    mock_diff.text = "diff --git a/concurrent.py b/concurrent.py\n+concurrent line"
                    mock_diff.headers = mock_metadata.headers
                    
                    mock_files = Mock()
                    mock_files.status_code = 200
                    mock_files.json.return_value = [{"filename": "concurrent.py"}]
                    mock_files.headers = mock_metadata.headers
                    
                    def side_effect(*args, **kwargs):
                        headers = kwargs.get('headers', {})
                        if 'application/vnd.github.v3.diff' in headers.get('Accept', ''):
                            return mock_diff
                        elif '/files' in args[0]:
                            return mock_files
                        else:
                            return mock_metadata
                    
                    mock_get.side_effect = side_effect
                    
                    with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                        # Create both flows
                        flow_file = PRCodeReviewFlow()
                        flow_file._state = ReviewState(pr_input=temp_path)
                        
                        flow_github = PRCodeReviewFlow()
                        flow_github._state = ReviewState(pr_input=github_url)
                        
                        # Execute both
                        flow_file.read_pr_data()
                        flow_github.read_pr_data()
                        
                        # Verify both worked correctly
                        assert len(flow_file.state.errors) == 0
                        assert flow_file.state.pr_metadata["provider"] == "file"
                        assert sample_diff_content in flow_file.state.pr_content
                        
                        assert len(flow_github.state.errors) == 0
                        assert flow_github.state.pr_metadata["provider"] == "github"
                        assert "concurrent line" in flow_github.state.pr_content
                        
                        # Verify no cross-contamination
                        assert flow_file.state.pr_content != flow_github.state.pr_content
                        assert flow_file.state.pr_metadata["author"] != flow_github.state.pr_metadata["author"]
            
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        
        finally:
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
