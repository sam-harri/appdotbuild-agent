# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

This project implements an AI codegen agent system with various components for handling API interactions, core logic, and specific agent implementations. The system is built primarily in Python with some TypeScript components.

Refer to `agent/architecture.puml` for a visual representation of the system architecture.

## Project Structure

- `agent` - Contains the main codegen agent code
  - `api` - IO layer for the agent
    - `agent_server` - API of the agent server
      - `models.py` - Models for the agent server consistent with agent_api.tsp
      - `agent_api.tsp` - Server type specification for the agent server
      - `async_server.py` - Agent server implementation
    - `cli` - CLI entrypoint
  - `core` - Core framework logic (base classes, state machine, etc.)
  - `trpc_agent` - Agent for fullstack code generation (new agents follow this pattern)
  - `llm` - LLM wrappers
  - `stash_bot` - Deprecated!
  - `log.py` - Global logging and tracing

## Development Workflow

### Setup and Installation

*[Add any specific setup instructions here]*

### Build/Test/Lint Commands

Commands should typically be run from the `./agent` directory:

- **Run all tests**: `uv run pytest -v .`
- **Lint code**: `uv run ruff check` 
- **Format code**: `uv run ruff format`
- **Run tests in isolated env**: `docker build --target test -t agent-test:latest . && docker run --rm agent-test:latest`

### CI and Tests

We use GitHub Actions, triggered on PRs and pushes to main. The workflow configuration is in `.github/workflows/build_and_test.yml`.

## Code Style Guidelines

### Python

#### Formatting and Structure
- **Line Length**: 120 characters max
- **Imports**: Standard library → third-party → local modules
- **Docstrings**: Use triple double quotes (`"""`)

#### Naming Conventions
- **Variables/Functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **JSON Keys/API Payload Fields**: `PascalCase` (must be hidden behind models.py with from_json/to_json methods)

#### Language Features
- **Types**: Use modern typing: `def func(param: str | None = None)` not `param: str = None`
- **Async Code**: Use `anyio` over `asyncio`
- **Pattern Matching**: Prefer `match/case` over lengthy if/elif chains
- **Quotes**: 
  - Single quotes (`'`) for strings without special characters/apostrophes
  - Double quotes (`"`) for strings with special characters/apostrophes

#### Error Handling and Logging
- **Logging**: Use `logger = get_logger(__name__)` 
- **Error Handling**: Prefer `logger.exception("message")` over `logger.error(str(e))`

#### Testing
- **Framework**: Use `pytest` for unit tests
- **Mocks**: Avoid mocks unless explicitly required

### TypeScript

- **Types**: Use explicit interfaces and Zod for schema validation
- **Variables**: Prefer `const` over `let`
- **Naming**: 
  - Variables/Functions: `camelCase`
  - Types/Interfaces: `PascalCase`
- **Imports**: No renamed imports

## Common Tasks and Examples

*[Add examples of common development tasks, like adding a new agent, extending the API, etc.]*

## Known Issues and Workarounds

*[Document any known issues or quirks in the codebase that Claude should be aware of]*

## Contributing Guidelines

*[Add any specific guidelines for contributing to the project]*
