"""Pytest configuration for agentic code review tests."""

import sys
import os
import pytest
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture(autouse=True)
def isolate_environment_variables(monkeypatch):
    """
    Automatically isolate environment variables for each test.
    
    This fixture ensures that model configuration environment variables
    are cleared before each test, preventing test pollution from .env files
    or previous test runs.
    
    This works by:
    1. Storing original values from os.environ
    2. Deleting model env vars from os.environ
    3. Mocking load_env() to prevent .env file from being reloaded
    4. Restoring original state after test
    """
    from agentic_code_review import utils
    
    model_env_vars = [
        "SENIOR_DEVELOPER_MODEL",
        "SECURITY_ENGINEER_MODEL", 
        "TECH_LEAD_MODEL",
    ]
    
    # Store original values
    original_values = {}
    for var in model_env_vars:
        if var in os.environ:
            original_values[var] = os.environ[var]
            del os.environ[var]
    
    # Mock load_env() to do nothing, preventing .env file reload
    original_load_env = utils.load_env
    utils.load_env = lambda: None
    
    # Run the test
    yield
    
    # Restore original load_env function
    utils.load_env = original_load_env
    
    # Clean up: remove any model env vars that were set during test
    for var in model_env_vars:
        if var in os.environ:
            del os.environ[var]
    
    # Restore original values
    for var, value in original_values.items():
        os.environ[var] = value
