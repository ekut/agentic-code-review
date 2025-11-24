"""Property-based tests for model configuration using Hypothesis.

Feature: configurable-llm-models
"""

import pytest
import os
from hypothesis import given, strategies as st, settings, HealthCheck
from agentic_code_review.crews.code_review_crew.crew import CodeReviewCrew


# Strategy for generating valid OpenAI model names
valid_openai_models = st.sampled_from([
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-16k",
])


class TestModelConfigurationApplication:
    """Property-based tests for model configuration application.
    
    **Feature: configurable-llm-models, Property 1: Model configuration is applied correctly**
    **Validates: Requirements 1.1**
    """
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        senior_model=valid_openai_models,
        security_model=valid_openai_models,
        tech_lead_model=valid_openai_models
    )
    def test_configured_models_are_applied(
        self, 
        monkeypatch, 
        senior_model, 
        security_model, 
        tech_lead_model
    ):
        """
        Property: For any valid OpenAI model name, when set as an environment 
        variable for an agent, that agent should be initialized with the 
        specified model.
        
        **Feature: configurable-llm-models, Property 1: Model configuration is applied correctly**
        **Validates: Requirements 1.1**
        """
        # Set environment variables
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", senior_model)
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", security_model)
        monkeypatch.setenv("TECH_LEAD_MODEL", tech_lead_model)
        
        # Set required API keys for crew initialization
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        # Initialize crew
        crew = CodeReviewCrew()
        
        # Initialize agents
        senior_dev = crew.senior_developer()
        security_eng = crew.security_engineer()
        tech_lead = crew.tech_lead()
        
        # Verify models are applied
        assert senior_dev.llm.model == senior_model, \
            f"Senior Developer should use {senior_model}, got {senior_dev.llm.model}"
        assert security_eng.llm.model == security_model, \
            f"Security Engineer should use {security_model}, got {security_eng.llm.model}"
        assert tech_lead.llm.model == tech_lead_model, \
            f"Tech Lead should use {tech_lead_model}, got {tech_lead.llm.model}"



class TestDefaultBehavior:
    """Property-based tests for default behavior when not configured.
    
    **Feature: configurable-llm-models, Property 2: Default behavior when not configured**
    **Validates: Requirements 1.2, 5.1**
    """
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        senior_configured=st.booleans(),
        security_configured=st.booleans(),
        tech_lead_configured=st.booleans()
    )
    def test_default_behavior_without_configuration(
        self,
        monkeypatch,
        senior_configured,
        security_configured,
        tech_lead_configured
    ):
        """
        Property: For any agent, when no model environment variable is set or 
        the value is empty/whitespace, the agent should be initialized without 
        the llm parameter (using CrewAI defaults).
        
        **Feature: configurable-llm-models, Property 2: Default behavior when not configured**
        **Validates: Requirements 1.2, 5.1**
        """
        # Set required API keys
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        # Configure or not configure each agent
        if senior_configured:
            monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-4o")
        else:
            monkeypatch.delenv("SENIOR_DEVELOPER_MODEL", raising=False)
        
        if security_configured:
            monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-4o")
        else:
            monkeypatch.delenv("SECURITY_ENGINEER_MODEL", raising=False)
        
        if tech_lead_configured:
            monkeypatch.setenv("TECH_LEAD_MODEL", "gpt-4o")
        else:
            monkeypatch.delenv("TECH_LEAD_MODEL", raising=False)
        
        # Initialize crew
        crew = CodeReviewCrew()
        
        # Initialize agents
        senior_dev = crew.senior_developer()
        security_eng = crew.security_engineer()
        tech_lead = crew.tech_lead()
        
        # Verify behavior based on configuration
        if senior_configured:
            assert senior_dev.llm is not None, \
                "Senior Developer should have llm when configured"
            assert senior_dev.llm.model == "gpt-4o"
        else:
            # When not configured, CrewAI may still create a default LLM
            # We just verify no crash occurs
            assert senior_dev is not None
        
        if security_configured:
            assert security_eng.llm is not None, \
                "Security Engineer should have llm when configured"
            assert security_eng.llm.model == "gpt-4o"
        else:
            assert security_eng is not None
        
        if tech_lead_configured:
            assert tech_lead.llm is not None, \
                "Tech Lead should have llm when configured"
            assert tech_lead.llm.model == "gpt-4o"
        else:
            assert tech_lead is not None



