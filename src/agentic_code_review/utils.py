# Add your utilities or helper functions to this file.

import os
from dotenv import load_dotenv, find_dotenv
import json
from crewai import TaskOutput

# these expect to find a .env file at the directory above the lesson.                                                                                                                     # the format for that file is (without the comment)                                                                                                                                       #API_KEYNAME=AStringThatIsTheLongAPIKeyFromSomeService
def load_env():
    _ = load_dotenv(find_dotenv())

def get_openai_api_key():
    load_env()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    return openai_api_key

def get_serper_api_key():
    load_env()
    serper_api_key = os.getenv("SERPER_API_KEY")
    return serper_api_key

def get_github_token() -> str:
    """
    Load GitHub token from environment variables.
    
    Returns:
        GitHub personal access token from GITHUB_TOKEN environment variable.
        Returns empty string if not set.
    
    Note:
        The token should have appropriate permissions (e.g., 'repo' scope)
        to access the repositories you want to review.
    """
    load_env()
    github_token = os.getenv("GITHUB_TOKEN", "")
    return github_token

def get_gitlab_token() -> str:
    """
    Load GitLab token from environment variables (future implementation).
    
    Returns:
        GitLab personal access token from GITLAB_TOKEN environment variable.
        Returns empty string if not set.
    
    Note:
        This is a placeholder for future GitLab integration.
    """
    load_env()
    gitlab_token = os.getenv("GITLAB_TOKEN", "")
    return gitlab_token

def create_pr_cache_key(provider: str, owner: str, repo: str, pr_number: int) -> str:
    """
    Generate cache key for PR data.
    
    Args:
        provider: Provider name (e.g., "github", "gitlab", "bitbucket")
        owner: Repository owner (user or organization)
        repo: Repository name
        pr_number: Pull request number
    
    Returns:
        Cache key string in format "provider:owner:repo:pr_number"
    
    Example:
        >>> create_pr_cache_key("github", "octocat", "Hello-World", 123)
        'github:octocat:Hello-World:123'
    """
    return f"{provider}:{owner}:{repo}:{pr_number}"
    