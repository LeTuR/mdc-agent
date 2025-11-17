<!--
SYNC IMPACT REPORT
===================
Version Change: 2.0.1 → 2.1.0
Action: Minor amendment - Python tooling migration to UV and Python 3.14

Modified Principles:
  - NEW Principle VI: Python Tooling & Environment (NON-NEGOTIABLE)
    * Mandates UV as package manager (replaces Poetry)
    * Mandates Python 3.14 as minimum version
    * Mandates pytest (latest) for testing
    * Specifies uv.lock for reproducible builds

Added Sections:
  - Principle VI: Python Tooling & Environment

Removed Sections: None

Removed Requirements:
  - Poetry usage (replaced by UV)
  - Python 3.11 (upgraded to Python 3.14)

Templates & Artifacts Requiring Updates:
  ⚠ plan.md - Update Python 3.11 → 3.14, Poetry → UV
  ⚠ tasks.md - Update T002 (Poetry init → UV init), dependencies tasks
  ⚠ quickstart.md - Replace Poetry installation/usage with UV
  ⚠ research.md - Update technology stack references
  ⚠ CLAUDE.md - Update framework and language version
  ⚠ All GitHub issues (#1-#86) - Update references in issue descriptions

Follow-up TODOs:
  - Update all spec artifacts to reference UV instead of Poetry
  - Update GitHub issues created with Poetry references
  - Regenerate tasks.md with UV-based setup instructions
  - Update quickstart guide with UV commands

Previous Versions:
  - v2.0.1 (2025-11-17): Add semantic-release framework reference
  - v2.0.0 (2025-11-17): TDD adoption and GitHub Actions CI/CD specification
  - v1.0.0 (2025-11-17): Initial constitution ratification
===================
-->

# MDC Agent API Constitution

## Core Principles

### I. API-First Design

All functionality MUST be exposed through well-defined RESTful API endpoints. API contracts are the primary interface specification.

**Rules**:
- Every feature starts with OpenAPI/contract definition
- Endpoints MUST follow RESTful conventions (resource-oriented, proper HTTP verbs)
- Request/response schemas MUST be explicitly typed and validated
- API versioning MUST be implemented (URL-based: `/v1/`, `/v2/`)
- Breaking changes require new major version

**Rationale**: API contracts serve as the source of truth for LLM agents and enable contract testing. Explicit schemas prevent ambiguity that could confuse agent interpretation.

### II. Agent-Optimized Interface

API responses MUST be optimized for LLM agent consumption with clear, structured, and actionable data formats.

**Rules**:
- Response payloads MUST include:
  - Structured data (JSON) with consistent field naming (snake_case)
  - Actionable fields (e.g., `recommendation_id`, `exemption_status`)
  - Human-readable summaries where appropriate
- Error responses MUST be consistent with `error_code`, `message`, and `details`
- Pagination MUST follow standard patterns (limit/offset or cursor-based)
- Response size MUST be reasonable (<1MB per request) to fit LLM context windows

**Rationale**: LLM agents require predictable, well-structured data. Optimized responses reduce token usage and parsing errors.

### III. Conventional Commits & Semantic Release (NON-NEGOTIABLE)

All commits MUST follow Conventional Commits specification. Releases are automated via semantic-release based on commit messages.

**Rules**:
- Commit format: `<type>(<scope>): <subject>`
  - Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`
  - Breaking changes: include `BREAKING CHANGE:` in footer or `!` after type
- Pre-commit hooks MUST enforce:
  - Commit message format validation
  - Code linting and formatting
  - Test execution (fast unit tests only)
- Semantic-release framework: https://github.com/semantic-release/semantic-release
- Semantic-release MUST run on main branch merges
- Version bumps:
  - `feat:` → MINOR version bump
  - `fix:` → PATCH version bump
  - `BREAKING CHANGE:` → MAJOR version bump

**Rationale**: Automated versioning ensures reliable release process. Conventional commits enable automatic changelog generation and clear commit history.

### IV. Azure MDC Integration

Integration with Azure Microsoft Defender for Cloud MUST be clean, abstracted, and resilient.

**Rules**:
- Azure SDK interactions MUST be encapsulated in dedicated service layer
- Retry logic MUST be implemented for transient Azure API failures (exponential backoff)
- Azure credentials MUST be managed via Azure Identity (DefaultAzureCredential)
- API MUST NOT expose raw Azure API responses; transform to agent-optimized format
- Support for:
  - Fetching and processing security recommendations
  - Creating and managing exemptions
  - Managing policy assignments
  - Proposing policy configuration changes

**Rationale**: Clean abstraction prevents Azure API changes from cascading through the entire application. Resilience handles Azure API rate limits and transient failures gracefully.

### V. Test-Driven Development (TDD) (NON-NEGOTIABLE)

All implementation MUST follow Test-Driven Development practice. Tests are written and verified to fail before any implementation code is written.

**Rules**:
- Red-Green-Refactor cycle MUST be followed:
  1. **Red**: Write test that fails (no implementation exists yet)
  2. **Green**: Write minimal code to make test pass
  3. **Refactor**: Improve code while keeping tests green
- Tests MUST be written in this order:
  1. Contract tests (API endpoint contracts)
  2. Integration tests (end-to-end workflows)
  3. Unit tests (business logic, if needed)
- Implementation code MUST NOT be written until corresponding test exists and fails
- Coverage thresholds are NOT enforced; focus is on test-first discipline
- CI pipeline MUST fail on:
  - Any test failure
  - Linting errors

**Rationale**: TDD ensures every feature is testable by design and prevents untested code. Writing tests first forces clear thinking about interfaces and behavior. Coverage metrics can create false confidence; test quality and coverage naturally emerge from TDD practice.

### VI. Python Tooling & Environment (NON-NEGOTIABLE)

All Python projects MUST use UV as the package manager and Python 3.14 as the minimum language version.

**Rules**:
- Package manager: UV (https://github.com/astral-sh/uv) MUST be used instead of Poetry/pip
- Python version: Python 3.14 or later MUST be used
- Testing framework: pytest (latest version) MUST be used for all tests
- Dependency management:
  - Dependencies MUST be declared in `pyproject.toml`
  - Lock file (`uv.lock`) MUST be committed for reproducible builds
  - Use `uv sync` for installing dependencies
  - Use `uv add` for adding new dependencies
- Virtual environments:
  - UV automatically manages virtual environments
  - Use `uv run` to execute commands in the virtual environment
- Pre-commit hooks MUST work with UV-managed environment
- CI/CD workflows MUST use UV for dependency installation

**Rationale**: UV is significantly faster than Poetry (10-100x for some operations) and provides better dependency resolution. Python 3.14 includes performance improvements and modern language features. UV's speed improves developer experience and CI/CD pipeline performance.

## Development Workflow & CI/CD

### Branch Strategy
- **main**: Production-ready code, protected, requires PR approval
- **feature branches**: Named `feat/description` or `fix/description`
- PRs MUST pass all CI checks before merge

### TDD Workflow
For every feature or bug fix:
1. Write contract/integration test that demonstrates the requirement
2. Verify test fails (RED)
3. Implement minimal code to pass test (GREEN)
4. Refactor for quality while keeping tests green (REFACTOR)
5. Commit with conventional commit message
6. Repeat for next requirement

### Pre-commit Hooks
All developers MUST have pre-commit hooks installed and active:
- `commitlint`: Enforce conventional commit messages
- `ruff`: Python code formatting and linting (replaces black + flake8)
- `mypy`: Type checking
- Fast unit tests (< 10 seconds total)
- Run via: `uv run pre-commit install`

### CI Pipeline (GitHub Actions - MANDATORY)

All CI/CD MUST be implemented using GitHub Actions workflows.

**Workflow: `.github/workflows/ci.yml`**

Triggers: Pull requests and pushes to main

Jobs:
1. **Lint and Format**
   - Install dependencies with `uv sync`
   - Run code formatter and linter (`uv run ruff check` and `uv run ruff format`)
   - Run type checker (`uv run mypy`)
2. **Test**
   - Run all tests (unit, contract, integration)
   - Fail fast on any test failure
3. **Build**
   - Build Docker image (if applicable)
   - Verify build succeeds
4. **Security**
   - Dependency vulnerability scanning
   - SAST (static analysis security testing)

**Workflow: `.github/workflows/release.yml`**

Triggers: Push to main branch (after PR merge)

Jobs:
1. **Semantic Release**
   - Run semantic-release (https://github.com/semantic-release/semantic-release)
   - Generate changelog
   - Create git tag
   - Create GitHub release
2. **Publish Artifacts**
   - Build and push Docker image with version tag
   - Publish packages (if applicable)

**Required Secrets**:
- `GITHUB_TOKEN`: Automatically provided
- `AZURE_CREDENTIALS`: For Azure deployment (if needed)
- Additional secrets as required

## Quality Gates

### Pull Request Requirements
PRs MUST NOT be merged unless:
- All CI checks pass (green)
- At least one approval from code owner
- No unresolved comments
- Conventional commit format validated
- All tests pass (TDD cycle completed)

### Release Gates
Releases MUST NOT proceed unless:
- All tests pass on main branch
- semantic-release successfully determines version
- No critical security vulnerabilities in dependencies
- GitHub Actions workflows complete successfully

## Governance

### Amendment Process
1. Propose constitution change via PR to `.specify/memory/constitution.md`
2. Update dependent templates (plan-template.md, tasks-template.md) in same PR
3. Require approval from at least 2 maintainers
4. Update `CONSTITUTION_VERSION` following semantic versioning
5. Document rationale in Sync Impact Report (HTML comment at top of file)

### Version Semantics
- **MAJOR**: Principle removal, incompatible governance changes
- **MINOR**: New principle added, expanded guidance
- **PATCH**: Clarifications, typos, non-semantic fixes

### Compliance Review
- Constitution compliance MUST be verified in every PR review
- Violations MUST be justified in `plan.md` Complexity Tracking table
- Unjustified violations MUST block PR merge

### Tooling Enforcement
Where possible, principles MUST be enforced by tooling:
- Pre-commit hooks enforce commit format
- GitHub Actions enforce test passage and linting
- API schema validation enforces contract compliance
- Semantic-release enforces versioning rules

**Version**: 2.1.0 | **Ratified**: 2025-11-17 | **Last Amended**: 2025-11-17
