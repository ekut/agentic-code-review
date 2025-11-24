# Design Document: Configurable LLM Models

## Overview

This design document describes the implementation of configurable LLM model selection for each agent in the code review crew. The feature allows users to specify different OpenAI models for the Senior Developer, Security Engineer, and Tech Lead agents through environment variables, while maintaining backward compatibility and preserving CrewAI's default behavior when no configuration is provided.

The implementation follows the existing patterns in the codebase:
- Environment variable management through `utils.py`
- Agent initialization using the `@agent` decorator pattern
- Minimal changes to existing code structure

## Architecture

### High-Level Design

The configuration system consists of three main components:

1. **Environment Variable Layer**: New environment variables in `.env` file for each agent's model
2. **Configuration Loader**: New utility functions in `utils.py` to load and validate model configurations
3. **Agent Initialization**: Modified agent methods in `crew.py` to use configured models

```
┌─────────────────┐
│   .env file     │
│  (user config)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   utils.py      │
│ (load & validate│
│   model config) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    crew.py      │
│ (apply models   │
│  to agents)     │
└─────────────────┘
```

### Configuration Flow

1. Application starts
2. `utils.py` loads environment variables
3. For each agent, check if model is configured
4. If configured and valid: pass `llm` parameter to Agent
5. If not configured or invalid: omit `llm` parameter (CrewAI default)
6. Agents are initialized with appropriate models

## Components and Interfaces

### 1. Environment Variables

New environment variables to be added to `.env`:

```bash
# LLM Model Configuration (Optional)
# If not set, CrewAI will use its default model selection
# Common options: gpt-4o, gpt-4o-mini, gpt-3.5-turbo, gpt-4-turbo

# Model for Senior Developer agent (code quality analysis)
SENIOR_DEVELOPER_MODEL=gpt-4o-mini

# Model for Security Engineer agent (security vulnerability detection)
SECURITY_ENGINEER_MODEL=gpt-4o-mini

# Model for Tech Lead agent (final decision making)
TECH_LEAD_MODEL=gpt-4o-mini
```

### 2. Utility Functions (utils.py)

New functions to be added:

```python
def get_agent_model(agent_name: str) -> str | None:
    """
    Get configured LLM model for a specific agent.
    
    Args:
        agent_name: Name of the agent (e.g., "senior_developer", "security_engineer", "tech_lead")
    
    Returns:
        Model name if configured and valid, None otherwise
        
    Example:
        >>> get_agent_model("senior_developer")
        'gpt-4o-mini'
        >>> get_agent_model("tech_lead")  # Not configured
        None
    """
    pass

def get_senior_developer_model() -> str | None:
    """Get model for Senior Developer agent from SENIOR_DEVELOPER_MODEL env var."""
    pass

def get_security_engineer_model() -> str | None:
    """Get model for Security Engineer agent from SECURITY_ENGINEER_MODEL env var."""
    pass

def get_tech_lead_model() -> str | None:
    """Get model for Tech Lead agent from TECH_LEAD_MODEL env var."""
    pass
```

### 3. Agent Initialization (crew.py)

Modified agent methods:

```python
@agent
def senior_developer(self) -> Agent:
    model = get_senior_developer_model()
    agent_config = {
        "config": self.agents_config["senior_developer"],
    }
    if model:
        agent_config["llm"] = model
    return Agent(**agent_config)

@agent
def security_engineer(self) -> Agent:
    model = get_security_engineer_model()
    agent_config = {
        "config": self.agents_config["security_engineer"],
        "tools": [
            SerperDevTool(search_url="https://owasp.org",
                          base_url=os.getenv("DLAI_SERPER_BASE_URL", "https://google.serper.dev")),
            ScrapeWebsiteTool()
        ],
    }
    if model:
        agent_config["llm"] = model
    return Agent(**agent_config)

@agent
def tech_lead(self) -> Agent:
    model = get_tech_lead_model()
    agent_config = {
        "config": self.agents_config["tech_lead"],
    }
    if model:
        agent_config["llm"] = model
    return Agent(**agent_config)
```

## Data Models

No new data models are required. The feature uses existing Python types:
- `str | None` for model names
- Environment variables as strings
- Agent configuration dictionaries

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Acceptance Criteria Testing Prework

1.1 WHEN a user sets environment variables for agent models THEN the system SHALL use the specified models for the corresponding agents
  Thoughts: This is a rule that should apply to all valid model names. We can test this by setting environment variables to various valid OpenAI model names, initializing agents, and verifying they use the configured models.
  Testable: yes - property

