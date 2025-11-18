# Research: MDC Agent API Technical Decisions

**Feature**: MDC Agent API
**Date**: 2025-11-17
**Updated**: 2025-11-17 (Azure Active User Integration)
**Purpose**: Document technical research and decisions for Azure Defender for Cloud integration

## 1. Azure Defender for Cloud SDK Patterns

**Decision**: Use `azure-mgmt-security` SDK with `SecurityCenter` client for recommendation retrieval

**Rationale**:
- Official Microsoft SDK with comprehensive Defender for Cloud API coverage
- Built-in support for pagination, filtering, and Azure authentication
- Active maintenance and Azure support
- Native integration with `azure-identity` for credential management

**Implementation Pattern**:
```python
from azure.mgmt.security import SecurityCenter
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
client = SecurityCenter(credential, subscription_id)

# List recommendations with filtering
recommendations = client.assessments.list(scope=f"/subscriptions/{subscription_id}")
```

**Filtering Approach**:
- SDK provides `scope` parameter for subscription/resource group/resource filtering
- Severity filtering done client-side after retrieval (no SDK filter param)
- Resource type filtering via OData `$filter` parameter where supported

**Alternatives Considered**:
- Direct Azure REST API calls: Rejected - more boilerplate, manual auth, no type safety
- Azure CLI wrapper: Rejected - subprocess overhead, harder to test, no async support

## 2. Azure Exemption API Best Practices

**Decision**: Use `SecurityCenter.assessments_metadata` for exemption management with proper RBAC validation

**Permission Requirements**:
- **Read**: `Security Reader` role or higher
- **Write**: `Security Admin` or `Contributor` role required for exemptions
- Validate permissions before exemption operations to provide clear error messages

**Exemption Workflow**:
1. Retrieve recommendation details to validate it exists
2. Check user has `Security Admin` role on scope
3. Create exemption via `client.assessment_metadata.create_in_subscription()`
4. Set expiration date and justification in metadata

**Best Practices**:
- Always require justification text (min 10 characters)
- Set explicit expiration dates (default 90 days if not specified)
- Validate exemption scope matches recommendation scope
- Log all exemptions for audit trail

**Alternatives Considered**:
- Custom exemption tracking in PostgreSQL: Rejected - must use Azure native exemptions for compliance/audit
- Policy-based exemptions: Not suitable - requires policy management which is out of scope

## 3. Azure Active User Feature Integration

**Decision**: Use Azure Defender for Cloud's native Active User API for intelligent user assignment suggestions and automatic notifications

**Azure Active User API Endpoints**:
```python
from azure.mgmt.security import SecurityCenter

# Get Active User suggestions for a recommendation
suggestions = client.active_user_suggestions.list(
    scope=f"/subscriptions/{subscription_id}/providers/Microsoft.Security/assessments/{assessment_id}"
)

# Assign user to recommendation
assignment = client.active_user_assignments.create_or_update(
    scope=f"/subscriptions/{subscription_id}/providers/Microsoft.Security/assessments/{assessment_id}",
    assigned_user_email=user_email,
    due_date="2025-12-31",
    grace_period_enabled=True
)

# Query assignment history
assignments = client.active_user_assignments.list(
    scope=f"/subscriptions/{subscription_id}"
)
```

**Active User Suggestion Features**:
- Up to 3 user candidates ranked by confidence score
- Based on control plane activity data (resource access patterns)
- Includes user details: name, email, department, role, manager, recent activities
- Confidence score indicates likelihood user is appropriate owner

**Automatic Email Notifications**:
- Azure sends email automatically when assignment is created
- Email includes recommendation details and direct link
- No custom email infrastructure needed
- Notification delivery status tracked by Azure

**Prerequisites**:
- Defender CSPM plan must be enabled on subscription
- User creating assignment needs Security Administrator, Owner, or Contributor role
- Feature availability varies by Azure region

**Rationale**:
- Intelligent suggestions based on actual resource activity (not guessing)
- Automatic email delivery (no custom SMTP/Azure Communication Services needed)
- Native grace period support built into Azure API
- Reduced custom code and maintenance burden
- Better integration with Azure RBAC and compliance

**Alternatives Considered**:
- Custom assignment tracking in PostgreSQL: Rejected - Azure provides native capability
- Manual user selection only: Rejected - Active User suggestions provide intelligence
- Custom email notification system: Rejected - Azure handles this natively

## 4. Azure Active User Assignment Tracking

**Decision**: Query Azure Defender API for assignment history instead of maintaining separate database

**Query Patterns**:
```python
# Get assignments for subscription
assignments = client.active_user_assignments.list(
    scope=f"/subscriptions/{subscription_id}"
)

# Filter by status (active, completed, overdue)
active_assignments = [a for a in assignments if a.status == 'active']
overdue_assignments = [a for a in assignments if a.due_date < datetime.now()]

# Get assignment for specific recommendation
assignment = client.active_user_assignments.get(
    scope=f"/subscriptions/{subscription_id}/providers/Microsoft.Security/assessments/{assessment_id}"
)
```

**Assignment Attributes**:
- `assignment_id`: Azure-generated unique identifier
- `assigned_user_email`, `assigned_user_name`: User details
- `assigner_id`: Who created the assignment
- `assignment_date`, `due_date`: Timeline
- `grace_period_enabled`: Boolean flag
- `assignment_status`: active/completed/overdue
- `notification_sent_timestamp`: When Azure sent email
- `notification_delivery_status`: Delivery confirmation

