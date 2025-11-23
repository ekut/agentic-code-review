"""
Property-based tests for FileProvider.

**Feature: github-pr-integration, Property 20: File input backward compatibility**
**Validates: Requirements 6.3**

**Feature: github-pr-integration, Property 19: Input type detection and routing**
**Validates: Requirements 6.1, 6.2, 6.4**
"""

import os
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, strategies as st, assume, settings

from agentic_code_review.providers import FileProvider, ProviderFactory, ProviderError


# Test data strategies
@st.composite
def file_content_strategy(draw):
    """Generate random file content for testing."""
    # Generate realistic diff-like content
    lines = draw(st.lists(st.text(min_size=0, max_size=100), min_size=1, max_size=50))
    return "\n".join(lines)


@st.composite
def file_path_strategy(draw):
    """Generate valid file path strings."""
    # Generate various file path formats
    path_type = draw(st.sampled_from([
        "relative",
        "relative_with_dot",
        "relative_with_dotdot",
        "with_extension"
    ]))
    
    if path_type == "relative":
        return draw(st.text(min_size=1, max_size=20, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='_-'
        )))
    elif path_type == "relative_with_dot":
        filename = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='_-'
        )))
        return f"./{filename}"
    elif path_type == "relative_with_dotdot":
        filename = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='_-'
        )))
        return f"../{filename}"
    else:  # with_extension
        name = draw(st.text(min_size=1, max_size=15, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='_-'
        )))
        ext = draw(st.sampled_from(['txt', 'diff', 'patch', 'md']))
        return f"{name}.{ext}"


class TestFileInputBackwardCompatibility:
    """
    Property 20: File input backward compatibility
    
    For any local file path input, the system should read and process it
    with the same behavior as the pre-integration implementation.
    """
    
    @given(file_content_strategy())
    @settings(max_examples=100)
    def test_file_provider_reads_content_correctly(self, content: str):
        """
        Property 20: File input backward compatibility
        
        For any file content, FileProvider should read and return it correctly
        in the PRData structure, maintaining backward compatibility.
        
        This property runs 100 iterations with random file content.
        """
        # Create a temporary file with the content
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', newline='') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            # Read back what was actually written (to handle platform line ending normalization)
            with open(temp_path, 'r', encoding='utf-8') as f:
                actual_written_content = f.read()
            
            provider = FileProvider()
            pr_data = provider.fetch_pr_data(file_path=temp_path)
            
            # Verify the diff content matches what was actually written to disk
            # (accounting for platform-specific line ending normalization)
            assert pr_data.diff == actual_written_content
            
            # Verify provider type is "file"
            assert pr_data.provider == "file"
            
            # Verify minimal metadata is present
            assert pr_data.title == Path(temp_path).name
            assert pr_data.repository == "local"
            assert pr_data.pr_number == 0
            
        finally:
            # Clean up
            os.unlink(temp_path)
    
    def test_file_provider_handles_existing_test_files(self):
        """
        Property 20: File input backward compatibility
        
        FileProvider should successfully read the existing test files that
        were used in the pre-integration implementation.
        """
        # Test with the actual test files from the project
        test_files = [
            "files/code_changes.txt",
            "files/code_changes_simple.txt"
        ]
        
        provider = FileProvider()
        
        for file_path in test_files:
            # Check if file exists (it should in the project)
            if not Path(file_path).exists():
                pytest.skip(f"Test file {file_path} not found")
            
            # Read with FileProvider
            pr_data = provider.fetch_pr_data(file_path=file_path)
            
            # Read directly (old way)
            with open(file_path, 'r') as f:
                expected_content = f.read()
            
            # Verify content matches
            assert pr_data.diff == expected_content
            assert pr_data.provider == "file"
    
    @given(file_content_strategy())
    @settings(max_examples=100)
    def test_file_provider_maintains_content_integrity(self, content: str):
        """
        Property 20: File input backward compatibility
        
        For any file content, reading through FileProvider should preserve
        the content as it was written to disk (accounting for platform-specific
        text mode normalization).
        
        This property runs 100 iterations with random content.
        """
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.diff', encoding='utf-8', newline='') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            # Read back what was actually written to disk
            with open(temp_path, 'r', encoding='utf-8') as f:
                actual_written_content = f.read()
            
            provider = FileProvider()
            pr_data = provider.fetch_pr_data(file_path=temp_path)
            
            # Content should match what was actually written to disk
            assert pr_data.diff == actual_written_content
            assert len(pr_data.diff) == len(actual_written_content)
            
        finally:
            os.unlink(temp_path)
    
    def test_file_provider_error_handling_matches_old_behavior(self):
        """
        Property 20: File input backward compatibility
        
        FileProvider should handle errors (missing files, permission issues)
        in a way that's compatible with the old implementation.
        """
        provider = FileProvider()
        
        # Test missing file
        with pytest.raises(ProviderError, match="File not found"):
            provider.fetch_pr_data(file_path="nonexistent_file.txt")
        
        # Test directory instead of file
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ProviderError, match="not a file"):
                provider.fetch_pr_data(file_path=temp_dir)
        
        # Test missing file_path parameter
        with pytest.raises(ProviderError, match="file_path is required"):
            provider.fetch_pr_data()
    
    @given(
        st.lists(file_content_strategy(), min_size=2, max_size=5)
    )
    @settings(max_examples=100)
    def test_file_provider_handles_multiple_files_independently(self, contents: list[str]):
        """
        Property 20: File input backward compatibility
        
        For any list of files, FileProvider should read each independently
        and return the correct content for each, maintaining statelessness.
        
        This property runs 100 iterations with multiple files.
        """
        provider = FileProvider()
        temp_files = []
        
        try:
            # Create multiple temporary files
            for content in contents:
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', newline='') as f:
                    f.write(content)
                    temp_path = f.name
                
                # Read back what was actually written (after file is closed)
                with open(temp_path, 'r', encoding='utf-8') as rf:
                    actual_content = rf.read()
                temp_files.append((temp_path, actual_content))
            
            # Read each file and verify content
            for file_path, expected_content in temp_files:
                pr_data = provider.fetch_pr_data(file_path=file_path)
                assert pr_data.diff == expected_content
                
        finally:
            # Clean up all temp files
            for file_path, _ in temp_files:
                if os.path.exists(file_path):
                    os.unlink(file_path)


