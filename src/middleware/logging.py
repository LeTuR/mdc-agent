"""Request/response logging middleware for observability.

Logs all HTTP requests and responses with timing information for debugging
and performance monitoring.
"""

import logging
import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests and responses with timing info."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response from downstream handler
        """
        # Record start time
        start_time = time.time()

        # Extract request details
        method = request.method
        path = request.url.path
        query_params = str(request.query_params) if request.query_params else ""

        logger.info(
            f"Request started: {method} {path}",
            extra={
                "method": method,
                "path": path,
                "query_params": query_params,
                "client_host": request.client.host if request.client else None,
            },
        )

        # Process request
        try:
            response = await call_next(request)
        except Exception as exc:
            # Log error and re-raise (will be caught by error handler)
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Request failed: {method} {path} - {type(exc).__name__}",
                extra={
                    "method": method,
                    "path": path,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(exc),
                },
                exc_info=True,
            )
            raise

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log response
        logger.info(
            f"Request completed: {method} {path} - {response.status_code}",
            extra={
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )

        # Add timing header for clients
        response.headers["X-Process-Time-Ms"] = str(round(duration_ms, 2))

        return response  # type: ignore[no-any-return]
