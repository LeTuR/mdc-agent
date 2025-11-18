# MDC Agent API

LLM-optimized API for Azure Microsoft Defender for Cloud

## Description

This API simplifies interaction between LLM agents and Azure Microsoft Defender for Cloud by providing:

- Retrieval of security recommendations with filtering and pagination
- Creation of security exemptions with proper validation
- Intelligent user assignment leveraging Azure Active User feature
- Automatic email notifications for assignments
- LLM-friendly response formats (snake_case, <1MB responses, structured errors)

## Technology Stack

- **Python 3.14**
- **UV** - Fast Python package manager
- **FastAPI** - Modern web framework
- **Azure SDK** - Integration with Azure Defender for Cloud
- **Pydantic** - Data validation and serialization
- **pytest** - Testing framework
- **ruff** - Linting and formatting

## Quick Start

See [specs/001-mdc-agent-api/quickstart.md](specs/001-mdc-agent-api/quickstart.md) for detailed setup instructions.

## Development

This project follows Test-Driven Development (TDD) practices and uses conventional commits for automated versioning.

See the [constitution](.specify/memory/constitution.md) for development principles and guidelines.

## License

[Add license information]
