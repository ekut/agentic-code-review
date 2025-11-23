"""File-based provider for local PR diff files."""

import os
from pathlib import Path

from .base import PRProvider, PRData, ProviderError


class FileProvider(PRProvider):
    """Provider for local file-based PR data (backward compatibility)."""
    
    def __init__(self, **kwargs):
        """
        Initialize FileProvider.
        
        Args:
            **kwargs: Configuration parameters (ignored for file provider)
        """
        # File provider doesn't need any configuration
        pass
    
    def fetch_pr_data(self, file_path: str = None, **kwargs) -> PRData:
        """
        Read PR data from local file.
        
        Args:
            file_path: Path to local diff file
            **kwargs: Additional parameters (ignored)
        
        Returns:
            PRData object with diff content and minimal metadata
        
        Raises:
            ProviderError: If file doesn't exist or cannot be read
        """
        if not file_path:
            raise ProviderError("file_path is required for FileProvider")
        
        # Convert to Path object for better path handling
        path = Path(file_path)
        
        # Check if file exists
        if not path.exists():
            raise ProviderError(
                f"File not found: {file_path}. "
                f"Please check that the file path is correct."
            )
        
        # Check if it's a file (not a directory)
        if not path.is_file():
            raise ProviderError(
                f"Path is not a file: {file_path}. "
                f"Please provide a path to a file, not a directory."
            )
        
        # Try to read the file
        try:
            with open(path, 'r', encoding='utf-8') as f:
                diff_content = f.read()
        except PermissionError:
            raise ProviderError(
                f"Permission denied reading file: {file_path}. "
                f"Please check file permissions."
            )
        except UnicodeDecodeError:
            raise ProviderError(
                f"Unable to decode file as UTF-8: {file_path}. "
                f"Please ensure the file is a text file."
            )
        except Exception as e:
            raise ProviderError(
                f"Error reading file {file_path}: {str(e)}"
            )
        
        # Return PRData with minimal metadata (file-based has no PR metadata)
        return PRData(
            diff=diff_content,
            title=path.name,  # Use filename as title
            description="Local file diff",
            author="unknown",
            files_changed=[],  # Cannot determine from diff file alone
            pr_number=0,  # No PR number for local files
            repository="local",
            url=file_path,  # Use original file path as provided
            provider="file"
        )
    
    def validate_input(self, file_path: str = None, **kwargs) -> bool:
        """
        Validate that file path exists and is readable.
        
        Args:
            file_path: Path to validate
            **kwargs: Additional parameters (ignored)
        
        Returns:
            True if file path is valid and readable, False otherwise
        """
        if not file_path:
            return False
        
        path = Path(file_path)
        
        # Check if path exists and is a file
        if not path.exists() or not path.is_file():
            return False
        
        # Check if file is readable
        try:
            with open(path, 'r', encoding='utf-8') as f:
                # Try to read first byte to verify readability
                f.read(1)
            return True
        except Exception:
            return False
    
    @staticmethod
    def can_handle(input_str: str) -> bool:
        """
        Determine if input is a file path.
        
        Args:
            input_str: URL or file path
        
        Returns:
            True if input appears to be a file path
        """
        if not input_str:
            return False
        
        # If it contains a URL scheme (except file://), it's not a file path
        # Common URL schemes: http://, https://, git://, ssh://, etc.
        if "://" in input_str:
            # Allow file:// URLs
            if input_str.startswith("file://"):
                return True
            # Reject other URL schemes
            return False
        
        # If it looks like a file path, return True
        # This includes:
        # - Absolute paths: /path/to/file, C:\path\to\file
        # - Relative paths: file.txt, ./file.txt, ../file.txt
        # - Paths with extensions: file.diff, changes.txt
        return True
