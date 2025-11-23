# Design Document: GitHub PR Integration

## Overview

This design extends the Agentic Code Review system to fetch Pull Request data directly from version control platforms via their APIs, starting with GitHub as the initial implementation (MVP/PoC). The integration maintains backward compatibility with local files while adding the ability to automatically retrieve PR diffs and metadata from remote repositories.

The design follows the existing CrewAI Flow architecture pattern, introducing a **pluggable provider architecture** that allows easy addition of new platforms (GitLab, Bitbucket, AWS CodeCommit, etc.) in the future. The initial implementation focuses on GitHub, but the abstraction layer is designed to accommodate multiple providers without modifying the core flow logic.

The system will handle authentication, rate limiting, error recovery, and caching to ensure reliable operation across different providers.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PRCodeReviewFlow                              │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Input Handler (New)                                           │ │
│  │  - Detect input type (URL vs local file)                      │ │
│  │  - Detect provider (GitHub, GitLab, etc.)                     │ │
│  │  - Route to appropriate provider                              │ │
│  └────────────────┬───────────────────────────────────────────────┘ │
│                   │                                                  │
│         ┌─────────▼──────────┐                                      │
│         │  Provider Factory  │                                      │
│         │  (New Module)      │                                      │
│         └─────────┬──────────┘                                      │
│                   │                                                  │
│    ┌──────────────┼──────────────┬──────────────┐                  │
│    │              │              │              │                   │
│ ┌──▼────────┐ ┌──▼────────┐ ┌──▼────────┐ ┌───▼──────┐           │
│ │  GitHub   │ │  GitLab   │ │ Bitbucket │ │   File   │           │
│ │  Provider │ │  Provider │ │  Provider │ │  Reader  │           │
│ │  (MVP)    │ │ (Future)  │ │ (Future)  │ │(Existing)│           │
│ └──┬────────┘ └───────────┘ └───────────┘ └───┬──────┘           │
│    │                                            │                   │
│    │         All implement PRProvider          │                   │
│    │              interface                     │                   │
│    └────────────────┬───────────────────────────┘                  │
│                     │                                               │
│          ┌──────────▼──────────┐                                   │
│          │   Unified PR Data   │                                   │
│          │   (PRData model)    │                                   │
│          └──────────┬──────────┘                                   │
│                     │                                               │
│          ┌──────────▼──────────┐                                   │
│          │  Existing Flow      │                                   │
│          │  (analyze_changes,  │                                   │
│          │   review, decision) │                                   │
│          └─────────────────────┘                                   │
└─────────────────────────────────────────────────────────────────────┘

External Dependencies:
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   GitHub API     │  │   GitLab API     │  │  Bitbucket API   │
│  (REST API v3)   │  │   (Future)       │  │    (Future)      │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

### Module Structure

```
src/agentic_code_review/
├── main.py                    # Flow definition (modified)
├── utils.py                   # Helper functions (modified)
├── providers/                 # New: Provider abstraction layer
│   ├── __init__.py           # Provider factory and base interface
│   ├── base.py               # PRProvider abstract base class
│   ├── file_provider.py      # Local file provider (refactored)
│   └── github_provider.py    # GitHub API provider (MVP)
│   # Future providers:
│   # ├── gitlab_provider.py
│   # ├── bitbucket_provider.py
│   # └── codecommit_provider.py
└── crews/
    └── code_review_crew/
        └── crew.py            # Unchanged
```

### Data Flow

1. **Input Phase**: User provides GitHub PR URL or local file path
2. **Detection Phase**: System determines input type
3. **Retrieval Phase**: 
   - GitHub path: Authenticate → Fetch PR data → Parse response → Cache
   - Local path: Read file (existing behavior)
4. **Normalization Phase**: Convert to unified ReviewState format
5. **Review Phase**: Existing flow continues unchanged

## Components and Interfaces

### 1. PRProvider Abstract Base Class

**Purpose**: Define the interface that all PR data providers must implement, enabling pluggable architecture.

**Location**: `src/agentic_code_review/providers/base.py`

**Interface**:

```python
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass

@dataclass
class PRData:
    """Unified PR data structure returned by all providers"""
    diff: str
    title: str
    description: str
    author: str
    files_changed: list[str]
    pr_number: int
    repository: str
    url: str
    provider: str  # "github", "gitlab", "bitbucket", etc.

class PRProvider(ABC):
    """Abstract base class for PR data providers"""
    
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
```

