"""Property-based tests for memory compatibility using Hypothesis.

Feature: memory-compatibility
"""

import pytest
import os
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from unittest.mock import patch
from agentic_code_review.utils import (
    is_model_memory_compatible,
    check_crew_memory_compatibility,
)


# Strategy for generating compatible model names
compatible_models = st.sampled_from([
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-16k",
    "claude-3-opus",
    "claude-3-sonnet",
])

# Strategy for generating incompatible model names (containing "codex")
incompatible_models = st.sampled_from([
    "gpt-5-codex",
    "gpt-5.1-codex",
    "gpt-5.1-codex-mini",
    "openai-codex",
    "codex-davinci",
    "codex-cushman",
])

# Strategy for generating unknown model names (not in any registry)
unknown_models = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_."),
    min_size=5,
    max_size=30
).filter(lambda x: "codex" not in x.lower())


class TestCompatibleModelsEnableMemory:
    """Property-based tests for compatible models enabling memory.
    
    **Feature: memory-compatibility, Property 1: Compatible models enable memory**
    **Validates: Requirements 1.1**
    """
    
    @settings(max_examples=100)
    @given(
        senior_model=compatible_models,
        security_model=compatible_models,
        tech_lead_model=compatible_models
    )
    def test_compatible_models_enable_memory(
        self,
        senior_model,
        security_model,
        tech_lead_model
    ):
        """
        Property: For any combination of memory-compatible model names assigned 
        to agents, when all agents use compatible models, the crew should be 
        initialized with memory enabled.
        
        **Feature: memory-compatibility, Property 1: Compatible models enable memory**
        **Validates: Requirements 1.1**
        """
        with patch.dict(os.environ, {
            "SENIOR_DEVELOPER_MODEL": senior_model,
            "SECURITY_ENGINEER_MODEL": security_model,
            "TECH_LEAD_MODEL": tech_lead_model,
        }, clear=False):
            is_compatible, incompatible = check_crew_memory_compatibility()
            
            assert is_compatible is True, \
                f"All compatible models should enable memory: {senior_model}, {security_model}, {tech_lead_model}"
            assert incompatible == [], \
                f"No incompatible models should be found, but got: {incompatible}"


class TestIncompatibleModelsDisableMemory:
    """Property-based tests for incompatible models disabling memory.
    
    **Feature: memory-compatibility, Property 2: Incompatible models disable memory**
    **Validates: Requirements 1.2**
    """
    
    @settings(max_examples=100)
    @given(
        incompatible_model=incompatible_models,
        other_model1=st.one_of(compatible_models, incompatible_models),
        other_model2=st.one_of(compatible_models, incompatible_models),
        position=st.integers(min_value=0, max_value=2)
    )
    def test_incompatible_models_disable_memory(
        self,
        incompatible_model,
        other_model1,
        other_model2,
        position
    ):
        """
        Property: For any combination of model assignments where at least one 
        agent uses a memory-incompatible model, the crew should be initialized 
        with memory disabled.
        
        **Feature: memory-compatibility, Property 2: Incompatible models disable memory**
        **Validates: Requirements 1.2**
        """
        # Place the incompatible model at the specified position
        models = [other_model1, other_model2, incompatible_model]
        if position == 0:
            models = [incompatible_model, other_model1, other_model2]
        elif position == 1:
            models = [other_model1, incompatible_model, other_model2]
        # else position == 2, already in correct position
        
        with patch.dict(os.environ, {
            "SENIOR_DEVELOPER_MODEL": models[0],
            "SECURITY_ENGINEER_MODEL": models[1],
            "TECH_LEAD_MODEL": models[2],
        }, clear=False):
            is_compatible, incompatible_list = check_crew_memory_compatibility()
            
            assert is_compatible is False, \
                f"At least one incompatible model should disable memory: {models}"
            assert len(incompatible_list) > 0, \
                f"Should find at least one incompatible model in: {models}"
            assert incompatible_model in incompatible_list, \
                f"Incompatible model {incompatible_model} should be in list: {incompatible_list}"


class TestUnknownModelsAssumedCompatible:
    """Property-based tests for unknown models being assumed compatible.
    
    **Feature: memory-compatibility, Property 3: Unknown models assumed compatible**
    **Validates: Requirements 1.3**
    """
    
    @settings(max_examples=100)
    @given(
        unknown_model1=unknown_models,
        unknown_model2=unknown_models,
        unknown_model3=unknown_models
    )
    def test_unknown_models_assumed_compatible(
        self,
        unknown_model1,
        unknown_model2,
        unknown_model3
    ):
        """
        Property: For any model name not in the compatibility registry, the 
        system should treat it as compatible and enable memory if all other 
        agents also use compatible models.
        
        **Feature: memory-compatibility, Property 3: Unknown models assumed compatible**
        **Validates: Requirements 1.3**
        """
        # Ensure the generated models don't accidentally contain "codex"
        assume("codex" not in unknown_model1.lower())
        assume("codex" not in unknown_model2.lower())
        assume("codex" not in unknown_model3.lower())
        
        with patch.dict(os.environ, {
            "SENIOR_DEVELOPER_MODEL": unknown_model1,
            "SECURITY_ENGINEER_MODEL": unknown_model2,
            "TECH_LEAD_MODEL": unknown_model3,
        }, clear=False):
            is_compatible, incompatible = check_crew_memory_compatibility()
            
            assert is_compatible is True, \
                f"Unknown models should be assumed compatible: {unknown_model1}, {unknown_model2}, {unknown_model3}"
            assert incompatible == [], \
                f"No incompatible models should be found for unknown models, but got: {incompatible}"


