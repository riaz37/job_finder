"""
Authentication endpoints
"""
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from prisma import Prisma

from app.core.config import settings
from app.core.security import verify_token
from app.db.database import get_database
from app.models.user import User, UserCreate, UserInDB, Token
from app.services.auth_service import AuthService
from app.services.redis_service import redis_service

router = APIRouter()

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_auth_service(db: Annotated[Prisma, Depends(get_database)]) -> AuthService:
    """Dependency to get authentication service"""
    return AuthService(db)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> UserInDB:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Verify JWT token
    user_id = verify_token(token)
    if user_id is None:
        raise credentials_exception
    
    # Check if session exists in Redis
    session = await auth_service.get_session(user_id)
    if not session:
        raise credentials_exception
    
    # Get user from database
    user = await auth_service.get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: Annotated[UserInDB, Depends(get_current_user)]
) -> UserInDB:
    """Get current active user (placeholder for future user status checks)"""
    return current_user


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """Register a new user"""
    try:
        # Ensure Redis is connected
        if not redis_service.redis_client:
            await redis_service.connect()
        
        # Create user
        db_user = await auth_service.create_user(user_data)
        
        # Return user without password hash
        return User(
            id=db_user.id,
            email=db_user.email,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """Login user and return access token"""
    try:
        # Ensure Redis is connected
        if not redis_service.redis_client:
            await redis_service.connect()
        
        # Authenticate user
        user = await auth_service.authenticate_user(form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create session and get token
        access_token = await auth_service.create_session(user)
        
        return Token(access_token=access_token, token_type="bearer")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.post("/logout")
async def logout(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """Logout user and invalidate session"""
    try:
        await auth_service.invalidate_session(current_user.id)
        return {"message": "Successfully logged out"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """Refresh user access token"""
    try:
        new_token = await auth_service.refresh_session(current_user.id)
        if not new_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not refresh token"
            )
        
        return Token(access_token=new_token, token_type="bearer")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )


@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    """Get current user information"""
    return User(
        id=current_user.id,
        email=current_user.email,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )