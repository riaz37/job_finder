"""
API v1 router configuration
"""
from fastapi import APIRouter
from app.api.v1 import auth, users, resume, preferences

api_router = APIRouter()

# Include authentication routes
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# Include user management routes
api_router.include_router(users.router, prefix="/users", tags=["users"])

# Include resume management routes
api_router.include_router(resume.router, prefix="/resume", tags=["resume"])

# Include preferences management routes
api_router.include_router(preferences.router, prefix="/preferences", tags=["preferences"])

# Placeholder for future endpoint routers
# api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
# api_router.include_router(applications.router, prefix="/applications", tags=["applications"])