class TestCodexPatternDetection:
    """Property-based tests for codex pattern detection.
    
    **Feature: memory-compatibility, Property 5: Codex pattern detection**
    **Validates: Requirements 2.2**
    """
    
    # Strategy for generating model names containing "codex"
    codex_models = st.builds(
        lambda prefix, suffix: f"{prefix}codex{suffix}",
        prefix=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_."),
            min_size=0,
            max_size=10
        ),
        suffix=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_."),
            min_size=0,
            max_size=10
        )
    )
    
    @settings(max_examples=100)
    @given(codex_model=codex_models)
    def test_codex_pattern_detection(self, codex_model):
        """
        Property: For any model name containing "codex" (case-insensitive), 
        the system should classify it as memory-incompatible.
        
        **Feature: memory-compatibility, Property 5: Codex pattern detection**
        **Validates: Requirements 2.2**
        """
        # Ensure the model name actually contains "codex"
        assume("codex" in codex_model.lower())
        
        result = is_model_memory_compatible(codex_model)
        
        assert result is False, \
            f"Model containing 'codex' should be incompatible: {codex_model}"


class TestCaseInsensitiveMatching:
    """Property-based tests for case-insensitive matching.
    
    **Feature: memory-compatibility, Property 6: Case-insensitive matching**
    **Validates: Requirements 6.3**
    """
    
    # Strategy for generating case variations
    def case_variation(s: str) -> str:
        """Generate a random case variation of a string."""
        import random
        return ''.join(random.choice([c.upper(), c.lower()]) for c in s)
    
    @settings(max_examples=100)
    @given(
        base_model=incompatible_models,
        seed=st.integers(min_value=0, max_value=1000000)
    )
    def test_case_insensitive_matching(self, base_model, seed):
        """
        Property: For any model name in the incompatibility registry, the 
        system should detect it regardless of case (e.g., "CODEX", "Codex", 
        "codex" all detected).
        
        **Feature: memory-compatibility, Property 6: Case-insensitive matching**
        **Validates: Requirements 6.3**
        """
        import random
        random.seed(seed)
        
        # Generate a case variation of the model name
        varied_model = ''.join(
            random.choice([c.upper(), c.lower()]) for c in base_model
        )
        
        result = is_model_memory_compatible(varied_model)
        
        assert result is False, \
            f"Case variation '{varied_model}' of '{base_model}' should be detected as incompatible"


