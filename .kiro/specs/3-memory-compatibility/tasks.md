# Implementation Plan

- [x] 1. Add memory compatibility registry and checker functions to utils.py
  - Define `MEMORY_INCOMPATIBLE_MODELS` constant with "codex" pattern
  - Implement `is_model_memory_compatible(model_name: str | None) -> bool` function
  - Implement `check_crew_memory_compatibility() -> tuple[bool, list[str]]` function
  - Functions should handle None/empty values (treat as compatible)
  - Functions should perform case-insensitive pattern matching
  - Add clear documentation explaining the registry and how to update it
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 6.1, 6.2, 6.3_

- [x] 1.1 Write unit tests for memory compatibility functions
  - Test `is_model_memory_compatible()` with compatible models (gpt-4o, gpt-4o-mini)
  - Test `is_model_memory_compatible()` with incompatible models (gpt-5-codex, gpt-5.1-codex-mini)
  - Test `is_model_memory_compatible()` with None and empty string
  - Test case-insensitive matching (CODEX, Codex, codex)
  - Test `check_crew_memory_compatibility()` with all compatible models
  - Test `check_crew_memory_compatibility()` with at least one incompatible model
  - Test `check_crew_memory_compatibility()` with no configured models
  - _Requirements: 1.1, 1.2, 1.3, 2.2, 6.1, 6.2, 6.3_

- [x] 1.2 Write property-based test for compatible models
  - **Property 1: Compatible models enable memory**
  - **Validates: Requirements 1.1**
  - Generate random combinations of compatible model names
  - Verify `check_crew_memory_compatibility()` returns (True, [])
  - Run minimum 100 iterations

- [x] 1.3 Write property-based test for incompatible models
  - **Property 2: Incompatible models disable memory**
  - **Validates: Requirements 1.2**
  - Generate random combinations with at least one incompatible model
  - Verify `check_crew_memory_compatibility()` returns (False, [incompatible_models])
  - Run minimum 100 iterations

- [x] 1.4 Write property-based test for unknown models
  - **Property 3: Unknown models assumed compatible**
  - **Validates: Requirements 1.3**
  - Generate random model names not in registry
  - Verify they are treated as compatible
  - Run minimum 100 iterations

- [x] 1.5 Write property-based test for codex pattern detection
  - **Property 5: Codex pattern detection**
  - **Validates: Requirements 2.2**
  - Generate random model names containing "codex"
  - Verify all are detected as incompatible
  - Run minimum 100 iterations

- [x] 1.6 Write property-based test for case-insensitive matching
  - **Property 6: Case-insensitive matching**
  - **Validates: Requirements 6.3**
  - Generate random case variations of incompatible models
  - Verify all variations are detected
  - Run minimum 100 iterations

- [x] 2. Update crew.py to use memory compatibility checking
  - Import `check_crew_memory_compatibility` from utils
  - Call compatibility check in `crew()` method before creating Crew instance
  - Set `memory` parameter based on compatibility check result (True or False)
  - Remove explicit `short_term_memory` and `entity_memory` configuration (handled automatically by memory=True)
  - Log warning message when memory is disabled due to incompatibility
  - Include incompatible model names in log message
  - Include link to docs/TROUBLESHOOTING.md in log message
  - Deduplicate model names in log message (use set)
  - _Requirements: 1.1, 1.2, 1.4, 4.1, 4.2, 3.2, 3.4_

- [x] 2.1 Write property-based test for incompatibility logging
  - **Property 4: Incompatibility logging**
  - **Validates: Requirements 1.4, 3.2, 3.4**
  - Generate random incompatible model configurations
  - Initialize crew and capture logs
  - Verify warning message appears with correct model names
  - Verify log message includes link to docs/TROUBLESHOOTING.md
  - Run minimum 100 iterations

- [x] 2.2 Write property-based test for default behavior
  - **Property 7: Default behavior without configuration**
  - **Validates: Requirements 4.3, 6.1**
  - Test crew initialization with no model configuration
  - Verify memory is enabled
  - Run minimum 100 iterations

- [x] 2.3 Write property-based test for error handling
  - **Property 8: Error handling fallback**
  - **Validates: Requirements 6.4**
  - Simulate errors during compatibility checking
  - Verify memory is enabled and warning is logged
  - Run minimum 100 iterations

- [x] 3. Add memory compatibility documentation to docs/TROUBLESHOOTING.md
  - Add section explaining CrewAI memory compatibility
  - List known incompatible models (codex variants)
  - Explain that memory is automatically managed based on model selection
  - Explain what to do if memory is disabled (warning message will appear in logs)
  - Include link to this documentation in warning log message
  - _Requirements: 3.1, 3.4_

- [x] 4. Checkpoint - Verify backward compatibility
  - Ensure all tests pass, ask the user if questions arise.
  - Run existing test suite without setting new model configurations
  - Verify all existing tests pass
  - Verify crew functionality is preserved
  - Test with compatible models (memory should be enabled)
  - Test with incompatible models (memory should be disabled, crew still works)
  - _Requirements: 1.5, 3.1, 3.5, 4.3_

- [x] 5. Write integration tests for memory compatibility
  - Test full crew execution with all compatible models (memory enabled)
  - Test full crew execution with incompatible model (memory disabled)
  - Test mixed configuration (some agents with compatible, some with incompatible)
  - Verify crew completes successfully with memory disabled
  - Verify logging output is correct
  - Test that memory components are only added when memory is enabled
  - _Requirements: 1.1, 1.2, 1.4, 1.5, 4.1, 4.2_

- [x] 6. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
