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

# Memory Compatibility Registry
# Models in this list are known to be incompatible with CrewAI's memory feature.
# This list is maintained by developers as incompatibilities are discovered.
# 
# To add a new incompatible model pattern:
# 1. Add the pattern (or substring) to the MEMORY_INCOMPATIBLE_MODELS list below
# 2. The pattern matching is case-insensitive
# 3. Any model name containing the pattern will be marked as incompatible
#
# Known incompatible patterns:
# - "codex": All models containing "codex" (e.g., gpt-5-codex, gpt-5.1-codex-mini)
MEMORY_INCOMPATIBLE_MODELS = [
    "codex",  # All models containing "codex" (e.g., gpt-5-codex, gpt-5.1-codex-mini)
]

def is_model_memory_compatible(model_name: str | None) -> bool:
    """
    Check if a model is compatible with CrewAI memory.
    
    Args:
        model_name: The OpenAI model name, or None if using CrewAI default
    
    Returns:
        True if the model is compatible with CrewAI memory, False otherwise
        
    Logic:
        - None or empty string → True (CrewAI default assumed compatible)
        - Model name contains any pattern from MEMORY_INCOMPATIBLE_MODELS → False
        - Otherwise → True (unknown models assumed compatible)
        
    Example:
        >>> is_model_memory_compatible("gpt-4o-mini")
        True
        >>> is_model_memory_compatible("gpt-5-codex")
        False
        >>> is_model_memory_compatible(None)
        True
    """
    # None or empty string means using CrewAI default, which is assumed compatible
    if model_name is None or not model_name.strip():
        return True
    
    # Check if model name contains any incompatible pattern (case-insensitive)
    model_lower = model_name.lower()
    for pattern in MEMORY_INCOMPATIBLE_MODELS:
        if pattern.lower() in model_lower:
            return False
    
    # Unknown models are assumed compatible
    return True

def check_crew_memory_compatibility() -> tuple[bool, list[str]]:
    """
    Check if all agents in the crew use memory-compatible models.
    
    Returns:
        Tuple of (is_compatible, incompatible_models)
        - is_compatible: True if all agents use compatible models
        - incompatible_models: List of incompatible model names found
        
    Logic:
        - Get models for all three agents (senior_developer, security_engineer, tech_lead)
        - Check each model for compatibility
        - Return False if any model is incompatible
        - Return list of incompatible models for logging
        
    Example:
        >>> check_crew_memory_compatibility()
        (True, [])
        >>> # With SENIOR_DEVELOPER_MODEL=gpt-5-codex
        >>> check_crew_memory_compatibility()
        (False, ['gpt-5-codex'])
    """
    # Get models for all agents
    models = [
        get_senior_developer_model(),
        get_security_engineer_model(),
        get_tech_lead_model(),
    ]
    
    # Check each model for compatibility
    incompatible_models = []
    for model in models:
        if model is not None and not is_model_memory_compatible(model):
            incompatible_models.append(model)
    
    # Return compatibility status and list of incompatible models
    is_compatible = len(incompatible_models) == 0
    return is_compatible, incompatible_models
    