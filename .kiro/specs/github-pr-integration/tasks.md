# Implementation Plan

- [x] 1. Create provider abstraction layer
  - Create `src/agentic_code_review/providers/` directory structure
  - Define `PRData` dataclass with unified structure for all providers
  - Define `PRProvider` abstract base class with required interface methods
  - Define base exception classes (ProviderError, ProviderAPIError, NetworkError, RateLimitError, AuthenticationError)
  - _Requirements: 8.1, 8.5_

- [x] 1.1 Write property test for provider interface compliance
  - **Property 23: Provider interface compliance**
  - **Validates: Requirements 8.1**

- [x] 2. Implement ProviderFactory
  - Create factory class with provider registry
  - Implement `get_provider()` method for automatic provider detection
  - Implement `register_provider()` method for extensibility
  - Add error handling for unsupported input types
  - _Requirements: 8.2, 8.3, 8.4_

- [x] 2.1 Write property test for provider factory detection
  - **Property 24: Provider factory detection**
  - **Validates: Requirements 8.3, 8.4**

- [x] 3. Refactor existing file reading into FileProvider
  - Create `FileProvider` class implementing `PRProvider` interface
  - Move existing file reading logic from `main.py` to `FileProvider.fetch_pr_data()`
  - Implement `can_handle()` to detect file paths
  - Implement `validate_input()` for file path validation
  - Return `PRData` with diff content and minimal metadata
  - _Requirements: 6.1, 6.3_

- [x] 3.1 Write property test for file input backward compatibility
  - **Property 20: File input backward compatibility**
  - **Validates: Requirements 6.3**

- [x] 3.2 Write property test for input type detection and routing
  - **Property 19: Input type detection and routing**
  - **Validates: Requirements 6.1, 6.2, 6.4**

- [x] 4. Implement GitHubProvider core functionality
  - Create `GitHubProvider` class implementing `PRProvider` interface
  - Implement `__init__()` with token loading from environment
  - Implement `can_handle()` to detect GitHub URLs
  - Implement `parse_pr_url()` static method for URL parsing
  - Implement `validate_input()` for GitHub-specific validation
  - _Requirements: 1.1, 1.2, 1.4, 2.1_

- [x] 4.1 Write property test for URL parsing correctness
  - **Property 1: URL parsing correctness**
  - **Validates: Requirements 1.1**

- [x] 4.2 Write property test for multiple URL format support
  - **Property 4: Multiple URL format support**
  - **Validates: Requirements 1.4**

- [x] 4.3 Write property test for multiple parameter input acceptance
  - **Property 2: Multiple parameter input acceptance**
  - **Validates: Requirements 1.2**

- [x] 4.4 Write property test for invalid input rejection
  - **Property 3: Invalid input rejection**
  - **Validates: Requirements 1.3**

- [x] 5. Implement GitHub API data fetching
  - Implement `fetch_pr_data()` method to call GitHub API
  - Make authenticated requests with token in headers
  - Fetch PR metadata (title, description, author, files_changed)
  - Fetch PR diff using appropriate Accept header
  - Parse JSON responses and extract required fields
  - Return unified `PRData` object
  - _Requirements: 2.2, 3.1, 3.2, 4.1, 4.2_

- [x] 5.1 Write property test for token inclusion in API requests
  - **Property 6: Token inclusion in API requests**
  - **Validates: Requirements 2.2, 3.1**

- [x] 5.2 Write property test for diff extraction from responses
  - **Property 8: Diff extraction from responses**
  - **Validates: Requirements 3.2**

- [x] 5.3 Write property test for complete metadata retrieval
  - **Property 11: Complete metadata retrieval**
  - **Validates: Requirements 4.1**

- [x] 5.4 Write property test for metadata field extraction
  - **Property 12: Metadata field extraction**
  - **Validates: Requirements 4.2**

- [x] 5.5 Write property test for URL inclusion in metadata
  - **Property 14: URL inclusion in metadata**
  - **Validates: Requirements 4.5**

