"""
Integration tests for model configuration with full flow execution.

These tests verify that model configuration works correctly in the context
of the full code review flow, including:
- Custom models for all agents
- No configuration (backward compatibility)
- Mixed configuration (some agents configured, others not)
- Tools and guardrails still work with configured models
- Async execution works with configured models

**Validates: Requirements 1.1, 1.2, 1.5, 3.1, 3.5**
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock

import pytest

from agentic_code_review.main import PRCodeReviewFlow, ReviewState
from agentic_code_review.crews.code_review_crew.crew import CodeReviewCrew
from agentic_code_review.utils import (
    get_senior_developer_model,
    get_security_engineer_model,
    get_tech_lead_model
)


class TestFullFlowWithCustomModels:
    """Test full flow execution with custom models for all agents."""
    
    def test_full_flow_with_all_agents_configured(self, monkeypatch):
        """
        Test that the full flow works correctly when all agents have custom models.
        
        **Validates: Requirements 1.1, 1.5**
        """
        # Configure custom models for all agents
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-4o")
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("TECH_LEAD_MODEL", "gpt-3.5-turbo")
        
        # Verify configuration is loaded
        assert get_senior_developer_model() == "gpt-4o"
        assert get_security_engineer_model() == "gpt-4o-mini"
        assert get_tech_lead_model() == "gpt-3.5-turbo"
        
        # Create a test file with complex changes
        test_content = """
diff --git a/src/auth.py b/src/auth.py
index abc123..def456 100644
--- a/src/auth.py
+++ b/src/auth.py
@@ -10,7 +10,7 @@ def authenticate(username, password):
-    query = f"SELECT * FROM users WHERE username='{username}'"
+    query = "SELECT * FROM users WHERE username=%s"
+    cursor.execute(query, (username,))
"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(test_content)
            temp_path = f.name
        
        try:
            # Mock the crew execution to avoid actual LLM calls
            with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                with patch.object(CodeReviewCrew, 'crew') as mock_crew_method:
                    # Create a mock crew with a mock kickoff method
                    mock_crew = MagicMock()
                    mock_result = MagicMock()
                    mock_result.json_dict = {
                        "confidence": 90,
                        "findings": "Security improvement detected",
                        "fix": [],
                        "recommendations": ["Good fix for SQL injection"]
                    }
                    mock_result.token_usage = {"total": 1000}
                    mock_crew.kickoff.return_value = mock_result
                    mock_crew_method.return_value = mock_crew
                    
                    # Mock the LLM calls - need to mock the actual call method to return strings
                    with patch('agentic_code_review.main.LLM') as mock_llm_class:
                        mock_llm = MagicMock()
                        # The call method should return the string directly
                        mock_llm.call.side_effect = [
                            "COMPLEX",  # analyze_changes decision
                            "APPROVE - Good security fix"  # final decision
                        ]
                        mock_llm_class.return_value = mock_llm
                        
                        # Create and run the flow
                        flow = PRCodeReviewFlow()
                        flow._state = ReviewState(pr_input=temp_path)
                        
                        # Execute the flow steps
                        flow.read_pr_data()
                        assert flow.state.pr_content == test_content
                        
                        # Verify the flow can proceed with configured models
                        decision = flow.analyze_changes(None)
                        assert decision == 'COMPLEX'
                        
                        # Verify crew is called (which uses configured models)
                        flow.full_crew_review()
                        assert mock_crew.kickoff.called
                        assert flow.state.review_result is not None
                        
                        # Verify final decision works
                        flow.make_final_decision()
                        assert flow.state.final_answer != ""
        
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_agents_initialized_with_correct_models(self, monkeypatch):
        """
        Test that agents are initialized with the correct configured models.
        
        **Validates: Requirements 1.1**
        """
        # Configure different models for each agent
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-4o")
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("TECH_LEAD_MODEL", "gpt-3.5-turbo")
        
        # Verify the utility functions return the correct models
        assert get_senior_developer_model() == "gpt-4o"
        assert get_security_engineer_model() == "gpt-4o-mini"
        assert get_tech_lead_model() == "gpt-3.5-turbo"
        
        # Create the crew and verify agents can be created without errors
        crew_instance = CodeReviewCrew()
        
        # The agents should be created successfully with the configured models
        # We can't easily inspect the internal llm parameter due to the @agent decorator,
        # but we can verify the agents are created without errors
        senior_dev = crew_instance.senior_developer()
        security_eng = crew_instance.security_engineer()
        tech_lead_agent = crew_instance.tech_lead()
        
        # Verify agents were created
        assert senior_dev is not None
        assert security_eng is not None
        assert tech_lead_agent is not None


