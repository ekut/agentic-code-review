"""
Integration tests for memory compatibility with full crew execution.

These tests verify that memory compatibility checking works correctly in the context
of the full code review flow, including:
- Full crew execution with all compatible models (memory enabled)
- Full crew execution with incompatible model (memory disabled)
- Mixed configuration (some agents with compatible, some with incompatible)
- Crew completes successfully with memory disabled
- Logging output is correct
- Memory components are only added when memory is enabled

**Validates: Requirements 1.1, 1.2, 1.4, 1.5, 4.1, 4.2**
"""

import os
import tempfile
import logging
from unittest.mock import patch, MagicMock

import pytest

from agentic_code_review.crews.code_review_crew.crew import CodeReviewCrew
from agentic_code_review.utils import (
    get_senior_developer_model,
    get_security_engineer_model,
    get_tech_lead_model,
    check_crew_memory_compatibility
)


class TestFullCrewExecutionWithCompatibleModels:
    """Test full crew execution with all compatible models (memory enabled)."""
    
    def test_crew_execution_with_all_compatible_models(self, monkeypatch, caplog):
        """
        Test that the crew executes successfully with all compatible models
        and memory is enabled.
        
        **Validates: Requirements 1.1, 4.1**
        """
        # Configure all agents with compatible models
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-4o")
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("TECH_LEAD_MODEL", "gpt-4-turbo")
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        # Verify configuration
        assert get_senior_developer_model() == "gpt-4o"
        assert get_security_engineer_model() == "gpt-4o-mini"
        assert get_tech_lead_model() == "gpt-4-turbo"
        
        # Verify compatibility check returns True
        is_compatible, incompatible = check_crew_memory_compatibility()
        assert is_compatible is True
        assert incompatible == []
        
        # Clear logs
        caplog.clear()
        
        with caplog.at_level(logging.WARNING):
            # Create the crew
            crew_instance = CodeReviewCrew()
            crew = crew_instance.crew()
            
            # Verify memory is enabled
            assert crew.memory is True, "Memory should be enabled with all compatible models"
            
            # Verify no warning was logged
            memory_warnings = [
                record for record in caplog.records
                if "CrewAI memory disabled" in record.message
            ]
            assert len(memory_warnings) == 0, "No memory warnings should be logged with compatible models"
    
    def test_crew_kickoff_with_compatible_models(self, monkeypatch, caplog):
        """
        Test that the crew can kickoff successfully with compatible models
        and memory enabled.
        
        **Validates: Requirements 1.1, 4.1, 4.2**
        """
        # Configure compatible models
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-4o")
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("TECH_LEAD_MODEL", "gpt-4-turbo")
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        caplog.clear()
        
        with caplog.at_level(logging.WARNING):
            # Create the crew
            crew_instance = CodeReviewCrew()
            crew = crew_instance.crew()
            
            # Verify memory is enabled
            assert crew.memory is True
            
            # Verify the crew has the expected structure for kickoff
            assert hasattr(crew, 'kickoff'), "Crew should have kickoff method"
            assert callable(crew.kickoff), "kickoff should be callable"
            
            # Verify crew is properly configured for execution
            assert len(crew.agents) == 3, "Crew should have 3 agents"
            assert len(crew.tasks) == 3, "Crew should have 3 tasks"


