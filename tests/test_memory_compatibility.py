"""Unit tests for memory compatibility functions."""

import os
import pytest
from unittest.mock import patch
from agentic_code_review.utils import (
    is_model_memory_compatible,
    check_crew_memory_compatibility,
    MEMORY_INCOMPATIBLE_MODELS,
)


class TestIsModelMemoryCompatible:
    """Test is_model_memory_compatible function."""
    
    def test_compatible_models(self):
        """Test that standard models are compatible."""
        assert is_model_memory_compatible("gpt-4o") is True
        assert is_model_memory_compatible("gpt-4o-mini") is True
        assert is_model_memory_compatible("gpt-4-turbo") is True
        assert is_model_memory_compatible("gpt-3.5-turbo") is True
    
    def test_incompatible_codex_models(self):
        """Test that codex models are incompatible."""
        assert is_model_memory_compatible("gpt-5-codex") is False
        assert is_model_memory_compatible("gpt-5.1-codex-mini") is False
        assert is_model_memory_compatible("gpt-5.1-codex") is False
        assert is_model_memory_compatible("openai-codex") is False
    
    def test_none_and_empty_string(self):
        """Test that None and empty string are treated as compatible."""
        assert is_model_memory_compatible(None) is True
        assert is_model_memory_compatible("") is True
        assert is_model_memory_compatible("   ") is True
    
    def test_case_insensitive_matching(self):
        """Test that matching is case-insensitive."""
        assert is_model_memory_compatible("GPT-5-CODEX") is False
        assert is_model_memory_compatible("Gpt-5-Codex") is False
        assert is_model_memory_compatible("gpt-5-CODEX") is False
        assert is_model_memory_compatible("CODEX") is False
        assert is_model_memory_compatible("Codex") is False
        assert is_model_memory_compatible("codex") is False


class TestCheckCrewMemoryCompatibility:
    """Test check_crew_memory_compatibility function."""
    
    def test_all_compatible_models(self):
        """Test with all compatible models configured."""
        with patch.dict(os.environ, {
            "SENIOR_DEVELOPER_MODEL": "gpt-4o",
            "SECURITY_ENGINEER_MODEL": "gpt-4o-mini",
            "TECH_LEAD_MODEL": "gpt-4-turbo",
        }, clear=False):
            is_compatible, incompatible = check_crew_memory_compatibility()
            assert is_compatible is True
            assert incompatible == []
    
    def test_one_incompatible_model(self):
        """Test with one incompatible model."""
        with patch.dict(os.environ, {
            "SENIOR_DEVELOPER_MODEL": "gpt-5-codex",
            "SECURITY_ENGINEER_MODEL": "gpt-4o-mini",
            "TECH_LEAD_MODEL": "gpt-4-turbo",
        }, clear=False):
            is_compatible, incompatible = check_crew_memory_compatibility()
            assert is_compatible is False
            assert "gpt-5-codex" in incompatible
            assert len(incompatible) == 1
    
    def test_multiple_incompatible_models(self):
        """Test with multiple incompatible models."""
        with patch.dict(os.environ, {
            "SENIOR_DEVELOPER_MODEL": "gpt-5-codex",
            "SECURITY_ENGINEER_MODEL": "gpt-5.1-codex-mini",
            "TECH_LEAD_MODEL": "gpt-4-turbo",
        }, clear=False):
            is_compatible, incompatible = check_crew_memory_compatibility()
            assert is_compatible is False
            assert "gpt-5-codex" in incompatible
            assert "gpt-5.1-codex-mini" in incompatible
            assert len(incompatible) == 2
    
    def test_no_configured_models(self):
        """Test with no models configured (all None)."""
        # Explicitly set all model variables to empty strings
        with patch.dict(os.environ, {
            "SENIOR_DEVELOPER_MODEL": "",
            "SECURITY_ENGINEER_MODEL": "",
            "TECH_LEAD_MODEL": "",
        }, clear=False):
            is_compatible, incompatible = check_crew_memory_compatibility()
            assert is_compatible is True
            assert incompatible == []
    
    def test_mixed_none_and_compatible(self):
        """Test with some None and some compatible models."""
        with patch.dict(os.environ, {
            "SENIOR_DEVELOPER_MODEL": "gpt-4o",
            "SECURITY_ENGINEER_MODEL": "",
            "TECH_LEAD_MODEL": "",
        }, clear=False):
            is_compatible, incompatible = check_crew_memory_compatibility()
            assert is_compatible is True
            assert incompatible == []
    
    def test_mixed_none_and_incompatible(self):
        """Test with some None and some incompatible models."""
        with patch.dict(os.environ, {
            "SENIOR_DEVELOPER_MODEL": "",
            "SECURITY_ENGINEER_MODEL": "gpt-5-codex",
            "TECH_LEAD_MODEL": "",
        }, clear=False):
            is_compatible, incompatible = check_crew_memory_compatibility()
            assert is_compatible is False
            assert "gpt-5-codex" in incompatible
            assert len(incompatible) == 1