1.2 WHEN a user does not set an environment variable for a specific agent THEN the system SHALL omit the llm parameter and rely on CrewAI's default behavior
  Thoughts: This is testing what happens when configuration is absent. We can test by not setting environment variables and verifying the llm parameter is not passed to Agent initialization.
  Testable: yes - property

1.3 WHEN a user provides an invalid or empty model name THEN the system SHALL omit the llm parameter and rely on CrewAI's default behavior
  Thoughts: This is testing error handling for invalid inputs. We can test with empty strings, whitespace-only strings, and verify the system falls back correctly.
  Testable: yes - property

1.4 WHEN the application starts THEN the system SHALL load model configurations from environment variables before initializing agents
  Thoughts: This is about the order of operations. We can test by mocking environment loading and verifying it happens before agent creation.
  Testable: yes - example

1.5 WHERE model configuration is needed, THE system SHALL support separate configuration for each of the three agents
  Thoughts: This is testing that each agent can have independent configuration. We can test by setting different models for each agent and verifying they're applied correctly.
  Testable: yes - property

2.1 WHEN a user views the `.env.example` file THEN the system SHALL provide example environment variable names for all three agent models
  Thoughts: This is about documentation content, not runtime behavior.
  Testable: no

2.2 WHEN a user views the `.env.example` file THEN the system SHALL include comments explaining the purpose of each model configuration variable
  Thoughts: This is about documentation content, not runtime behavior.
  Testable: no

2.3 WHEN a user views the `.env.example` file THEN the system SHALL list common OpenAI model options as examples
  Thoughts: This is about documentation content, not runtime behavior.
  Testable: no

2.4 WHEN a user reads the documentation THEN the system SHALL explain the trade-offs between different model choices
  Thoughts: This is about documentation content, not runtime behavior.
  Testable: no

3.1 WHEN the model configuration feature is implemented THEN the system SHALL maintain backward compatibility with existing code
  Thoughts: This is testing that existing functionality still works. We can test by running existing tests and verifying they all pass.
  Testable: yes - property

3.2 WHEN no environment variables are set THEN the system SHALL behave identically to the current implementation
  Thoughts: This is a specific case of backward compatibility. We can test by comparing behavior with and without the feature when no config is set.
  Testable: yes - example

3.3 WHEN the system loads model configurations THEN the system SHALL use the existing `utils.py` module pattern for environment variable access
  Thoughts: This is about code structure, not functional behavior.
  Testable: no

3.4 WHEN agents are initialized THEN the system SHALL apply the configured models without requiring changes to the agent decorator pattern
  Thoughts: This is about implementation approach, not functional behavior.
  Testable: no

3.5 WHEN the crew is created THEN the system SHALL maintain all existing functionality including tools, guardrails, and async execution
  Thoughts: This is testing that existing features still work. We can verify tools, guardrails, and async execution are preserved.
  Testable: yes - property

4.1 WHEN tests are executed THEN the system SHALL allow mocking or overriding model configurations
  Thoughts: This is about test infrastructure capability.
  Testable: no

4.2 WHEN a test sets specific model environment variables THEN the system SHALL use those models in the test execution
  Thoughts: This is the same as 1.1 but in a test context. Already covered.
  Testable: yes - property

4.3 WHEN tests verify model configuration THEN the system SHALL provide a way to inspect which model each agent is using
  Thoughts: This is about test observability. We need to be able to check what model was configured.
  Testable: yes - example

4.4 WHEN the system loads model configurations THEN the system SHALL handle missing or malformed environment variables gracefully without crashing
  Thoughts: This is testing error handling. We can test with various invalid inputs and ensure no exceptions are raised.
  Testable: yes - property

5.1 WHEN no model environment variables are configured THEN the system SHALL NOT pass the llm parameter to Agent initialization
  Thoughts: This is the same as 1.2, testing the absence of configuration.
  Testable: yes - property

5.2 WHEN the llm parameter is omitted THEN CrewAI SHALL use its own default model selection logic
  Thoughts: This is testing CrewAI's behavior, not our code. We can only verify we don't pass the parameter.
  Testable: no

5.3 WHEN upgrading CrewAI versions THEN the system SHALL automatically benefit from any changes to CrewAI's default model
  Thoughts: This is about future compatibility, not testable in current implementation.
  Testable: no

### Property Reflection

After reviewing all testable properties, I identify the following redundancies:

- Properties 1.2 and 5.1 are identical (both test that no llm parameter is passed when not configured)
- Property 4.2 is redundant with 1.1 (same behavior, just in test context)
- Property 1.4 is more of an implementation detail than a unique property

Consolidated properties:
- Combine 1.2 and 5.1 into single property about default behavior
- Remove 4.2 as it's covered by 1.1
- Keep 1.4 as an example since it's about initialization order

