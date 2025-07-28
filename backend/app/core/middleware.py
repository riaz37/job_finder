"""
Authentication and security middleware
"""
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.security import verify_token
from app.services.redis_service import redis_service


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT token authentication"""
    
    def __init__(self, app, exclude_paths: Optional[list] = None):
        super().__init__(app)
        # Paths that don't require authentication
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/health",
            "/"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Process request and validate authentication"""
        # Skip authentication for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Get authorization header
        authorization = request.headers.get("Authorization")
        if not authorization:
            return Response(
                content='{"detail":"Authorization header missing"}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json"
            )
        
        # Parse token from header
        scheme, token = get_authorization_scheme_param(authorization)
        if scheme.lower() != "bearer" or not token:
            return Response(
                content='{"detail":"Invalid authorization header format"}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json"
            )
        
        # Verify JWT token
        user_id = verify_token(token)
        if not user_id:
            return Response(
                content='{"detail":"Invalid or expired token"}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json"
            )
        
        # Check session in Redis
        try:
            if not redis_service.redis_client:
                await redis_service.connect()
            
            session_key = f"session:{user_id}"
            session = await redis_service.get(session_key)
            if not session:
                return Response(
                    content='{"detail":"Session expired or invalid"}',
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    media_type="application/json"
                )
        except Exception:
            return Response(
                content='{"detail":"Session validation failed"}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                media_type="application/json"
            )
        
        # Add user_id to request state for use in endpoints
        request.state.user_id = user_id
        
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers"""
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response"""
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Basic rate limiting middleware using Redis"""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
    
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting based on client IP"""
        client_ip = request.client.host
        
        try:
            if not redis_service.redis_client:
                await redis_service.connect()
            
            # Create rate limit key
            rate_limit_key = f"rate_limit:{client_ip}"
            
            # Get current request count
            current_requests = await redis_service.get(rate_limit_key)
            if current_requests is None:
                current_requests = 0
            else:
                current_requests = int(current_requests)
            
            # Check if rate limit exceeded
            if current_requests >= self.requests_per_minute:
                return Response(
                    content='{"detail":"Rate limit exceeded"}',
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    media_type="application/json"
                )
            
            # Increment request count
            await redis_service.set(rate_limit_key, current_requests + 1, expire=60)
            
        except Exception:
            # If Redis is unavailable, allow request to proceed
            pass
        
        return await call_next(request)