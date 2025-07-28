"""
Unit tests for security utilities
"""
import pytest
from datetime import datetime, timedelta
from jose import jwt

from app.core.security import (
    create_access_token,
    verify_password,
    get_password_hash,
    verify_token,
    ALGORITHM
)
from app.core.config import settings


class TestSecurityUtils:
    """Test cases for security utilities"""
    
    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "testpassword123"
        
        # Hash password
        hashed = get_password_hash(password)
        
        # Verify correct password
        assert verify_password(password, hashed) is True
        
        # Verify incorrect password
        assert verify_password("wrongpassword", hashed) is False
    
    def test_password_hash_different_each_time(self):
        """Test that password hashing produces different hashes each time"""
        password = "testpassword123"
        
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Hashes should be different due to salt
        assert hash1 != hash2
        
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True
    
    def test_create_access_token_default_expiry(self):
        """Test creating access token with default expiry"""
        data = {"sub": "user123"}
        
        token = create_access_token(data)
        
        # Decode token to verify contents
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "user123"
        assert "exp" in payload
        
        # Check expiry is approximately correct (within 1 minute)
        expected_exp = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        actual_exp = datetime.fromtimestamp(payload["exp"])
        assert abs((expected_exp - actual_exp).total_seconds()) < 60
    
    def test_create_access_token_custom_expiry(self):
        """Test creating access token with custom expiry"""
        data = {"sub": "user123"}
        expires_delta = timedelta(minutes=30)
        
        token = create_access_token(data, expires_delta)
        
        # Decode token to verify contents
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "user123"
        
        # Check custom expiry
        expected_exp = datetime.utcnow() + expires_delta
        actual_exp = datetime.fromtimestamp(payload["exp"])
        assert abs((expected_exp - actual_exp).total_seconds()) < 60
    
    def test_verify_token_valid(self):
        """Test verifying valid token"""
        data = {"sub": "user123"}
        token = create_access_token(data)
        
        user_id = verify_token(token)
        
        assert user_id == "user123"
    
    def test_verify_token_invalid(self):
        """Test verifying invalid token"""
        invalid_token = "invalid.token.here"
        
        user_id = verify_token(invalid_token)
        
        assert user_id is None
    
    def test_verify_token_expired(self):
        """Test verifying expired token"""
        data = {"sub": "user123"}
        # Create token that expires immediately
        expires_delta = timedelta(seconds=-1)
        token = create_access_token(data, expires_delta)
        
        user_id = verify_token(token)
        
        assert user_id is None
    
    def test_verify_token_no_subject(self):
        """Test verifying token without subject"""
        # Create token without 'sub' claim
        data = {"user": "user123"}  # Wrong key
        token = create_access_token(data)
        
        user_id = verify_token(token)
        
        assert user_id is None
    
    def test_verify_token_wrong_secret(self):
        """Test verifying token with wrong secret"""
        data = {"sub": "user123"}
        
        # Create token with different secret
        wrong_token = jwt.encode(data, "wrong_secret", algorithm=ALGORITHM)
        
        user_id = verify_token(wrong_token)
        
        assert user_id is None