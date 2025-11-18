# Tasks: MDC Agent API

**Input**: Design documents from `/specs/001-mdc-agent-api/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Per constitution Principle V (TDD), tests are MANDATORY and MUST be written before implementation code (Red-Green-Refactor cycle).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- All paths shown below follow plan.md structure

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project directory structure (src/, tests/, .github/workflows/) per plan.md
- [ ] T002 Initialize Python 3.11 project with Poetry and pyproject.toml
- [ ] T003 [P] Add core dependencies: FastAPI 0.104+, Pydantic 2.x, azure-mgmt-security, azure-identity
- [ ] T004 [P] Add development dependencies: pytest 7.x, pytest-asyncio, httpx, black, flake8, mypy
- [ ] T005 [P] Add retry dependency: tenacity library for exponential backoff
- [ ] T006 [P] Configure pre-commit hooks for black, isort, flake8, mypy, conventional commits
- [ ] T007 Create .env.example file with required Azure environment variables (AZURE_SUBSCRIPTION_ID, AZURE_TENANT_ID)
- [ ] T008 [P] Configure .gitignore for Python, Poetry, .env files, and IDE artifacts
- [ ] T009 [P] Create GitHub Actions workflow .github/workflows/ci.yml (lint, test, build)
- [ ] T010 [P] Create GitHub Actions workflow .github/workflows/release.yml (semantic-release integration)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T011 Create src/main.py with FastAPI application initialization and CORS configuration
- [ ] T012 [P] Implement Azure authentication in src/middleware/auth.py using DefaultAzureCredential
- [ ] T013 [P] Create error response models in src/models/error.py (ErrorResponse with error_code, message, details)
- [ ] T014 [P] Implement global error handler in src/middleware/error_handler.py with LLM-friendly responses
- [ ] T015 [P] Setup request/response logging middleware in src/middleware/logging.py
- [ ] T016 [P] Create base Azure Defender client wrapper in src/services/azure_defender.py with retry logic
- [ ] T017 Configure tenacity retry decorator for Azure API calls with exponential backoff (1s to 60s max)
- [ ] T018 [P] Implement snake_case transformation utility in src/utils/transformers.py (PascalCase → snake_case)
- [ ] T019 [P] Create response size validator in src/utils/validators.py to ensure <1MB responses
- [ ] T020 Implement custom OpenAPI schema generation in src/main.py with x-llm-optimized metadata
- [ ] T021 [P] Setup pytest configuration in tests/conftest.py with Azure client mocking fixtures
- [ ] T022 [P] Create test utilities in tests/utils/azure_mocks.py for mocking Azure SDK responses

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Retrieve Security Recommendations (Priority: P1) 🎯 MVP

**Goal**: Enable LLM agents to retrieve and filter security recommendations from Azure Defender for Cloud with all relevant details (severity, resources, remediation, assignments)

**Independent Test**: Call GET /v1/recommendations with valid Azure credentials and receive a paginated list of recommendations with snake_case fields, <1MB response size, and proper filtering

### Tests for User Story 1 (MANDATORY per TDD) ⚠️

> **TDD REQUIREMENT: Write these tests FIRST, verify they FAIL, then implement**

- [ ] T023 [P] [US1] Contract test for GET /v1/recommendations in tests/contract/test_recommendations_contract.py validating OpenAPI schema
- [ ] T024 [P] [US1] Integration test for recommendation retrieval workflow in tests/integration/test_recommendation_workflow.py
- [ ] T025 [P] [US1] Unit test for Azure Defender service recommendation parsing in tests/unit/test_azure_defender_service.py
- [ ] T026 [P] [US1] Unit test for snake_case transformation in tests/unit/test_transformers.py

### Implementation for User Story 1

- [ ] T027 [P] [US1] Create Recommendation Pydantic model in src/models/recommendation.py with all fields from data-model.md
- [ ] T028 [P] [US1] Create Resource sub-entity model in src/models/recommendation.py
- [ ] T029 [P] [US1] Create AssignedUser sub-entity model in src/models/recommendation.py
- [ ] T030 [US1] Implement list_recommendations method in src/services/azure_defender.py using SecurityCenter.assessments.list
- [ ] T031 [US1] Add filtering logic in src/services/azure_defender.py for severity, resource_type, subscription, assignment_status
- [ ] T032 [US1] Add pagination support (limit/offset) in src/services/azure_defender.py
- [ ] T033 [US1] Implement GET /v1/recommendations endpoint in src/api/v1/recommendations.py
- [ ] T034 [US1] Add query parameter validation for filters in src/api/v1/recommendations.py
- [ ] T035 [US1] Apply snake_case transformation to recommendation responses in src/api/v1/recommendations.py
- [ ] T036 [US1] Add response size validation (<1MB) in src/api/v1/recommendations.py
- [ ] T037 [US1] Register recommendations router in src/main.py

**Checkpoint**: At this point, User Story 1 should be fully functional - LLM agents can retrieve recommendations with filtering and pagination

---

## Phase 4: User Story 2 - Create Security Exemptions (Priority: P2)

**Goal**: Enable LLM agents to create exemptions for security recommendations with justification, expiration date, and proper permission validation

**Independent Test**: Call POST /v1/exemptions with valid exemption request and receive confirmation with exemption_id, or appropriate error if validation fails

### Tests for User Story 2 (MANDATORY per TDD) ⚠️

> **TDD REQUIREMENT: Write these tests FIRST, verify they FAIL, then implement**

- [ ] T038 [P] [US2] Contract test for POST /v1/exemptions in tests/contract/test_exemptions_contract.py validating OpenAPI schema
- [ ] T039 [P] [US2] Integration test for exemption creation workflow in tests/integration/test_exemption_workflow.py
- [ ] T040 [P] [US2] Unit test for exemption validation in tests/unit/test_exemption_service.py

### Implementation for User Story 2

- [ ] T041 [P] [US2] Create CreateExemptionRequest Pydantic model in src/models/exemption.py with validation (min 10 chars justification)
- [ ] T042 [P] [US2] Create ExemptionResponse Pydantic model in src/models/exemption.py
- [ ] T043 [US2] Implement create_exemption method in src/services/azure_defender.py using SecurityCenter.assessment_metadata.create_in_subscription
- [ ] T044 [US2] Add permission validation in src/services/azure_defender.py (Security Admin or Contributor role check)
- [ ] T045 [US2] Add recommendation existence check in src/services/azure_defender.py before creating exemption
- [ ] T046 [US2] Add scope matching validation in src/services/azure_defender.py (exemption scope matches recommendation)
- [ ] T047 [US2] Implement POST /v1/exemptions endpoint in src/api/v1/exemptions.py
- [ ] T048 [US2] Add request validation for justification length and expiration date in src/api/v1/exemptions.py
- [ ] T049 [US2] Add error handling for permission denied and recommendation not found in src/api/v1/exemptions.py
- [ ] T050 [US2] Register exemptions router in src/main.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - agents can view recommendations and create exemptions

---

## Phase 5: User Story 3 - Assign Active Users and Track Notifications (Priority: P3)

**Goal**: Enable LLM agents to leverage Azure Defender Active User API for intelligent assignment suggestions, create assignments with grace periods, and track notification delivery status

**Independent Test**: Call GET /v1/active-user/suggestions to get user recommendations, POST /v1/assignments to assign a user with automatic email notification, and GET /v1/assignments to query assignment history with notification status

### Tests for User Story 3 (MANDATORY per TDD) ⚠️

> **TDD REQUIREMENT: Write these tests FIRST, verify they FAIL, then implement**

- [ ] T051 [P] [US3] Contract test for GET /v1/active-user/suggestions in tests/contract/test_assignments_contract.py validating OpenAPI schema
- [ ] T052 [P] [US3] Contract test for POST /v1/assignments in tests/contract/test_assignments_contract.py validating OpenAPI schema
- [ ] T053 [P] [US3] Contract test for GET /v1/assignments in tests/contract/test_assignments_contract.py validating OpenAPI schema
- [ ] T054 [P] [US3] Integration test for Active User assignment workflow in tests/integration/test_assignment_workflow.py
- [ ] T055 [P] [US3] Unit test for Active User suggestion parsing in tests/unit/test_assignment_service.py
- [ ] T056 [P] [US3] Unit test for assignment creation and notification tracking in tests/unit/test_assignment_service.py

### Implementation for User Story 3

- [ ] T057 [P] [US3] Create ActiveUserSuggestion Pydantic model in src/models/assignment.py with confidence_score and activities
- [ ] T058 [P] [US3] Create Activity sub-entity model in src/models/assignment.py
- [ ] T059 [P] [US3] Create CreateAssignmentRequest Pydantic model in src/models/assignment.py
- [ ] T060 [P] [US3] Create Assignment Pydantic model in src/models/assignment.py with all notification fields
- [ ] T061 [US3] Implement get_active_user_suggestions method in src/services/azure_defender.py using SecurityCenter.active_user_suggestions.list
- [ ] T062 [US3] Add CSPM plan validation in src/services/azure_defender.py (check Defender CSPM enabled before Active User operations)
- [ ] T063 [US3] Implement create_assignment method in src/services/azure_defender.py using SecurityCenter.active_user_assignments.create_or_update
- [ ] T064 [US3] Add role validation in src/services/azure_defender.py (Security Administrator, Owner, or Contributor)
- [ ] T065 [US3] Add Azure AD user existence validation in src/services/azure_defender.py
- [ ] T066 [US3] Implement list_assignments method in src/services/azure_defender.py with filtering support
- [ ] T067 [US3] Add due date and status filtering logic in src/services/azure_defender.py
- [ ] T068 [US3] Implement GET /v1/active-user/suggestions endpoint in src/api/v1/assignments.py
- [ ] T069 [US3] Implement POST /v1/assignments endpoint in src/api/v1/assignments.py
- [ ] T070 [US3] Add validation for due_date (must be future) and email format in src/api/v1/assignments.py
- [ ] T071 [US3] Implement GET /v1/assignments endpoint in src/api/v1/assignments.py with query filters
- [ ] T072 [US3] Add error handling for CSPM_NOT_ENABLED and USER_NOT_FOUND in src/api/v1/assignments.py
- [ ] T073 [US3] Register assignments router in src/main.py

**Checkpoint**: All user stories should now be independently functional - full recommendation lifecycle (retrieve → exempt → assign) works end-to-end

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and final deployment readiness

- [ ] T074 [P] Add comprehensive API documentation in src/main.py OpenAPI schema with examples
- [ ] T075 [P] Create Dockerfile for containerized deployment with Python 3.11 base image
- [ ] T076 [P] Create docker-compose.yml for local development with environment variables
- [ ] T077 [P] Add health check endpoint GET /health in src/main.py
- [ ] T078 [P] Add metrics endpoint GET /metrics for monitoring (request counts, latencies)
- [ ] T079 Code cleanup: Remove debug logs, add production logging configuration
- [ ] T080 Performance optimization: Add in-memory cache for recommendations (5-minute TTL)
- [ ] T081 Security hardening: Add rate limiting middleware in src/middleware/rate_limit.py
- [ ] T082 [P] Update README.md with quickstart instructions from quickstart.md
- [ ] T083 Run full test suite and validate all acceptance scenarios from spec.md
- [ ] T084 Verify response sizes <1MB across all endpoints with large datasets
- [ ] T085 Validate snake_case transformation across all response models
- [ ] T086 Test retry logic with Azure API rate limit simulation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3, 4, 5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - No dependencies on other stories, independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - No dependencies on other stories, independently testable

**Key Insight**: All three user stories are fully independent after Foundational phase. They can be implemented in parallel by different developers.

### Within Each User Story

- Tests MUST be written FIRST and verified to FAIL before implementation (Red-Green-Refactor)
- Models before services (data structures before logic)
- Services before endpoints (business logic before HTTP layer)
- Core implementation before integration with other stories
- Story must be independently testable before moving to next priority

### Parallel Opportunities

**Setup Phase (Phase 1)**:
- T003, T004, T005 (dependency installation) can run in parallel
- T006, T008, T009, T010 (configuration files) can run in parallel

**Foundational Phase (Phase 2)**:
- T012, T013, T014, T015 (middleware components) can run in parallel
- T018, T019 (utilities) can run in parallel
- T021, T022 (test infrastructure) can run in parallel

**User Story 1 (Phase 3)**:
- T023, T024, T025, T026 (all tests) can run in parallel
- T027, T028, T029 (all models) can run in parallel

**User Story 2 (Phase 4)**:
- T038, T039, T040 (all tests) can run in parallel
- T041, T042 (models) can run in parallel

**User Story 3 (Phase 5)**:
- T051, T052, T053, T054, T055, T056 (all tests) can run in parallel
- T057, T058, T059, T060 (all models) can run in parallel

**Polish Phase (Phase 6)**:
- T074, T075, T076, T077, T078, T082 (documentation and deployment) can run in parallel

**Cross-Story Parallelism**:
- Once Foundational (Phase 2) is complete, ALL THREE user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Step 1: Launch all tests for User Story 1 together (TDD RED phase):
Task T023: "Contract test for GET /v1/recommendations in tests/contract/test_recommendations_contract.py"
Task T024: "Integration test for recommendation retrieval workflow in tests/integration/test_recommendation_workflow.py"
Task T025: "Unit test for Azure Defender service recommendation parsing in tests/unit/test_azure_defender_service.py"
Task T026: "Unit test for snake_case transformation in tests/unit/test_transformers.py"

# Verify all tests FAIL (no implementation exists)

# Step 2: Launch all models for User Story 1 together:
Task T027: "Create Recommendation Pydantic model in src/models/recommendation.py"
Task T028: "Create Resource sub-entity model in src/models/recommendation.py"
Task T029: "Create AssignedUser sub-entity model in src/models/recommendation.py"

# Step 3: Sequential implementation (service depends on models):
Task T030: "Implement list_recommendations method in src/services/azure_defender.py"
Task T031: "Add filtering logic in src/services/azure_defender.py"
# ... continue sequentially through endpoint implementation

# Step 4: Run tests - should now PASS (TDD GREEN phase)
# Step 5: Refactor code while keeping tests green
```

