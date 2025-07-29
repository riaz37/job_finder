"""
Service for managing user preferences business logic
"""
from typing import Optional
from fastapi import HTTPException, status
from app.db.preferences_repository import PreferencesRepository
from app.models.preferences import (
    UserPreferences, 
    UserPreferencesCreate, 
    UserPreferencesUpdate,
    UserPreferencesData
)
from app.core.validators import PreferencesValidator


class PreferencesService:
    def __init__(self, preferences_repo: PreferencesRepository):
        self.preferences_repo = preferences_repo
    
    async def create_user_preferences(self, user_id: str, preferences: UserPreferencesCreate) -> UserPreferences:
        """Create new user preferences"""
        # Check if preferences already exist
        existing = await self.preferences_repo.preferences_exist(user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User preferences already exist. Use update endpoint instead."
            )
        
        # Validate preferences data
        self._validate_preferences_data(preferences.preferences_data)
        
        # Create preferences
        db_preferences = await self.preferences_repo.create_preferences(user_id, preferences)
        
        # Parse JSON string back to dictionary
        import json
        if isinstance(db_preferences.preferencesData, str):
            preferences_dict = json.loads(db_preferences.preferencesData)
        else:
            # Fallback for existing data that might still be dict
            preferences_dict = db_preferences.preferencesData

        return UserPreferences(
            id=db_preferences.id,
            user_id=db_preferences.userId,
            preferences_data=UserPreferencesData(**preferences_dict),
            created_at=db_preferences.createdAt,
            updated_at=db_preferences.updatedAt
        )
    
    async def get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """Get user preferences by user ID"""
        db_preferences = await self.preferences_repo.get_preferences_by_user_id(user_id)
        
        if not db_preferences:
            return None
        
        # Parse JSON string back to dictionary
        import json
        if isinstance(db_preferences.preferencesData, str):
            preferences_dict = json.loads(db_preferences.preferencesData)
        else:
            # Fallback for existing data that might still be dict
            preferences_dict = db_preferences.preferencesData

        return UserPreferences(
            id=db_preferences.id,
            user_id=db_preferences.userId,
            preferences_data=UserPreferencesData(**preferences_dict),
            created_at=db_preferences.createdAt,
            updated_at=db_preferences.updatedAt
        )
    
    async def update_user_preferences(self, user_id: str, preferences: UserPreferencesUpdate) -> UserPreferences:
        """Update existing user preferences"""
        # Check if preferences exist
        existing = await self.preferences_repo.preferences_exist(user_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User preferences not found"
            )
        
        # Validate preferences data
        self._validate_preferences_data(preferences.preferences_data)
        
        # Update preferences
        db_preferences = await self.preferences_repo.update_preferences(user_id, preferences)
        
        if not db_preferences:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User preferences not found"
            )
        
        # Parse JSON string back to dictionary
        import json
        if isinstance(db_preferences.preferencesData, str):
            preferences_dict = json.loads(db_preferences.preferencesData)
        else:
            # Fallback for existing data that might still be dict
            preferences_dict = db_preferences.preferencesData

        return UserPreferences(
            id=db_preferences.id,
            user_id=db_preferences.userId,
            preferences_data=UserPreferencesData(**preferences_dict),
            created_at=db_preferences.createdAt,
            updated_at=db_preferences.updatedAt
        )
    
    async def delete_user_preferences(self, user_id: str) -> bool:
        """Delete user preferences"""
        try:
            await self.preferences_repo.delete_preferences(user_id)
            return True
        except Exception:
            return False
    
    async def create_or_update_preferences(self, user_id: str, preferences: UserPreferencesCreate) -> UserPreferences:
        """Create preferences if they don't exist, otherwise update them"""
        existing = await self.preferences_repo.preferences_exist(user_id)
        
        if existing:
            update_data = UserPreferencesUpdate(preferences_data=preferences.preferences_data)
            return await self.update_user_preferences(user_id, update_data)
        else:
            return await self.create_user_preferences(user_id, preferences)
    
    def _validate_preferences_data(self, preferences_data: UserPreferencesData) -> None:
        """Validate preferences data for business rules"""
        # Use advanced validators
        PreferencesValidator.validate_job_titles(preferences_data.job_titles)
        PreferencesValidator.validate_locations(preferences_data.locations)
        PreferencesValidator.validate_company_names(preferences_data.preferred_companies)
        PreferencesValidator.validate_company_names(preferences_data.excluded_companies)
        PreferencesValidator.validate_keywords(preferences_data.required_keywords)
        PreferencesValidator.validate_keywords(preferences_data.excluded_keywords)
        
        # Validate no conflicts between preferred and excluded items
        PreferencesValidator.validate_no_conflicts(
            preferences_data.preferred_companies, 
            preferences_data.excluded_companies, 
            "companies"
        )
        PreferencesValidator.validate_no_conflicts(
            preferences_data.preferred_industries, 
            preferences_data.excluded_industries, 
            "industries"
        )
        
        # Validate automation settings
        PreferencesValidator.validate_automation_settings(preferences_data.automation_settings)
        
        # Additional business logic validation
        if preferences_data.salary_range:
            salary_range = preferences_data.salary_range
            if (salary_range.min_salary is not None and 
                salary_range.max_salary is not None and 
                salary_range.min_salary > salary_range.max_salary):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Minimum salary cannot be greater than maximum salary"
                )