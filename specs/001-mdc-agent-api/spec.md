# Feature Specification: MDC Agent API

**Feature Branch**: `001-mdc-agent-api`
**Created**: 2025-11-17
**Updated**: 2025-11-17
**Status**: Draft
**Input**: User description: "I want an API that simplify interaction for LLM agent with Azure Microsoft Defender for Cloud."
**Update**: Removed policy management capabilities, added user assignment and email notifications

## User Scenarios & Testing

### User Story 1 - Retrieve Security Recommendations (Priority: P1)

An LLM agent needs to retrieve and understand current security recommendations from Azure Microsoft Defender for Cloud to provide security insights to users.

**Why this priority**: This is the foundation capability - agents must be able to read security recommendations before taking any action on them. This provides immediate value by making security data accessible.

**Independent Test**: Can be fully tested by calling the recommendation retrieval endpoint with valid Azure credentials and receiving a structured list of recommendations with all required fields.

**Acceptance Scenarios**:

1. **Given** an LLM agent has valid Azure credentials, **When** the agent requests all active security recommendations, **Then** the API returns a list of recommendations with ID, severity, description, affected resources, and remediation guidance
2. **Given** an LLM agent requests recommendations, **When** multiple recommendations exist across different subscriptions, **Then** the API returns recommendations grouped by subscription with clear resource identifiers
3. **Given** an LLM agent requests recommendations, **When** the response payload is returned, **Then** all field names use consistent snake_case naming and the total response is under 1MB

---

### User Story 2 - Create Security Exemptions (Priority: P2)

An LLM agent needs to create exemptions for security recommendations when a user determines certain findings are acceptable risks or false positives.

**Why this priority**: After viewing recommendations (P1), the most common action is to exempt findings that don't apply. This reduces noise and allows focus on actionable items.

**Independent Test**: Can be fully tested by creating an exemption for a specific recommendation and verifying it no longer appears in the active recommendations list.

**Acceptance Scenarios**:

1. **Given** an LLM agent has identified a recommendation to exempt, **When** the agent submits an exemption request with recommendation ID, justification, and expiration date, **Then** the API creates the exemption and returns confirmation with exemption ID
2. **Given** an exemption request is submitted, **When** the justification text is missing or invalid, **Then** the API returns a clear error message with error_code and required field details
3. **Given** an exemption is created, **When** the agent retrieves recommendations again, **Then** the exempted recommendation is marked as exempted with exemption details

---

### User Story 3 - Assign Active Users and Track Notifications (Priority: P3)

An LLM agent needs to leverage Azure Defender for Cloud's native Active User feature to assign appropriate users to remediate security recommendations based on their resource activity, with optional due dates and grace periods, and track assignment status including notification delivery.

**Why this priority**: After identifying and triaging recommendations, the next step is assigning ownership and tracking outcomes. Using Azure's built-in Active User feature provides intelligent user suggestions based on actual resource activity, automatic email notifications, and built-in tracking capabilities.

**Independent Test**: Can be fully tested by retrieving active user suggestions, assigning a user with due date and grace period, verifying the assignment with notification delivery, and querying assignment history for follow-up.

**Acceptance Scenarios**:

1. **Given** an LLM agent has identified a recommendation requiring remediation, **When** the agent requests active user suggestions for that recommendation, **Then** the API returns up to 3 suggested users ranked by activity confidence with their name, email, department, role, and recent activities
2. **Given** an LLM agent has active user suggestions, **When** the agent assigns one of the suggested users with a due_date and grace_period_enabled flag, **Then** the API creates the assignment via Azure Defender API and the assigned user receives an automatic email notification with recommendation details
3. **Given** a recommendation has an active assignment, **When** the agent retrieves recommendation details, **Then** the response includes assigned_user information, due_date, grace_period status, assignment timestamp, and notification_delivery_status
4. **Given** an agent needs to override suggestions, **When** the agent assigns a user by email address not in the suggestion list, **Then** the API accepts the manual assignment and creates it via Azure Defender API
5. **Given** recommendations have been assigned to users, **When** the agent requests assignment history for a subscription or resource group, **Then** the API returns all assignments with assigned_user, due_date, grace_period status, notification_sent timestamp, and assignment_status (active/completed/overdue)
6. **Given** an agent wants to follow up on overdue assignments, **When** the agent queries assignments with due_date filters, **Then** the API returns assignments that are overdue or due within a specified timeframe
7. **Given** multiple recommendations for the same resource, **When** the agent requests active user suggestions, **Then** the API returns consistent user suggestions based on resource ownership patterns

---

### Edge Cases

- What happens when Azure API rate limits are reached during recommendation retrieval?
- How does the system handle expired or invalid Azure credentials?
- What happens when an exemption is requested for a recommendation that no longer exists?
- What happens when Active User suggestions return no candidates (new resource, no activity data)?
- How does the system handle grace period expiration when the assigned user hasn't taken action?
- What happens when Azure Defender email notification fails (invalid email, service issue)?
- How does the system handle duplicate assignment requests for the same recommendation?
- What happens when the user making the assignment lacks Security Administrator or Contributor role?
- What happens when Azure Defender for Cloud returns partial data due to timeout?
- What happens when subscription access permissions change mid-request?
- How does the system handle assignments when Defender CSPM plan is not enabled?

## Requirements

### Functional Requirements

