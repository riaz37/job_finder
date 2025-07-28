"""
Unit tests for authentication endpoints
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import status, FastAPI
from datetime import datetime

from app.models.user import UserInDB
from app.api.v1.api import api_router
from app.core.config import settings


@pytest.fixture
def app():
    """Create test FastAPI app without database dependencies"""
    test_app = FastAPI()
    test_app.include_router(api_router, prefix=settings.API_V1_STR)
    return test_app


@pytest.fixture
def client(app):
    """Test client for FastAPI app"""
    return TestClient(app)


@pytest.fixture
def sample_user():
    """Sample user for testing"""
    return UserInDB(
        id="user123",
        email="test@example.com",
        password_hash="$2b$12$hashed_password",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


class TestAuthEndpoints:
    """Test cases for authentication endpoints"""
    
    @patch('app.api.v1.auth.redis_service')
    @patch('app.api.v1.auth.get_auth_service')
    def test_register_success(self, mock_get_auth_service, mock_redis, client):
        """Test successful user registration"""
        # Mock auth service
        mock_auth_service = AsyncMock()
        mock_auth_service.create_user.return_value = UserInDB(
            id="user123",
            email="test@example.com",
            password_hash="$2b$12$hashed_password",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        mock_get_auth_service.return_value = mock_auth_service
        
        # Mock Redis
        mock_redis.redis_client = MagicMock()
        mock_redis.connect = AsyncMock()
        
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "testpassword123"}
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "id" in data
        assert "password" not in data
    
    @patch('app.api.v1.auth.redis_service')
    @patch('app.api.v1.auth.get_auth_service')
    def test_register_email_exists(self, mock_get_auth_service, mock_redis, client):
        """Test registration with existing email"""
        # Mock auth service to raise HTTPException
        mock_auth_service = AsyncMock()
        from fastapi import HTTPException
        mock_auth_service.create_user.side_effect = HTTPException(
            status_code=400, detail="Email already registered"
        )
        mock_get_auth_service.return_value = mock_auth_service
        
        # Mock Redis
        mock_redis.redis_client = MagicMock()
        mock_redis.connect = AsyncMock()
        
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "existing@example.com", "password": "testpassword123"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Email already registered" in response.json()["detail"]
    
    @patch('app.api.v1.auth.redis_service')
    @patch('app.api.v1.auth.get_auth_service')
    def test_login_success(self, mock_get_auth_service, mock_redis, client, sample_user):
        """Test successful login"""
        # Mock auth service
        mock_auth_service = AsyncMock()
        mock_auth_service.authenticate_user.return_value = sample_user
        mock_auth_service.create_session.return_value = "mock_access_token"
        mock_get_auth_service.return_value = mock_auth_service
        
        # Mock Redis
        mock_redis.redis_client = MagicMock()
        mock_redis.connect = AsyncMock()
        
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "testpassword123"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["access_token"] == "mock_access_token"
        assert data["token_type"] == "bearer"
    
    @patch('app.api.v1.auth.redis_service')
    @patch('app.api.v1.auth.get_auth_service')
    def test_login_invalid_credentials(self, mock_get_auth_service, mock_redis, client):
        """Test login with invalid credentials"""
        # Mock auth service
        mock_auth_service = AsyncMock()
        mock_auth_service.authenticate_user.return_value = None
        mock_get_auth_service.return_value = mock_auth_service
        
        # Mock Redis
        mock_redis.redis_client = MagicMock()
        mock_redis.connect = AsyncMock()
        
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "wrongpassword"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Incorrect email or password" in response.json()["detail"]
    
    @patch('app.api.v1.auth.get_current_active_user')
    @patch('app.api.v1.auth.get_auth_service')
    def test_logout_success(self, mock_get_auth_service, mock_get_current_user, client, sample_user):
        """Test successful logout"""
        # Mock current user
        mock_get_current_user.return_value = sample_user
        
        # Mock auth service
        mock_auth_service = AsyncMock()
        mock_auth_service.invalidate_session.return_value = True
        mock_get_auth_service.return_value = mock_auth_service
        
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer mock_token"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert "Successfully logged out" in response.json()["message"]
    
    @patch('app.api.v1.auth.get_current_active_user')
    @patch('app.api.v1.auth.get_auth_service')
    def test_refresh_token_success(self, mock_get_auth_service, mock_get_current_user, client, sample_user):
        """Test successful token refresh"""
        # Mock current user
        mock_get_current_user.return_value = sample_user
        
        # Mock auth service
        mock_auth_service = AsyncMock()
        mock_auth_service.refresh_session.return_value = "new_access_token"
        mock_get_auth_service.return_value = mock_auth_service
        
        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": "Bearer mock_token"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["access_token"] == "new_access_token"
        assert data["token_type"] == "bearer"
    
    @patch('app.api.v1.auth.get_current_active_user')
    def test_get_current_user_info(self, mock_get_current_user, client, sample_user):
        """Test getting current user info"""
        # Mock current user
        mock_get_current_user.return_value = sample_user
        
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer mock_token"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["id"] == "user123"
        assert "password" not in data
    
    def test_protected_endpoint_no_token(self, client):
        """Test accessing protected endpoint without token"""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @patch('app.api.v1.auth.verify_token')
    def test_protected_endpoint_invalid_token(self, mock_verify_token, client):
        """Test accessing protected endpoint with invalid token"""
        mock_verify_token.return_value = None
        
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED