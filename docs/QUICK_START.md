# Quick Start Guide

Get up and running with Agentic Code Review in 5 minutes.

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd agentic_code_review

# Install dependencies
uv sync

# Copy environment template
cp .env.example .env
```

## Configuration

Edit `.env` and add your API keys:

```bash
# Required
OPENAI_API_KEY=sk-...
SERPER_API_KEY=...

# For GitHub integration
GITHUB_TOKEN=ghp_...
```

### Get GitHub Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scope: `repo` (private repos) or `public_repo` (public only)
4. Copy token to `.env`

## Usage

### Review a GitHub PR

```bash
uv run kickoff --pr-input "https://github.com/owner/repo/pull/123"
```

### Review a Local File

```bash
uv run kickoff --pr-input "files/code_changes.txt"
```

## Common Commands

```bash
# Run review
uv run kickoff --pr-input "<url-or-file>"

# Run tests
uv run pytest

# Generate flow diagram
uv run plot

# Check rate limit
curl -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/rate_limit
```

## Troubleshooting

### "GitHub token is invalid"

**Solution**: Check that `GITHUB_TOKEN` in `.env` is correct and has proper scopes.

### "Rate limit exceeded"

**Solution**: Wait until reset time or use authentication for higher limits.

### "PR not found"

**Solution**: Verify PR number and repository name are correct.

## Next Steps

- Read the full [README](../README.md) for detailed documentation
- Check [CONTRIBUTING](../CONTRIBUTING.md) to add new features
- Review [examples](../README.md#examples) for more use cases

## Support

- Open an issue for bugs or questions
- Check existing documentation
- Review error messages for troubleshooting tips
