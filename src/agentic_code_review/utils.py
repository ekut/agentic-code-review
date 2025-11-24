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

def get_agent_model(agent_name: str) -> str | None:
    """
    Get configured LLM model for a specific agent.
    
    Args:
        agent_name: Name of the agent (e.g., "senior_developer", "security_engineer", "tech_lead")
    
    Returns:
        Model name if configured and valid, None otherwise
        
    Example:
        >>> get_agent_model("senior_developer")
        'gpt-4o-mini'
        >>> get_agent_model("tech_lead")  # Not configured
        None
    """
    load_env()
    env_var_name = f"{agent_name.upper()}_MODEL"
    model = os.getenv(env_var_name)
    
    # Return None for missing, empty, or whitespace-only values
    if model is None or not model.strip():
        return None
    
    return model.strip()

def get_senior_developer_model() -> str | None:
    """
    Get model for Senior Developer agent from SENIOR_DEVELOPER_MODEL env var.
    
    Returns:
        Model name if configured and valid, None otherwise
    """
    return get_agent_model("senior_developer")

def get_security_engineer_model() -> str | None:
    """
    Get model for Security Engineer agent from SECURITY_ENGINEER_MODEL env var.
    
    Returns:
        Model name if configured and valid, None otherwise
    """
    return get_agent_model("security_engineer")

def get_tech_lead_model() -> str | None:
    """
    Get model for Tech Lead agent from TECH_LEAD_MODEL env var.
    
    Returns:
        Model name if configured and valid, None otherwise
    """
    return get_agent_model("tech_lead")
    