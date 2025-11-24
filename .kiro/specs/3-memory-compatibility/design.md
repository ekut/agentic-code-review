# Design Document: Memory Compatibility

## Overview

This design document describes the implementation of automatic memory compatibility detection for CrewAI crews based on the OpenAI models used by agents. Certain OpenAI models (specifically those containing "codex" in their name) are incompatible with CrewAI's memory feature and cause runtime errors when memory operations are attempted. Since there is no public documentation about model compatibility, this feature maintains an internal registry of known incompatible models and conditionally enables or disables memory for the entire crew based on the models used by all agents.

The implementation integrates seamlessly with the existing configurable-llm-models feature and follows these principles:
- Automatic detection with no additional user configuration required
- Conservative approach: if any agent uses an incompatible model, disable memory for the entire crew
- Safe defaults: unknown models are assumed compatible
- Clear logging to inform users when memory is disabled and why

## Architecture

### High-Level Design

The memory compatibility system consists of four main components:

1. **Compatibility Registry**: A data structure listing known memory-incompatible model patterns
2. **Compatibility Checker**: Functions to determine if a model is compatible with CrewAI memory
3. **Crew Memory Configurator**: Logic to determine whether to enable memory based on all agents' models
4. **Logging**: Clear messages when memory is disabled due to incompatibility

```
┌─────────────────────┐
│  Model Config       │
│  (from utils.py)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Compatibility      │
│  Checker            │
│  (new in utils.py)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Crew Memory        │
│  Configurator       │
│  (in crew.py)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Crew Instance      │
│  (memory=True/False)│
└─────────────────────┘
```

### Compatibility Detection Flow

1. Crew initialization begins
2. System retrieves configured models for all agents (using existing utilities)
3. For each agent's model:
   - If model is None/empty → assume compatible (CrewAI default)
   - If model matches incompatible pattern → mark as incompatible
   - If model not in registry → assume compatible
4. If ALL agents use compatible models → enable memory
5. If ANY agent uses incompatible model → disable memory and log warning
6. Crew is created with determined memory setting

## Components and Interfaces

### 1. Compatibility Registry (utils.py)

A constant defining known incompatible model patterns:

```python
# Memory Compatibility Registry
# Models in this list are known to be incompatible with CrewAI's memory feature.
# This list is maintained by developers as incompatibilities are discovered.
MEMORY_INCOMPATIBLE_MODELS = [
    "codex",  # All models containing "codex" (e.g., gpt-5-codex, gpt-5.1-codex-mini)
]
```

### 2. Compatibility Checker Functions (utils.py)

New functions to check model compatibility:

```python
def is_model_memory_compatible(model_name: str | None) -> bool:
    """
    Check if a model is compatible with CrewAI memory.
    
    Args:
        model_name: The OpenAI model name, or None if using CrewAI default
    
    Returns:
        True if the model is compatible with CrewAI memory, False otherwise
        
    Logic:
        - None or empty string → True (CrewAI default assumed compatible)
        - Model name contains any pattern from MEMORY_INCOMPATIBLE_MODELS → False
        - Otherwise → True (unknown models assumed compatible)
        
    Example:
        >>> is_model_memory_compatible("gpt-4o-mini")
        True
        >>> is_model_memory_compatible("gpt-5-codex")
        False
        >>> is_model_memory_compatible(None)
        True
    """
    pass

def check_crew_memory_compatibility() -> tuple[bool, list[str]]:
    """
    Check if all agents in the crew use memory-compatible models.
    
    Returns:
        Tuple of (is_compatible, incompatible_models)
        - is_compatible: True if all agents use compatible models
        - incompatible_models: List of incompatible model names found
        
    Logic:
        - Get models for all three agents (senior_developer, security_engineer, tech_lead)
        - Check each model for compatibility
        - Return False if any model is incompatible
        - Return list of incompatible models for logging
        
    Example:
        >>> check_crew_memory_compatibility()
        (True, [])
        >>> # With SENIOR_DEVELOPER_MODEL=gpt-5-codex
        >>> check_crew_memory_compatibility()
        (False, ['gpt-5-codex'])
    """
    pass
```

### 3. Crew Memory Configuration (crew.py)

Modified crew method to use compatibility check:

