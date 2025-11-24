# Tech Stack

## Core Technologies
- **Python**: 3.10 - 3.13
- **CrewAI**: 0.203.1 (with tools) - Multi-agent orchestration framework
- **Pydantic**: Data validation and structured outputs
- **dill**: Serialization for flow state persistence

## Build System
- **Package Manager**: uv (modern Python package manager)
- **Build Backend**: hatchling
- **Project Type**: CrewAI Flow

## Key Dependencies
- `crewai[tools]` - Agent framework with tool support
- `crewai_tools` - SerperDevTool, ScrapeWebsiteTool for web research
- `python-dotenv` - Environment variable management
- `pydantic` - Data validation and structured outputs

## Common Commands

```bash
# Run the code review flow
uv run kickoff
# or
uv run run_crew

# Generate flow visualization
uv run plot

# Install dependencies
uv sync

# Run from Python
python -m agentic_code_review.main
```

## Environment Variables
Required in `.env` file:
- `OPENAI_API_KEY` - For LLM calls
- `SERPER_API_KEY` - For web search functionality
- `GITHUB_TOKEN` - For GitHub PR integration
- `DLAI_SERPER_BASE_URL` - Optional, defaults to https://google.serper.dev
- `CREWAI_TESTING` - Set to "true" in code for testing mode

Optional model configuration (per-agent LLM selection):
- `SENIOR_DEVELOPER_MODEL` - Model for Senior Developer agent (default: CrewAI default)
- `SECURITY_ENGINEER_MODEL` - Model for Security Engineer agent (default: CrewAI default)
- `TECH_LEAD_MODEL` - Model for Tech Lead agent (default: CrewAI default)
