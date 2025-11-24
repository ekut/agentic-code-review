"""Unit tests for model configuration utility functions."""

import pytest
import os
from agentic_code_review.utils import (
    get_agent_model,
    get_senior_developer_model,
    get_security_engineer_model,
    get_tech_lead_model
)


class TestGetAgentModel:
    """Test suite for get_agent_model function."""
    
    def test_valid_model_name_returned(self, monkeypatch):
        """Test that valid model configuration is returned correctly."""
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-4o")
        assert get_agent_model("senior_developer") == "gpt-4o"
    
    def test_empty_string_returns_none(self, monkeypatch):
        """Test that empty string configuration returns None."""
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "")
        assert get_agent_model("senior_developer") is None
    
    def test_whitespace_only_returns_none(self, monkeypatch):
        """Test that whitespace-only configuration returns None."""
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "   ")
        assert get_agent_model("senior_developer") is None
    
    def test_whitespace_with_tabs_returns_none(self, monkeypatch):
        """Test that whitespace with tabs returns None."""
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "\t\n  ")
        assert get_agent_model("senior_developer") is None
    
    def test_missing_env_var_returns_none(self, monkeypatch):
        """Test that missing environment variable returns None."""
        # Ensure the env var is not set
        monkeypatch.delenv("SENIOR_DEVELOPER_MODEL", raising=False)
        assert get_agent_model("senior_developer") is None
    
    def test_model_name_with_surrounding_whitespace_is_trimmed(self, monkeypatch):
        """Test that model names with surrounding whitespace are trimmed."""
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "  gpt-4o  ")
        assert get_agent_model("senior_developer") == "gpt-4o"


class TestGetSeniorDeveloperModel:
    """Test suite for get_senior_developer_model function."""
    
    def test_valid_model_returned(self, monkeypatch):
        """Test that valid model configuration is returned."""
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-4o-mini")
        assert get_senior_developer_model() == "gpt-4o-mini"
    
    def test_empty_string_returns_none(self, monkeypatch):
        """Test that empty configuration returns None."""
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "")
        assert get_senior_developer_model() is None
    
    def test_whitespace_only_returns_none(self, monkeypatch):
        """Test that whitespace-only configuration returns None."""
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "   ")
        assert get_senior_developer_model() is None
    
    def test_missing_config_returns_none(self, monkeypatch):
        """Test that missing configuration returns None."""
        monkeypatch.delenv("SENIOR_DEVELOPER_MODEL", raising=False)
        assert get_senior_developer_model() is None


class TestGetSecurityEngineerModel:
    """Test suite for get_security_engineer_model function."""
    
    def test_valid_model_returned(self, monkeypatch):
        """Test that valid model configuration is returned."""
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-4o")
        assert get_security_engineer_model() == "gpt-4o"
    
    def test_empty_string_returns_none(self, monkeypatch):
        """Test that empty configuration returns None."""
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "")
        assert get_security_engineer_model() is None
    
    def test_whitespace_only_returns_none(self, monkeypatch):
        """Test that whitespace-only configuration returns None."""
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "  \t  ")
        assert get_security_engineer_model() is None
    
    def test_missing_config_returns_none(self, monkeypatch):
        """Test that missing configuration returns None."""
        monkeypatch.delenv("SECURITY_ENGINEER_MODEL", raising=False)
        assert get_security_engineer_model() is None


class TestGetTechLeadModel:
    """Test suite for get_tech_lead_model function."""
    
    def test_valid_model_returned(self, monkeypatch):
        """Test that valid model configuration is returned."""
        monkeypatch.setenv("TECH_LEAD_MODEL", "gpt-3.5-turbo")
        assert get_tech_lead_model() == "gpt-3.5-turbo"
    
    def test_empty_string_returns_none(self, monkeypatch):
        """Test that empty configuration returns None."""
        monkeypatch.setenv("TECH_LEAD_MODEL", "")
        assert get_tech_lead_model() is None
    
    def test_whitespace_only_returns_none(self, monkeypatch):
        """Test that whitespace-only configuration returns None."""
        monkeypatch.setenv("TECH_LEAD_MODEL", "\n\t  ")
        assert get_tech_lead_model() is None
    
    def test_missing_config_returns_none(self, monkeypatch):
        """Test that missing configuration returns None."""
        monkeypatch.delenv("TECH_LEAD_MODEL", raising=False)
        assert get_tech_lead_model() is None


class TestMultipleAgentConfigurations:
    """Test suite for multiple agent configurations working independently."""
    
    def test_different_models_for_different_agents(self, monkeypatch):
        """Test that different agents can have different models."""
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-4o")
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("TECH_LEAD_MODEL", "gpt-3.5-turbo")
        
        assert get_senior_developer_model() == "gpt-4o"
        assert get_security_engineer_model() == "gpt-4o-mini"
        assert get_tech_lead_model() == "gpt-3.5-turbo"
    
    def test_some_configured_some_not(self, monkeypatch):
        """Test that some agents can be configured while others are not."""
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-4o")
        monkeypatch.delenv("SECURITY_ENGINEER_MODEL", raising=False)
        monkeypatch.setenv("TECH_LEAD_MODEL", "")
        
        assert get_senior_developer_model() == "gpt-4o"
        assert get_security_engineer_model() is None
        assert get_tech_lead_model() is None