```python
@crew
def crew(self) -> Crew:
    """Creates the CodeReviewCrew crew with automatic memory compatibility detection"""
    from crewai.memory import ShortTermMemory, EntityMemory
    import logging
    
    # Check if all agents use memory-compatible models
    memory_compatible, incompatible_models = check_crew_memory_compatibility()
    
    # Determine memory setting
    enable_memory = memory_compatible
    
    # Log warning if memory is disabled due to incompatibility
    if not memory_compatible:
        models_str = ", ".join(set(incompatible_models))
        logging.warning(
            f"CrewAI memory disabled: The following models are incompatible with "
            f"CrewAI memory: {models_str}. The crew will function normally without "
            f"memory features. See docs/TROUBLESHOOTING.md for more information."
        )
    
    # Create crew with determined memory setting
    crew_config = {
        "agents": self.agents,
        "tasks": self.tasks,
        "process": Process.sequential,
        "verbose": True,
        "memory": enable_memory,
    }
    
    # Add memory components if enabled
    if enable_memory:
        crew_config["short_term_memory"] = ShortTermMemory()
        crew_config["entity_memory"] = EntityMemory()
        crew_config["long_term_memory"] = None
    
    return Crew(**crew_config)
```

## Data Models

No new Pydantic models are required. The feature uses:
- `MEMORY_INCOMPATIBLE_MODELS`: List of strings (model name patterns)
- `is_model_memory_compatible()`: Returns `bool`
- `check_crew_memory_compatibility()`: Returns `tuple[bool, list[str]]`

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After reviewing the prework, I identify these redundancies:
- Properties 1.1, 5.1 are identical (all compatible models enable memory)
- Properties 1.2, 5.2, 5.3 are related (any incompatible model disables memory)
- Properties 1.4 and 3.3 are identical (logging when memory disabled)
- Properties 4.3, 6.1, 6.2 are all about default behavior (no config → memory enabled)

Consolidated properties:
- Combine 1.1 and 5.1 into single property about compatible models
- Combine 1.2, 5.2, 5.3 into single property about incompatible models
- Combine 1.4 and 3.3 into single property about logging
- Combine 4.3, 6.1, 6.2 into single property about default behavior
- Keep 1.3, 2.2, 6.3, 6.4 as distinct properties

### Property 1: Compatible models enable memory
*For any* combination of memory-compatible model names assigned to agents, when all agents use compatible models, the crew should be initialized with memory enabled
**Validates: Requirements 1.1**

### Property 2: Incompatible models disable memory
*For any* combination of model assignments where at least one agent uses a memory-incompatible model, the crew should be initialized with memory disabled
**Validates: Requirements 1.2**

### Property 3: Unknown models assumed compatible
*For any* model name not in the compatibility registry, the system should treat it as compatible and enable memory if all other agents also use compatible models
**Validates: Requirements 1.3**

### Property 4: Incompatibility logging
*For any* crew initialization where memory is disabled due to incompatible models, a warning message should be logged indicating which models caused the incompatibility and including a link to documentation
**Validates: Requirements 1.4, 3.2, 3.4**

### Property 5: Codex pattern detection
*For any* model name containing "codex" (case-insensitive), the system should classify it as memory-incompatible
**Validates: Requirements 2.2**

### Property 6: Case-insensitive matching
*For any* model name in the incompatibility registry, the system should detect it regardless of case (e.g., "CODEX", "Codex", "codex" all detected)
**Validates: Requirements 6.3**

### Property 7: Default behavior without configuration
*For any* crew initialization where no models are explicitly configured, the system should assume CrewAI defaults are compatible and enable memory
**Validates: Requirements 4.3, 6.1**

### Property 8: Error handling fallback
*For any* error encountered during compatibility checking, the system should default to enabling memory and log a warning
**Validates: Requirements 6.4**

## Error Handling

### Compatibility Check Errors

If an error occurs during compatibility checking:
1. Log a warning about the error
2. Default to enabling memory (safe fallback)
3. Continue crew initialization normally

### Invalid Model Names

When model names are None, empty, or whitespace:
1. Treat as "using CrewAI default"
2. Assume compatible
3. Enable memory if all other agents also compatible

### Registry Updates

When developers discover new incompatible models:
1. Add pattern to `MEMORY_INCOMPATIBLE_MODELS` list
2. No configuration file changes needed
3. Automatic detection on next run

## Testing Strategy

### Unit Testing

Unit tests will verify:
- `is_model_memory_compatible()` correctly identifies compatible models
- `is_model_memory_compatible()` correctly identifies incompatible models (codex patterns)
- `is_model_memory_compatible()` handles None/empty values correctly
- `check_crew_memory_compatibility()` returns correct results for various model combinations
- Case-insensitive matching works correctly