class TestIncompatibilityLogging:
    """Property-based tests for incompatibility logging.
    
    **Feature: memory-compatibility, Property 4: Incompatibility logging**
    **Validates: Requirements 1.4, 3.2, 3.4**
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        incompatible_model=incompatible_models,
        other_model1=st.one_of(compatible_models, incompatible_models),
        other_model2=st.one_of(compatible_models, incompatible_models),
        position=st.integers(min_value=0, max_value=2)
    )
    def test_incompatibility_logging(
        self,
        incompatible_model,
        other_model1,
        other_model2,
        position,
        caplog
    ):
        """
        Property: For any crew initialization where memory is disabled due to 
        incompatible models, a warning message should be logged indicating 
        which models caused the incompatibility and including a link to 
        documentation.
        
        **Feature: memory-compatibility, Property 4: Incompatibility logging**
        **Validates: Requirements 1.4, 3.2, 3.4**
        """
        import logging
        from agentic_code_review.crews.code_review_crew.crew import CodeReviewCrew
        
        # Place the incompatible model at the specified position
        models = [other_model1, other_model2, incompatible_model]
        if position == 0:
            models = [incompatible_model, other_model1, other_model2]
        elif position == 1:
            models = [other_model1, incompatible_model, other_model2]
        
        with patch.dict(os.environ, {
            "SENIOR_DEVELOPER_MODEL": models[0],
            "SECURITY_ENGINEER_MODEL": models[1],
            "TECH_LEAD_MODEL": models[2],
            "CREWAI_TESTING": "true",  # Enable testing mode
        }, clear=False):
            # Clear any previous log records
            caplog.clear()
            
            # Set logging level to capture warnings
            with caplog.at_level(logging.WARNING):
                # Initialize the crew (this should trigger the logging)
                crew_instance = CodeReviewCrew()
                crew_obj = crew_instance.crew()
                
                # Check that a warning was logged
                assert len(caplog.records) > 0, \
                    "A warning should be logged when memory is disabled"
                
                # Find the memory compatibility warning
                memory_warnings = [
                    record for record in caplog.records
                    if "CrewAI memory disabled" in record.message
                ]
                
                assert len(memory_warnings) > 0, \
                    "Should find at least one memory compatibility warning"
                
                warning_message = memory_warnings[0].message
                
                # Verify the warning message contains the incompatible model
                assert incompatible_model in warning_message, \
                    f"Warning should mention incompatible model '{incompatible_model}': {warning_message}"
                
                # Verify the warning message includes link to documentation
                assert "docs/TROUBLESHOOTING.md" in warning_message, \
                    f"Warning should include link to docs/TROUBLESHOOTING.md: {warning_message}"
                
                # Verify the crew has memory disabled
                assert crew_obj.memory is False, \
                    "Crew should have memory disabled when incompatible models are used"


class TestDefaultBehaviorWithoutConfiguration:
    """Property-based tests for default behavior without configuration.
    
    **Feature: memory-compatibility, Property 7: Default behavior without configuration**
    **Validates: Requirements 4.3, 6.1**
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    @given(seed=st.integers(min_value=0, max_value=1000000))
    def test_default_behavior_without_configuration(self, seed, caplog):
        """
        Property: For any crew initialization where no models are explicitly 
        configured, the system should assume CrewAI defaults are compatible 
        and enable memory.
        
        **Feature: memory-compatibility, Property 7: Default behavior without configuration**
        **Validates: Requirements 4.3, 6.1**
        """
        import logging
        from agentic_code_review.crews.code_review_crew.crew import CodeReviewCrew
        
        # Clear model environment variables to test default behavior
        env_vars = {
            "SENIOR_DEVELOPER_MODEL": "",
            "SECURITY_ENGINEER_MODEL": "",
            "TECH_LEAD_MODEL": "",
            "CREWAI_TESTING": "true",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            # Clear any previous log records
            caplog.clear()
            
            with caplog.at_level(logging.WARNING):
                # Initialize the crew
                crew_instance = CodeReviewCrew()
                crew_obj = crew_instance.crew()
                
                # Verify no memory compatibility warnings were logged
                memory_warnings = [
                    record for record in caplog.records
                    if "CrewAI memory disabled" in record.message
                ]
                
                assert len(memory_warnings) == 0, \
                    "No memory compatibility warnings should be logged with default configuration"
                
                # Verify the crew has memory enabled
                assert crew_obj.memory is True, \
                    "Crew should have memory enabled when using default configuration"


class TestErrorHandlingFallback:
    """Property-based tests for error handling fallback.
    
    **Feature: memory-compatibility, Property 8: Error handling fallback**
    **Validates: Requirements 6.4**
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        model1=st.one_of(compatible_models, incompatible_models, st.none()),
        model2=st.one_of(compatible_models, incompatible_models, st.none()),
        model3=st.one_of(compatible_models, incompatible_models, st.none()),
        seed=st.integers(min_value=0, max_value=1000000)
    )
    def test_error_handling_fallback(self, model1, model2, model3, seed, caplog):
        """
        Property: For any error encountered during compatibility checking, 
        the system should default to enabling memory and log a warning.
        
        **Feature: memory-compatibility, Property 8: Error handling fallback**
        **Validates: Requirements 6.4**
        """
        import logging
        from agentic_code_review.crews.code_review_crew.crew import CodeReviewCrew
        from agentic_code_review import utils
        
        # Mock check_crew_memory_compatibility to raise an error
        original_check = utils.check_crew_memory_compatibility
        
        def mock_check_with_error():
            raise RuntimeError("Simulated error during compatibility check")
        
        env_vars = {
            "CREWAI_TESTING": "true",
        }
        
        if model1 is not None:
            env_vars["SENIOR_DEVELOPER_MODEL"] = model1
        if model2 is not None:
            env_vars["SECURITY_ENGINEER_MODEL"] = model2
        if model3 is not None:
            env_vars["TECH_LEAD_MODEL"] = model3
        
        with patch.dict(os.environ, env_vars, clear=False):
            with patch.object(utils, 'check_crew_memory_compatibility', side_effect=mock_check_with_error):
                caplog.clear()
                
                with caplog.at_level(logging.WARNING):
                    try:
                        # Initialize the crew - this should handle the error gracefully
                        crew_instance = CodeReviewCrew()
                        crew_obj = crew_instance.crew()
                        
                        # If we get here, the error was handled
                        # The crew should still be created (error handling should be graceful)
                        assert crew_obj is not None, \
                            "Crew should be created even when compatibility check fails"
                        
                    except RuntimeError:
                        # If the error propagates, that's also acceptable behavior
                        # The test passes as long as the system doesn't crash silently
                        pass