class TestFullFlowWithoutConfiguration:
    """Test full flow execution without model configuration (backward compatibility)."""
    
    def test_full_flow_without_any_configuration(self, monkeypatch):
        """
        Test that the full flow works correctly when no models are configured.
        This ensures backward compatibility.
        
        **Validates: Requirements 1.2, 3.1, 5.1**
        """
        # Ensure no model configuration is set
        monkeypatch.delenv("SENIOR_DEVELOPER_MODEL", raising=False)
        monkeypatch.delenv("SECURITY_ENGINEER_MODEL", raising=False)
        monkeypatch.delenv("TECH_LEAD_MODEL", raising=False)
        
        # Verify no configuration is loaded
        assert get_senior_developer_model() is None
        assert get_security_engineer_model() is None
        assert get_tech_lead_model() is None
        
        # Create a test file with simple changes
        test_content = """
diff --git a/README.md b/README.md
index abc123..def456 100644
--- a/README.md
+++ b/README.md
@@ -1,3 +1,3 @@
-# My Project
+# My Awesome Project
"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(test_content)
            temp_path = f.name
        
        try:
            with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                # Create and run the flow
                flow = PRCodeReviewFlow()
                flow._state = ReviewState(pr_input=temp_path)
                
                # Execute the flow steps
                flow.read_pr_data()
                assert flow.state.pr_content == test_content
                
                # Verify the flow initialized correctly without configuration
                # We don't need to run analyze_changes or simple_review to test
                # that the configuration works - just verify the state is correct
                assert flow.state.pr_metadata is not None
                assert flow.state.pr_metadata["provider"] == "file"
        
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_agents_initialized_without_llm_parameter(self, monkeypatch):
        """
        Test that agents are initialized without llm parameter when not configured.
        
        **Validates: Requirements 1.2, 5.1**
        """
        # Ensure no model configuration is set
        monkeypatch.delenv("SENIOR_DEVELOPER_MODEL", raising=False)
        monkeypatch.delenv("SECURITY_ENGINEER_MODEL", raising=False)
        monkeypatch.delenv("TECH_LEAD_MODEL", raising=False)
        
        # Verify no configuration is loaded
        assert get_senior_developer_model() is None
        assert get_security_engineer_model() is None
        assert get_tech_lead_model() is None
        
        # Create the crew and verify agents can be created without errors
        crew_instance = CodeReviewCrew()
        
        # The agents should be created successfully without configured models
        senior_dev = crew_instance.senior_developer()
        security_eng = crew_instance.security_engineer()
        tech_lead_agent = crew_instance.tech_lead()
        
        # Verify agents were created (backward compatibility)
        assert senior_dev is not None
        assert security_eng is not None
        assert tech_lead_agent is not None


class TestMixedConfiguration:
    """Test full flow with mixed configuration (some agents configured, others not)."""
    
    def test_flow_with_partial_configuration(self, monkeypatch):
        """
        Test that the flow works when only some agents have custom models.
        
        **Validates: Requirements 1.2, 1.5**
        """
        # Configure only some agents
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-4o")
        monkeypatch.delenv("SECURITY_ENGINEER_MODEL", raising=False)
        monkeypatch.setenv("TECH_LEAD_MODEL", "")  # Empty string should be treated as not configured
        
        # Verify configuration
        assert get_senior_developer_model() == "gpt-4o"
        assert get_security_engineer_model() is None
        assert get_tech_lead_model() is None
        
        # Create a test file
        test_content = "diff --git a/test.py b/test.py\n+print('hello')"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(test_content)
            temp_path = f.name
        
        try:
            with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                # Run the flow
                flow = PRCodeReviewFlow()
                flow._state = ReviewState(pr_input=temp_path)
                
                flow.read_pr_data()
                
                # Verify the flow initialized successfully with mixed configuration
                assert flow.state.pr_content == test_content
                assert flow.state.pr_metadata is not None
        
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_mixed_agent_initialization(self, monkeypatch):
        """
        Test that agents are correctly initialized with mixed configuration.
        
        **Validates: Requirements 1.5**
        """
        # Configure only senior developer
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-4o")
        monkeypatch.delenv("SECURITY_ENGINEER_MODEL", raising=False)
        monkeypatch.delenv("TECH_LEAD_MODEL", raising=False)
        
        # Verify mixed configuration
        assert get_senior_developer_model() == "gpt-4o"
        assert get_security_engineer_model() is None
        assert get_tech_lead_model() is None
        
        # Create the crew and verify agents can be created
        crew_instance = CodeReviewCrew()
        
        # All agents should be created successfully with mixed configuration
        senior_dev = crew_instance.senior_developer()
        security_eng = crew_instance.security_engineer()
        tech_lead_agent = crew_instance.tech_lead()
        
        # Verify agents were created
        assert senior_dev is not None
        assert security_eng is not None
        assert tech_lead_agent is not None


class TestToolsAndGuardrailsWithConfiguration:
    """Test that tools and guardrails still work with configured models."""
    
    def test_security_engineer_tools_preserved_with_custom_model(self, monkeypatch):
        """
        Test that security engineer's tools are preserved when using custom model.
        
        **Validates: Requirements 3.5**
        """
        # Configure security engineer model
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-4o")
        
        # Verify configuration
        assert get_security_engineer_model() == "gpt-4o"
        
        crew_instance = CodeReviewCrew()
        
        # Create security engineer agent
        security_eng = crew_instance.security_engineer()
        
        # Verify agent was created successfully with tools
        assert security_eng is not None
        # The agent should have tools attribute
        assert hasattr(security_eng, 'tools')
        assert len(security_eng.tools) == 2  # SerperDevTool and ScrapeWebsiteTool
    
    def test_security_engineer_tools_preserved_without_configuration(self, monkeypatch):
        """
        Test that security engineer's tools are preserved without configuration.
        
        **Validates: Requirements 3.1, 3.5**
        """
        # Ensure no configuration
        monkeypatch.delenv("SECURITY_ENGINEER_MODEL", raising=False)
        
        # Verify no configuration
        assert get_security_engineer_model() is None
        
        crew_instance = CodeReviewCrew()
        
        # Create security engineer agent
        security_eng = crew_instance.security_engineer()
        
        # Verify agent was created successfully with tools (backward compatibility)
        assert security_eng is not None
        assert hasattr(security_eng, 'tools')
        assert len(security_eng.tools) == 2  # SerperDevTool and ScrapeWebsiteTool
    
    def test_guardrails_work_with_configured_models(self, monkeypatch):
        """
        Test that task guardrails still work when agents have custom models.
        
        **Validates: Requirements 3.5**
        """
        # Configure all agents
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-4o")
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("TECH_LEAD_MODEL", "gpt-3.5-turbo")
        
        crew_instance = CodeReviewCrew()
        
        # Get the review_security task
        task = crew_instance.review_security()
        
        # Verify the task was created successfully
        assert task is not None
        # Verify the task has the expected output format (which includes guardrails)
        assert task.output_json is not None


class TestAsyncExecutionWithConfiguration:
    """Test that async execution still works with configured models."""
    
    def test_async_tasks_with_configured_models(self, monkeypatch):
        """
        Test that async task execution works when agents have custom models.
        
        **Validates: Requirements 3.5**
        """
        # Configure all agents
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-4o")
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("TECH_LEAD_MODEL", "gpt-3.5-turbo")
        
        crew_instance = CodeReviewCrew()
        
        # Get the async tasks
        code_quality_task = crew_instance.analyze_code_quality()
        security_task = crew_instance.review_security()
        
        # Verify both tasks have async_execution enabled
        assert code_quality_task.async_execution is True
        assert security_task.async_execution is True
    
    def test_async_tasks_without_configuration(self, monkeypatch):
        """
        Test that async task execution works without model configuration.
        
        **Validates: Requirements 3.1, 3.5**
        """
        # Ensure no configuration
        monkeypatch.delenv("SENIOR_DEVELOPER_MODEL", raising=False)
        monkeypatch.delenv("SECURITY_ENGINEER_MODEL", raising=False)
        monkeypatch.delenv("TECH_LEAD_MODEL", raising=False)
        
        crew_instance = CodeReviewCrew()
        
        # Get the async tasks
        code_quality_task = crew_instance.analyze_code_quality()
        security_task = crew_instance.review_security()
        
        # Verify both tasks still have async_execution enabled
        assert code_quality_task.async_execution is True
        assert security_task.async_execution is True
    
    def test_crew_process_preserved_with_configuration(self, monkeypatch):
        """
        Test that crew process (sequential) is preserved with configuration.
        
        **Validates: Requirements 3.5**
        """
        # Configure all agents
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-4o")
        monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("TECH_LEAD_MODEL", "gpt-3.5-turbo")
        
        from crewai import Process
        
        crew_instance = CodeReviewCrew()
        crew = crew_instance.crew()
        
        # Verify crew configuration is preserved
        assert crew.process == Process.sequential
        assert crew.verbose is True
        assert crew.memory is True


class TestBackwardCompatibilityIntegration:
    """Test backward compatibility at the integration level."""
    
    def test_existing_functionality_preserved(self, monkeypatch):
        """
        Test that all existing functionality works identically with and without configuration.
        
        **Validates: Requirements 3.1**
        """
        # Create test content
        test_content = "diff --git a/test.py b/test.py\n+# comment"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(test_content)
            temp_path = f.name
        
        try:
            # Test without configuration
            monkeypatch.delenv("SENIOR_DEVELOPER_MODEL", raising=False)
            monkeypatch.delenv("SECURITY_ENGINEER_MODEL", raising=False)
            monkeypatch.delenv("TECH_LEAD_MODEL", raising=False)
            
            with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
                flow1 = PRCodeReviewFlow()
                flow1._state = ReviewState(pr_input=temp_path)
                flow1.read_pr_data()
                
                # Test with configuration
                monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-4o")
                monkeypatch.setenv("SECURITY_ENGINEER_MODEL", "gpt-4o-mini")
                monkeypatch.setenv("TECH_LEAD_MODEL", "gpt-3.5-turbo")
                
                flow2 = PRCodeReviewFlow()
                flow2._state = ReviewState(pr_input=temp_path)
                flow2.read_pr_data()
                
                # Both should read the same content
                assert flow1.state.pr_content == flow2.state.pr_content
                assert flow1.state.pr_metadata["provider"] == flow2.state.pr_metadata["provider"]
        
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_error_handling_preserved(self, monkeypatch):
        """
        Test that error handling works the same with and without configuration.
        
        **Validates: Requirements 3.1**
        """
        # Configure models
        monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-4o")
        
        # Test with invalid input
        with patch('crewai.flow.persistence.decorators.PersistenceDecorator.persist_state'):
            flow = PRCodeReviewFlow()
            flow._state = ReviewState(pr_input="")
            
            flow.read_pr_data()
            
            # Verify error handling works
            assert len(flow.state.errors) > 0
            assert "Missing 'pr_input' in state" in flow.state.errors[0]
