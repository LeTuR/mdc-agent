# Quickstart Guide: MDC Agent API

**Feature**: MDC Agent API
**Date**: 2025-11-17
**Purpose**: Get developers up and running with local development environment

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11** or higher
- **Poetry** 1.6+ (Python dependency management)
- **Docker** and **Docker Compose** (for running tests with Testcontainers)
- **Azure CLI** 2.50+ (for local authentication)
- **Git** (for version control)

### Azure Requirements

- **Azure Subscription** with Microsoft Defender for Cloud enabled
- **Defender CSPM Plan** enabled (required for Active User feature)
- **Azure AD Credentials** with appropriate roles:
  - Minimum: **Security Reader** (read recommendations)
  - For exemptions: **Security Administrator** or **Contributor**
  - For assignments: **Security Administrator**, **Owner**, or **Contributor**

## Initial Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd mdc-agent
```

### 2. Install Python Dependencies

```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install

# Activate virtual environment
poetry shell
```

### 3. Configure Azure Authentication

#### Option A: Azure CLI (Development)

```bash
# Login to Azure
az login

# Set default subscription
az account set --subscription <your-subscription-id>

# Verify authentication
az account show
```

#### Option B: Service Principal (CI/CD)

Create a service principal with appropriate permissions:

```bash
# Create service principal
az ad sp create-for-rbac --name "mdc-agent-api-dev" \
  --role "Security Reader" \
  --scopes /subscriptions/<subscription-id>

# Note the output: appId, password, tenant
```

Set environment variables (add to `.env` file):

```bash
AZURE_CLIENT_ID=<appId from output>
AZURE_CLIENT_SECRET=<password from output>
AZURE_TENANT_ID=<tenant from output>
AZURE_SUBSCRIPTION_ID=<your-subscription-id>
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Azure Configuration
AZURE_SUBSCRIPTION_ID=12345678-1234-1234-1234-123456789012
AZURE_TENANT_ID=87654321-4321-4321-4321-210987654321

# Service Principal (optional, if not using Azure CLI)
# AZURE_CLIENT_ID=<service-principal-app-id>
# AZURE_CLIENT_SECRET=<service-principal-password>

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# Azure AD Authentication
AZURE_AD_TENANT_ID=${AZURE_TENANT_ID}
AZURE_AD_CLIENT_ID=<api-app-registration-client-id>
AZURE_AD_AUDIENCE=api://mdc-agent-api

# Feature Flags
ENABLE_ACTIVE_USER=true
```

**Note**: Never commit `.env` files to version control. Add `.env` to `.gitignore`.

### 5. Verify Azure Defender Setup

Check that Defender for Cloud and CSPM plan are enabled:

```bash
# Check Defender for Cloud status
az security pricing show --name VirtualMachines

# Check CSPM plan (required for Active User feature)
az security pricing show --name CloudPosture
```

If CSPM is not enabled:

```bash
az security pricing create --name CloudPosture --tier Standard
```

## Running the API Locally

### Start the Development Server

```bash
# Using Poetry
poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Or if already in Poetry shell
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs (Swagger UI)**: http://localhost:8000/docs
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Test the API

#### Using Swagger UI

1. Navigate to http://localhost:8000/docs
2. Click "Authorize" and provide an Azure AD bearer token
3. Try the `GET /v1/recommendations` endpoint

#### Using curl

```bash
# Get Azure AD token (if using Azure CLI auth)
TOKEN=$(az account get-access-token --resource api://mdc-agent-api --query accessToken -o tsv)

# List recommendations
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/recommendations?limit=10

# Get Active User suggestions
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/v1/active-user/suggestions?recommendation_id=/subscriptions/..."

# Create assignment
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "recommendation_id": "/subscriptions/.../assessments/abc-123",
    "assigned_user_email": "user@contoso.com",
    "due_date": "2025-12-31",
    "grace_period_enabled": true
  }' \
  http://localhost:8000/v1/assignments
```

## Running Tests

### Prerequisites for Testing

Ensure Docker is running (required for Testcontainers):

```bash
docker ps
```

### Run All Tests

```bash
# Run all tests with coverage
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run specific test type
poetry run pytest tests/contract/
poetry run pytest tests/integration/
poetry run pytest tests/unit/
```

### Test-Driven Development Workflow

Per constitution Principle V, follow the **Red-Green-Refactor** cycle:

1. **Red**: Write a failing test

```bash
# Example: Create a new test file
touch tests/unit/test_new_feature.py

# Write test that will fail (no implementation yet)
poetry run pytest tests/unit/test_new_feature.py
# Expected: FAILED (as implementation doesn't exist)
```

2. **Green**: Write minimal code to pass the test