class TestFullCrewExecutionWithIncompatibleModel:
    """Test full crew execution with incompatible model (memory disabled)."""
    
    def test_crew_execution_with_one_incompatible_model(self, monkeypatch, caplog):
        """
        Test that the crew executes successfully with one incompatible model
        and memory is disabled.
        
        **Validates: Requirements 1.2, 1.4, 4.1**
        """
        # Configure one agent with incompatible model
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-5-codex")
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("TECH_LEAD_MODEL", "gpt-4-turbo")
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        # Verify configuration
        assert get_senior_developer_model() == "gpt-5-codex"
        
        # Verify compatibility check returns False
        is_compatible, incompatible = check_crew_memory_compatibility()
        assert is_compatible is False
        assert "gpt-5-codex" in incompatible
        
        # Clear logs
        caplog.clear()
        
        with caplog.at_level(logging.WARNING):
            # Create the crew
            crew_instance = CodeReviewCrew()
            crew = crew_instance.crew()
            
            # Verify memory is disabled
            assert crew.memory is False, "Memory should be disabled with incompatible model"
            
            # Verify warning was logged
            memory_warnings = [
                record for record in caplog.records
                if "CrewAI memory disabled" in record.message
            ]
            assert len(memory_warnings) > 0, "Memory warning should be logged"
            
            # Verify warning contains the incompatible model name
            warning_message = memory_warnings[0].message
            assert "gpt-5-codex" in warning_message
            assert "docs/TROUBLESHOOTING.md" in warning_message
    
    def test_crew_completes_successfully_with_memory_disabled(self, monkeypatch, caplog):
        """
        Test that the crew completes successfully even with memory disabled.
        
        **Validates: Requirements 1.5, 4.2**
        """
        # Configure incompatible model
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-5-codex")
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("TECH_LEAD_MODEL", "gpt-4-turbo")
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        caplog.clear()
        
        with caplog.at_level(logging.WARNING):
            # Create the crew
            crew_instance = CodeReviewCrew()
            crew = crew_instance.crew()
            
            # Verify memory is disabled
            assert crew.memory is False
            
            # Verify the crew can still be used for execution
            assert hasattr(crew, 'kickoff'), "Crew should have kickoff method even with memory disabled"
            assert callable(crew.kickoff), "kickoff should be callable even with memory disabled"
            
            # Verify crew structure is intact
            assert len(crew.agents) == 3, "Crew should have 3 agents even with memory disabled"
            assert len(crew.tasks) == 3, "Crew should have 3 tasks even with memory disabled"
            
            # Verify the crew is properly configured for execution
            assert crew.process.value == "sequential", "Process should be sequential"
            assert crew.verbose is True, "Verbose should be enabled"
    
    def test_crew_with_all_incompatible_models(self, monkeypatch, caplog):
        """
        Test that the crew works when all agents have incompatible models.
        
        **Validates: Requirements 1.2, 1.4, 1.5**
        """
        # Configure all agents with incompatible models
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-5-codex")
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-5.1-codex-mini")
        monkeypatch.setenv("TECH_LEAD_MODEL", "openai-codex")
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        # Verify compatibility check
        is_compatible, incompatible = check_crew_memory_compatibility()
        assert is_compatible is False
        assert len(incompatible) == 3
        
        caplog.clear()
        
        with caplog.at_level(logging.WARNING):
            # Create the crew
            crew_instance = CodeReviewCrew()
            crew = crew_instance.crew()
            
            # Verify memory is disabled
            assert crew.memory is False
            
            # Verify warning was logged with all incompatible models
            memory_warnings = [
                record for record in caplog.records
                if "CrewAI memory disabled" in record.message
            ]
            assert len(memory_warnings) > 0
            
            warning_message = memory_warnings[0].message
            # At least one of the incompatible models should be mentioned
            assert any(model in warning_message for model in incompatible)


class TestMixedConfiguration:
    """Test mixed configuration (some agents with compatible, some with incompatible)."""
    
    def test_crew_with_mixed_compatible_and_incompatible(self, monkeypatch, caplog):
        """
        Test that memory is disabled when mixing compatible and incompatible models.
        
        **Validates: Requirements 1.2, 1.4**
        """
        # Configure mixed models
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-4o")  # Compatible
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-5-codex")  # Incompatible
        monkeypatch.setenv("TECH_LEAD_MODEL", "gpt-4-turbo")  # Compatible
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        # Verify compatibility check
        is_compatible, incompatible = check_crew_memory_compatibility()
        assert is_compatible is False
        assert "gpt-5-codex" in incompatible
        assert len(incompatible) == 1
        
        caplog.clear()
        
        with caplog.at_level(logging.WARNING):
            # Create the crew
            crew_instance = CodeReviewCrew()
            crew = crew_instance.crew()
            
            # Verify memory is disabled (one incompatible model disables memory for all)
            assert crew.memory is False
            
            # Verify warning was logged
            memory_warnings = [
                record for record in caplog.records
                if "CrewAI memory disabled" in record.message
            ]
            assert len(memory_warnings) > 0
            assert "gpt-5-codex" in memory_warnings[0].message
    
    def test_crew_with_mixed_configured_and_default(self, monkeypatch, caplog):
        """
        Test that memory works correctly when mixing configured and default models.
        
        **Validates: Requirements 1.1, 4.1**
        """
        # Configure only some agents (others use defaults)
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-4o")
        monkeypatch.delenv("SECURITY_ENGINEER_MODEL", raising=False)
        monkeypatch.delenv("TECH_LEAD_MODEL", raising=False)
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        # Verify configuration
        assert get_senior_developer_model() == "gpt-4o"
        assert get_security_engineer_model() is None
        assert get_tech_lead_model() is None
        
        # Verify compatibility check (defaults are compatible)
        is_compatible, incompatible = check_crew_memory_compatibility()
        assert is_compatible is True
        assert incompatible == []
        
        caplog.clear()
        
        with caplog.at_level(logging.WARNING):
            # Create the crew
            crew_instance = CodeReviewCrew()
            crew = crew_instance.crew()
            
            # Verify memory is enabled
            assert crew.memory is True
            
            # Verify no warning was logged
            memory_warnings = [
                record for record in caplog.records
                if "CrewAI memory disabled" in record.message
            ]
            assert len(memory_warnings) == 0
    
    def test_crew_with_one_incompatible_and_defaults(self, monkeypatch, caplog):
        """
        Test that one incompatible model disables memory even with defaults.
        
        **Validates: Requirements 1.2, 1.4**
        """
        # Configure one incompatible, others use defaults
        monkeypatch.delenv("SENIOR_DEVELOPER_MODEL", raising=False)
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-5-codex")
        monkeypatch.delenv("TECH_LEAD_MODEL", raising=False)
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        # Verify compatibility check
        is_compatible, incompatible = check_crew_memory_compatibility()
        assert is_compatible is False
        assert "gpt-5-codex" in incompatible
        
        caplog.clear()
        
        with caplog.at_level(logging.WARNING):
            # Create the crew
            crew_instance = CodeReviewCrew()
            crew = crew_instance.crew()
            
            # Verify memory is disabled
            assert crew.memory is False
            
            # Verify warning was logged
            memory_warnings = [
                record for record in caplog.records
                if "CrewAI memory disabled" in record.message
            ]
            assert len(memory_warnings) > 0


