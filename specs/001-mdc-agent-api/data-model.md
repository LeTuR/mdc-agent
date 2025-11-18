# Data Model: MDC Agent API

**Feature**: MDC Agent API
**Date**: 2025-11-17
**Purpose**: Define entities and their relationships for Azure Defender for Cloud integration

## Overview

This API acts as a wrapper around Azure Defender for Cloud native capabilities. Most data is **NOT stored locally** - it's queried from Azure APIs and transformed for LLM consumption.

**Data Sources**:
- **Azure Defender for Cloud**: Recommendations, exemptions, assignments (source of truth)
- **Azure Active Directory**: User information via Active User suggestions
- **No Local Database**: API is stateless, all data retrieved from Azure

## Entity Definitions

### 1. Security Recommendation

**Source**: Azure Defender for Cloud Assessments API

**Description**: Represents a security finding from Azure Microsoft Defender for Cloud

**Attributes**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| recommendation_id | string | Yes | Azure assessment ID (unique identifier) |
| severity | enum | Yes | Critical, High, Medium, Low |
| title | string | Yes | Short recommendation title |
| description | string | Yes | Detailed explanation of the security issue |
| affected_resources | array[Resource] | Yes | List of affected Azure resources |
| remediation_steps | string | Yes | How to fix the issue |
| assessment_status | enum | Yes | Healthy, Unhealthy, NotApplicable |
| compliance_standards | array[string] | No | Related compliance frameworks (e.g., "CIS", "PCI-DSS") |
| assigned_user | AssignedUser | No | Present if Active User assignment exists |
| due_date | date (ISO 8601) | No | Assignment due date (if assigned) |
| grace_period_enabled | boolean | No | Whether grace period is active (if assigned) |
| subscription_id | string | Yes | Azure subscription containing the resource |
| resource_group | string | No | Resource group (if applicable) |

**Resource Sub-entity**:
- `resource_id`: string (Azure resource ID)
- `resource_type`: string (e.g., "Microsoft.Compute/virtualMachines")
- `resource_name`: string (display name)

**AssignedUser Sub-entity**:
- `user_email`: string
- `user_name`: string
- `assignment_date`: datetime (ISO 8601)
- `notification_sent`: boolean

**Validation Rules**:
- `recommendation_id` must be valid Azure assessment ID format
- `severity` must be one of: Critical, High, Medium, Low
- `affected_resources` must contain at least one resource
- `due_date` must be future date if present

**State Transitions**:
- Unhealthy → Healthy (when remediated)
- Unhealthy → NotApplicable (when exempted)
- Unassigned → Assigned (when Active User assigned)

---

### 2. Exemption

**Source**: Azure Defender for Cloud Exemptions API

**Description**: Represents a decision to exclude a recommendation from active findings

**Attributes**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| exemption_id | string | Yes | Azure exemption ID (unique identifier) |
| recommendation_id | string | Yes | Related assessment ID |
| justification | string | Yes | Why this finding is exempted (min 10 chars) |
| exempted_by | string | Yes | Azure AD user ID who created exemption |
| expiration_date | date (ISO 8601) | Yes | When exemption expires |
| scope | string | Yes | Azure scope (subscription/resource group/resource) |
| creation_timestamp | datetime (ISO 8601) | Yes | When exemption was created |
| exemption_category | enum | No | Waiver, Mitigated (Azure categories) |

**Validation Rules**:
- `justification` minimum 10 characters
- `expiration_date` must be future date
- `scope` must match recommendation scope or be more specific
- User must have Security Admin or Contributor role on scope

**State Transitions**:
- Active → Expired (when expiration_date passes)

---

### 3. Active User Suggestion

**Source**: Azure Defender for Cloud Active User API

**Description**: Suggested user for assignment based on resource activity

**Attributes**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_email | string | Yes | User's email address |
| user_name | string | Yes | Display name |
| department | string | No | User's department/org unit |
| role | string | No | Job role/title |
| manager | string | No | Manager's name |
| confidence_score | integer (1-100) | Yes | Confidence this user is appropriate (Azure calculated) |
| recent_activities | array[Activity] | Yes | Control plane actions on related resources |
| suggestion_rank | integer (1-3) | Yes | Ranking among suggestions (1 = highest confidence) |

**Activity Sub-entity**:
- `action`: string (e.g., "Microsoft.Compute/virtualMachines/write")
- `timestamp`: datetime (ISO 8601)
- `resource_id`: string (affected resource)

**Validation Rules**:
- `confidence_score` must be 1-100
- `suggestion_rank` must be 1-3
- `user_email` must be valid email format
- `recent_activities` must contain at least one activity

