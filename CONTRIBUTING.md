# Contributing to Agentic Code Review

Thank you for your interest in contributing to Agentic Code Review! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Architecture Overview](#architecture-overview)
- [Adding New Providers](#adding-new-providers)
- [Testing Guidelines](#testing-guidelines)
- [Code Style](#code-style)
- [Submitting Changes](#submitting-changes)
- [Documentation](#documentation)

## Code of Conduct

This project follows a code of conduct to ensure a welcoming environment for all contributors. Please be respectful and constructive in all interactions.

## Getting Started

### Prerequisites

- Python 3.10 - 3.13
- [uv](https://docs.astral.sh/uv/) package manager
- Git
- A GitHub account

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/agentic-code-review.git
   cd agentic-code-review
   ```
3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/original-owner/agentic-code-review.git
   ```

## Development Setup

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

3. Run tests to verify setup:
   ```bash
   uv run pytest
   ```

4. Run the application:
   ```bash
   uv run kickoff --pr-input "files/code_changes_simple.txt"
   ```

## Architecture Overview

The project uses a **Flow-Based Architecture** with a **Pluggable Provider Pattern** that makes it easy to add new data sources.

### Key Concepts

- **Provider Pattern**: Abstracts data fetching from different platforms (GitHub, GitLab, local files)
- **Unified Interface**: All providers implement `PRProvider` and return `PRData` objects
- **Auto-Detection**: Factory automatically selects the right provider based on input

📖 **For detailed architecture documentation, diagrams, and technical details, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**

## Adding New Providers

To add support for a new platform (e.g., GitLab, Bitbucket):

### Step 1: Create Provider Class

Create `src/agentic_code_review/providers/your_provider.py`:

```python
from typing import Optional
from .base import PRProvider, PRData, AuthenticationError
import os

class YourProvider(PRProvider):
    """Provider for [Platform Name] API integration."""
    
    def __init__(self, token: Optional[str] = None, **kwargs):
        """Initialize provider with authentication."""
        self.token = token or os.getenv("YOUR_PLATFORM_TOKEN")
        if not self.token:
            raise AuthenticationError(
                "your_platform",
                "Token required. Set YOUR_PLATFORM_TOKEN environment variable."
            )
    
    @staticmethod
    def can_handle(input_str: str) -> bool:
        """Detect if input is a [Platform] URL."""
        return "your-platform.com" in input_str
    
    def validate_input(self, url: str = None, **kwargs) -> bool:
        """Validate input parameters."""
        return url and self.can_handle(url)
    
    def fetch_pr_data(self, url: str = None, **kwargs) -> PRData:
        """Fetch PR data from [Platform] API."""
        # Implementation here
        pass
```

### Step 2: Register Provider

Update `src/agentic_code_review/providers/__init__.py`:

```python
from .your_provider import YourProvider

# Register in factory
ProviderFactory.register_provider(YourProvider)
```

### Step 3: Add Tests

Create `tests/test_your_provider.py`:

```python
import pytest
from hypothesis import given, strategies as st
from agentic_code_review.providers import YourProvider

def test_can_handle():
    """Test URL detection."""
    assert YourProvider.can_handle("https://your-platform.com/owner/repo/pr/123")
    assert not YourProvider.can_handle("https://github.com/owner/repo/pull/123")

@given(st.integers(min_value=1, max_value=10000))
def test_url_parsing(pr_number):
    """Property test: URL parsing correctness."""
    url = f"https://your-platform.com/owner/repo/pr/{pr_number}"
    # Test parsing logic
    pass
```

### Step 4: Update Documentation

- Add environment variable to `.env.example`
- Add usage examples to `README.md`
- Document any platform-specific behavior

### Step 5: Submit Pull Request

See [Submitting Changes](#submitting-changes) section below.

## Testing Guidelines

### Test Types

1. **Unit Tests**: Test individual functions and methods
2. **Property-Based Tests**: Test with random inputs using Hypothesis
3. **Integration Tests**: Test end-to-end flows

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/agentic_code_review

# Run specific test file
uv run pytest tests/test_github_provider.py

# Run specific test
uv run pytest tests/test_github_provider.py::test_can_handle

# Run property-based tests only
uv run pytest -k "property"
```

### Writing Tests

#### Unit Tests

```python
def test_github_can_handle():
    """Test that GitHubProvider detects GitHub URLs."""
    assert GitHubProvider.can_handle("https://github.com/owner/repo/pull/123")
    assert not GitHubProvider.can_handle("files/local.txt")
```

#### Property-Based Tests

```python
from hypothesis import given, strategies as st

@given(st.integers(min_value=1, max_value=10000))
def test_url_parsing_correctness(pr_number):
    """
    Property test: URL parsing correctness.
    Feature: github-pr-integration, Property 1: URL parsing correctness
    """
    url = f"https://github.com/owner/repo/pull/{pr_number}"
    owner, repo, parsed_pr = GitHubProvider.parse_pr_url(url)
    assert parsed_pr == pr_number
```

### Test Requirements

- All new code must have tests
- Tests must pass before merging
- Maintain or improve code coverage
- Use descriptive test names
- Test both success and error cases

## Code Style

### Python Style Guide

- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints for function signatures
- Write docstrings for all public functions and classes
- Keep functions focused and small
- Use meaningful variable names

### Docstring Format

```python
def function_name(param1: str, param2: int) -> bool:
    """
    Brief description of what the function does.
    
    Args:
        param1: Description of param1
        param2: Description of param2
    
    Returns:
        Description of return value
    
    Raises:
        ExceptionType: When this exception is raised
    """
    pass
```

### Code Organization

- Keep related code together
- Use clear module boundaries
- Avoid circular dependencies
- Follow the existing project structure

### Formatting

```bash
# Format code with black (if available)
black src/ tests/

# Sort imports with isort (if available)
isort src/ tests/
```

## Submitting Changes

### Before Submitting

1. **Run tests**: Ensure all tests pass
   ```bash
   uv run pytest
   ```

2. **Check code style**: Follow PEP 8 guidelines

3. **Update documentation**: Update README and docstrings

4. **Test manually**: Run the application with your changes

5. **Check backward compatibility**: Ensure existing functionality still works

### Commit Messages

Write clear, descriptive commit messages:

```
Add GitLab provider support

- Implement GitLabProvider class
- Add URL parsing for GitLab MRs
- Add tests for GitLab integration
- Update documentation with GitLab examples

Fixes #123
```

### Pull Request Process

1. **Create a branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** and commit:
   ```bash
   git add .
   git commit -m "Your descriptive commit message"
   ```

3. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

4. **Create Pull Request** on GitHub:
   - Provide a clear title and description
   - Reference any related issues
   - Explain what changed and why
   - Include screenshots if relevant

5. **Respond to feedback**:
   - Address review comments
   - Make requested changes
   - Push updates to the same branch

### Pull Request Checklist

- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Documentation updated
- [ ] Code follows style guidelines
- [ ] Backward compatibility maintained
- [ ] Commit messages are clear
- [ ] PR description is complete

## Documentation

### What to Document

- **Code**: Docstrings for all public functions and classes
- **README**: Usage examples and setup instructions
- **CONTRIBUTING**: Development guidelines (this file)
- **Comments**: Complex logic and non-obvious decisions

### Documentation Style

- Write in clear, simple English
- Use examples to illustrate concepts
- Keep documentation up-to-date with code changes
- Include error messages and troubleshooting tips

### Updating Documentation

When making changes:

1. Update relevant docstrings
2. Update README if user-facing changes
3. Update CONTRIBUTING if development process changes
4. Add examples for new features

## Questions?

If you have questions:

1. Check existing documentation
2. Search existing issues
3. Open a new issue with your question
4. Tag it with "question" label

## Thank You!

Thank you for contributing to Agentic Code Review! Your contributions help make this project better for everyone.
