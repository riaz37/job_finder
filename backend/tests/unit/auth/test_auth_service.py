"""
Unit tests for authentication service
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from fastapi import HTTPException

from app.services.auth_service import AuthService
from app.models.user import UserCreate, UserInDB


@pytest.fixture
def mock_db():
    """Mock Prisma database client"""
    return AsyncMock()


@pytest.fixture
def auth_service(mock_db):
    """Create AuthService instance with mocked database"""
    return AuthService(mock_db)


@pytest.fixture
def sample_user_create():
    """Sample user creation data"""
    return UserCreate(email="test@example.com", password="testpassword123")


@pytest.fixture
def sample_user_db():
    """Sample user database model"""
    return UserInDB(
        id="user123",
        email="test@example.com",
        password_hash="$2b$12$hashed_password",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


class TestAuthService:
    """Test cases for AuthService"""
    
    @pytest.mark.asyncio
    async def test_create_user_success(self, auth_service, mock_db, sample_user_create):
        """Test successful user creation"""
        # Mock database responses
        mock_db.user.find_unique.return_value = None  # User doesn't exist
        mock_db.user.create.return_value = MagicMock(
            id="user123",
            email="test@example.com",
            passwordHash="$2b$12$hashed_password",
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )
        
        # Create user
        result = await auth_service.create_user(sample_user_create)
        
        # Assertions
        assert result.email == "test@example.com"
        assert result.id == "user123"
        mock_db.user.find_unique.assert_called_once()
        mock_db.user.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_user_email_exists(self, auth_service, mock_db, sample_user_create):
        """Test user creation with existing email"""
        # Mock existing user
        mock_db.user.find_unique.return_value = MagicMock(id="existing_user")
        
        # Attempt to create user
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.create_user(sample_user_create)
        
        assert exc_info.value.status_code == 400
        assert "Email already registered" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, auth_service, mock_db):
        """Test successful user authentication"""
        # Mock database response
        mock_db.user.find_unique.return_value = MagicMock(
            id="user123",
            email="test@example.com",
            passwordHash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )
        
        with patch('app.services.auth_service.verify_password', return_value=True):
            result = await auth_service.authenticate_user("test@example.com", "secret")
        
        assert result is not None
        assert result.email == "test@example.com"
        assert result.id == "user123"
    
    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_email(self, auth_service, mock_db):
        """Test authentication with invalid email"""
        mock_db.user.find_unique.return_value = None
        
        result = await auth_service.authenticate_user("invalid@example.com", "password")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_password(self, auth_service, mock_db):
        """Test authentication with invalid password"""
        mock_db.user.find_unique.return_value = MagicMock(
            id="user123",
            email="test@example.com",
            passwordHash="$2b$12$hashed_password",
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )
        
        with patch('app.services.auth_service.verify_password', return_value=False):
            result = await auth_service.authenticate_user("test@example.com", "wrongpassword")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, auth_service, mock_db):
        """Test getting user by ID"""
        mock_db.user.find_unique.return_value = MagicMock(
            id="user123",
            email="test@example.com",
            passwordHash="$2b$12$hashed_password",
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )
        
        result = await auth_service.get_user_by_id("user123")
        
        assert result is not None
        assert result.id == "user123"
        assert result.email == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, auth_service, mock_db):
        """Test getting user by ID when user doesn't exist"""
        mock_db.user.find_unique.return_value = None
        
        result = await auth_service.get_user_by_id("nonexistent")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_user_password_success(self, auth_service, mock_db):
        """Test successful password update"""
        mock_db.user.update.return_value = MagicMock()
        
        result = await auth_service.update_user_password("user123", "newpassword")
        
        assert result is True
        mock_db.user.update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_user_password_failure(self, auth_service, mock_db):
        """Test password update failure"""
        mock_db.user.update.side_effect = Exception("Database error")
        
        result = await auth_service.update_user_password("user123", "newpassword")
        
        assert result is False
    
    @pytest.mark.asyncio
    @patch('app.services.auth_service.redis_service')
    async def test_create_session(self, mock_redis, auth_service, sample_user_db):
        """Test session creation"""
        mock_redis.set = AsyncMock()
        
        with patch('app.services.auth_service.create_access_token', return_value="mock_token"):
            token = await auth_service.create_session(sample_user_db)
        
        assert token == "mock_token"
        mock_redis.set.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.auth_service.redis_service')
    async def test_get_session(self, mock_redis, auth_service):
        """Test getting session"""
        mock_redis.get = AsyncMock(return_value={"user_id": "user123", "email": "test@example.com"})
        
        result = await auth_service.get_session("user123")
        
        assert result["user_id"] == "user123"
        assert result["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    @patch('app.services.auth_service.redis_service')
    async def test_invalidate_session(self, mock_redis, auth_service):
        """Test session invalidation"""
        mock_redis.delete = AsyncMock()
        
        result = await auth_service.invalidate_session("user123")
        
        assert result is True
        mock_redis.delete.assert_called_once_with("session:user123")
    
    @pytest.mark.asyncio
    @patch('app.services.auth_service.redis_service')
    async def test_refresh_session_success(self, mock_redis, auth_service, mock_db):
        """Test successful session refresh"""
        # Mock session exists
        mock_redis.get = AsyncMock(return_value={"user_id": "user123"})
        
        # Mock user exists
        mock_db.user.find_unique.return_value = MagicMock(
            id="user123",
            email="test@example.com",
            passwordHash="$2b$12$hashed_password",
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )
        
        # Mock session creation
        mock_redis.set = AsyncMock()
        
        with patch('app.services.auth_service.create_access_token', return_value="new_token"):
            result = await auth_service.refresh_session("user123")
        
        assert result == "new_token"
    
    @pytest.mark.asyncio
    @patch('app.services.auth_service.redis_service')
    async def test_refresh_session_no_session(self, mock_redis, auth_service):
        """Test session refresh when no session exists"""
        mock_redis.get = AsyncMock(return_value=None)
        
        result = await auth_service.refresh_session("user123")
        
        assert result is None