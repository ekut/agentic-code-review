# Project Structure

## Directory Layout

```
src/agentic_code_review/
├── main.py                    # Flow definition and entry point
├── utils.py                   # Helper functions (env loading, API keys)
└── crews/
    └── code_review_crew/
        ├── crew.py            # Crew definition with agents and tasks
        ├── config/
        │   ├── agents.yaml    # Agent role definitions
        │   └── tasks.yaml     # Task descriptions and outputs
        └── guardrails/
            └── guardrails.py  # Output validation functions

files/                         # Input PR diff files
├── code_changes.txt
└── code_changes_simple.txt
```

## Architecture Patterns

### Flow-Based Architecture
- Main flow defined in `main.py` using `@persist()` decorator
- State management via Pydantic `ReviewState` model
- Router pattern for conditional execution (`@router`, `@listen`)
- Parallel execution support with `or_()` combinator

### Crew Structure
- Agents defined with `@agent` decorator in `crew.py`
- Tasks defined with `@task` decorator, reference YAML configs
- Sequential process execution
- Async task execution enabled for parallel agent work

### Configuration Pattern
- Agent roles/goals/backstory in `agents.yaml`
- Task descriptions/outputs in `tasks.yaml`
- Structured outputs using Pydantic models (`output_json` parameter)
- Guardrails for output validation

### State Flow
1. `read_pr_file()` - Load PR content
2. `analyze_changes()` - Route to SIMPLE or COMPLEX
3. `simple_review()` or `full_crew_review()` - Execute review
4. `make_final_decision()` - Synthesize results
5. `return_final_answer()` - Output final decision

## Key Conventions

- All `__init__.py` files are empty (package markers only)
- Flow state persisted to `result.dill` and `flow_state.json`
- Project root calculated as `Path(__file__).parent.parent.parent`
- LLM model: `gpt-4o-mini` for all agents and decisions
- Memory enabled for crew to maintain context
- Verbose mode enabled for debugging