class TestInputTypeDetectionAndRouting:
    """
    Property 19: Input type detection and routing
    
    For any input provided (file path or GitHub identifier), the system
    should correctly detect the type and route to the appropriate handler.
    """
    
    @given(file_path_strategy())
    @settings(max_examples=100)
    def test_can_handle_detects_file_paths(self, path: str):
        """
        Property 19: Input type detection and routing
        
        For any file path string (without URL scheme), FileProvider.can_handle
        should return True.
        
        This property runs 100 iterations with random file paths.
        """
        # Assume the path doesn't contain URL schemes (except file://)
        assume("://" not in path or path.startswith("file://"))
        
        result = FileProvider.can_handle(path)
        assert result is True
    
    @given(
        st.sampled_from([
            "https://github.com/owner/repo/pull/123",
            "http://github.com/owner/repo/pull/456",
            "https://gitlab.com/group/project/-/merge_requests/789",
            "git://github.com/owner/repo.git",
            "ssh://git@github.com/owner/repo.git",
        ])
    )
    @settings(max_examples=100)
    def test_can_handle_rejects_urls(self, url: str):
        """
        Property 19: Input type detection and routing
        
        For any URL with a scheme (http://, https://, git://, etc.),
        FileProvider.can_handle should return False.
        
        This property runs 100 iterations with various URL formats.
        """
        result = FileProvider.can_handle(url)
        assert result is False
    
    def test_can_handle_accepts_file_urls(self):
        """
        Property 19: Input type detection and routing
        
        FileProvider should accept file:// URLs as they represent local files.
        """
        assert FileProvider.can_handle("file:///path/to/file.txt") is True
        assert FileProvider.can_handle("file://relative/path.txt") is True
    
    @given(
        st.one_of(
            file_path_strategy(),
            st.just("files/code_changes.txt"),
            st.just("./test.diff"),
            st.just("../parent/file.txt"),
            st.just("/absolute/path/file.txt"),
        )
    )
    @settings(max_examples=100)
    def test_factory_routes_file_paths_to_file_provider(self, file_path: str):
        """
        Property 19: Input type detection and routing
        
        For any file path input, ProviderFactory should route to FileProvider.
        
        This property runs 100 iterations with various file path formats.
        """
        # Assume it's a file path (no URL scheme except file://)
        assume("://" not in file_path or file_path.startswith("file://"))
        
        provider = ProviderFactory.get_provider(file_path)
        assert isinstance(provider, FileProvider)
    
    @given(file_content_strategy())
    @settings(max_examples=100)
    def test_validate_input_correctly_validates_files(self, content: str):
        """
        Property 19: Input type detection and routing
        
        For any file that exists and is readable, validate_input should
        return True. For non-existent or invalid paths, it should return False.
        
        This property runs 100 iterations with random content.
        """
        provider = FileProvider()
        
        # Create a valid file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            # Should validate successfully
            assert provider.validate_input(file_path=temp_path) is True
            
            # After deletion, should fail validation
            os.unlink(temp_path)
            assert provider.validate_input(file_path=temp_path) is False
            
        except:
            # Clean up if test fails
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    
    def test_validate_input_rejects_invalid_inputs(self):
        """
        Property 19: Input type detection and routing
        
        validate_input should return False for invalid inputs.
        """
        provider = FileProvider()
        
        # Missing file_path
        assert provider.validate_input() is False
        
        # Non-existent file
        assert provider.validate_input(file_path="nonexistent.txt") is False
        
        # Directory instead of file
        with tempfile.TemporaryDirectory() as temp_dir:
            assert provider.validate_input(file_path=temp_dir) is False
    
    @given(
        st.lists(
            st.one_of(
                file_path_strategy(),
                st.sampled_from([
                    "https://github.com/owner/repo/pull/1",
                    "files/test.txt",
                    "./local.diff",
                ])
            ),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=100)
    def test_can_handle_is_consistent(self, inputs: list[str]):
        """
        Property 19: Input type detection and routing
        
        For any list of inputs, can_handle should return consistent results
        when called multiple times with the same input.
        
        This property runs 100 iterations with random input lists.
        """
        for input_str in inputs:
            # Call can_handle twice
            result1 = FileProvider.can_handle(input_str)
            result2 = FileProvider.can_handle(input_str)
            
            # Results should be identical
            assert result1 == result2
            
            # Result should be a boolean
            assert isinstance(result1, bool)