### 2. GitHubProvider Class

**Purpose**: Implement GitHub-specific API interactions with authentication, error handling, and rate limiting.

**Location**: `src/agentic_code_review/providers/github_provider.py`

**Interface**:

```python
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from .base import PRProvider, PRData

@dataclass
class RateLimitInfo:
    """GitHub API rate limit information"""
    remaining: int
    limit: int
    reset_time: datetime

class GitHubProvider(PRProvider):
    """Provider for GitHub API integration (MVP implementation)"""
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub provider with authentication token.
        
        Args:
            token: GitHub personal access token or OAuth token.
                   If None, reads from GITHUB_TOKEN environment variable.
        
        Raises:
            AuthenticationError: If token is not provided and not in environment
        """
        pass
    
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
        
        Returns:
            PRData object with all PR information
        
        Raises:
            GitHubAPIError: For API errors (404, 403, 500, etc.)
            NetworkError: For network/connection issues
            RateLimitError: When rate limit is exceeded
        """
        pass
    
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
        
        Returns:
            True if either (owner, repo, pr_number) or url is valid
        """
        pass
    
    @staticmethod
    def can_handle(input_str: str) -> bool:
        """
        Determine if input is a GitHub URL.
        
        Args:
            input_str: URL or file path
        
        Returns:
            True if input is a GitHub PR URL
        """
        pass
    
    def get_rate_limit_info(self) -> RateLimitInfo:
        """
        Get current rate limit status.
        
        Returns:
            RateLimitInfo with current limits and reset time
        """
        pass
    
    @staticmethod
    def parse_pr_url(url: str) -> tuple[str, str, int]:
        """
        Parse GitHub PR URL to extract components.
        
        Args:
            url: GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
        
        Returns:
            Tuple of (owner, repo, pr_number)
        
        Raises:
            ValueError: If URL format is invalid
        """
        pass
```

### 3. FileProvider Class

**Purpose**: Refactor existing file reading logic into provider pattern for consistency.

**Location**: `src/agentic_code_review/providers/file_provider.py`

**Interface**:

```python
from .base import PRProvider, PRData
from pathlib import Path

class FileProvider(PRProvider):
    """Provider for local file-based PR data (backward compatibility)"""
    
    def fetch_pr_data(self, file_path: str, **kwargs) -> PRData:
        """
        Read PR data from local file.
        
        Args:
            file_path: Path to local diff file
        
        Returns:
            PRData object with diff content
        
        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If file cannot be read
        """
        pass
    
    def validate_input(self, file_path: str = None, **kwargs) -> bool:
        """
        Validate that file path exists and is readable.
        
        Returns:
            True if file path is valid
        """
        pass
    
    @staticmethod
    def can_handle(input_str: str) -> bool:
        """
        Determine if input is a file path.
        
        Args:
            input_str: URL or file path
        
        Returns:
            True if input appears to be a file path
        """
        pass
```

### 4. ProviderFactory

**Purpose**: Automatically detect and instantiate the appropriate provider based on input.

**Location**: `src/agentic_code_review/providers/__init__.py`

**Interface**:

```python
from typing import Type
from .base import PRProvider
from .github_provider import GitHubProvider
from .file_provider import FileProvider

class ProviderFactory:
    """Factory for creating appropriate PR data provider"""
    
    # Registry of available providers (extensible)
    _providers: list[Type[PRProvider]] = [
        GitHubProvider,  # MVP
        FileProvider,    # Backward compatibility
        # Future: GitLabProvider, BitbucketProvider, etc.
    ]
    
    @classmethod
    def get_provider(cls, input_str: str, **config) -> PRProvider:
        """
        Detect and instantiate appropriate provider for input.
        
        Args:
            input_str: URL or file path
            **config: Provider-specific configuration (e.g., tokens)
        
        Returns:
            Instantiated provider ready to fetch data
        
        Raises:
            ValueError: If no provider can handle the input
        """
        for provider_class in cls._providers:
            if provider_class.can_handle(input_str):
                return provider_class(**config)
        raise ValueError(f"No provider found for input: {input_str}")
    
    @classmethod
    def register_provider(cls, provider_class: Type[PRProvider]):
        """
        Register a new provider (for future extensibility).
        
        Args:
            provider_class: Provider class to register
        """
        cls._providers.insert(0, provider_class)  # New providers take precedence
```

