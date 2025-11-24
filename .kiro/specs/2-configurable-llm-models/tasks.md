# Implementation Plan

- [x] 1. Add model configuration utility functions to utils.py
  - Implement `get_agent_model(agent_name: str) -> str | None` function
  - Implement `get_senior_developer_model() -> str | None` function
  - Implement `get_security_engineer_model() -> str | None` function
  - Implement `get_tech_lead_model() -> str | None` function
  - Functions should return None for empty, whitespace-only, or missing values
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 1.1 Write unit tests for model configuration utilities
  - Test valid model names are returned correctly
  - Test empty strings return None
  - Test whitespace-only strings return None
  - Test missing environment variables return None
  - _Requirements: 1.1, 1.2, 1.3, 4.4_

- [x] 2. Update agent initialization in crew.py to use configured models
  - Modify `senior_developer()` method to use `get_senior_developer_model()`
  - Modify `security_engineer()` method to use `get_security_engineer_model()`
  - Modify `tech_lead()` method to use `get_tech_lead_model()`
  - Only pass `llm` parameter to Agent if model is not None
  - Preserve all existing agent configuration (tools, guardrails, etc.)
  - _Requirements: 1.1, 1.2, 1.5, 3.4, 3.5_

- [x] 2.1 Write property-based test for model configuration application
  - **Property 1: Model configuration is applied correctly**
  - **Validates: Requirements 1.1**
  - Generate random valid OpenAI model names
  - Set environment variables and initialize agents
  - Verify configured models are used
  - Run minimum 100 iterations

- [x] 2.2 Write property-based test for default behavior
  - **Property 2: Default behavior when not configured**
  - **Validates: Requirements 1.2, 5.1**
  - Generate random combinations of set/unset environment variables
  - Initialize agents and verify those without config don't have llm parameter
  - Run minimum 100 iterations

- [x] 2.3 Write property-based test for invalid input handling
  - **Property 3: Invalid model names fall back to default**
  - **Validates: Requirements 1.3, 4.4**
  - Generate random invalid strings (empty, whitespace, special characters)
  - Set as environment variables and initialize agents
  - Verify no crashes and fallback to default behavior
  - Run minimum 100 iterations

- [x] 2.4 Write property-based test for independent agent configuration
  - **Property 4: Independent agent configuration**
  - **Validates: Requirements 1.5**
  - Generate random model assignments for each agent
  - Initialize all agents and verify each uses its own model
  - Run minimum 100 iterations

- [x] 3. Update .env.example with model configuration documentation
  - Add SENIOR_DEVELOPER_MODEL environment variable with example
  - Add SECURITY_ENGINEER_MODEL environment variable with example
  - Add TECH_LEAD_MODEL environment variable with example
  - Include comments explaining purpose and common options
  - List common OpenAI models (gpt-4o, gpt-4o-mini, gpt-3.5-turbo, gpt-4-turbo)
  - Explain that these are optional and CrewAI defaults will be used if not set
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 4. Checkpoint - Verify backward compatibility
  - Ensure all tests pass, ask the user if questions arise.
  - Run existing test suite without setting new environment variables
  - Verify all existing tests pass
  - Verify crew functionality (tools, guardrails, async execution) is preserved
  - _Requirements: 3.1, 3.2, 3.5_

- [x] 4.1 Write property-based test for backward compatibility
  - **Property 5: Backward compatibility preserved**
  - **Validates: Requirements 3.1, 3.5**
  - Run existing test suite with and without configuration
  - Verify all tests pass in both cases
  - Run minimum 100 iterations

- [x] 5. Write integration tests for model configuration
  - Test full flow with custom models for all agents
  - Test full flow with no configuration (backward compatibility)
  - Test mixed configuration (some agents configured, others not)
  - Test that model configuration doesn't break tools or guardrails
  - Test that async execution still works with configured models
  - _Requirements: 1.1, 1.2, 1.5, 3.1, 3.5_

- [x] 6. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
