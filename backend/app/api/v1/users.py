"""
User profile management endpoints
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from prisma import Prisma

from app.db.database import get_database
from app.models.user import User, UserInDB, UserUpdate
from app.services.auth_service import AuthService
from app.api.v1.auth import get_current_active_user, get_auth_service

router = APIRouter()


@router.get("/profile", response_model=User)
async def get_user_profile(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    """Get current user profile"""
    return User(
        id=current_user.id,
        email=current_user.email,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )


@router.put("/profile", response_model=User)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """Update user profile"""
    try:
        # Get database client
        db = auth_service.db
        
        # Prepare update data
        update_data = {}
        
        # Update email if provided
        if user_update.email and user_update.email != current_user.email:
            # Check if email is already taken
            existing_user = await db.user.find_unique(
                where={"email": user_update.email}
            )
            if existing_user and existing_user.id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            update_data["email"] = user_update.email
        
        # Update password if provided
        if user_update.password:
            success = await auth_service.update_user_password(
                current_user.id, 
                user_update.password
            )
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update password"
                )
        
        # Update user in database if there are changes
        if update_data:
            updated_user = await db.user.update(
                where={"id": current_user.id},
                data=update_data
            )
            
            return User(
                id=updated_user.id,
                email=updated_user.email,
                created_at=updated_user.createdAt,
                updated_at=updated_user.updatedAt
            )
        
        # Return current user if no changes
        return User(
            id=current_user.id,
            email=current_user.email,
            created_at=current_user.created_at,
            updated_at=current_user.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )


@router.delete("/profile")
async def delete_user_profile(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """Delete user profile and all associated data"""
    try:
        # Get database client
        db = auth_service.db
        
        # Delete user (cascade will handle related data)
        await db.user.delete(
            where={"id": current_user.id}
        )
        
        # Invalidate session
        await auth_service.invalidate_session(current_user.id)
        
        return {"message": "User profile deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete profile: {str(e)}"
        )


@router.post("/change-password")
async def change_password(
    password_data: dict,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """Change user password with current password verification"""
    try:
        current_password = password_data.get("current_password")
        new_password = password_data.get("new_password")
        
        if not current_password or not new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both current_password and new_password are required"
            )
        
        # Verify current password
        user = await auth_service.authenticate_user(current_user.email, current_password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        success = await auth_service.update_user_password(current_user.id, new_password)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password"
            )
        
        # Invalidate current session to force re-login
        await auth_service.invalidate_session(current_user.id)
        
        return {"message": "Password changed successfully. Please log in again."}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to change password: {str(e)}"
        )


@router.get("/sessions")
async def get_user_sessions(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """Get current user session information"""
    try:
        session = await auth_service.get_session(current_user.id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active session found"
            )
        
        # Remove sensitive information before returning
        safe_session = {
            "user_id": session.get("user_id"),
            "email": session.get("email"),
            "created_at": session.get("created_at")
        }
        
        return {"session": safe_session}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session info: {str(e)}"
        )