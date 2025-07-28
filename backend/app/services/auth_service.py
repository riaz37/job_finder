"""
Authentication service for user management
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status
from prisma import Prisma
from prisma.models import User

from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.user import UserCreate, UserInDB
from app.services.redis_service import redis_service


class AuthService:
    """Service for handling authentication operations"""
    
    def __init__(self, db: Prisma):
        self.db = db
    
    async def create_user(self, user_data: UserCreate) -> UserInDB:
        """Create a new user with hashed password"""
        # Check if user already exists
        existing_user = await self.db.user.find_unique(
            where={"email": user_data.email}
        )
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash the password
        hashed_password = get_password_hash(user_data.password)
        
        # Create user in database
        db_user = await self.db.user.create(
            data={
                "email": user_data.email,
                "passwordHash": hashed_password
            }
        )
        
        return UserInDB(
            id=db_user.id,
            email=db_user.email,
            password_hash=db_user.passwordHash,
            created_at=db_user.createdAt,
            updated_at=db_user.updatedAt
        )
    
    async def authenticate_user(self, email: str, password: str) -> Optional[UserInDB]:
        """Authenticate user with email and password"""
        # Find user by email
        db_user = await self.db.user.find_unique(
            where={"email": email}
        )
        
        if not db_user:
            return None
        
        # Verify password
        if not verify_password(password, db_user.passwordHash):
            return None
        
        return UserInDB(
            id=db_user.id,
            email=db_user.email,
            password_hash=db_user.passwordHash,
            created_at=db_user.createdAt,
            updated_at=db_user.updatedAt
        )
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """Get user by ID"""
        db_user = await self.db.user.find_unique(
            where={"id": user_id}
        )
        
        if not db_user:
            return None
        
        return UserInDB(
            id=db_user.id,
            email=db_user.email,
            password_hash=db_user.passwordHash,
            created_at=db_user.createdAt,
            updated_at=db_user.updatedAt
        )
    
    async def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """Get user by email"""
        db_user = await self.db.user.find_unique(
            where={"email": email}
        )
        
        if not db_user:
            return None
        
        return UserInDB(
            id=db_user.id,
            email=db_user.email,
            password_hash=db_user.passwordHash,
            created_at=db_user.createdAt,
            updated_at=db_user.updatedAt
        )
    
    async def update_user_password(self, user_id: str, new_password: str) -> bool:
        """Update user password"""
        hashed_password = get_password_hash(new_password)
        
        try:
            await self.db.user.update(
                where={"id": user_id},
                data={"passwordHash": hashed_password}
            )
            return True
        except Exception:
            return False
    
    async def create_session(self, user: UserInDB) -> str:
        """Create user session and store in Redis"""
        # Create JWT token
        access_token = create_access_token(data={"sub": user.id})
        
        # Store session in Redis with expiration
        session_key = f"session:{user.id}"
        session_data = {
            "user_id": user.id,
            "email": user.email,
            "created_at": datetime.utcnow().isoformat(),
            "token": access_token
        }
        
        # Set session to expire in 8 days (same as JWT)
        await redis_service.set(
            session_key, 
            session_data, 
            expire=60 * 60 * 24 * 8  # 8 days in seconds
        )
        
        return access_token
    
    async def get_session(self, user_id: str) -> Optional[dict]:
        """Get user session from Redis"""
        session_key = f"session:{user_id}"
        return await redis_service.get(session_key)
    
    async def invalidate_session(self, user_id: str) -> bool:
        """Invalidate user session"""
        session_key = f"session:{user_id}"
        await redis_service.delete(session_key)
        return True
    
    async def refresh_session(self, user_id: str) -> Optional[str]:
        """Refresh user session and return new token"""
        # Check if session exists
        session = await self.get_session(user_id)
        if not session:
            return None
        
        # Get user data
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
        
        # Create new session
        return await self.create_session(user)