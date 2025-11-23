# Development Standards

## Documentation and Code Language

All documentation in the repository, as well as comments inside the code, must be written in English. This includes:
- README files
- Code comments and docstrings
- Commit messages
- Design documents
- API documentation
- Inline code comments

## Backward Compatibility and Testing

A task cannot be considered complete if its implementation causes previously existing tests to fail. This ensures:
- **Backward Compatibility (BC)**: New features must not break existing functionality
- **Test Integrity**: All existing tests must continue to pass after changes
- **Regression Prevention**: Changes that break existing tests indicate potential regressions

### Test Requirements
- All existing tests must pass before marking a task as complete
- If new functionality requires changes to existing tests, those changes must be explicitly documented and justified
- When adding new features that interact with existing code, update affected tests to maintain compatibility
- Cache clearing, mocking adjustments, or other test infrastructure updates are acceptable if they maintain the same test coverage

### Exception Handling
If a task legitimately requires breaking changes:
1. Document the breaking change clearly
2. Update all affected tests
3. Ensure the breaking change is intentional and necessary
4. Get explicit approval before proceeding
