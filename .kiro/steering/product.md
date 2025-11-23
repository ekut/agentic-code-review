# Product Overview

Agentic Code Review is an automated pull request review system powered by CrewAI. It analyzes code changes for quality issues and security vulnerabilities, then makes intelligent decisions about whether to approve, request changes, or escalate to human review.

The system uses a multi-agent approach with three specialized roles:
- **Senior Developer**: Evaluates code quality, style, and maintainability
- **Security Engineer**: Identifies security vulnerabilities and assesses risk levels
- **Tech Lead**: Synthesizes findings and makes final approval decisions

The flow intelligently routes simple changes through a lightweight review while complex changes trigger a full crew analysis with web research capabilities for security best practices.