- **FR-001**: System MUST retrieve security recommendations from Azure Microsoft Defender for Cloud with all relevant details (ID, severity, description, affected resources, remediation steps, assigned user if present)
- **FR-002**: System MUST support filtering recommendations by severity, resource type, subscription, and assignment status
- **FR-003**: System MUST create security exemptions with justification text, expiration date, and exemption scope
- **FR-004**: System MUST validate exemption requests to ensure recommendation exists and user has permission to exempt
- **FR-005**: System MUST retrieve Active User suggestions for a recommendation via Azure Defender for Cloud API, returning up to 3 suggested users with activity confidence scores
- **FR-006**: System MUST include user details in Active User suggestions (name, email, department, role, manager, recent activities)
- **FR-007**: System MUST assign users to recommendations using Azure Defender Active User API with due_date and grace_period_enabled parameters
- **FR-008**: System MUST validate assignment requests to ensure user has Security Administrator, Owner, or Contributor role and Defender CSPM plan is enabled
- **FR-009**: System MUST support manual user assignment by email address when overriding Active User suggestions
- **FR-010**: System MUST retrieve assignment history for recommendations including assigned_user, due_date, grace_period status, and notification timestamps
- **FR-011**: System MUST query assignments with filters for due_date, assignment_status (active/completed/overdue), and subscription/resource scope
- **FR-012**: System MUST provide assignment notification delivery status from Azure Defender (notification_sent timestamp, delivery_status)
- **FR-013**: System MUST transform Azure API responses into LLM-friendly format with consistent field naming (snake_case)
- **FR-014**: System MUST return structured error responses with error_code, message, and details fields for all failures
- **FR-015**: System MUST implement pagination for large result sets using limit/offset pattern
- **FR-016**: System MUST authenticate with Azure using Azure Identity DefaultAzureCredential
- **FR-017**: System MUST retry transient Azure API failures with exponential backoff
- **FR-018**: System MUST log all API requests and responses for audit and debugging
- **FR-019**: System MUST ensure all API responses are under 1MB to fit within LLM context windows
- **FR-020**: System MUST validate Defender CSPM plan is enabled before attempting Active User operations and return clear error if not available

### Key Entities

- **Security Recommendation**: Represents a security finding from Azure Defender with attributes including recommendation_id, severity (Critical/High/Medium/Low), title, description, affected_resources (list), remediation_steps, assessment_status, compliance_standards, assigned_user (if assigned), due_date (if assigned), and grace_period_enabled (boolean)
- **Exemption**: Represents a user decision to exclude a recommendation from active findings with attributes including exemption_id, recommendation_id, justification (text), exempted_by (user identifier), expiration_date, scope (subscription/resource group/resource), and creation_timestamp
- **Active User Suggestion**: Represents a suggested user from Azure Defender based on resource activity with attributes including user_email, user_name, department, role, manager, confidence_score (ranking), and recent_activities (list of control plane actions)
- **User Assignment**: Represents an active assignment created via Azure Defender Active User API with attributes including assignment_id, recommendation_id, assigned_user_email, assigned_user_name, assigner_id (who made the assignment), assignment_date, due_date, grace_period_enabled (boolean), assignment_status (active/completed/overdue), notification_sent_timestamp, and notification_delivery_status

## Success Criteria

### Measurable Outcomes

- **SC-001**: LLM agents can retrieve all active security recommendations in under 5 seconds for subscriptions with up to 1000 recommendations
- **SC-002**: LLM agents can create exemptions that take effect immediately and are reflected in subsequent recommendation queries within 10 seconds
- **SC-003**: Active User suggestions are retrieved in under 2 seconds per recommendation
- **SC-004**: 95% of user assignment operations via Azure Defender Active User API complete successfully on first attempt without retry
- **SC-005**: All API responses fit within 1MB size limit while maintaining complete necessary information
- **SC-006**: LLM agents can successfully complete the full workflow (retrieve recommendations → get Active User suggestions → assign user → verify notification delivery) without human intervention in 90% of cases
- **SC-007**: System handles Azure API rate limits gracefully with automatic retry, achieving 99% eventual success rate
- **SC-008**: Azure Defender sends assignment email notifications within 5 minutes of assignment creation
- **SC-009**: Assignment history queries return results in under 3 seconds for up to 500 assignments
- **SC-010**: Error messages are clear enough that LLM agents can determine corrective action without additional context in 85% of error scenarios
- **SC-011**: Active User suggestions provide at least one candidate in 80% of recommendations for resources with activity history

## Assumptions

- Azure credentials will be provided via environment variables or Azure managed identity
- Users have appropriate Azure RBAC permissions (Security Reader minimum, Security Administrator/Owner/Contributor for assignments)
- Azure subscriptions are already onboarded to Microsoft Defender for Cloud with Defender CSPM plan enabled
- LLM agents can handle paginated responses and make multiple requests when needed
- Standard Azure API rate limits apply (will be documented in API specification)
- Exemptions follow organizational approval workflows defined in Azure Defender for Cloud settings
- Email notifications are handled natively by Azure Defender for Cloud and sent automatically upon assignment
- Active User suggestions are based on Azure control plane activity data collected by Defender for Cloud
- Grace period functionality is controlled via grace_period_enabled boolean flag in Azure Defender Active User API
- User assignments can be made for users in Azure AD with valid email addresses
- Azure Defender Active User feature availability depends on cloud region and Defender CSPM plan
- Assignment notifications use Azure Defender's standard email templates and cannot be customized via this API
- Active User suggestions provide up to 3 candidates ranked by confidence score based on resource activity
- Due dates are specified in ISO 8601 format (YYYY-MM-DD)
- API acts as a wrapper around Azure Defender native Active User feature, not replacing it with custom logic