class TestLoggingOutput:
    """Test that logging output is correct."""
    
    def test_warning_message_format(self, monkeypatch, caplog):
        """
        Test that the warning message has the correct format.
        
        **Validates: Requirements 1.4**
        """
        # Configure incompatible model
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-5-codex")
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("TECH_LEAD_MODEL", "gpt-4-turbo")
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        caplog.clear()
        
        with caplog.at_level(logging.WARNING):
            # Create the crew
            crew_instance = CodeReviewCrew()
            crew = crew_instance.crew()
            
            # Find the memory warning
            memory_warnings = [
                record for record in caplog.records
                if "CrewAI memory disabled" in record.message
            ]
            
            assert len(memory_warnings) > 0
            warning_message = memory_warnings[0].message
            
            # Verify message format
            assert "CrewAI memory disabled" in warning_message
            assert "gpt-5-codex" in warning_message
            assert "incompatible with CrewAI memory" in warning_message
            assert "function normally without memory features" in warning_message
            assert "docs/TROUBLESHOOTING.md" in warning_message
    
    def test_warning_deduplicates_model_names(self, monkeypatch, caplog):
        """
        Test that duplicate model names are deduplicated in the warning message.
        
        **Validates: Requirements 1.4**
        """
        # Configure multiple agents with the same incompatible model
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-5-codex")
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-5-codex")
        monkeypatch.setenv("TECH_LEAD_MODEL", "gpt-5-codex")
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        caplog.clear()
        
        with caplog.at_level(logging.WARNING):
            # Create the crew
            crew_instance = CodeReviewCrew()
            crew = crew_instance.crew()
            
            # Find the memory warning
            memory_warnings = [
                record for record in caplog.records
                if "CrewAI memory disabled" in record.message
            ]
            
            assert len(memory_warnings) > 0
            warning_message = memory_warnings[0].message
            
            # Count occurrences of the model name
            count = warning_message.count("gpt-5-codex")
            
            # Should appear only once (deduplicated)
            assert count == 1, f"Model name should appear only once, but appeared {count} times"
    
    def test_no_warning_with_compatible_models(self, monkeypatch, caplog):
        """
        Test that no warning is logged when all models are compatible.
        
        **Validates: Requirements 1.1**
        """
        # Configure all compatible models
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-4o")
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("TECH_LEAD_MODEL", "gpt-4-turbo")
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        caplog.clear()
        
        with caplog.at_level(logging.WARNING):
            # Create the crew
            crew_instance = CodeReviewCrew()
            crew = crew_instance.crew()
            
            # Verify no memory warnings
            memory_warnings = [
                record for record in caplog.records
                if "CrewAI memory disabled" in record.message
            ]
            
            assert len(memory_warnings) == 0, "No warnings should be logged with compatible models"
    
    def test_warning_logged_at_warning_level(self, monkeypatch, caplog):
        """
        Test that the memory compatibility message is logged at WARNING level.
        
        **Validates: Requirements 1.4**
        """
        # Configure incompatible model
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-5-codex")
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("TECH_LEAD_MODEL", "gpt-4-turbo")
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        caplog.clear()
        
        with caplog.at_level(logging.WARNING):
            # Create the crew
            crew_instance = CodeReviewCrew()
            crew = crew_instance.crew()
            
            # Find the memory warning
            memory_warnings = [
                record for record in caplog.records
                if "CrewAI memory disabled" in record.message
            ]
            
            assert len(memory_warnings) > 0
            
            # Verify it's logged at WARNING level
            assert memory_warnings[0].levelname == "WARNING"