### 5. Modified ReviewState

**Purpose**: Simplify state to use provider abstraction, removing provider-specific fields.

**Location**: `src/agentic_code_review/main.py`

```python
from typing import Optional

class ReviewState(BaseModel):
    # Input configuration (simplified - provider-agnostic)
    pr_input: str = ""  # Can be file path, GitHub URL, GitLab URL, etc.
    
    # PR data
    pr_content: str = ""
    pr_metadata: dict = {}  # title, description, author, files_changed, url, provider
    
    # Existing fields
    errors: list = []
    review_result: dict = {}
    crew_needed: bool = False
    tokens_used: dict = {}
    final_answer: str = ""
```

### 6. Modified Flow Methods

**read_pr_file → read_pr_data**

```python
from agentic_code_review.providers import ProviderFactory

@start()
def read_pr_data(self):
    """
    Read PR data using appropriate provider (file, GitHub, etc.).
    Provider is automatically detected based on input format.
    """
    print("🔍 Starting PR Code Review...")
    
    pr_input = self.state.pr_input
    
    if not pr_input:
        self.state.errors.append("Missing 'pr_input' in state")
        self.state.final_answer = "No input provided. Please set 'pr_input' with a file path or PR URL."
        return
    
    try:
        # Get appropriate provider (factory pattern)
        provider = ProviderFactory.get_provider(
            pr_input,
            github_token=os.getenv("GITHUB_TOKEN")
            # Future: gitlab_token=..., bitbucket_token=...
        )
        
        # Fetch PR data (unified interface)
        pr_data = provider.fetch_pr_data(url=pr_input)
        
        # Update state with unified data
        self.state.pr_content = pr_data.diff
        self.state.pr_metadata = {
            "title": pr_data.title,
            "description": pr_data.description,
            "author": pr_data.author,
            "files_changed": pr_data.files_changed,
            "url": pr_data.url,
            "provider": pr_data.provider
        }
        
    except Exception as e:
        error_message = f"Error fetching PR data: {str(e)}"
        print(f"❌ {error_message}")
        self.state.errors.append(error_message)
        self.state.final_answer = error_message
```

### 7. Utility Functions

**Location**: `src/agentic_code_review/utils.py`

```python
def get_github_token() -> str:
    """Load GitHub token from environment variables"""
    pass

def get_gitlab_token() -> str:
    """Load GitLab token from environment variables (future)"""
    pass

def create_pr_cache_key(provider: str, owner: str, repo: str, pr_number: int) -> str:
    """Generate cache key for PR data"""
    pass
```

### 8. Custom Exceptions

**Location**: `src/agentic_code_review/providers/base.py`

```python
from datetime import datetime

class ProviderError(Exception):
    """Base exception for provider-related errors"""
    pass

class ProviderAPIError(ProviderError):
    """API request failed (4xx, 5xx errors)"""
    def __init__(self, provider: str, status_code: int, message: str):
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"{provider} API error {status_code}: {message}")

class NetworkError(ProviderError):
    """Network connectivity issues"""
    pass

class RateLimitError(ProviderError):
    """Rate limit exceeded"""
    def __init__(self, provider: str, reset_time: datetime):
        self.provider = provider
        self.reset_time = reset_time
        super().__init__(f"{provider} rate limit exceeded. Resets at {reset_time}")

class AuthenticationError(ProviderError):
    """Authentication failed"""
    def __init__(self, provider: str, message: str):
        self.provider = provider
        super().__init__(f"{provider} authentication error: {message}")
```

## Data Models

### PRData Structure

```python
@dataclass
class PRData:
    diff: str                    # Complete diff content
    title: str                   # PR title
    description: str             # PR body/description
    author: str                  # GitHub username of PR author
    files_changed: list[str]     # List of file paths modified
    pr_number: int              # PR number
    repository: str             # "owner/repo" format
    url: str                    # Full GitHub PR URL
```

### Cache Entry Structure

```python
@dataclass
class CacheEntry:
    data: PRData
    timestamp: datetime
    ttl_seconds: int = 300  # 5 minutes default
    
    def is_expired(self) -> bool:
        return (datetime.now() - self.timestamp).total_seconds() > self.ttl_seconds
```

## Correctness Properties


*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: URL parsing correctness
*For any* valid GitHub PR URL, parsing should extract the correct owner, repository name, and PR number that match the URL components
**Validates: Requirements 1.1**

