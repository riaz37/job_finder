"""
Repository for user preferences database operations
"""
from typing import Optional
from prisma import Prisma
from prisma.models import UserPreferences as PrismaUserPreferences
from app.models.preferences import UserPreferencesCreate, UserPreferencesUpdate, UserPreferencesData


class PreferencesRepository:
    def __init__(self, db: Prisma):
        self.db = db
    
    async def create_preferences(self, user_id: str, preferences: UserPreferencesCreate) -> PrismaUserPreferences:
        """Create new user preferences"""
        return await self.db.userpreferences.create(
            data={
                "userId": user_id,
                "preferencesData": preferences.preferences_data.dict()
            }
        )
    
    async def get_preferences_by_user_id(self, user_id: str) -> Optional[PrismaUserPreferences]:
        """Get user preferences by user ID"""
        return await self.db.userpreferences.find_unique(
            where={"userId": user_id}
        )
    
    async def update_preferences(self, user_id: str, preferences: UserPreferencesUpdate) -> Optional[PrismaUserPreferences]:
        """Update existing user preferences"""
        return await self.db.userpreferences.update(
            where={"userId": user_id},
            data={"preferencesData": preferences.preferences_data.dict()}
        )
    
    async def delete_preferences(self, user_id: str) -> Optional[PrismaUserPreferences]:
        """Delete user preferences"""
        return await self.db.userpreferences.delete(
            where={"userId": user_id}
        )
    
    async def preferences_exist(self, user_id: str) -> bool:
        """Check if user preferences exist"""
        preferences = await self.db.userpreferences.find_unique(
            where={"userId": user_id}
        )
        return preferences is not None