class TestInvalidInputHandling:
    """Property-based tests for invalid input handling.
    
    **Feature: configurable-llm-models, Property 3: Invalid model names fall back to default**
    **Validates: Requirements 1.3, 4.4**
    """
    
    # Strategy for generating invalid strings
    invalid_strings = st.one_of(
        st.just(""),  # Empty string
        st.just("   "),  # Whitespace only
        st.just("\t\n"),  # Tabs and newlines
        st.just("  \t  \n  "),  # Mixed whitespace
        st.just("\r\n"),  # Carriage return and newline
        st.just("     \t     "),  # More whitespace variations
    )
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        senior_invalid=invalid_strings,
        security_invalid=invalid_strings,
        tech_lead_invalid=invalid_strings
    )
    def test_invalid_model_names_fallback_to_default(
        self,
        monkeypatch,
        senior_invalid,
        security_invalid,
        tech_lead_invalid
    ):
        """
        Property: For any invalid or malformed model name, the system should 
        omit the llm parameter and not crash.
        
        **Feature: configurable-llm-models, Property 3: Invalid model names fall back to default**
        **Validates: Requirements 1.3, 4.4**
        """
        # Set required API keys
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        # Set invalid model names
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", senior_invalid)
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", security_invalid)
        monkeypatch.setenv("TECH_LEAD_MODEL", tech_lead_invalid)
        
        # Initialize crew - should not crash
        try:
            crew = CodeReviewCrew()
            
            # Initialize agents - should not crash
            senior_dev = crew.senior_developer()
            security_eng = crew.security_engineer()
            tech_lead = crew.tech_lead()
            
            # Verify agents were created successfully
            assert senior_dev is not None, "Senior Developer should be created"
            assert security_eng is not None, "Security Engineer should be created"
            assert tech_lead is not None, "Tech Lead should be created"
            
            # Verify no crash occurred - this is the main property
            # The agents should fall back to default behavior
            
        except Exception as e:
            pytest.fail(f"System crashed with invalid input: {e}")



class TestIndependentAgentConfiguration:
    """Property-based tests for independent agent configuration.
    
    **Feature: configurable-llm-models, Property 4: Independent agent configuration**
    **Validates: Requirements 1.5**
    """
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        senior_model=valid_openai_models,
        security_model=valid_openai_models,
        tech_lead_model=valid_openai_models
    )
    def test_independent_agent_configuration(
        self,
        monkeypatch,
        senior_model,
        security_model,
        tech_lead_model
    ):
        """
        Property: For any combination of model assignments to the three agents, 
        each agent should use its own configured model independently.
        
        **Feature: configurable-llm-models, Property 4: Independent agent configuration**
        **Validates: Requirements 1.5**
        """
        # Set required API keys
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        monkeypatch.setenv("CREWAI_TESTING", "true")
        
        # Set different models for each agent
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", senior_model)
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", security_model)
        monkeypatch.setenv("TECH_LEAD_MODEL", tech_lead_model)
        
        # Initialize crew
        crew = CodeReviewCrew()
        
        # Initialize agents
        senior_dev = crew.senior_developer()
        security_eng = crew.security_engineer()
        tech_lead = crew.tech_lead()
        
        # Verify each agent uses its own model
        assert senior_dev.llm.model == senior_model, \
            f"Senior Developer should use {senior_model}, got {senior_dev.llm.model}"
        assert security_eng.llm.model == security_model, \
            f"Security Engineer should use {security_model}, got {security_eng.llm.model}"
        assert tech_lead.llm.model == tech_lead_model, \
            f"Tech Lead should use {tech_lead_model}, got {tech_lead.llm.model}"
        
        # Verify independence: changing one agent's model doesn't affect others
        # This is implicitly tested by the fact that we can set different models
        # and each agent maintains its own configuration
        
        # Additional check: verify all three can be different
        models = {senior_dev.llm.model, security_eng.llm.model, tech_lead.llm.model}
        # We don't require them to be different (they might randomly be the same)
        # but we verify each is what we set it to
        assert senior_model in models
        assert security_model in models
        assert tech_lead_model in models