### Property 2: Multiple parameter input acceptance
*For any* valid combination of owner, repository, and PR number provided as separate parameters, the system should accept and process them correctly
**Validates: Requirements 1.2**

### Property 3: Invalid input rejection
*For any* invalid input (malformed URLs, missing components, wrong formats), the system should reject it and provide an error message indicating the expected format
**Validates: Requirements 1.3**

### Property 4: Multiple URL format support
*For any* GitHub PR URL in supported formats (HTTPS, API URL), parsing should successfully extract the components
**Validates: Requirements 1.4**

### Property 5: State update after parsing
*For any* successfully parsed PR identifier, the system state should contain the extracted owner, repo, and PR number
**Validates: Requirements 1.5**

### Property 6: Token inclusion in API requests
*For any* API request made to GitHub, the authentication token should be included in the request headers
**Validates: Requirements 2.2, 3.1**

### Property 7: Token confidentiality
*For any* log output or error message generated by the system, authentication tokens should never appear in the text
**Validates: Requirements 2.4**

### Property 8: Diff extraction from responses
*For any* successful API response containing PR data, the system should extract and store the diff content
**Validates: Requirements 3.2**

### Property 9: Retry with exponential backoff
*For any* network failure during API requests, the system should retry up to 3 times with exponentially increasing delays between attempts
**Validates: Requirements 3.4**

### Property 10: Non-empty diff validation
*For any* retrieved diff content, the system should validate it is non-empty before proceeding to review
**Validates: Requirements 3.5**

### Property 11: Complete metadata retrieval
*For any* successful PR data fetch, the result should include title, description, author username, and list of changed files
**Validates: Requirements 4.1**

### Property 12: Metadata field extraction
*For any* GitHub API JSON response, the system should extract all required metadata fields (title, description, author, files_changed)
**Validates: Requirements 4.2**

### Property 13: Metadata availability to crew
*For any* successfully fetched PR metadata, it should be accessible in the ReviewState for use by the review crew
**Validates: Requirements 4.3**

### Property 14: URL inclusion in metadata
*For any* fetched PR data, the metadata should include the complete GitHub PR URL
**Validates: Requirements 4.5**

### Property 15: Rate limit header inspection
*For any* GitHub API response, the system should check and extract rate limit information from response headers
**Validates: Requirements 5.1**

### Property 16: Rate limit waiting behavior
*For any* API request that exceeds the rate limit, the system should wait until the reset time before retrying
**Validates: Requirements 5.3**

### Property 17: Rate limit info in errors
*For any* error message generated when rate limit information is available, the message should include the rate limit details
**Validates: Requirements 5.4**

### Property 18: PR data caching
*For any* PR identifier, fetching it multiple times within 5 minutes should result in only one API call, with subsequent requests served from cache
**Validates: Requirements 5.5**

### Property 19: Input type detection and routing
*For any* input provided (file path or GitHub identifier), the system should correctly detect the type and route to the appropriate handler (file reader or GitHub client)
**Validates: Requirements 6.1, 6.2, 6.4**

### Property 20: File input backward compatibility
*For any* local file path input, the system should read and process it with the same behavior as the pre-integration implementation
**Validates: Requirements 6.3**

### Property 21: Dual-level error reporting
*For any* error that occurs, the system should generate both detailed logging information for debugging and user-friendly error messages for end users
**Validates: Requirements 7.1, 7.5**

### Property 22: Network error classification
*For any* network error (timeout, connection failure, DNS error), the system should correctly classify and report the specific error type
**Validates: Requirements 7.4**

### Property 23: Provider interface compliance
*For any* provider implementation, it should implement all required methods from the PRProvider abstract base class (fetch_pr_data, validate_input, can_handle)
**Validates: Requirements 8.1**

### Property 24: Provider factory detection
*For any* input string (file path, GitHub URL, or future platform URLs), the provider factory should successfully detect and instantiate the appropriate provider
**Validates: Requirements 8.3, 8.4**

## Error Handling

### Error Categories

1. **Input Validation Errors**
   - Invalid URL format
   - Missing required parameters
   - Unsupported URL schemes
   - **Handling**: Immediate rejection with descriptive error message

2. **Authentication Errors**
   - Missing token
   - Invalid token
   - Insufficient permissions
   - **Handling**: Fail fast with guidance on token configuration

