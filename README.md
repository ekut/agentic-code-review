# Agentic Code Review

An automated pull request review system powered by CrewAI that analyzes code changes for quality issues and security vulnerabilities, then makes intelligent decisions about whether to approve, request changes, or escalate to human review.

## Features

- **Multi-Agent Analysis**: Uses specialized AI agents (Senior Developer, Security Engineer, Tech Lead) for comprehensive code review
- **Intelligent Routing**: Automatically routes simple changes through lightweight review while complex changes trigger full crew analysis
- **GitHub Integration**: Fetch PR data directly from GitHub repositories via API
- **Local File Support**: Backward compatible with local diff file input
- **Security Focus**: Identifies vulnerabilities and assesses risk levels with web research capabilities
- **Automated Decisions**: Makes approval/rejection decisions based on code quality and security analysis

## Prerequisites

- Python 3.10 - 3.13
- [uv](https://docs.astral.sh/uv/) package manager
- OpenAI API key
- Serper API key (for web search)
- GitHub Personal Access Token (for GitHub PR integration)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd agentic_code_review
```

2. Install dependencies using uv:
```bash
uv sync
```

3. Set up environment variables (see Configuration section below)

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Required: OpenAI API Key for LLM calls
OPENAI_API_KEY=your_openai_api_key_here

# Required: Serper API Key for web search functionality
SERPER_API_KEY=your_serper_api_key_here

# Optional: Serper base URL (defaults to https://google.serper.dev)
DLAI_SERPER_BASE_URL=https://google.serper.dev

# Required for GitHub integration: GitHub Personal Access Token
GITHUB_TOKEN=your_github_token_here
```

You can copy `.env.example` to `.env` and fill in your actual values:
```bash
cp .env.example .env
```

### GitHub Token Setup

To use the GitHub PR integration feature, you need to create a Personal Access Token:

1. Go to [GitHub Settings > Developer settings > Personal access tokens > Tokens (classic)](https://github.com/settings/tokens)
2. Click "Generate new token" → "Generate new token (classic)"
3. Give your token a descriptive name (e.g., "Agentic Code Review")
4. Select the required scopes:
   - For **private repositories**: Select `repo` (Full control of private repositories)
   - For **public repositories only**: Select `public_repo` (Access public repositories)
5. Click "Generate token"
6. Copy the token immediately (you won't be able to see it again)
7. Add the token to your `.env` file as `GITHUB_TOKEN=ghp_your_token_here`

**Security Note**: Never commit your `.env` file or expose your tokens. The `.gitignore` file is configured to exclude `.env` files.

## Usage

### Review a GitHub Pull Request

The system automatically detects GitHub URLs and fetches PR data via the GitHub API:

```bash
# Using a GitHub PR URL (HTTPS format)
uv run kickoff --pr-input "https://github.com/owner/repo/pull/123"

# Using a GitHub API URL format
uv run kickoff --pr-input "https://api.github.com/repos/owner/repo/pulls/123"
```

**Example with Real Repository:**
```bash
# Review a PR from a public repository
uv run kickoff --pr-input "https://github.com/crewAIInc/crewAI/pull/1234"
```

**What Happens:**
1. System detects GitHub URL format
2. Authenticates with GitHub API using `GITHUB_TOKEN`
3. Fetches PR metadata (title, description, author, files changed)
4. Fetches PR diff content
5. Caches the data for 5 minutes
6. Routes to appropriate review flow (simple or complex)
7. Returns review decision with recommendations

### Review a Local Diff File

For backward compatibility, you can still use local diff files:

```bash
# Using a local file path
uv run kickoff --pr-input "files/code_changes.txt"

# Using an absolute path
uv run kickoff --pr-input "/path/to/your/diff.txt"
```

**Example:**
```bash
# Review a local diff file
uv run kickoff --pr-input "files/code_changes_simple.txt"
```

**What Happens:**
1. System detects file path format
2. Reads diff content from local file
3. Routes to appropriate review flow
4. Returns review decision

### Programmatic Usage

You can also use the system programmatically in Python:

```python
from agentic_code_review.main import PRCodeReviewFlow

# Initialize the flow
flow = PRCodeReviewFlow()

# Review a GitHub PR
result = flow.kickoff(inputs={"pr_input": "https://github.com/owner/repo/pull/123"})
print(result["final_answer"])

# Review a local file
result = flow.kickoff(inputs={"pr_input": "files/code_changes.txt"})
print(result["final_answer"])
```

### Alternative Commands

```bash
# Run the code review flow
uv run run_crew

# Generate flow visualization (creates flow diagram)
uv run plot

# Run from Python module
python -m agentic_code_review.main

# Run with specific Python version
uv run python -m agentic_code_review.main
```

## Architecture

The system uses a **Flow-Based Architecture** with CrewAI and a **Pluggable Provider Pattern** for extensibility.

### Key Components

1. **Provider Layer**: Pluggable architecture supporting multiple platforms
   - **GitHubProvider**: Fetches PR data from GitHub API (active)
   - **FileProvider**: Reads local diff files (backward compatibility)
   - **Future Providers**: GitLab, Bitbucket, AWS CodeCommit (extensible)

2. **Analysis Router**: Routes simple changes to lightweight review, complex changes to full crew

3. **Multi-Agent Crew**: 
   - **Senior Developer**: Evaluates code quality, style, and maintainability
   - **Security Engineer**: Identifies security vulnerabilities and assesses risk
   - **Tech Lead**: Synthesizes findings and makes final decisions

### Supported Input Formats

- **GitHub URLs**: `https://github.com/owner/repo/pull/123`
- **Local Files**: Any file path containing a diff (e.g., `files/code_changes.txt`)
- **Future Support**: GitLab, Bitbucket, AWS CodeCommit

📖 **For detailed architecture documentation, diagrams, and technical details, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**

## Project Structure

```
src/agentic_code_review/
├── main.py                    # Flow definition and entry point
├── utils.py                   # Helper functions
├── providers/                 # Provider abstraction layer
│   ├── __init__.py           # Provider factory
│   ├── base.py               # Abstract base class
│   ├── file_provider.py      # Local file provider
│   └── github_provider.py    # GitHub API provider
└── crews/
    └── code_review_crew/
        ├── crew.py            # Crew definition with agents and tasks
        ├── config/
        │   ├── agents.yaml    # Agent role definitions
        │   └── tasks.yaml     # Task descriptions
        └── guardrails/
            └── guardrails.py  # Output validation

files/                         # Sample input files
tests/                         # Test suite
```

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/agentic_code_review

# Run specific test file
uv run pytest tests/test_github_provider.py
```

### Testing Mode

Set `CREWAI_TESTING=true` in your code to enable testing mode, which uses mock responses instead of real API calls.

## Error Handling and Troubleshooting

The system provides clear, actionable error messages for common issues. All errors follow this format:

```
[ERROR_TYPE] Brief description
Details: Specific information about what went wrong
Suggestion: How to fix or what to try next
```

### Common Issues

- **Authentication Errors**: Missing or invalid GitHub token
- **Rate Limit Errors**: Too many API requests
- **Network Errors**: Connection timeouts, DNS failures
- **Input Validation Errors**: Invalid URL format, file not found

🔧 **For detailed troubleshooting, error messages, and solutions, see [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)**

### Quick Troubleshooting

```bash
# Test GitHub token
curl -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/user

# Check rate limit
curl -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/rate_limit

# Enable verbose logging
flow = PRCodeReviewFlow()
flow.verbose = True
```

## Advanced Features

The system includes advanced features for reliability and performance:

- **Caching**: 5-minute cache for PR data to reduce API calls
- **Rate Limiting**: Automatic monitoring and handling of GitHub API limits
- **Retry Logic**: Exponential backoff for transient network errors
- **Error Recovery**: Comprehensive error handling with clear messages

🏗️ **For technical details on caching, rate limiting, and retry strategies, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**

## Examples

### Example 1: Review a Simple PR

```bash
# Review a small PR with a few file changes
uv run kickoff --pr-input "https://github.com/owner/repo/pull/123"
```

**Expected Output:**
```
🔍 Starting PR Code Review...
✓ Fetched PR data from GitHub
✓ Detected SIMPLE change (3 files, 45 lines)
✓ Running lightweight review...
✓ Review complete

Decision: APPROVE
Reasoning: Code changes are minimal and follow best practices. No security concerns identified.
```

### Example 2: Review a Complex PR

```bash
# Review a large PR with many changes
uv run kickoff --pr-input "https://github.com/owner/repo/pull/456"
```

**Expected Output:**
```
🔍 Starting PR Code Review...
✓ Fetched PR data from GitHub
✓ Detected COMPLEX change (15 files, 500 lines)
✓ Assembling review crew...
✓ Senior Developer analyzing code quality...
✓ Security Engineer checking for vulnerabilities...
✓ Tech Lead synthesizing findings...
✓ Review complete

Decision: REQUEST_CHANGES
Reasoning: Found potential SQL injection vulnerability in database query. Recommend using parameterized queries.
Recommendations:
- Fix SQL injection in user_service.py line 45
- Add input validation for user-provided data
- Consider adding integration tests for database operations
```

### Example 3: Review Local File

```bash
# Review a local diff file (backward compatibility)
uv run kickoff --pr-input "files/code_changes.txt"
```

**Expected Output:**
```
🔍 Starting PR Code Review...
✓ Read PR data from local file
✓ Detected SIMPLE change
✓ Running lightweight review...
✓ Review complete

Decision: APPROVE
```

### Example 4: Programmatic Usage

```python
from agentic_code_review.main import PRCodeReviewFlow

# Initialize flow
flow = PRCodeReviewFlow()

# Review multiple PRs
prs = [
    "https://github.com/owner/repo/pull/123",
    "https://github.com/owner/repo/pull/124",
    "https://github.com/owner/repo/pull/125",
]

for pr_url in prs:
    result = flow.kickoff(inputs={"pr_input": pr_url})
    print(f"PR: {pr_url}")
    print(f"Decision: {result['final_answer']}")
    print("-" * 80)
```

### Example 5: Handling Errors

```python
from agentic_code_review.main import PRCodeReviewFlow
from agentic_code_review.providers.base import (
    AuthenticationError,
    RateLimitError,
    ProviderAPIError
)

flow = PRCodeReviewFlow()

try:
    result = flow.kickoff(inputs={
        "pr_input": "https://github.com/owner/repo/pull/999999"
    })
except ProviderAPIError as e:
    print(f"API Error: {e}")
    print(f"Status Code: {e.status_code}")
except AuthenticationError as e:
    print(f"Auth Error: {e}")
    print("Please check your GITHUB_TOKEN")
except RateLimitError as e:
    print(f"Rate Limit Error: {e}")
    print(f"Resets at: {e.reset_time}")
```

## Best Practices

### Security

1. **Never commit tokens**: Keep `.env` file out of version control
2. **Use minimal scopes**: Only grant necessary permissions to tokens
3. **Rotate tokens regularly**: Generate new tokens periodically
4. **Use environment variables**: Never hardcode tokens in code
5. **Monitor token usage**: Check for unauthorized access

### Performance

1. **Use caching**: Let the system cache PR data for repeated reviews
2. **Batch reviews**: Review multiple PRs in sequence to leverage caching
3. **Monitor rate limits**: Check rate limit status before bulk operations
4. **Use authentication**: Authenticated requests have higher rate limits

### Reliability

1. **Handle errors gracefully**: Catch and handle provider-specific errors
2. **Implement retries**: Let the system retry transient failures
3. **Monitor logs**: Check logs for warnings and errors
4. **Test with mocks**: Use `CREWAI_TESTING=true` for development

### Maintainability

1. **Follow provider pattern**: Use the provider abstraction for new platforms
2. **Write tests**: Add unit and property-based tests for new features
3. **Document changes**: Update README and docstrings
4. **Keep backward compatibility**: Don't break existing file-based workflows

## Contributing

Contributions are welcome! The system is designed to be easily extensible.

### Quick Start for Contributors

1. Follow the existing code structure and patterns
2. Add tests for new functionality (unit tests and property-based tests)
3. Update documentation
4. Ensure backward compatibility
5. Run the full test suite before submitting

### Adding New Providers

The system uses a pluggable provider pattern that makes it easy to add support for new platforms (GitLab, Bitbucket, AWS CodeCommit, etc.).

🤝 **For detailed instructions on adding new providers, testing requirements, and code review checklist, see [CONTRIBUTING.md](CONTRIBUTING.md)**

## Documentation

### Quick Links

- 📚 **[Quick Start Guide](docs/QUICK_START.md)** - Get up and running in 5 minutes
- 🏗️ **[Architecture Documentation](docs/ARCHITECTURE.md)** - Detailed system architecture and design
- 🔧 **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- 🤝 **[Contributing Guide](CONTRIBUTING.md)** - How to contribute to the project

### Documentation by Topic

**Installation & Setup**
- [Installation](#installation)
- [Configuration](#configuration)
- [GitHub Token Setup](#github-token-setup)

**Usage**
- [Review GitHub PR](#review-a-github-pull-request)
- [Review Local File](#review-a-local-diff-file)
- [Programmatic Usage](#programmatic-usage)
- [Examples](#examples)

**Development**
- [Development Setup](CONTRIBUTING.md#development-setup)
- [Adding New Providers](CONTRIBUTING.md#adding-new-providers)
- [Testing Guidelines](CONTRIBUTING.md#testing-guidelines)
- [Code Style](CONTRIBUTING.md#code-style)

**Troubleshooting**
- [Installation Issues](docs/TROUBLESHOOTING.md#installation-issues)
- [Authentication Issues](docs/TROUBLESHOOTING.md#authentication-issues)
- [GitHub API Issues](docs/TROUBLESHOOTING.md#github-api-issues)
- [Rate Limiting Issues](docs/TROUBLESHOOTING.md#rate-limiting-issues)
- [Network Issues](docs/TROUBLESHOOTING.md#network-issues)

## License

[Add your license information here]

## Support

For issues, questions, or contributions, please [open an issue](link-to-issues) or contact the maintainers.
