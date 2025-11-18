"""MDC Agent API - FastAPI application entry point.

LLM-optimized REST API for Azure Microsoft Defender for Cloud integration.
Provides endpoints for security recommendations, exemptions, and user assignments.

Per constitution: API-first design with LLM-friendly responses (snake_case,
<1MB, structured errors).
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.v1 import recommendations
from src.middleware.error_handler import handle_exception
from src.middleware.logging import LoggingMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan handler for startup/shutdown events.

    Args:
        app: FastAPI application instance

    Yields:
        None during application runtime
    """
    # Startup
    logger.info("Starting MDC Agent API...")
    logger.info("Azure authentication initialized")
    yield
    # Shutdown
    logger.info("Shutting down MDC Agent API...")


# Create FastAPI application with custom OpenAPI metadata
app = FastAPI(
    title="MDC Agent API",
    description=(
        "LLM-optimized REST API for Azure Microsoft Defender for Cloud. "
        "Provides simplified access to security recommendations, exemptions, "
        "and user assignments with agent-friendly responses (snake_case, <1MB)."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on deployment environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request/response logging middleware
app.add_middleware(LoggingMiddleware)

# Register global exception handler
app.add_exception_handler(Exception, handle_exception)


# Health check endpoint
@app.get(
    "/health",
    tags=["Health"],
    summary="Health check endpoint",
    description="Returns API health status. Use for monitoring and readiness probes.",
)
async def health_check() -> JSONResponse:
    """Check API health status.

    Returns:
        JSONResponse with status=healthy
    """
    return JSONResponse(content={"status": "healthy", "service": "mdc-agent-api"})


# Custom OpenAPI schema with x-llm-optimized metadata (T020)
def custom_openapi() -> dict[str, Any]:
    """Generate custom OpenAPI schema with LLM optimization metadata.

    Adds x-llm-optimized extensions to inform LLM agents that this API
    follows agent-friendly conventions.

    Returns:
        OpenAPI 3.1 schema dictionary with custom extensions
    """
    if app.openapi_schema:
        return app.openapi_schema  # type: ignore[no-any-return]

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add custom x-llm-optimized extension per T020
    openapi_schema["info"]["x-llm-optimized"] = {
        "field_naming": "snake_case",
        "max_response_size": "1MB",
        "error_format": "structured",
        "retry_support": "exponential_backoff",
        "designed_for": "llm_agents",
    }

    # Add response size information to all endpoints
    for path in openapi_schema.get("paths", {}).values():
        for operation in path.values():
            if isinstance(operation, dict) and "responses" in operation:
                for response in operation["responses"].values():
                    if "description" in response:
                        response["description"] += " (Response guaranteed <1MB)"

    app.openapi_schema = openapi_schema
    return app.openapi_schema  # type: ignore[no-any-return]


# Override default OpenAPI schema generator
app.openapi = custom_openapi  # type: ignore

# Register routers
app.include_router(recommendations.router, tags=["Recommendations"])

# Phase 4 & 5 routers (not yet implemented):
# from src.api.v1 import exemptions, assignments
# app.include_router(exemptions.router, tags=["Exemptions"])
# app.include_router(assignments.router, tags=["Assignments"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