---

## Parallel Example: Multiple User Stories

```bash
# After Foundational phase completes, assign developers:

# Developer A works on User Story 1:
- T023-T037 (Retrieve Security Recommendations)

# Developer B works on User Story 2 (in parallel):
- T038-T050 (Create Security Exemptions)

# Developer C works on User Story 3 (in parallel):
- T051-T073 (Assign Active Users and Track Notifications)

# All three developers can work simultaneously after Phase 2
# Each story is independently testable and deployable
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T010)
2. Complete Phase 2: Foundational (T011-T022) - CRITICAL - blocks all stories
3. Complete Phase 3: User Story 1 (T023-T037)
4. **STOP and VALIDATE**: Test User Story 1 independently using acceptance scenarios from spec.md
5. Deploy MVP: LLM agents can now retrieve and filter recommendations
6. Gather feedback before implementing P2 and P3

### Incremental Delivery

1. **Foundation**: Complete Setup + Foundational (T001-T022) → Infrastructure ready
2. **MVP**: Add User Story 1 (T023-T037) → Test independently → Deploy/Demo (agents can read recommendations)
3. **Iteration 2**: Add User Story 2 (T038-T050) → Test independently → Deploy/Demo (agents can now exempt findings)
4. **Iteration 3**: Add User Story 3 (T051-T073) → Test independently → Deploy/Demo (agents can now assign users)
5. **Polish**: Complete Phase 6 (T074-T086) → Production-ready
6. Each iteration adds value without breaking previous functionality

### Parallel Team Strategy

With multiple developers after Foundational phase:

**Team completes Setup + Foundational together** (T001-T022)

**Then split into parallel workstreams**:
- **Developer A**: User Story 1 (T023-T037) - Recommendations retrieval
- **Developer B**: User Story 2 (T038-T050) - Exemption management
- **Developer C**: User Story 3 (T051-T073) - Active User assignments

**Stories integrate at the end** - each works independently, minimal merge conflicts

---

## Validation Checklist

Before marking the feature complete, verify:

- [ ] All tests follow TDD workflow (written first, failed, then passed)
- [ ] Each user story passes its independent test criteria from spec.md
- [ ] All responses use snake_case field naming (no PascalCase leakage)
- [ ] All responses are under 1MB (validate with large datasets)
- [ ] Azure API retry logic works with exponential backoff
- [ ] Error responses follow consistent structure (error_code, message, details)
- [ ] OpenAPI schema at /openapi.json matches contracts/ specifications
- [ ] Swagger UI at /docs displays all endpoints correctly
- [ ] All FR-001 through FR-020 functional requirements are implemented
- [ ] All SC-001 through SC-011 success criteria are met
- [ ] CI/CD workflows run successfully (lint, test, build)
- [ ] Conventional commits enforced via pre-commit hooks
- [ ] Documentation matches quickstart.md instructions
- [ ] Azure authentication works with DefaultAzureCredential
- [ ] CSPM plan validation works for Active User endpoints
- [ ] Permission validation works for exemptions and assignments

---

## Notes

- **[P] tasks**: Different files, no dependencies - can run in parallel
- **[Story] label**: Maps task to specific user story for traceability and independent testing
- **TDD MANDATORY**: Write tests first (RED), implement minimal code (GREEN), refactor while keeping tests green
- **Commit strategy**: Commit after each RED-GREEN-REFACTOR cycle with conventional commit message (feat:, fix:, test:)
- **Checkpoints**: Stop at any checkpoint to validate story independently before proceeding
- **Independence**: Each user story should be completable, testable, and deployable without the others
- **Azure native approach**: No PostgreSQL, no custom email - all data from Azure APIs
- **Constitution compliance**: All tasks follow TDD principle, API-first design, agent-optimized responses

---

## Total Task Count

- **Phase 1 (Setup)**: 10 tasks
- **Phase 2 (Foundational)**: 12 tasks
- **Phase 3 (User Story 1)**: 15 tasks (6 tests + 9 implementation)
- **Phase 4 (User Story 2)**: 13 tasks (3 tests + 10 implementation)
- **Phase 5 (User Story 3)**: 23 tasks (6 tests + 17 implementation)
- **Phase 6 (Polish)**: 13 tasks
- **TOTAL**: 86 tasks

**Parallel Opportunities**: 35 tasks marked [P] can run in parallel within their phases

**MVP Scope** (recommended first iteration): Phases 1-3 only = 37 tasks

**Independent Test Criteria Met**: Each user story has clear acceptance scenarios and can be tested without dependencies on other stories
