# Architecture Documentation

This document provides a detailed overview of the Agentic Code Review system architecture.

## Table of Contents

- [Overview](#overview)
- [Architecture Diagram](#architecture-diagram)
- [Component Details](#component-details)
- [Data Flow](#data-flow)
- [Provider Pattern](#provider-pattern)
- [State Management](#state-management)
- [Error Handling](#error-handling)
- [Caching Strategy](#caching-strategy)
- [Extensibility](#extensibility)

## Overview

Agentic Code Review uses a **Flow-Based Architecture** with CrewAI for multi-agent orchestration and a **Pluggable Provider Pattern** for data source abstraction.

### Key Design Principles

1. **Separation of Concerns**: Clear boundaries between data fetching, analysis, and decision-making
2. **Extensibility**: Easy to add new data sources without modifying core logic
3. **Backward Compatibility**: Maintains support for existing file-based workflows
4. **Reliability**: Comprehensive error handling and retry logic
5. **Performance**: Caching and rate limit management

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PRCodeReviewFlow                              │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  1. Input Handler (read_pr_data)                               │ │
│  │     - Receives pr_input (URL or file path)                     │ │
│  │     - Detects input type                                       │ │
│  │     - Routes to appropriate provider                           │ │
│  └────────────────┬───────────────────────────────────────────────┘ │
│                   │                                                  │
│         ┌─────────▼──────────┐                                      │
│         │  Provider Factory  │                                      │
│         │  - Auto-detection  │                                      │
│         │  - Provider registry                                     │
│         └─────────┬──────────┘                                      │
│                   │                                                  │
│    ┌──────────────┼──────────────┬──────────────┐                  │
│    │              │              │              │                   │
│ ┌──▼────────┐ ┌──▼────────┐ ┌──▼────────┐ ┌───▼──────┐           │
│ │  GitHub   │ │  GitLab   │ │ Bitbucket │ │   File   │           │
│ │  Provider │ │  Provider │ │  Provider │ │  Reader  │           │
│ │           │ │           │ │           │ │          │           │
│ │ - Auth    │ │ (Future)  │ │ (Future)  │ │ - Read   │           │
│ │ - Fetch   │ │           │ │           │ │ - Parse  │           │
│ │ - Cache   │ │           │ │           │ │          │           │
│ │ - Retry   │ │           │ │           │ │          │           │
│ └──┬────────┘ └───────────┘ └───────────┘ └───┬──────┘           │
│    │                                            │                   │
│    │         All implement PRProvider          │                   │
│    │              interface                     │                   │
│    └────────────────┬───────────────────────────┘                  │
│                     │                                               │
│          ┌──────────▼──────────┐                                   │
│          │   Unified PR Data   │                                   │
│          │   (PRData model)    │                                   │
│          │   - diff            │                                   │
│          │   - metadata        │                                   │
│          └──────────┬──────────┘                                   │
│                     │                                               │
│  ┌──────────────────▼──────────────────┐                          │
│  │  2. Analysis Router (analyze_changes)│                          │
│  │     - Count lines/files             │                          │
│  │     - Classify as SIMPLE/COMPLEX    │                          │
│  └──────────────────┬──────────────────┘                          │
│                     │                                               │
│         ┌───────────┴───────────┐                                  │
│         │                       │                                   │
│  ┌──────▼──────┐       ┌───────▼────────┐                        │
│  │ 3a. Simple  │       │ 3b. Full Crew  │                        │
│  │    Review   │       │     Review     │                        │
│  │             │       │                │                        │
│  │ - Quick LLM │       │ - Senior Dev   │                        │
│  │   analysis  │       │ - Security Eng │                        │
│  │             │       │ - Tech Lead    │                        │
│  └──────┬──────┘       └───────┬────────┘                        │
│         │                       │                                   │
│         └───────────┬───────────┘                                  │
│                     │                                               │
│          ┌──────────▼──────────┐                                   │
│          │ 4. Final Decision   │                                   │
│          │    (make_final_     │                                   │
│          │     decision)       │                                   │
│          │                     │                                   │
│          │ - Synthesize        │                                   │
│          │ - Decide            │                                   │
│          │ - Format output     │                                   │
│          └──────────┬──────────┘                                   │
│                     │                                               │
│          ┌──────────▼──────────┐                                   │
│          │ 5. Return Answer    │                                   │
│          │    (return_final_   │                                   │
│          │     answer)         │                                   │
│          └─────────────────────┘                                   │
└─────────────────────────────────────────────────────────────────────┘

External Dependencies:
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   GitHub API     │  │   OpenAI API     │  │   Serper API     │
│  (REST API v3)   │  │   (gpt-4o-mini)  │  │  (Web Search)    │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

## Component Details

### 1. Flow Layer (`main.py`)

**Purpose**: Orchestrates the entire review process using CrewAI Flow.

**Key Methods**:
- `read_pr_data()`: Entry point, fetches PR data
- `analyze_changes()`: Routes to simple or complex review
- `simple_review()`: Lightweight review for small changes
- `full_crew_review()`: Multi-agent review for complex changes
- `make_final_decision()`: Synthesizes findings
- `return_final_answer()`: Returns final output

**State Management**:
```python
class ReviewState(BaseModel):
    pr_input: str              # URL or file path
    pr_content: str            # Diff content
    pr_metadata: dict          # Title, author, etc.
    errors: list               # Error messages
    review_result: dict        # Review findings
    crew_needed: bool          # Simple vs complex
    tokens_used: dict          # Token tracking
    final_answer: str          # Final decision
```

### 2. Provider Layer (`providers/`)

**Purpose**: Abstract data fetching from different platforms.

**Components**:

#### Base Classes (`base.py`)
- `PRProvider`: Abstract base class
- `PRData`: Unified data structure
- Custom exceptions: `AuthenticationError`, `ProviderAPIError`, etc.

#### GitHub Provider (`github_provider.py`)
- Authenticates with GitHub API
- Fetches PR metadata and diff
- Handles rate limiting
- Implements caching
- Retries on network errors

#### File Provider (`file_provider.py`)
- Reads local diff files
- Maintains backward compatibility
- Simple file I/O operations

#### Provider Factory (`__init__.py`)
- Auto-detects input type
- Instantiates appropriate provider
- Extensible registry pattern

### 3. Crew Layer (`crews/code_review_crew/`)

**Purpose**: Multi-agent system for code analysis.

**Agents**:

1. **Senior Developer**
   - Role: Code quality expert
   - Goal: Evaluate maintainability, style, best practices
   - Tools: None (LLM-based analysis)

2. **Security Engineer**
   - Role: Security specialist
   - Goal: Identify vulnerabilities and risks
   - Tools: SerperDevTool (web research)

3. **Tech Lead**
   - Role: Decision maker
   - Goal: Synthesize findings and make final call
   - Tools: None (synthesis)

**Process**: Sequential execution with memory enabled.

### 4. Utility Layer (`utils.py`)

**Purpose**: Helper functions for common operations.

**Functions**:
- `get_github_token()`: Load token from environment
- `create_pr_cache_key()`: Generate cache keys
- Environment variable management

## Data Flow

### GitHub PR Review Flow

```
1. User Input
   └─> "https://github.com/owner/repo/pull/123"

2. Provider Factory
   └─> Detects GitHub URL
   └─> Instantiates GitHubProvider

3. GitHub Provider
   └─> Check cache (5-minute TTL)
   └─> If not cached:
       ├─> Authenticate with token
       ├─> Fetch PR metadata (GET /repos/{owner}/{repo}/pulls/{pr})
       ├─> Fetch PR diff (Accept: application/vnd.github.v3.diff)
       ├─> Check rate limits
       └─> Cache result

4. Unified PRData
   └─> diff: "diff --git a/file.py..."
   └─> title: "Add new feature"
   └─> description: "This PR adds..."
   └─> author: "username"
   └─> files_changed: ["file1.py", "file2.py"]
   └─> pr_number: 123
   └─> repository: "owner/repo"
   └─> url: "https://github.com/owner/repo/pull/123"
   └─> provider: "github"

5. Analysis Router
   └─> Count lines and files
   └─> If < 100 lines and < 5 files: SIMPLE
   └─> Else: COMPLEX

6a. Simple Review (SIMPLE)
    └─> Single LLM call
    └─> Quick analysis
    └─> Return decision

6b. Full Crew Review (COMPLEX)
    └─> Senior Developer analyzes code
    └─> Security Engineer checks vulnerabilities
    └─> Tech Lead synthesizes findings
    └─> Return comprehensive decision

7. Final Decision
   └─> Synthesize all findings
   └─> Format output
   └─> Return to user
```

### File-Based Review Flow

```
1. User Input
   └─> "files/code_changes.txt"

2. Provider Factory
   └─> Detects file path
   └─> Instantiates FileProvider

3. File Provider
   └─> Read file content
   └─> Create minimal PRData

4. [Continue with steps 5-7 from above]
```

## Provider Pattern

### Interface Definition

```python
class PRProvider(ABC):
    @abstractmethod
    def fetch_pr_data(self, **kwargs) -> PRData:
        """Fetch PR data from the provider."""
        pass
    
    @abstractmethod
    def validate_input(self, **kwargs) -> bool:
        """Validate input parameters."""
        pass
    
    @staticmethod
    @abstractmethod
    def can_handle(input_str: str) -> bool:
        """Determine if this provider can handle the input."""
        pass
```

### Provider Selection Algorithm

```python
def get_provider(input_str: str, **config) -> PRProvider:
    for provider_class in _providers:
        if provider_class.can_handle(input_str):
            return provider_class(**config)
    raise ValueError(f"No provider found for input: {input_str}")
```

**Order matters**: Providers are checked in registration order. First match wins.

### Adding New Providers

1. Implement `PRProvider` interface
2. Register in `ProviderFactory._providers`
3. Add tests
4. Update documentation

## State Management

### ReviewState Model

```python
class ReviewState(BaseModel):
    # Input
    pr_input: str = ""
    
    # PR Data
    pr_content: str = ""
    pr_metadata: dict = {}
    
    # Analysis
    errors: list = []
    review_result: dict = {}
    crew_needed: bool = False
    
    # Output
    tokens_used: dict = {}
    final_answer: str = ""
```

### State Transitions

```
Initial State
    ↓
read_pr_data() → pr_content, pr_metadata populated
    ↓
analyze_changes() → crew_needed set
    ↓
simple_review() OR full_crew_review() → review_result populated
    ↓
make_final_decision() → final_answer set
    ↓
return_final_answer() → Return to user
```

### State Persistence

- State saved to `flow_state.json` after each step
- Result saved to `result.dill` (serialized)
- Enables resume on failure

## Error Handling

### Error Hierarchy

```
ProviderError (base)
├── AuthenticationError
├── ProviderAPIError
│   ├── 401 Unauthorized
│   ├── 403 Forbidden
│   ├── 404 Not Found
│   └── 500+ Server Errors
├── NetworkError
│   ├── Connection Timeout
│   ├── Connection Refused
│   └── DNS Resolution
└── RateLimitError
```

### Error Handling Strategy

1. **Validation Errors**: Fail fast with clear message
2. **Authentication Errors**: Fail fast with setup instructions
3. **Network Errors**: Retry with exponential backoff (max 3 attempts)
4. **Rate Limit Errors**: Wait until reset time
5. **API Errors**: Log details, show user-friendly message

### Retry Logic

```python
MAX_RETRIES = 3
INITIAL_BACKOFF = 1  # seconds
BACKOFF_MULTIPLIER = 2

# Retry sequence: 1s, 2s, 4s
for attempt in range(MAX_RETRIES):
    try:
        return fetch_data()
    except NetworkError:
        if attempt == MAX_RETRIES - 1:
            raise
        wait_time = INITIAL_BACKOFF * (BACKOFF_MULTIPLIER ** attempt)
        time.sleep(wait_time)
```

## Caching Strategy

### Cache Implementation

```python
@dataclass
class CacheEntry:
    data: PRData
    timestamp: datetime
    ttl_seconds: int = 300  # 5 minutes
    
    def is_expired(self) -> bool:
        return (datetime.now() - self.timestamp).total_seconds() > self.ttl_seconds

# In-memory cache
_pr_cache: Dict[str, CacheEntry] = {}
```

### Cache Key Generation

```python
def create_pr_cache_key(provider: str, owner: str, repo: str, pr_number: int) -> str:
    return f"{provider}:{owner}:{repo}:{pr_number}"
```

### Cache Behavior

- **TTL**: 5 minutes
- **Storage**: In-memory (lost on restart)
- **Invalidation**: Automatic expiration
- **Benefits**: Reduces API calls, improves performance

## Extensibility

### Adding New Providers

The architecture is designed for easy extensibility:

1. **No Core Changes**: Add new provider without modifying flow logic
2. **Interface Compliance**: Implement `PRProvider` interface
3. **Auto-Detection**: Factory automatically routes to new provider
4. **Isolated Testing**: Test provider independently

### Future Enhancements

Potential areas for extension:

1. **More Providers**: GitLab, Bitbucket, AWS CodeCommit, Azure DevOps
2. **Persistent Cache**: Redis or database-backed caching
3. **Webhooks**: Automatic review on PR creation
4. **Custom Agents**: Domain-specific review agents
5. **Output Formats**: JSON, Markdown, HTML reports
6. **Integration**: CI/CD pipeline integration

### Design Patterns Used

1. **Abstract Factory**: Provider factory for object creation
2. **Strategy Pattern**: Different providers for different platforms
3. **Template Method**: Base provider with customizable steps
4. **Decorator**: Caching and retry decorators
5. **Observer**: Flow state changes trigger next steps

## Performance Considerations

### Optimization Strategies

1. **Caching**: Reduce redundant API calls
2. **Parallel Execution**: Agents work concurrently (CrewAI async)
3. **Lazy Loading**: Only fetch data when needed
4. **Rate Limit Management**: Avoid hitting limits
5. **Efficient Parsing**: Minimal string operations

### Scalability

- **Horizontal**: Multiple instances can run independently
- **Vertical**: Increase resources for larger PRs
- **Caching**: Shared cache (Redis) for multi-instance deployments

## Security Considerations

1. **Token Management**: Never log or expose tokens
2. **Input Validation**: Validate all user inputs
3. **Error Messages**: Redact sensitive information
4. **Environment Variables**: Use `.env` for secrets
5. **HTTPS Only**: All API calls use HTTPS

## Monitoring and Observability

### Logging

- **Levels**: INFO, WARNING, ERROR
- **Format**: Structured logging with context
- **Redaction**: Automatic token redaction

### Metrics

Track:
- API call count
- Cache hit rate
- Error rate
- Review duration
- Token usage

## Conclusion

The architecture balances:
- **Simplicity**: Easy to understand and use
- **Extensibility**: Easy to add new features
- **Reliability**: Comprehensive error handling
- **Performance**: Caching and optimization
- **Maintainability**: Clear separation of concerns

For questions or suggestions, please open an issue or contribute to the documentation.
