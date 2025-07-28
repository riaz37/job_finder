"""
API endpoints for user preferences management
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.preferences import (
    UserPreferences,
    UserPreferencesCreate,
    UserPreferencesUpdate,
    UserPreferencesResponse
)
from app.services.preferences_service import PreferencesService
from app.db.preferences_repository import PreferencesRepository
from app.db.database import get_database

router = APIRouter()


def get_preferences_service(db=Depends(get_database)) -> PreferencesService:
    """Dependency to get preferences service"""
    preferences_repo = PreferencesRepository(db)
    return PreferencesService(preferences_repo)


@router.post("/", response_model=UserPreferencesResponse, status_code=status.HTTP_201_CREATED)
async def create_preferences(
    preferences: UserPreferencesCreate,
    current_user: User = Depends(get_current_user),
    preferences_service: PreferencesService = Depends(get_preferences_service)
):
    """Create new user preferences"""
    try:
        user_preferences = await preferences_service.create_user_preferences(
            current_user.id, preferences
        )
        return UserPreferencesResponse(**user_preferences.dict())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create preferences: {str(e)}"
        )


@router.get("/", response_model=Optional[UserPreferencesResponse])
async def get_preferences(
    current_user: User = Depends(get_current_user),
    preferences_service: PreferencesService = Depends(get_preferences_service)
):
    """Get current user's preferences"""
    try:
        user_preferences = await preferences_service.get_user_preferences(current_user.id)
        if user_preferences:
            return UserPreferencesResponse(**user_preferences.dict())
        return None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve preferences: {str(e)}"
        )


@router.put("/", response_model=UserPreferencesResponse)
async def update_preferences(
    preferences: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    preferences_service: PreferencesService = Depends(get_preferences_service)
):
    """Update existing user preferences"""
    try:
        user_preferences = await preferences_service.update_user_preferences(
            current_user.id, preferences
        )
        return UserPreferencesResponse(**user_preferences.dict())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update preferences: {str(e)}"
        )


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_preferences(
    current_user: User = Depends(get_current_user),
    preferences_service: PreferencesService = Depends(get_preferences_service)
):
    """Delete user preferences"""
    try:
        success = await preferences_service.delete_user_preferences(current_user.id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User preferences not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete preferences: {str(e)}"
        )


@router.post("/upsert", response_model=UserPreferencesResponse)
async def upsert_preferences(
    preferences: UserPreferencesCreate,
    current_user: User = Depends(get_current_user),
    preferences_service: PreferencesService = Depends(get_preferences_service)
):
    """Create or update user preferences (upsert operation)"""
    try:
        user_preferences = await preferences_service.create_or_update_preferences(
            current_user.id, preferences
        )
        return UserPreferencesResponse(**user_preferences.dict())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upsert preferences: {str(e)}"
        )