```bash
# Implement feature in src/
poetry run pytest tests/unit/test_new_feature.py
# Expected: PASSED
```

3. **Refactor**: Improve code while keeping tests green

```bash
# Refactor implementation
poetry run pytest tests/unit/test_new_feature.py
# Expected: PASSED (tests still green)
```

### Contract Tests (API Endpoint Contracts)

```bash
# Test that API responses match OpenAPI schema
poetry run pytest tests/contract/ -v
```

### Integration Tests (End-to-End Workflows)

```bash
# Test complete workflows (retrieve → assign → notify)
poetry run pytest tests/integration/ -v
```

### Unit Tests (Business Logic)

```bash
# Test individual services and components
poetry run pytest tests/unit/ -v
```

## Development Tools

### Code Formatting

```bash
# Format code with black
poetry run black src/ tests/

# Sort imports with isort
poetry run isort src/ tests/
```

### Linting

```bash
# Run flake8 linter
poetry run flake8 src/ tests/

# Run mypy type checker
poetry run mypy src/
```

### Pre-commit Hooks

Install pre-commit hooks to ensure code quality:

```bash
# Install pre-commit
poetry run pre-commit install

# Run hooks manually
poetry run pre-commit run --all-files
```

The hooks will run automatically on `git commit` and check:
- Code formatting (black, isort)
- Linting (flake8)
- Type checking (mypy)
- Conventional commit messages

## Common Issues

### Issue: Azure Authentication Fails

**Symptom**: `DefaultAzureCredential failed to retrieve a token`

**Solution**:
1. Verify Azure CLI login: `az account show`
2. Check environment variables in `.env`
3. Ensure service principal has correct permissions
4. Try: `az login --tenant <tenant-id>`

### Issue: CSPM Plan Not Enabled

**Symptom**: `CSPM_PLAN_NOT_ENABLED` error when using Active User endpoints

**Solution**:
```bash
# Enable Defender CSPM plan
az security pricing create --name CloudPosture --tier Standard

# Wait 5-10 minutes for plan to activate
az security pricing show --name CloudPosture
```

### Issue: Permission Denied for Assignments

**Symptom**: `ASSIGNMENT_PERMISSION_DENIED` error

**Solution**:
1. Verify your role: `az role assignment list --assignee <your-email>`
2. Ensure you have one of: Security Administrator, Owner, Contributor
3. Grant role if needed:
```bash
az role assignment create \
  --assignee <your-email> \
  --role "Security Admin" \
  --scope /subscriptions/<subscription-id>
```

### Issue: Docker Not Running (Test Failures)

**Symptom**: `Cannot connect to the Docker daemon` during tests

**Solution**:
```bash
# Start Docker Desktop (macOS/Windows)
# Or start Docker service (Linux)
sudo systemctl start docker

# Verify Docker is running
docker ps
```

### Issue: Poetry Install Fails

**Symptom**: Dependency resolution errors

**Solution**:
```bash
# Clear Poetry cache
poetry cache clear pypi --all

# Update Poetry
poetry self update

# Reinstall dependencies
poetry install --no-cache
```

## Next Steps

### Implement Your First Feature

Following TDD workflow:

1. Review functional requirements in `specs/001-mdc-agent-api/spec.md`
2. Choose a user story to implement
3. Write contract tests first (verify they fail)
4. Write integration tests (verify they fail)
5. Implement minimal code to pass tests
6. Refactor while keeping tests green

### Generate Implementation Tasks

Once planning is complete:

```bash
# Generate task breakdown
/speckit.tasks
```

This will create `specs/001-mdc-agent-api/tasks.md` with dependency-ordered implementation tasks following TDD principles.

### Explore API Contracts

Review the OpenAPI specifications:

- `specs/001-mdc-agent-api/contracts/recommendations.yaml`
- `specs/001-mdc-agent-api/contracts/exemptions.yaml`
- `specs/001-mdc-agent-api/contracts/assignments.yaml`

These define the exact request/response schemas your implementation must match.

## Additional Resources

- **Azure Defender for Cloud Docs**: https://learn.microsoft.com/en-us/azure/defender-for-cloud/
- **Active User Feature**: https://learn.microsoft.com/en-us/azure/defender-for-cloud/active-user
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Azure SDK for Python**: https://learn.microsoft.com/en-us/python/api/overview/azure/
- **Poetry Documentation**: https://python-poetry.org/docs/
- **Conventional Commits**: https://www.conventionalcommits.org/
- **Semantic Release**: https://github.com/semantic-release/semantic-release

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review Azure Defender for Cloud setup in Azure Portal
3. Consult `specs/001-mdc-agent-api/research.md` for technical decisions
4. Open an issue in the repository with detailed error messages