- [x] 6. Implement error handling and retry logic
  - Add try-except blocks for API errors (404, 403, 500, etc.)
  - Implement exponential backoff retry for network errors
  - Implement specific error types with descriptive messages
  - Add token redaction in all error messages and logs
  - Validate non-empty diff content before returning
  - _Requirements: 2.3, 2.4, 3.3, 3.4, 3.5, 7.1, 7.2, 7.3, 7.4_

- [x] 6.1 Write property test for retry with exponential backoff
  - **Property 9: Retry with exponential backoff**
  - **Validates: Requirements 3.4**

- [x] 6.2 Write property test for non-empty diff validation
  - **Property 10: Non-empty diff validation**
  - **Validates: Requirements 3.5**

- [x] 6.3 Write property test for token confidentiality
  - **Property 7: Token confidentiality**
  - **Validates: Requirements 2.4**

- [x] 6.4 Write property test for network error classification
  - **Property 22: Network error classification**
  - **Validates: Requirements 7.4**

- [x] 6.5 Write property test for dual-level error reporting
  - **Property 21: Dual-level error reporting**
  - **Validates: Requirements 7.1, 7.5**

- [x] 7. Implement rate limiting and caching
  - Implement `get_rate_limit_info()` to check GitHub rate limits
  - Check rate limit headers in all API responses
  - Log warnings when rate limit is low (< 10 requests)
  - Wait until reset time when rate limit is exceeded
  - Implement in-memory cache with 5-minute TTL
  - Generate cache keys based on provider, owner, repo, PR number
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 7.1 Write property test for rate limit header inspection
  - **Property 15: Rate limit header inspection**
  - **Validates: Requirements 5.1**

- [x] 7.2 Write property test for rate limit waiting behavior
  - **Property 16: Rate limit waiting behavior**
  - **Validates: Requirements 5.3**

- [x] 7.3 Write property test for rate limit info in errors
  - **Property 17: Rate limit info in errors**
  - **Validates: Requirements 5.4**

- [x] 7.4 Write property test for PR data caching
  - **Property 18: PR data caching**
  - **Validates: Requirements 5.5**

- [x] 8. Update ReviewState and flow logic
  - Modify `ReviewState` to use simplified `pr_input` field
  - Update `read_pr_file()` to `read_pr_data()` method
  - Use `ProviderFactory.get_provider()` to get appropriate provider
  - Call `provider.fetch_pr_data()` with unified interface
  - Update state with `pr_content` and `pr_metadata`
  - Maintain backward compatibility with existing flow steps
  - _Requirements: 6.1, 6.2, 6.4, 4.3_

- [x] 8.1 Write property test for state update after parsing
  - **Property 5: State update after parsing**
  - **Validates: Requirements 1.5**

- [x] 8.2 Write property test for metadata availability to crew
  - **Property 13: Metadata availability to crew**
  - **Validates: Requirements 4.3**

- [x] 9. Update utility functions
  - Add `get_github_token()` function to load token from environment
  - Add `create_pr_cache_key()` function for cache key generation
  - Update existing utilities to work with provider abstraction
  - _Requirements: 2.1, 5.5_

- [x] 10. Update dependencies and environment configuration
  - Add `requests>=2.31.0` to `pyproject.toml` dependencies
  - Update `.env.example` with `GITHUB_TOKEN` variable
  - Update documentation with token setup instructions
  - _Requirements: 2.1, 2.5_

- [x] 11. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Write integration tests for GitHub flow
  - Test complete flow with GitHub URL input
  - Test with mock GitHub API responses
  - Test error scenarios (404, 403, rate limit, network errors)
  - Test cache behavior across multiple requests
  - _Requirements: 3.1, 3.3, 5.1, 5.3, 5.5_

- [x] 13. Write integration tests for backward compatibility
  - Test complete flow with file path input
  - Verify existing behavior is maintained
  - Test switching between file and GitHub inputs
  - _Requirements: 6.1, 6.3, 6.4_

- [x] 14. Update documentation
  - Update README with GitHub integration usage examples
  - Document environment variable setup (GITHUB_TOKEN)
  - Add examples for both file and GitHub URL inputs
  - Document error messages and troubleshooting
  - Add architecture diagram showing provider pattern
  - Document how to add new providers in the future
  - _Requirements: 2.5, 7.1, 8.2_

- [x] 15. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
