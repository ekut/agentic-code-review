# Troubleshooting Guide

This guide helps you diagnose and fix common issues with Agentic Code Review.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Authentication Issues](#authentication-issues)
- [GitHub API Issues](#github-api-issues)
- [Rate Limiting Issues](#rate-limiting-issues)
- [Network Issues](#network-issues)
- [Performance Issues](#performance-issues)
- [Testing Issues](#testing-issues)

## Installation Issues

### Problem: `uv` command not found

**Symptoms**:
```bash
bash: uv: command not found
```

**Solution**:
Install uv package manager:
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv

# Or with homebrew (macOS)
brew install uv
```

### Problem: Python version mismatch

**Symptoms**:
```
Error: Python 3.9 is not supported. Requires 3.10-3.13
```

**Solution**:
Install a compatible Python version:
```bash
# Check current version
python --version

# Install Python 3.11 (recommended)
# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt install python3.11

# Then use uv with specific Python
uv venv --python 3.11
```

### Problem: Dependency conflicts

**Symptoms**:
```
Error: Could not resolve dependencies
```

**Solution**:
```bash
# Clear cache and reinstall
rm -rf .venv
uv cache clean
uv sync
```

## Authentication Issues

### Problem: Missing GitHub token

**Symptoms**:
```
[AUTHENTICATION_ERROR] GitHub token is invalid or missing
Details: Received 401 Unauthorized from GitHub API
```

**Solution**:
1. Create a GitHub Personal Access Token:
   - Go to https://github.com/settings/tokens
   - Click "Generate new token (classic)"
   - Select scopes: `repo` (private) or `public_repo` (public only)
   - Copy the token

2. Add to `.env` file:
   ```bash
   GITHUB_TOKEN=ghp_your_token_here
   ```

3. Verify token works:
   ```bash
   curl -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/user
   ```

### Problem: Token has insufficient permissions

**Symptoms**:
```
[API_ERROR] 403 Forbidden
Details: Resource not accessible with current token permissions
```

**Solution**:
1. Check token scopes at https://github.com/settings/tokens
2. Ensure token has:
   - `repo` scope for private repositories
   - `public_repo` scope for public repositories
3. Regenerate token with correct scopes if needed

### Problem: Token expired

**Symptoms**:
```
[AUTHENTICATION_ERROR] Token is invalid
```

**Solution**:
1. Check token expiration date on GitHub
2. Generate a new token
3. Update `.env` file with new token

### Problem: Environment variable not loaded

**Symptoms**:
Token is in `.env` but still getting authentication errors.

**Solution**:
```bash
# Verify .env file exists
ls -la .env

# Check file contents (be careful not to expose token)
grep GITHUB_TOKEN .env

# Ensure no extra spaces
# Wrong: GITHUB_TOKEN = ghp_...
# Right: GITHUB_TOKEN=ghp_...

# Restart application after changing .env
```

## GitHub API Issues

### Problem: PR not found (404)

**Symptoms**:
```
[API_ERROR] Pull request not found
Details: GitHub API returned 404 for PR #123
```

**Solution**:
1. Verify PR number is correct
2. Check repository owner and name
3. Ensure PR hasn't been deleted
4. For private repos, verify token has `repo` scope
5. Try accessing PR in browser first

### Problem: Invalid URL format

**Symptoms**:
```
[VALIDATION_ERROR] Invalid GitHub URL format
```

**Solution**:
Use correct URL format:
```bash
# Correct formats
https://github.com/owner/repo/pull/123
https://api.github.com/repos/owner/repo/pulls/123

# Incorrect formats
https://github.com/owner/repo/pulls/123  # Note: "pulls" not "pull"
github.com/owner/repo/pull/123           # Missing https://
```

### Problem: Empty diff content

**Symptoms**:
```
[VALIDATION_ERROR] Empty diff content
Details: PR #123 has no changes
```

**Solution**:
1. Check if PR has actual file changes
2. Verify PR isn't a draft with no commits
3. Try fetching PR in browser to confirm it has changes
4. Check if PR was force-pushed (may need to wait for cache expiration)

## Rate Limiting Issues

### Problem: Rate limit exceeded

**Symptoms**:
```
[RATE_LIMIT_ERROR] GitHub rate limit exceeded
Details: 0 requests remaining. Resets at 2024-01-15 14:30:00
```

**Solution**:

**Immediate**:
- Wait until reset time (shown in error message)
- Use authenticated requests (5,000/hour vs 60/hour)

**Long-term**:
```bash
# Check current rate limit
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/rate_limit

# Response shows:
# - limit: Total requests allowed
# - remaining: Requests left
# - reset: Unix timestamp when limit resets
```

**Prevention**:
1. Always use authentication
2. Leverage caching (5-minute TTL)
3. Batch reviews instead of one-by-one
4. Monitor rate limit warnings

### Problem: Rate limit warnings

**Symptoms**:
```
⚠️  GitHub API rate limit low: 8 requests remaining
```

**Solution**:
This is a warning, not an error. The system will continue working but:
1. Consider waiting before making more requests
2. Check when limit resets
3. Plan batch operations accordingly

## Network Issues

### Problem: Connection timeout

**Symptoms**:
```
[NETWORK_ERROR] Connection timeout
Details: Failed to connect to GitHub API after 30 seconds
```

**Solution**:
1. Check internet connection:
   ```bash
   ping github.com
   ```

2. Verify GitHub is accessible:
   ```bash
   curl https://api.github.com
   ```

3. Check for proxy/firewall issues:
   ```bash
   # If behind proxy, set environment variables
   export HTTP_PROXY=http://proxy.example.com:8080
   export HTTPS_PROXY=http://proxy.example.com:8080
   ```

4. The system automatically retries (up to 3 times)

### Problem: DNS resolution failure

**Symptoms**:
```
[NETWORK_ERROR] DNS resolution failed
Details: Could not resolve hostname api.github.com
```

**Solution**:
1. Check DNS settings:
   ```bash
   nslookup api.github.com
   ```

2. Try alternative DNS:
   ```bash
   # Use Google DNS
   export DNS_SERVER=8.8.8.8
   ```

3. Check `/etc/hosts` for incorrect entries:
   ```bash
   grep github.com /etc/hosts
   ```

### Problem: SSL certificate errors

**Symptoms**:
```
[NETWORK_ERROR] SSL certificate verification failed
```

**Solution**:
1. Update CA certificates:
   ```bash
   # Ubuntu/Debian
   sudo apt update && sudo apt install ca-certificates
   
   # macOS
   brew install ca-certificates
   ```

2. Check system time (SSL requires accurate time):
   ```bash
   date
   ```

## Performance Issues

### Problem: Slow review times

**Symptoms**:
Reviews taking longer than expected.

**Solution**:

**For GitHub PRs**:
1. First request is slower (API fetch)
2. Subsequent requests use cache (5 minutes)
3. Large PRs take longer (more content to analyze)

**For Complex PRs**:
1. Full crew review takes longer than simple review
2. Web research adds latency
3. Consider if PR can be split into smaller changes

**Optimization**:
```python
# Check if PR is cached
# Cached requests are much faster
```

### Problem: High memory usage

**Symptoms**:
System using excessive memory.

**Solution**:
1. Large PRs consume more memory
2. Clear cache by restarting application
3. Process PRs sequentially instead of parallel
4. Consider increasing system resources

### Problem: Token usage too high

**Symptoms**:
High OpenAI API costs.

**Solution**:
1. Use simple review for small changes (less tokens)
2. Monitor token usage in output
3. Consider using cheaper models for simple reviews
4. Batch similar PRs together

## Testing Issues

### Problem: Tests failing

**Symptoms**:
```bash
uv run pytest
# Multiple test failures
```

**Solution**:

**Check environment**:
```bash
# Ensure test environment is set up
export CREWAI_TESTING=true

# Run specific test
uv run pytest tests/test_github_provider.py -v
```

**Common test issues**:
1. Missing environment variables
2. Network issues (use mocks)
3. Outdated dependencies
4. Cache conflicts

**Fix**:
```bash
# Clear cache
rm -rf .pytest_cache __pycache__

# Reinstall dependencies
uv sync

# Run tests with verbose output
uv run pytest -v
```

### Problem: Property-based tests failing

**Symptoms**:
```
Hypothesis found a counterexample
```

**Solution**:
1. This indicates a real bug in the code
2. Review the counterexample provided
3. Fix the code to handle the edge case
4. Re-run tests to verify fix

### Problem: Integration tests failing

**Symptoms**:
Tests that call real APIs are failing.

**Solution**:
1. Check API credentials are set
2. Verify network connectivity
3. Check rate limits
4. Use mocked responses for CI/CD:
   ```python
   import os
   os.environ["CREWAI_TESTING"] = "true"
   ```

## General Debugging

### Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Environment Variables

```bash
# List all environment variables
env | grep -E "(GITHUB|OPENAI|SERPER)"

# Check specific variable
echo $GITHUB_TOKEN
```

### Verify Installation

```bash
# Check Python version
python --version

# Check installed packages
uv pip list

# Check project structure
ls -la src/agentic_code_review/
```

### Test Components Individually

```python
# Test provider directly
from agentic_code_review.providers import GitHubProvider

provider = GitHubProvider()
pr_data = provider.fetch_pr_data(
    url="https://github.com/owner/repo/pull/123"
)
print(pr_data)
```

### Clear All Caches

```bash
# Clear Python cache
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Clear uv cache
uv cache clean

# Clear pytest cache
rm -rf .pytest_cache

# Clear flow state
rm -f flow_state.json result.dill
```

## Getting Help

If you're still experiencing issues:

1. **Check Documentation**:
   - [README](../README.md)
   - [Architecture](ARCHITECTURE.md)
   - [Contributing](../CONTRIBUTING.md)

2. **Search Issues**:
   - Check existing GitHub issues
   - Search for similar problems

3. **Create Issue**:
   - Provide error message
   - Include steps to reproduce
   - Share relevant logs (redact tokens!)
   - Specify environment (OS, Python version)

4. **Debug Information**:
   ```bash
   # Gather debug info
   python --version
   uv --version
   env | grep -E "(GITHUB|OPENAI|SERPER)" | sed 's/=.*/=[REDACTED]/'
   uv pip list | grep -E "(crewai|requests|hypothesis)"
   ```

## Common Error Messages Reference

| Error Message | Cause | Solution |
|--------------|-------|----------|
| `GitHub token is invalid` | Missing/wrong token | Check `.env` file |
| `Rate limit exceeded` | Too many requests | Wait or use auth |
| `PR not found` | Wrong PR number | Verify PR exists |
| `Connection timeout` | Network issue | Check connectivity |
| `Invalid URL format` | Malformed URL | Use correct format |
| `Empty diff content` | PR has no changes | Verify PR has commits |
| `DNS resolution failed` | DNS issue | Check DNS settings |
| `SSL certificate error` | Certificate issue | Update CA certs |

## Prevention Tips

1. **Always use authentication** for higher rate limits
2. **Validate inputs** before processing
3. **Monitor rate limits** proactively
4. **Use caching** to reduce API calls
5. **Test with small PRs** first
6. **Keep dependencies updated**
7. **Review logs regularly**
8. **Use environment variables** for secrets
9. **Test in development** before production
10. **Have backup tokens** ready

## Still Need Help?

Open an issue with:
- Clear description of the problem
- Steps to reproduce
- Error messages (with tokens redacted)
- Environment information
- What you've already tried

We're here to help! 🚀
