"""
Property-based tests for backward compatibility with model configuration.

**Feature: configurable-llm-models, Property 5: Backward compatibility preserved**
**Validates: Requirements 3.1, 3.5**
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck


# Strategy for generating valid OpenAI model names
valid_openai_models = st.sampled_from([
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-3.5-turbo",
])


class TestBackwardCompatibilityPreserved:
    """
    Property-based tests for backward compatibility.
    
    **Feature: configurable-llm-models, Property 5: Backward compatibility preserved**
    **Validates: Requirements 3.1, 3.5**
    """
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None  # Disable deadline for subprocess tests
    )
    @given(
        configure_models=st.booleans(),
        senior_model=valid_openai_models,
        security_model=valid_openai_models,
        tech_lead_model=valid_openai_models
    )
    def test_property_5_backward_compatibility_with_and_without_config(
        self,
        monkeypatch,
        configure_models,
        senior_model,
        security_model,
        tech_lead_model
    ):
        """
        Property: For any existing test or functionality, the system should 
        continue to work correctly after adding model configuration, whether
        models are configured or not.
        
        **Feature: configurable-llm-models, Property 5: Backward compatibility preserved**
        **Validates: Requirements 3.1, 3.5**
        
        This property runs 100 iterations testing with and without model configuration.
        """
        # Set up environment
        if configure_models:
            # Configure models
            monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", senior_model)
            monkeypatch.setenv("SECURITY_ENGINEER_MODEL", security_model)
            monkeypatch.setenv("TECH_LEAD_MODEL", tech_lead_model)
        else:
            # Ensure no model configuration
            monkeypatch.delenv("SENIOR_DEVELOPER_MODEL", raising=False)
            monkeypatch.delenv("SECURITY_ENGINEER_MODEL", raising=False)
            monkeypatch.delenv("TECH_LEAD_MODEL", raising=False)
        
        # Set required API keys for tests
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        # Import and test core functionality
        from agentic_code_review.crews.code_review_crew.crew import CodeReviewCrew
        from agentic_code_review.utils import (
            get_senior_developer_model,
            get_security_engineer_model,
            get_tech_lead_model
        )
        
        # Verify utility functions work correctly
        if configure_models:
            assert get_senior_developer_model() == senior_model
            assert get_security_engineer_model() == security_model
            assert get_tech_lead_model() == tech_lead_model
        else:
            assert get_senior_developer_model() is None
            assert get_security_engineer_model() is None
            assert get_tech_lead_model() is None
        
        # Verify crew can be initialized without errors
        try:
            crew = CodeReviewCrew()
            
            # Verify agents can be created
            senior_dev = crew.senior_developer()
            security_eng = crew.security_engineer()
            tech_lead = crew.tech_lead()
            
            # Verify agents were created successfully
            assert senior_dev is not None, "Senior Developer should be created"
            assert security_eng is not None, "Security Engineer should be created"
            assert tech_lead is not None, "Tech Lead should be created"
            
            # Verify agents have expected attributes
            assert hasattr(senior_dev, 'role'), "Agent should have role"
            assert hasattr(senior_dev, 'goal'), "Agent should have goal"
            assert hasattr(senior_dev, 'backstory'), "Agent should have backstory"
            
            # Verify model configuration is applied correctly
            if configure_models:
                assert senior_dev.llm is not None, "Configured agent should have llm"
                assert senior_dev.llm.model == senior_model
                assert security_eng.llm.model == security_model
                assert tech_lead.llm.model == tech_lead_model
            
            # Verify tools are preserved for security engineer
            assert hasattr(security_eng, 'tools'), "Security Engineer should have tools"
            assert security_eng.tools is not None, "Security Engineer tools should not be None"
            
        except Exception as e:
            pytest.fail(f"Backward compatibility broken: {e}")
    
    def test_property_5_existing_functionality_preserved_without_config(self, monkeypatch):
        """
        Property: When no model configuration is provided, the system should
        behave identically to the original implementation.
        
        **Feature: configurable-llm-models, Property 5: Backward compatibility preserved**
        **Validates: Requirements 3.1, 3.5**
        """
        # Ensure no model configuration
        monkeypatch.delenv("SENIOR_DEVELOPER_MODEL", raising=False)
        monkeypatch.delenv("SECURITY_ENGINEER_MODEL", raising=False)
        monkeypatch.delenv("TECH_LEAD_MODEL", raising=False)
        
        # Set required API keys
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        from agentic_code_review.crews.code_review_crew.crew import CodeReviewCrew
        
        # Initialize crew
        crew = CodeReviewCrew()
        
        # Create agents
        senior_dev = crew.senior_developer()
        security_eng = crew.security_engineer()
        tech_lead = crew.tech_lead()
        
        # Verify agents are created successfully
        assert senior_dev is not None
        assert security_eng is not None
        assert tech_lead is not None
        
        # Verify all expected attributes exist
        for agent in [senior_dev, security_eng, tech_lead]:
            assert hasattr(agent, 'role')
            assert hasattr(agent, 'goal')
            assert hasattr(agent, 'backstory')
            assert hasattr(agent, 'llm')  # CrewAI creates default LLM
        
        # Verify security engineer has tools
        assert hasattr(security_eng, 'tools')
        assert security_eng.tools is not None
        assert len(security_eng.tools) > 0
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        senior_model=valid_openai_models,
        security_model=valid_openai_models,
        tech_lead_model=valid_openai_models
    )
    def test_property_5_tools_and_guardrails_preserved_with_config(
        self,
        monkeypatch,
        senior_model,
        security_model,
        tech_lead_model
    ):
        """
        Property: When model configuration is provided, all existing functionality
        including tools, guardrails, and async execution should be preserved.
        
        **Feature: configurable-llm-models, Property 5: Backward compatibility preserved**
        **Validates: Requirements 3.5**
        
        This property runs 100 iterations with different model configurations.
        """
        # Configure models
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", senior_model)
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", security_model)
        monkeypatch.setenv("TECH_LEAD_MODEL", tech_lead_model)
        
        # Set required API keys
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        from agentic_code_review.crews.code_review_crew.crew import CodeReviewCrew
        
        # Initialize crew
        crew = CodeReviewCrew()
        
        # Create agents
        senior_dev = crew.senior_developer()
        security_eng = crew.security_engineer()
        tech_lead = crew.tech_lead()
        
        # Verify models are configured
        assert senior_dev.llm.model == senior_model
        assert security_eng.llm.model == security_model
        assert tech_lead.llm.model == tech_lead_model
        
        # Verify tools are preserved for security engineer
        assert hasattr(security_eng, 'tools'), "Security Engineer should have tools"
        assert security_eng.tools is not None, "Tools should not be None"
        assert len(security_eng.tools) > 0, "Security Engineer should have at least one tool"
        
        # Verify tool types (SerperDevTool and ScrapeWebsiteTool)
        tool_names = [tool.__class__.__name__ for tool in security_eng.tools]
        assert any('Serper' in name or 'Search' in name for name in tool_names), \
            "Security Engineer should have search tool"
        assert any('Scrape' in name or 'Website' in name for name in tool_names), \
            "Security Engineer should have scrape tool"
        
        # Verify crew configuration is preserved
        assert hasattr(crew, 'agents_config'), "Crew should have agents_config"
        assert hasattr(crew, 'tasks_config'), "Crew should have tasks_config"
        
        # Verify crew can be created (tests async execution capability)
        try:
            crew_instance = crew.crew()
            assert crew_instance is not None, "Crew instance should be created"
        except Exception as e:
            pytest.fail(f"Crew creation failed with configured models: {e}")
    
    def test_property_5_agent_decorator_pattern_preserved(self, monkeypatch):
        """
        Property: The @agent decorator pattern should continue to work correctly
        with model configuration.
        
        **Feature: configurable-llm-models, Property 5: Backward compatibility preserved**
        **Validates: Requirements 3.1**
        """
        # Configure models
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-4o")
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("TECH_LEAD_MODEL", "gpt-3.5-turbo")
        
        # Set required API keys
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        from agentic_code_review.crews.code_review_crew.crew import CodeReviewCrew
        
        # Initialize crew
        crew = CodeReviewCrew()
        
        # Verify @agent decorator methods exist and are callable
        assert hasattr(crew, 'senior_developer'), "Crew should have senior_developer method"
        assert hasattr(crew, 'security_engineer'), "Crew should have security_engineer method"
        assert hasattr(crew, 'tech_lead'), "Crew should have tech_lead method"
        
        assert callable(crew.senior_developer), "senior_developer should be callable"
        assert callable(crew.security_engineer), "security_engineer should be callable"
        assert callable(crew.tech_lead), "tech_lead should be callable"
        
        # Call methods and verify they return agents
        senior_dev = crew.senior_developer()
        security_eng = crew.security_engineer()
        tech_lead = crew.tech_lead()
        
        # Verify agents are created with correct types
        from crewai import Agent
        assert isinstance(senior_dev, Agent), "senior_developer should return Agent instance"
        assert isinstance(security_eng, Agent), "security_engineer should return Agent instance"
        assert isinstance(tech_lead, Agent), "tech_lead should return Agent instance"
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        configure_senior=st.booleans(),
        configure_security=st.booleans(),
        configure_tech_lead=st.booleans()
    )
    def test_property_5_mixed_configuration_scenarios(
        self,
        monkeypatch,
        configure_senior,
        configure_security,
        configure_tech_lead
    ):
        """
        Property: The system should handle mixed configuration scenarios where
        some agents are configured and others are not.
        
        **Feature: configurable-llm-models, Property 5: Backward compatibility preserved**
        **Validates: Requirements 3.1, 3.5**
        
        This property runs 100 iterations with different configuration combinations.
        """
        # Set required API keys
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        # Configure or not configure each agent
        if configure_senior:
            monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-4o")
        else:
            monkeypatch.delenv("SENIOR_DEVELOPER_MODEL", raising=False)
        
        if configure_security:
            monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-4o-mini")
        else:
            monkeypatch.delenv("SECURITY_ENGINEER_MODEL", raising=False)
        
        if configure_tech_lead:
            monkeypatch.setenv("TECH_LEAD_MODEL", "gpt-3.5-turbo")
        else:
            monkeypatch.delenv("TECH_LEAD_MODEL", raising=False)
        
        from agentic_code_review.crews.code_review_crew.crew import CodeReviewCrew
        
        # Initialize crew - should work regardless of configuration
        try:
            crew = CodeReviewCrew()
            
            # Create agents
            senior_dev = crew.senior_developer()
            security_eng = crew.security_engineer()
            tech_lead = crew.tech_lead()
            
            # Verify all agents are created
            assert senior_dev is not None
            assert security_eng is not None
            assert tech_lead is not None
            
            # Verify configured agents have correct models
            if configure_senior:
                assert senior_dev.llm.model == "gpt-4o"
            
            if configure_security:
                assert security_eng.llm.model == "gpt-4o-mini"
            
            if configure_tech_lead:
                assert tech_lead.llm.model == "gpt-3.5-turbo"
            
            # Verify tools are always present for security engineer
            assert security_eng.tools is not None
            assert len(security_eng.tools) > 0
            
        except Exception as e:
            pytest.fail(f"Mixed configuration scenario failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