**No PostgreSQL Needed**:
- Azure is source of truth for assignments
- No need for custom schema or migrations
- Reduced infrastructure complexity
- Native Azure audit trail

**Rationale**:
- Azure API provides all necessary query capabilities
- Eliminates database sync issues
- Reduces operational overhead
- Native integration with Azure logging and monitoring

**Alternatives Considered**:
- PostgreSQL caching layer: Rejected - unnecessary complexity, sync issues
- Local assignment state: Rejected - Azure API is authoritative

## 5. Retry Strategy for Azure API Rate Limiting

**Decision**: Exponential backoff with jitter using `tenacity` library

**Configuration**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from azure.core.exceptions import HttpResponseError

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    retry=retry_if_exception_type(HttpResponseError),
    before_sleep=log_retry_attempt
)
async def call_azure_api():
    # Azure SDK call
    pass
```

**Rate Limit Handling**:
- Detect `429 Too Many Requests` responses
- Parse `Retry-After` header if present
- Exponential backoff: 1s, 2s, 4s, 8s, 16s, max 60s
- Add jitter (±20%) to prevent thundering herd
- Log all retry attempts for monitoring

**Circuit Breaker**: Implement circuit breaker pattern if >10 consecutive failures
- Open circuit: Return cached data or friendly error
- Half-open after 5 minutes: Test with single request
- Close circuit if successful

**Alternatives Considered**:
- Fixed delay retry: Rejected - inefficient, can worsen rate limit issues
- No retry: Rejected - violates constitution requirement for resilience
- Infinite retry: Rejected - can cause request timeout, need max attempts

## 6. Authentication with Azure DefaultAzureCredential

**Decision**: Use `DefaultAzureCredential` with support for multiple auth methods

**Credential Chain** (in order):
1. Environment variables (`AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`)
2. Managed Identity (when deployed to Azure)
3. Azure CLI credentials (development)
4. Visual Studio Code credentials (development)

**Implementation**:
```python
from azure.identity import DefaultAzureCredential
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()
credential = DefaultAzureCredential()

async def verify_azure_token(token: str = Security(security)):
    # Validate JWT token from Azure AD
    try:
        decoded = jwt.decode(
            token.credentials,
            options={"verify_signature": False},  # Azure AD pre-validated
            audience="api://mdc-agent-api"
        )
        return decoded
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

**Security Considerations**:
- Never log credentials or tokens
- Rotate service principal secrets every 90 days
- Use managed identity in production (no secrets)
- Validate token audience matches API

**Alternatives Considered**:
- Service Principal only: Rejected - less flexible for development, manual secret management
- Interactive browser flow: Rejected - not suitable for API service
- API keys: Rejected - less secure, no Azure AD integration

## 7. OpenAPI 3.1 Spec Generation

**Decision**: Use FastAPI automatic OpenAPI generation with Pydantic models

**Configuration**:
```python
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="MDC Agent API",
    description="LLM-optimized API for Azure Defender for Cloud",
    version="1.0.0",
    openapi_version="3.1.0"
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add custom extensions for LLM optimization
    openapi_schema["info"]["x-llm-optimized"] = True
    openapi_schema["info"]["x-response-format"] = "snake_case"

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

**Schema Export**:
- Generate OpenAPI specs per endpoint group (recommendations, exemptions, assignments)
- Export via `GET /openapi.json` and `GET /docs` (Swagger UI)
- Save static YAML files to `contracts/` directory for version control

**Pydantic Model Benefits**:
- Automatic request/response validation
- JSON schema generation for OpenAPI
- snake_case serialization via `alias_generator`
- Type hints for IDE support

**Alternatives Considered**:
- Manual OpenAPI spec writing: Rejected - error-prone, hard to maintain
- Swagger Codegen: Rejected - code-first approach is more maintainable with FastAPI
- GraphQL: Rejected - REST is simpler for LLM agents, meets requirements

## Summary of Decisions

| Area | Decision | Key Benefit |
|------|----------|-------------|
| Azure SDK | `azure-mgmt-security` | Official support, type safety |
| Exemptions | Native Azure exemptions | Compliance, audit trail |
| Active User | Azure Defender Active User API | Intelligence + automation |
| Notifications | Azure native (automatic) | No custom email infrastructure |
| Assignment Storage | Azure API (no database) | Eliminates sync issues, reduced ops |
| Retry | Exponential backoff with jitter | Resilience without hammering API |
| Auth | DefaultAzureCredential | Multi-environment support |
| OpenAPI | FastAPI auto-generation | Maintainability, accuracy |

## Technology Stack Summary

**Core**:
- Python 3.11
- FastAPI 0.104+
- Pydantic 2.x

**Azure Integration**:
- azure-mgmt-security (includes Active User API)
- azure-identity
- ~~azure-communication-email~~ (NOT NEEDED - Azure sends emails)

**Storage**:
- ~~PostgreSQL~~ (NOT NEEDED - Azure is source of truth)

**Testing**:
- pytest 7.x
- pytest-asyncio
- HTTPX (test client)

**Utilities**:
- tenacity (retry logic)
- python-jose (JWT validation)
- httpx (async HTTP client)

All decisions align with constitution principles and leverage Azure native capabilities.