### Property 1: Model configuration is applied correctly
*For any* valid OpenAI model name, when set as an environment variable for an agent, that agent should be initialized with the specified model
**Validates: Requirements 1.1**

### Property 2: Default behavior when not configured
*For any* agent, when no model environment variable is set or the value is empty/whitespace, the agent should be initialized without the llm parameter
**Validates: Requirements 1.2, 5.1**

### Property 3: Invalid model names fall back to default
*For any* invalid or malformed model name, the system should omit the llm parameter and not crash
**Validates: Requirements 1.3, 4.4**

### Property 4: Independent agent configuration
*For any* combination of model assignments to the three agents, each agent should use its own configured model independently
**Validates: Requirements 1.5**

### Property 5: Backward compatibility preserved
*For any* existing test or functionality, the system should continue to work correctly after adding model configuration
**Validates: Requirements 3.1, 3.5**

## Error Handling

### Invalid Model Names

When an invalid or empty model name is provided:
1. The utility function returns `None`
2. The agent is initialized without the `llm` parameter
3. CrewAI uses its default model selection
4. No error is raised, ensuring graceful degradation

### Missing Environment Variables

When environment variables are not set:
1. `os.getenv()` returns `None`
2. The utility function returns `None`
3. Same behavior as invalid model names

### Environment Loading Failures

If `.env` file is missing or malformed:
1. `load_dotenv()` handles this gracefully
2. Environment variables simply won't be set
3. System falls back to CrewAI defaults

## Testing Strategy

### Unit Testing

Unit tests will verify:
- `get_agent_model()` returns correct values for valid inputs
- `get_agent_model()` returns `None` for invalid/missing inputs
- Each agent-specific getter function works correctly
- Environment variable loading happens correctly

Example unit tests:
```python
def test_get_agent_model_with_valid_config(monkeypatch):
    """Test that valid model configuration is returned"""
    monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "gpt-4o")
    assert get_senior_developer_model() == "gpt-4o"

def test_get_agent_model_with_empty_config(monkeypatch):
    """Test that empty configuration returns None"""
    monkeypatch.setenv("SENIOR_DEVELOPER_MODEL", "")
    assert get_senior_developer_model() is None

def test_get_agent_model_without_config():
    """Test that missing configuration returns None"""
    assert get_senior_developer_model() is None
```

### Property-Based Testing

Property-based tests will use the Hypothesis library (already in use based on `.hypothesis` directory) to verify:

**Property Test 1: Model configuration application**
- Generate random valid OpenAI model names
- Set environment variables
- Initialize agents
- Verify configured models are used
- **Feature: configurable-llm-models, Property 1: Model configuration is applied correctly**

**Property Test 2: Default behavior**
- Generate random combinations of set/unset environment variables
- Initialize agents
- Verify agents without config don't have llm parameter
- **Feature: configurable-llm-models, Property 2: Default behavior when not configured**

**Property Test 3: Invalid input handling**
- Generate random invalid strings (empty, whitespace, special characters)
- Set as environment variables
- Initialize agents
- Verify no crashes and fallback to default
- **Feature: configurable-llm-models, Property 3: Invalid model names fall back to default**

**Property Test 4: Independent configuration**
- Generate random model assignments for each agent
- Set environment variables
- Initialize all agents
- Verify each uses its own model
- **Feature: configurable-llm-models, Property 4: Independent agent configuration**

**Property Test 5: Backward compatibility**
- Run existing test suite with and without configuration
- Verify all tests pass in both cases
- **Feature: configurable-llm-models, Property 5: Backward compatibility preserved**

### Integration Testing

Integration tests will verify:
- Full flow works with custom models
- Full flow works without configuration (backward compatibility)
- Mixed configuration (some agents configured, others not)
- Model configuration doesn't break tools, guardrails, or async execution

### Testing Configuration

- Property-based tests will run minimum 100 iterations
- Tests will use `pytest` with `hypothesis` plugin
- Environment variable mocking via `pytest-monkeypatch`
- Each property test explicitly references its design document property

## Implementation Notes

### Backward Compatibility

The implementation maintains 100% backward compatibility:
- If no environment variables are set, behavior is identical to current implementation
- Existing tests will pass without modification
- No breaking changes to API or configuration

### Performance Considerations

- Environment variable loading happens once at module import time
- No performance impact on agent initialization
- No additional API calls or network requests

### Security Considerations

- Model names are validated before use
- No sensitive data in environment variables (model names are public)
- Falls back to safe defaults on any error

### Future Extensibility

This design can be extended to support:
- Other LLM providers (Anthropic, Cohere, etc.)
- Per-task model configuration
- Dynamic model selection based on complexity
- Model configuration via config files (YAML/JSON)
