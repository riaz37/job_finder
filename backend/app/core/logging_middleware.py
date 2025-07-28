"""
Logging middleware for FastAPI to capture request/response information
and integrate with the structured logging system.
"""
import time
import uuid
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger, ActivityType, LogLevel


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log HTTP requests and responses with structured logging.
    """
    
    def __init__(self, app, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.logger = get_logger("http_middleware")
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process HTTP request and response with logging."""
        
        # Skip logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Generate correlation ID for request tracking
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        # Extract user information if available
        user_id = None
        session_id = None
        
        # Try to get user info from request state (set by auth middleware)
        if hasattr(request.state, 'user'):
            user_id = getattr(request.state.user, 'id', None)
        
        # Try to get session ID from headers or cookies
        session_id = request.headers.get('X-Session-ID') or request.cookies.get('session_id')
        
        # Record request start time
        start_time = time.time()
        
        # Log incoming request
        request_metadata = {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent")
        }
        
        self.logger.log_activity(
            level=LogLevel.INFO,
            activity_type=ActivityType.USER_ACTION,
            message=f"HTTP {request.method} {request.url.path}",
            user_id=user_id,
            session_id=session_id,
            correlation_id=correlation_id,
            metadata=request_metadata
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate response time
            process_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Log response
            response_metadata = {
                "status_code": response.status_code,
                "response_headers": dict(response.headers)
            }
            
            # Determine log level based on status code
            if response.status_code >= 500:
                log_level = LogLevel.ERROR
            elif response.status_code >= 400:
                log_level = LogLevel.WARNING
            else:
                log_level = LogLevel.INFO
            
            self.logger.log_activity(
                level=log_level,
                activity_type=ActivityType.SYSTEM_EVENT,
                message=f"HTTP {request.method} {request.url.path} - {response.status_code}",
                user_id=user_id,
                session_id=session_id,
                correlation_id=correlation_id,
                metadata=response_metadata,
                performance_metrics={
                    "response_time_ms": process_time,
                    "status_code": response.status_code
                }
            )
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            
            return response
            
        except Exception as e:
            # Calculate response time for error case
            process_time = (time.time() - start_time) * 1000
            
            # Log error
            self.logger.log_error_with_context(
                error=e,
                context=f"HTTP {request.method} {request.url.path}",
                user_id=user_id,
                session_id=session_id,
                correlation_id=correlation_id,
                additional_metadata={
                    "request_method": request.method,
                    "request_path": request.url.path,
                    "response_time_ms": process_time
                }
            )
            
            # Re-raise the exception
            raise


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add request context information to the request state
    for use by other parts of the application.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add context information to request state."""
        
        # Add correlation ID if not already present
        if not hasattr(request.state, 'correlation_id'):
            request.state.correlation_id = str(uuid.uuid4())
        
        # Add logger with context
        request.state.logger = get_logger("request_handler")
        
        return await call_next(request)


def get_request_logger(request: Request):
    """
    Get a logger with request context.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Logger with request context
    """
    logger = get_logger("request_handler")
    
    # Add request context to logger if available
    if hasattr(request.state, 'correlation_id'):
        # This would be used by the logger for context
        pass
    
    return logger