class TestMemoryComponentsOnlyAddedWhenEnabled:
    """Test that memory components are only added when memory is enabled."""
    
    def test_memory_enabled_with_compatible_models(self, monkeypatch):
        """
        Test that memory is enabled when all models are compatible.
        
        **Validates: Requirements 1.1, 4.1**
        """
        # Configure compatible models
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-4o")
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("TECH_LEAD_MODEL", "gpt-4-turbo")
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        # Create the crew
        crew_instance = CodeReviewCrew()
        crew = crew_instance.crew()
        
        # Verify memory is enabled
        assert crew.memory is True, "Memory should be enabled with compatible models"
    
    def test_memory_disabled_with_incompatible_models(self, monkeypatch):
        """
        Test that memory is disabled when any model is incompatible.
        
        **Validates: Requirements 1.2, 4.1**
        """
        # Configure incompatible model
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-5-codex")
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("TECH_LEAD_MODEL", "gpt-4-turbo")
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        # Create the crew
        crew_instance = CodeReviewCrew()
        crew = crew_instance.crew()
        
        # Verify memory is disabled
        assert crew.memory is False, "Memory should be disabled with incompatible model"
    
    def test_memory_enabled_with_no_configuration(self, monkeypatch):
        """
        Test that memory is enabled when no models are configured (defaults).
        
        **Validates: Requirements 1.1, 4.1**
        """
        # Ensure no configuration
        monkeypatch.delenv("SENIOR_DEVELOPER_MODEL", raising=False)
        monkeypatch.delenv("SECURITY_ENGINEER_MODEL", raising=False)
        monkeypatch.delenv("TECH_LEAD_MODEL", raising=False)
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        # Create the crew
        crew_instance = CodeReviewCrew()
        crew = crew_instance.crew()
        
        # Verify memory is enabled (defaults are compatible)
        assert crew.memory is True, "Memory should be enabled with default configuration"
    
    def test_memory_setting_reflects_compatibility_check(self, monkeypatch):
        """
        Test that the crew's memory setting matches the compatibility check result.
        
        **Validates: Requirements 1.1, 1.2, 4.1**
        """
        # Test with compatible models
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-4o")
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("TECH_LEAD_MODEL", "gpt-4-turbo")
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        is_compatible, _ = check_crew_memory_compatibility()
        crew_instance = CodeReviewCrew()
        crew = crew_instance.crew()
        
        assert crew.memory == is_compatible, "Crew memory should match compatibility check"
        
        # Test with incompatible model
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-5-codex")
        
        is_compatible, _ = check_crew_memory_compatibility()
        crew_instance = CodeReviewCrew()
        crew = crew_instance.crew()
        
        assert crew.memory == is_compatible, "Crew memory should match compatibility check"


class TestBackwardCompatibility:
    """Test backward compatibility with existing functionality."""
    
    def test_crew_creation_without_memory_configuration(self, monkeypatch):
        """
        Test that crew creation works without any memory-related configuration.
        
        **Validates: Requirements 1.5**
        """
        # Ensure no configuration
        monkeypatch.delenv("SENIOR_DEVELOPER_MODEL", raising=False)
        monkeypatch.delenv("SECURITY_ENGINEER_MODEL", raising=False)
        monkeypatch.delenv("TECH_LEAD_MODEL", raising=False)
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        # Create the crew - should work without errors
        crew_instance = CodeReviewCrew()
        crew = crew_instance.crew()
        
        # Verify crew was created successfully
        assert crew is not None
        assert crew.memory is True  # Default behavior
        assert len(crew.agents) == 3
        assert len(crew.tasks) == 3
    
    def test_existing_crew_functionality_preserved(self, monkeypatch):
        """
        Test that existing crew functionality is preserved with memory compatibility.
        
        **Validates: Requirements 1.5**
        """
        # Configure models
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-4o")
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("TECH_LEAD_MODEL", "gpt-4-turbo")
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        # Create the crew
        crew_instance = CodeReviewCrew()
        crew = crew_instance.crew()
        
        # Verify all existing functionality is preserved
        assert crew.verbose is True
        assert crew.process.value == "sequential"
        assert len(crew.agents) == 3
        assert len(crew.tasks) == 3
        
        # Verify agents have correct roles (strip whitespace from roles)
        agent_roles = [agent.role.strip() for agent in crew.agents]
        assert "Senior Developer" in agent_roles
        assert "Security Engineer" in agent_roles
        assert "Tech Lead" in agent_roles
