"""GitHub API provider for fetching PR data."""

import os
import re
import time
import logging
import requests
from typing import Optional, Dict
from datetime import datetime

from .base import (
    PRProvider,
    PRData,
    RateLimitInfo,
    CacheEntry,
    AuthenticationError,
    ProviderAPIError,
    NetworkError,
    RateLimitError,
)
from ..utils import create_pr_cache_key

# Configure logging
logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 1  # seconds
BACKOFF_MULTIPLIER = 2

# In-memory cache for PR data
_pr_cache: Dict[str, CacheEntry] = {}


class GitHubProvider(PRProvider):
    """Provider for GitHub API integration."""
    
    def __init__(self, token: Optional[str] = None, **kwargs):
        """
        Initialize GitHub provider with authentication token.
        
        Args:
            token: GitHub personal access token or OAuth token.
                   If None, reads from GITHUB_TOKEN environment variable.
            **kwargs: Additional configuration (ignored for compatibility)
        
        Raises:
            AuthenticationError: If token is not provided and not in environment
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        self._last_rate_limit_info: Optional[RateLimitInfo] = None
        
        if not self.token:
            raise AuthenticationError(
                "github",
                "GitHub token is required. Please set GITHUB_TOKEN environment "
                "variable or provide token parameter. "
                "You can create a token at https://github.com/settings/tokens"
            )
    
    def _redact_token(self, text: str) -> str:
        """
        Redact authentication token from text for safe logging.
        
        Args:
            text: Text that may contain the token
        
        Returns:
            Text with token replaced by [REDACTED]
        """
        if not self.token or not text:
            return text
        
        # Redact the full token
        redacted = text.replace(self.token, "[REDACTED]")
        
        # Also redact if it appears in Bearer format
        redacted = redacted.replace(f"Bearer {self.token}", "Bearer [REDACTED]")
        
        return redacted
    
    def _create_cache_key(self, owner: str, repo: str, pr_number: int) -> str:
        """
        Generate cache key for PR data.
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
        
        Returns:
            Cache key string
        """
        return create_pr_cache_key("github", owner, repo, pr_number)
    
    def _get_cached_pr(self, cache_key: str) -> Optional[PRData]:
        """
        Get PR data from cache if available and not expired.
        
        Args:
            cache_key: Cache key to lookup
        
        Returns:
            Cached PRData if available and valid, None otherwise
        """
        if cache_key in _pr_cache:
            entry = _pr_cache[cache_key]
            if not entry.is_expired():
                logger.info(f"Cache hit for {cache_key}")
                return entry.data
            else:
                logger.debug(f"Cache expired for {cache_key}")
                del _pr_cache[cache_key]
        return None
    
    def _cache_pr_data(self, cache_key: str, pr_data: PRData) -> None:
        """
        Store PR data in cache.
        
        Args:
            cache_key: Cache key
            pr_data: PR data to cache
        """
        _pr_cache[cache_key] = CacheEntry(
            data=pr_data,
            timestamp=datetime.now(),
            ttl_seconds=300  # 5 minutes
        )
        logger.debug(f"Cached PR data for {cache_key}")
    
    def _check_rate_limit(self, response_headers: dict) -> None:
        """
        Check rate limit headers and log warnings if low.
        
        Args:
            response_headers: HTTP response headers from GitHub API
        """
        try:
            remaining = int(response_headers.get('X-RateLimit-Remaining', -1))
            limit = int(response_headers.get('X-RateLimit-Limit', -1))
            reset_timestamp = int(response_headers.get('X-RateLimit-Reset', 0))
            
            if remaining >= 0 and limit >= 0:
                reset_time = datetime.fromtimestamp(reset_timestamp) if reset_timestamp else None
                
                # Store rate limit info
                self._last_rate_limit_info = RateLimitInfo(
                    remaining=remaining,
                    limit=limit,
                    reset_time=reset_time
                )
                
                # Log warning if rate limit is low
                if remaining < 10:
                    logger.warning(
                        f"GitHub API rate limit low: {remaining}/{limit} requests remaining. "
                        f"Resets at {reset_time}"
                    )
        except (ValueError, TypeError) as e:
            logger.debug(f"Could not parse rate limit headers: {e}")
    
    def get_rate_limit_info(self) -> Optional[RateLimitInfo]:
        """
        Get current rate limit status from last API call.
        
        Returns:
            RateLimitInfo with current limits and reset time, or None if not available
        """
        return self._last_rate_limit_info
    
    def _make_request_with_retry(
        self,
        url: str,
        headers: dict,
        timeout: int = 30
    ) -> requests.Response:
        """
        Make HTTP request with exponential backoff retry for network errors.
        
        Args:
            url: API endpoint URL
            headers: Request headers
            timeout: Request timeout in seconds
        
        Returns:
            Response object
        
        Raises:
            NetworkError: If all retries fail
            ProviderAPIError: For API errors (non-retryable)
            AuthenticationError: For authentication failures
            RateLimitError: If rate limit is exceeded
        """
        last_error = None
        
        for attempt in range(MAX_RETRIES):
            try:
                logger.debug(f"Making request to {url} (attempt {attempt + 1}/{MAX_RETRIES})")
                response = requests.get(url, headers=headers, timeout=timeout)
                
                # Check rate limit headers in all responses
                self._check_rate_limit(response.headers)
                
                # Check for rate limiting
                if response.status_code == 429:
                    reset_time = response.headers.get('X-RateLimit-Reset')
                    if reset_time:
                        reset_dt = datetime.fromtimestamp(int(reset_time))
                        wait_seconds = (reset_dt - datetime.now()).total_seconds()
                        
                        if wait_seconds > 0:
                            logger.warning(
                                f"Rate limit exceeded. Waiting {wait_seconds:.0f} seconds until {reset_dt}"
                            )
                            time.sleep(wait_seconds)
                            # Retry after waiting
                            continue
                        else:
                            raise RateLimitError("github", reset_dt)
                    else:
                        raise RateLimitError("github", datetime.now())
                
                # Return response for caller to handle status codes
                return response
                
            except (requests.exceptions.Timeout, 
                    requests.exceptions.ConnectionError,
                    requests.exceptions.RequestException) as e:
                last_error = e
                error_type = type(e).__name__
                
                # Log with redacted information
                safe_message = self._redact_token(str(e))
                logger.warning(
                    f"Network error ({error_type}) on attempt {attempt + 1}/{MAX_RETRIES}: {safe_message}"
                )
                
                # If this is the last attempt, raise the error
                if attempt == MAX_RETRIES - 1:
                    # Classify the network error
                    if isinstance(e, requests.exceptions.Timeout):
                        raise NetworkError(
                            f"Request timed out after {MAX_RETRIES} attempts. "
                            f"GitHub API may be slow or unreachable."
                        )
                    elif isinstance(e, requests.exceptions.ConnectionError):
                        error_msg = str(e).lower()
                        if "name or service not known" in error_msg or "nodename nor servname" in error_msg:
                            raise NetworkError(
                                f"DNS resolution failed for GitHub API. "
                                f"Please check your internet connection."
                            )
                        elif "connection refused" in error_msg:
                            raise NetworkError(
                                f"Connection refused by GitHub API. "
                                f"Please check if GitHub is accessible."
                            )
                        else:
                            raise NetworkError(
                                f"Connection error: {self._redact_token(str(e))}"
                            )
                    else:
                        raise NetworkError(
                            f"Network error after {MAX_RETRIES} attempts: {self._redact_token(str(e))}"
                        )
                
                # Calculate exponential backoff wait time
                wait_time = INITIAL_BACKOFF * (BACKOFF_MULTIPLIER ** attempt)
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        # This should never be reached, but just in case
        raise NetworkError(f"Failed after {MAX_RETRIES} attempts")
    
    def fetch_pr_data(
        self,
        owner: str = None,
        repo: str = None,
        pr_number: int = None,
        url: str = None,
        **kwargs
    ) -> PRData:
        """
        Fetch complete PR data including diff and metadata from GitHub.
        
        Args:
            owner: Repository owner (user or organization)
            repo: Repository name
            pr_number: Pull request number
            url: Alternative - full GitHub PR URL to parse
            **kwargs: Additional parameters (ignored)
        
        Returns:
            PRData object with all PR information
        
        Raises:
            ValueError: If neither (owner, repo, pr_number) nor url is provided
            ProviderAPIError: For API errors (404, 403, 500, etc.)
            NetworkError: For network/connection issues
            RateLimitError: When rate limit is exceeded
        """
        try:
            # Parse URL if provided
            if url:
                owner, repo, pr_number = self.parse_pr_url(url)
            
            # Validate we have all required parameters
            if not all([owner, repo, pr_number]):
                raise ValueError(
                    "Either 'url' or all of ('owner', 'repo', 'pr_number') must be provided"
                )
            
            # Check cache first
            cache_key = self._create_cache_key(owner, repo, pr_number)
            cached_data = self._get_cached_pr(cache_key)
            if cached_data:
                logger.info(f"Returning cached data for {owner}/{repo}#{pr_number}")
                return cached_data
            
            # Construct the PR URL for metadata
            pr_url = f"https://github.com/{owner}/{repo}/pull/{pr_number}"
            
            # Prepare headers for API requests
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }
            
            # API endpoint for PR metadata
            api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
            
            # Fetch PR metadata with retry logic
            logger.info(f"Fetching PR metadata for {owner}/{repo}#{pr_number}")
            response = self._make_request_with_retry(api_url, headers)
            
            # Handle API errors
            if response.status_code == 404:
                raise ProviderAPIError(
                    "github",
                    404,
                    f"Pull request #{pr_number} not found in {owner}/{repo}. "
                    f"Please verify the PR number and repository."
                )
            elif response.status_code == 403:
                raise ProviderAPIError(
                    "github",
                    403,
                    f"Access denied to {owner}/{repo}. "
                    f"Please check your token has the required permissions."
                )
            elif response.status_code == 401:
                raise AuthenticationError(
                    "github",
                    "Invalid or expired GitHub token. Please check your GITHUB_TOKEN."
                )
            elif response.status_code >= 500:
                raise ProviderAPIError(
                    "github",
                    response.status_code,
                    f"GitHub API server error. Please try again later."
                )
            elif response.status_code != 200:
                # Redact token from error message
                safe_text = self._redact_token(response.text[:200])
                raise ProviderAPIError(
                    "github",
                    response.status_code,
                    f"Unexpected API response: {safe_text}"
                )
            
            # Parse JSON response
            pr_metadata = response.json()
            
            # Extract metadata fields
            title = pr_metadata.get("title", "")
            description = pr_metadata.get("body", "") or ""
            author = pr_metadata.get("user", {}).get("login", "")
            
            # Extract commit information for versioning
            head_sha = pr_metadata.get("head", {}).get("sha", "")
            base_sha = pr_metadata.get("base", {}).get("sha", "")
            updated_at = pr_metadata.get("updated_at", "")
            
            # Fetch the diff
            logger.info(f"Fetching PR diff for {owner}/{repo}#{pr_number}")
            diff_headers = headers.copy()
            diff_headers["Accept"] = "application/vnd.github.v3.diff"
            
            diff_response = self._make_request_with_retry(api_url, diff_headers)
            
            if diff_response.status_code != 200:
                safe_text = self._redact_token(diff_response.text[:200])
                raise ProviderAPIError(
                    "github",
                    diff_response.status_code,
                    f"Failed to fetch PR diff: {safe_text}"
                )
            
            diff_content = diff_response.text
            
            # Validate non-empty diff
            if not diff_content or not diff_content.strip():
                raise ValueError(
                    f"PR #{pr_number} in {owner}/{repo} has no diff content. "
                    f"The PR may be empty or already merged."
                )
            
            # Fetch the list of files changed
            logger.info(f"Fetching changed files for {owner}/{repo}#{pr_number}")
            files_url = f"{api_url}/files"
            files_response = self._make_request_with_retry(files_url, headers)
            
            files_changed = []
            if files_response.status_code == 200:
                files_data = files_response.json()
                files_changed = [f.get("filename", "") for f in files_data if f.get("filename")]
            else:
                logger.warning(f"Could not fetch file list: status {files_response.status_code}")
            
            logger.info(f"Successfully fetched PR data for {owner}/{repo}#{pr_number}")
            
            # Create unified PRData object with extended metadata
            pr_data = PRData(
                diff=diff_content,
                title=title,
                description=description,
                author=author,
                files_changed=files_changed,
                pr_number=pr_number,
                repository=f"{owner}/{repo}",
                url=pr_url,
                provider="github",
                metadata={
                    "head_sha": head_sha,
                    "base_sha": base_sha,
                    "updated_at": updated_at
                }
            )
            
            # Cache the result
            self._cache_pr_data(cache_key, pr_data)
            
            return pr_data
            
        except RateLimitError as e:
            # Add rate limit info to error message if available
            if self._last_rate_limit_info:
                rate_info = self._last_rate_limit_info
                enhanced_message = (
                    f"{str(e)} "
                    f"(Rate limit: {rate_info.remaining}/{rate_info.limit} requests remaining)"
                )
                raise RateLimitError(e.provider, e.reset_time) from e
            raise
        except (ProviderAPIError, AuthenticationError, NetworkError, ValueError):
            # Re-raise our custom exceptions as-is
            # Add rate limit info if available
            if self._last_rate_limit_info:
                rate_info = self._last_rate_limit_info
                logger.info(
                    f"Rate limit status: {rate_info.remaining}/{rate_info.limit} requests remaining"
                )
            raise
        except Exception as e:
            # Catch any unexpected errors and wrap them with token redaction
            safe_message = self._redact_token(str(e))
            logger.error(f"Unexpected error fetching PR data: {safe_message}", exc_info=True)
            
            # Include rate limit info if available
            error_msg = f"Unexpected error: {safe_message}"
            if self._last_rate_limit_info:
                rate_info = self._last_rate_limit_info
                error_msg += f" (Rate limit: {rate_info.remaining}/{rate_info.limit} requests remaining)"
            
            raise ProviderAPIError(
                "github",
                0,
                error_msg
            )
    
    def validate_input(
        self,
        owner: str = None,
        repo: str = None,
        pr_number: int = None,
        url: str = None,
        **kwargs
    ) -> bool:
        """
        Validate GitHub-specific input parameters.
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            url: GitHub PR URL
            **kwargs: Additional parameters (ignored)
        
        Returns:
            True if either (owner, repo, pr_number) or url is valid
        """
        # If URL is provided, try to parse it
        if url:
            try:
                parsed_owner, parsed_repo, parsed_pr = self.parse_pr_url(url)
                return all([parsed_owner, parsed_repo, parsed_pr])
            except (ValueError, AttributeError):
                return False
        
        # If individual parameters provided, validate them
        if owner and repo and pr_number:
            # Check that owner and repo are non-empty strings
            if not isinstance(owner, str) or not owner.strip():
                return False
            if not isinstance(repo, str) or not repo.strip():
                return False
            # Check that pr_number is a positive integer
            if not isinstance(pr_number, int) or pr_number <= 0:
                return False
            return True
        
        return False
    
    @staticmethod
    def can_handle(input_str: str) -> bool:
        """
        Determine if input is a GitHub URL.
        
        Args:
            input_str: URL or file path
        
        Returns:
            True if input is a GitHub PR URL
        """
        if not input_str:
            return False
        
        # Check for GitHub domain
        return "github.com" in input_str.lower()
    
    @staticmethod
    def parse_pr_url(url: str) -> tuple[str, str, int]:
        """
        Parse GitHub PR URL to extract components.
        
        Supports multiple URL formats:
        - https://github.com/owner/repo/pull/123
        - https://github.com/owner/repo/pull/123/files
        - https://api.github.com/repos/owner/repo/pulls/123
        
        Args:
            url: GitHub PR URL
        
        Returns:
            Tuple of (owner, repo, pr_number)
        
        Raises:
            ValueError: If URL format is invalid or cannot be parsed
        """
        if not url:
            raise ValueError("URL cannot be empty")
        
        # Pattern for standard GitHub PR URLs
        # Matches: https://github.com/owner/repo/pull/123
        # Also matches with trailing paths like /files, /commits, etc.
        standard_pattern = r"github\.com/([^/]+)/([^/]+)/pull/(\d+)"
        
        # Pattern for GitHub API URLs
        # Matches: https://api.github.com/repos/owner/repo/pulls/123
        api_pattern = r"api\.github\.com/repos/([^/]+)/([^/]+)/pulls/(\d+)"
        
        # Try standard pattern first
        match = re.search(standard_pattern, url, re.IGNORECASE)
        if match:
            owner, repo, pr_number = match.groups()
            return owner, repo, int(pr_number)
        
        # Try API pattern
        match = re.search(api_pattern, url, re.IGNORECASE)
        if match:
            owner, repo, pr_number = match.groups()
            return owner, repo, int(pr_number)
        
        # If no pattern matched, raise error
        raise ValueError(
            f"Invalid GitHub PR URL format: {url}. "
            f"Expected format: https://github.com/owner/repo/pull/123 "
            f"or https://api.github.com/repos/owner/repo/pulls/123"
        )