3. **API Errors**
   - 404 Not Found (PR doesn't exist)
   - 403 Forbidden (access denied)
   - 422 Unprocessable Entity (invalid request)
   - 500+ Server errors
   - **Handling**: Specific error messages with status codes and suggested actions

4. **Network Errors**
   - Connection timeout
   - Connection refused
   - DNS resolution failure
   - **Handling**: Retry with exponential backoff (up to 3 attempts)

5. **Rate Limit Errors**
   - Rate limit exceeded
   - **Handling**: Wait until reset time, log warning when approaching limit

6. **Data Validation Errors**
   - Empty diff content
   - Missing required metadata fields
   - **Handling**: Graceful degradation with defaults where possible

### Error Recovery Strategy

```python
# Retry logic for transient errors
MAX_RETRIES = 3
INITIAL_BACKOFF = 1  # seconds
BACKOFF_MULTIPLIER = 2

def fetch_with_retry(fetch_func, *args, **kwargs):
    """Execute fetch with exponential backoff retry"""
    for attempt in range(MAX_RETRIES):
        try:
            return fetch_func(*args, **kwargs)
        except NetworkError as e:
            if attempt == MAX_RETRIES - 1:
                raise
            wait_time = INITIAL_BACKOFF * (BACKOFF_MULTIPLIER ** attempt)
            time.sleep(wait_time)
    raise NetworkError("Max retries exceeded")
```

### Error Message Format

All error messages follow this structure:
```
[ERROR_TYPE] Brief description
Details: Specific information about what went wrong
Suggestion: How to fix or what to try next
```

Example:
```
[AUTHENTICATION_ERROR] GitHub token is invalid
Details: Received 401 Unauthorized from GitHub API
Suggestion: Check that GITHUB_TOKEN environment variable contains a valid Personal Access Token with 'repo' scope
```

## Testing Strategy

### Unit Testing

Unit tests will cover specific examples and edge cases:

1. **URL Parsing Tests**
   - Valid HTTPS URLs
   - Valid API URLs
   - Invalid URLs (malformed, wrong domain, missing components)
   - Edge cases (special characters, very long URLs)

2. **Authentication Tests**
   - Token loading from environment
   - Token inclusion in headers
   - Missing token handling
   - Invalid token handling

3. **API Response Parsing Tests**
   - Complete responses with all fields
   - Responses with missing optional fields
   - Malformed JSON responses
   - Empty responses

4. **Error Handling Tests**
   - Each error type (404, 403, 500, network errors)
   - Error message format validation
   - Token redaction in error messages

5. **Cache Tests**
   - Cache hit scenarios
   - Cache expiration
   - Cache key generation

6. **Input Detection Tests**
   - File path detection
   - GitHub URL detection
   - Ambiguous inputs

### Property-Based Testing

Property-based tests will verify universal properties across many inputs using the **Hypothesis** library for Python:

**Configuration**: Each property test will run a minimum of 100 iterations to ensure thorough coverage of the input space.

**Test Organization**: Each correctness property from the design document will be implemented as a single property-based test, tagged with the format: `**Feature: github-pr-integration, Property {number}: {property_text}**`

**Key Property Tests**:

1. **URL Parsing Properties**
   - Generate random valid GitHub URLs → verify correct component extraction
   - Generate random invalid URLs → verify rejection with error message

2. **State Management Properties**
   - Generate random PR identifiers → verify state updates correctly
   - Generate random inputs → verify input type detection is correct

3. **Security Properties**
   - Generate random tokens and error scenarios → verify tokens never appear in output

4. **Retry Logic Properties**
   - Simulate random network failures → verify retry count and backoff timing

5. **Caching Properties**
   - Generate random PR identifiers and timestamps → verify cache behavior

6. **Metadata Properties**
   - Generate random API responses → verify all required fields are extracted

7. **Error Reporting Properties**
   - Generate random errors → verify dual-level reporting (detailed + user-friendly)

**Generators**:
- `github_url_strategy`: Generates valid GitHub PR URLs with random owners, repos, PR numbers
- `invalid_url_strategy`: Generates malformed URLs
- `pr_identifier_strategy`: Generates (owner, repo, pr_number) tuples
- `api_response_strategy`: Generates mock GitHub API JSON responses
- `error_scenario_strategy`: Generates various error conditions

### Integration Testing

Integration tests will verify end-to-end flows:

1. **GitHub Flow Integration**
   - Provide GitHub URL → verify complete flow through review
   - Test with real GitHub API (using test repository)

2. **File Flow Integration**
   - Provide file path → verify existing behavior maintained

3. **Mixed Input Integration**
   - Alternate between GitHub and file inputs → verify both work

### Testing Tools

- **pytest**: Test runner and framework
- **hypothesis**: Property-based testing library
- **pytest-mock**: Mocking GitHub API responses
- **responses**: HTTP request mocking
- **pytest-cov**: Code coverage measurement

### Test Data

- **Mock API Responses**: JSON files with sample GitHub API responses
- **Test Files**: Sample PR diff files for file input testing
- **Test Repository**: A dedicated GitHub repository for integration tests

## Implementation Notes

### Dependencies

Add to `pyproject.toml`:
```toml
dependencies = [
    "crewai[tools]==0.203.1",
    "dill",
    "requests>=2.31.0",  # HTTP client for GitHub API
    "python-dotenv",      # Already present
]
```

### Environment Variables

Add to `.env`:
```bash
GITHUB_TOKEN=ghp_your_token_here
```

### GitHub API Endpoints

- **Get PR**: `GET /repos/{owner}/{repo}/pulls/{pr_number}`
- **Get PR Diff**: `GET /repos/{owner}/{repo}/pulls/{pr_number}` with `Accept: application/vnd.github.v3.diff`
- **Rate Limit**: `GET /rate_limit`

### API Request Headers

```python
headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28"
}
```

### Caching Implementation

Use simple in-memory dictionary with timestamp-based expiration:
```python
_cache: Dict[str, CacheEntry] = {}

def get_cached_pr(cache_key: str) -> Optional[PRData]:
    if cache_key in _cache:
        entry = _cache[cache_key]
        if not entry.is_expired():
            return entry.data
        del _cache[cache_key]
    return None
```

### Rate Limit Handling

```python
def check_rate_limit(response_headers: dict):
    remaining = int(response_headers.get('X-RateLimit-Remaining', 0))
    reset_time = int(response_headers.get('X-RateLimit-Reset', 0))
    
    if remaining < 10:
        logger.warning(f"GitHub API rate limit low: {remaining} requests remaining")
    
    if remaining == 0:
        wait_seconds = reset_time - time.time()
        raise RateLimitError(datetime.fromtimestamp(reset_time))
```

### Backward Compatibility Strategy

The system uses provider factory pattern for automatic detection:
```python
# Old approach (still works):
state.pr_input = "files/code_changes.txt"

# New approach (GitHub):
state.pr_input = "https://github.com/owner/repo/pull/123"

# Future approaches (extensible):
# state.pr_input = "https://gitlab.com/owner/repo/-/merge_requests/123"
# state.pr_input = "https://bitbucket.org/owner/repo/pull-requests/123"

# Factory automatically detects and routes
provider = ProviderFactory.get_provider(state.pr_input)
```

### Migration Path

1. **Phase 1**: Implement provider abstraction layer (base classes, factory)
2. **Phase 2**: Refactor existing file reading into FileProvider
3. **Phase 3**: Implement GitHubProvider with all error handling (MVP)
4. **Phase 4**: Modify flow to use provider factory
5. **Phase 5**: Add integration tests with real GitHub API
6. **Phase 6**: Deploy with monitoring for errors
7. **Future Phases**: Add GitLabProvider, BitbucketProvider, etc. as needed

Users can continue using file-based input indefinitely, or migrate to GitHub URLs at their convenience. Future platform support can be added by implementing new provider classes without touching existing code.

### Extensibility Example

Adding a new provider (e.g., GitLab) in the future:

```python
# src/agentic_code_review/providers/gitlab_provider.py
from .base import PRProvider, PRData

class GitLabProvider(PRProvider):
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITLAB_TOKEN")
    
    @staticmethod
    def can_handle(input_str: str) -> bool:
        return "gitlab.com" in input_str
    
    def fetch_pr_data(self, url: str = None, **kwargs) -> PRData:
        # GitLab-specific implementation
        pass
    
    def validate_input(self, **kwargs) -> bool:
        # GitLab-specific validation
        pass

# Register in providers/__init__.py
from .gitlab_provider import GitLabProvider
ProviderFactory._providers.insert(0, GitLabProvider)
```

No changes needed to main.py or the flow logic!