**Notes**:
- Up to 3 suggestions returned per recommendation
- Ranked by confidence score (highest first)
- No suggestions if no activity data available

---

### 4. User Assignment

**Source**: Azure Defender for Cloud Active User Assignments API

**Description**: Active assignment of a user to remediate a recommendation

**Attributes**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| assignment_id | string | Yes | Azure assignment ID (unique identifier) |
| recommendation_id | string | Yes | Related assessment ID |
| assigned_user_email | string | Yes | Email of assigned user |
| assigned_user_name | string | Yes | Display name of assigned user |
| assigner_id | string | Yes | Azure AD user ID who created assignment |
| assignment_date | datetime (ISO 8601) | Yes | When assignment was created |
| due_date | date (ISO 8601) | No | Target completion date |
| grace_period_enabled | boolean | Yes | Whether grace period is active (default: false) |
| assignment_status | enum | Yes | active, completed, overdue |
| notification_sent_timestamp | datetime (ISO 8601) | No | When Azure sent email notification |
| notification_delivery_status | enum | No | sent, delivered, failed |
| completion_timestamp | datetime (ISO 8601) | No | When recommendation was remediated |

**Validation Rules**:
- `assigned_user_email` must be valid Azure AD user
- `due_date` must be future date if present
- `assignment_status` calculated based on due_date and recommendation status
- Assigner must have Security Administrator, Owner, or Contributor role
- Defender CSPM plan must be enabled on subscription

**State Transitions**:
- active → completed (when recommendation resolved)
- active → overdue (when due_date passes without completion)
- completed → active (if recommendation becomes unhealthy again)

**Notification Flow**:
1. Assignment created via Azure API
2. Azure automatically sends email to `assigned_user_email`
3. `notification_sent_timestamp` recorded by Azure
4. `notification_delivery_status` updated by Azure email service

---

## Entity Relationships

```text
Security Recommendation (1) ───┬─── (0..1) Exemption
                                │
                                ├─── (0..1) User Assignment
                                │
                                └─── (0..3) Active User Suggestions (transient)

User Assignment (1) ───┬─── (1) Security Recommendation
                        │
                        └─── (1) Azure AD User (via email)

Exemption (1) ─────────── (1) Security Recommendation
```

**Key Relationships**:
- One recommendation can have **at most one** active assignment
- One recommendation can have **at most one** active exemption
- One recommendation can have **up to 3** Active User suggestions (temporary, generated on request)
- Assignments and exemptions are mutually exclusive (can't exempt assigned recommendation)

---

## Data Flow

### Read Flow (Recommendations)
```
1. API receives request for recommendations
2. Query Azure Defender Assessments API
3. For each assessment, check for active assignment
4. Transform to snake_case, ensure <1MB response
5. Return to LLM agent
```

### Write Flow (Assignment)
```
1. API receives assignment request
2. Optional: Query Active User suggestions first
3. Validate user has appropriate role
4. Create assignment via Azure Active User API
5. Azure automatically sends email notification
6. Return assignment confirmation with notification status
```

### Write Flow (Exemption)
```
1. API receives exemption request
2. Validate recommendation exists
3. Validate user has Security Admin role
4. Create exemption via Azure Exemptions API
5. Return exemption confirmation
```

---

## Transformation Rules

### Azure → LLM-Optimized Format

**Field Naming**:
- Azure uses PascalCase (e.g., `AssessmentId`)
- API returns snake_case (e.g., `assessment_id`)
- Automated via Pydantic `alias_generator`

**Response Size**:
- Target <1MB per response
- Paginate if >1000 recommendations
- Truncate long text fields if necessary (with indicator)

**Error Responses**:
```json
{
  "error_code": "ASSIGNMENT_PERMISSION_DENIED",
  "message": "User lacks Security Administrator role",
  "details": {
    "required_role": "Security Administrator",
    "user_roles": ["Reader"]
  }
}
```

---

## No Local Storage

**Why no database?**:
1. Azure is authoritative source of truth
2. Eliminates data sync issues
3. Reduces operational complexity
4. Native Azure audit trail
5. No need for migrations or backups

**Caching Strategy**:
- Optional in-memory cache for recommendations (TTL: 5 minutes)
- No persistent cache to avoid stale data
- Let Azure handle scale and availability

---

## OpenAPI Schema Generation

All entities defined as Pydantic models with:
- Type hints for validation
- `Config` with `populate_by_name` and snake_case alias
- Docstrings for OpenAPI descriptions
- Examples for API documentation

See `contracts/` directory for generated OpenAPI 3.1 specifications.