Example unit tests:
```python
def test_compatible_model():
    """Test that standard models are compatible"""
    assert is_model_memory_compatible("gpt-4o-mini") == True
    assert is_model_memory_compatible("gpt-4o") == True

def test_codex_model_incompatible():
    """Test that codex models are incompatible"""
    assert is_model_memory_compatible("gpt-5-codex") == False
    assert is_model_memory_compatible("gpt-5.1-codex-mini") == False

def test_case_insensitive_matching():
    """Test that matching is case-insensitive"""
    assert is_model_memory_compatible("GPT-5-CODEX") == False
    assert is_model_memory_compatible("Gpt-5-Codex") == False

def test_none_model_compatible():
    """Test that None (CrewAI default) is compatible"""
    assert is_model_memory_compatible(None) == True
    assert is_model_memory_compatible("") == True
```

### Property-Based Testing

Property-based tests will use Hypothesis to verify:

**Property Test 1: Compatible models enable memory**
- Generate random combinations of compatible model names
- Configure agents with these models
- Verify memory is enabled
- Run minimum 100 iterations
- **Feature: memory-compatibility, Property 1: Compatible models enable memory**

**Property Test 2: Incompatible models disable memory**
- Generate random combinations where at least one model is incompatible
- Configure agents with these models
- Verify memory is disabled
- Run minimum 100 iterations
- **Feature: memory-compatibility, Property 2: Incompatible models disable memory**

**Property Test 3: Unknown models assumed compatible**
- Generate random model names not in registry
- Configure agents with these models
- Verify memory is enabled
- Run minimum 100 iterations
- **Feature: memory-compatibility, Property 3: Unknown models assumed compatible**

**Property Test 4: Incompatibility logging**
- Generate random incompatible model configurations
- Initialize crew and capture logs
- Verify warning message appears with correct model names
- Run minimum 100 iterations
- **Feature: memory-compatibility, Property 4: Incompatibility logging**

**Property Test 5: Codex pattern detection**
- Generate random model names containing "codex"
- Verify all are detected as incompatible
- Run minimum 100 iterations
- **Feature: memory-compatibility, Property 5: Codex pattern detection**

**Property Test 6: Case-insensitive matching**
- Generate random case variations of incompatible models
- Verify all variations are detected
- Run minimum 100 iterations
- **Feature: memory-compatibility, Property 6: Case-insensitive matching**

**Property Test 7: Default behavior without configuration**
- Test crew initialization with no model configuration
- Verify memory is enabled
- Run minimum 100 iterations
- **Feature: memory-compatibility, Property 7: Default behavior without configuration**

**Property Test 8: Error handling fallback**
- Simulate errors during compatibility checking
- Verify memory is enabled and warning is logged
- Run minimum 100 iterations
- **Feature: memory-compatibility, Property 8: Error handling fallback**

### Integration Testing

Integration tests will verify:
- Full crew execution with compatible models (memory enabled)
- Full crew execution with incompatible models (memory disabled)
- Mixed model configurations work correctly
- Logging output is correct
- Crew functions normally with memory disabled
- Backward compatibility with existing configurations

## Implementation Notes

### Backward Compatibility

The implementation maintains 100% backward compatibility:
- Current behavior (memory=False) is preserved when incompatible models are used
- If no models are configured, memory is enabled (assuming CrewAI defaults are compatible)
- Existing tests will pass without modification
- No breaking changes to API or configuration

### Performance Considerations

- Compatibility check happens once during crew initialization
- Minimal performance impact (simple string matching)
- No additional API calls or network requests
- Registry lookup is O(n) where n is number of patterns (very small)

### Security Considerations

- No sensitive data in compatibility registry
- Model names are not user input (come from environment variables)
- Safe fallback behavior on errors

### Logging Strategy

Log messages follow this format:
```
WARNING: CrewAI memory disabled: The following models are incompatible with CrewAI memory: gpt-5-codex. The crew will function normally without memory features. See docs/TROUBLESHOOTING.md for more information.
```

Deduplication: If multiple agents use the same incompatible model, it appears only once in the log message.

Documentation: Detailed information about memory compatibility will be added to `docs/TROUBLESHOOTING.md` rather than `.env.example` to keep configuration files simple and focused.

### Future Extensibility

This design can be extended to support:
- Additional incompatible model patterns as discovered
- Per-agent memory compatibility (if CrewAI adds this feature)
- External compatibility registry (JSON/YAML file)
- Automatic compatibility testing against CrewAI versions
- Memory compatibility for other LLM providers (Anthropic, etc.)

### Known Incompatible Models

Based on current knowledge:
- `gpt-5-codex`
- `gpt-5.1-codex`
- `gpt-5.1-codex-mini`
- Any model containing "codex" in the name

This list will be updated as new incompatibilities are discovered.
