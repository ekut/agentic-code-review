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

# Optional: LLM Model Configuration
# Configure which OpenAI model each agent uses for code review
# If not set, CrewAI will use its default model selection
SENIOR_DEVELOPER_MODEL=gpt-4o-mini
SECURITY_ENGINEER_MODEL=gpt-4o-mini
TECH_LEAD_MODEL=gpt-4o-mini
```

You can copy `.env.example` to `.env` and fill in your actual values:
```bash
cp .env.example .env
```

### Model Configuration (Optional)

Configure different OpenAI models for each agent to optimize cost and performance:

| Environment Variable | Purpose | Default |
|---------------------|---------|---------|
| `SENIOR_DEVELOPER_MODEL` | Code quality analysis | CrewAI default |
| `SECURITY_ENGINEER_MODEL` | Security vulnerability detection | CrewAI default |
| `TECH_LEAD_MODEL` | Final decision making | CrewAI default |

**Available models:** `gpt-4o` (most capable), `gpt-4o-mini` (recommended), `gpt-4-turbo`, `gpt-3.5-turbo` (most cost-effective)

🏗️ For cost optimization strategies and technical details, see [Model Configuration Architecture](docs/ARCHITECTURE.md#model-configuration-architecture).

### GitHub Token Setup

Create a Personal Access Token for GitHub integration:

1. Go to [GitHub Settings → Tokens](https://github.com/settings/tokens)
2. Generate new token (classic)
3. Select scope: `repo` (private repos) or `public_repo` (public only)
4. Copy token to `.env` as `GITHUB_TOKEN=ghp_...`

⚠️ **Security:** Never commit `.env` files. The `.gitignore` is configured to exclude them.

## Usage

### Review a GitHub Pull Request

```bash
# Review a GitHub PR
uv run kickoff --pr-input "https://github.com/owner/repo/pull/123"

# Example with real repository
uv run kickoff --pr-input "https://github.com/crewAIInc/crewAI/pull/1234"
```

The system automatically detects GitHub URLs, authenticates, fetches PR data, caches it (5 min), and routes to the appropriate review flow.

### Review a Local Diff File

```bash
# Review a local file (backward compatibility)
uv run kickoff --pr-input "files/code_changes.txt"
```

🏗️ For detailed data flow and processing steps, see [Data Flow](docs/ARCHITECTURE.md#data-flow).

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

### Basic Usage

```bash
# Simple PR (< 5 files, < 100 lines) → Quick review
uv run kickoff --pr-input "https://github.com/owner/repo/pull/123"

# Complex PR (many files/lines) → Full crew analysis
uv run kickoff --pr-input "https://github.com/owner/repo/pull/456"

# Local file (backward compatibility)
uv run kickoff --pr-input "files/code_changes.txt"
```

### Programmatic Usage

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

### Error Handling

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

**Security:** Never commit tokens • Use minimal scopes • Rotate regularly • Monitor usage

**Performance:** Leverage caching • Batch reviews • Monitor rate limits • Use authentication

**Reliability:** Handle errors gracefully • Let system retry failures • Monitor logs • Test with mocks

**Development:** Follow provider pattern • Write tests • Document changes • Maintain backward compatibility

🤝 For detailed guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md)

## Contributing

Contributions welcome! The system uses a pluggable provider pattern for easy extensibility.

**Quick Start:** Follow existing patterns • Add tests • Update docs • Maintain backward compatibility

🤝 For detailed guidelines on adding providers, testing, and code review, see [CONTRIBUTING.md](CONTRIBUTING.md)

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
