"""
Resume API endpoints for file upload, parsing, and management
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.security import HTTPBearer

from app.models.resume import Resume, ResumeUploadResponse, ResumeAnalysis
from app.models.user import UserInDB
from app.services.resume_service import resume_service
from app.api.v1.auth import get_current_user
from app.db.resume_repository import resume_repository
from app.services.ai_service import ai_service
from app.services.cloudinary_service import cloudinary_service

router = APIRouter()
security = HTTPBearer()


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Upload and parse a resume file
    
    - **file**: Resume file (PDF, DOC, or DOCX format)
    - Returns parsed resume data and analysis
    """
    try:
        # Debug: Check if current_user is properly set
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )
        
        print(f"DEBUG: Current user ID: {current_user.id}")
        print(f"DEBUG: Current user email: {current_user.email}")
        
        # Process the resume file
        raw_text, parsed_content = await resume_service.process_resume(file)
        
        print(f"DEBUG: Parsed content type: {type(parsed_content)}")
        print(f"DEBUG: Parsed content: {parsed_content.model_dump()}")
        
        # For now, use a placeholder embedding ID
        # In a complete implementation, this would create an actual vector embedding
        embedding_id = f"embedding_{current_user.id}_{file.filename}"
        
        # Upload file to Cloudinary
        file_url = await cloudinary_service.upload_resume(file, current_user.id)
        
        print(f"DEBUG: File URL: {file_url}")
        print(f"DEBUG: About to create resume with user_id: {current_user.id}")

        # Store in database
        resume = await resume_repository.create_resume(
            user_id=current_user.id,
            original_filename=file.filename,
            file_url=file_url,
            parsed_content=parsed_content,
            embedding_id=embedding_id
        )
        
        return ResumeUploadResponse(
            id=resume.id,
            filename=resume.original_filename,
            status="success",
            message="Resume uploaded and parsed successfully",
            parsed_content=resume.parsed_content
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process resume: {str(e)}"
        )


@router.get("/", response_model=List[Resume])
async def get_user_resumes(
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Get all resumes for the current user
    
    - Returns list of user's resumes
    """
    try:
        resumes = await resume_repository.get_resumes_by_user_id(current_user.id)
        return resumes
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve resumes: {str(e)}"
        )


@router.get("/{resume_id}", response_model=Resume)
async def get_resume(
    resume_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Get a specific resume by ID
    
    - **resume_id**: Resume ID
    - Returns resume data
    """
    try:
        resume = await resume_repository.get_resume_by_id(resume_id)
        
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )
        
        # Check if user owns this resume
        if resume.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return resume
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve resume: {str(e)}"
        )


@router.get("/{resume_id}/analyze", response_model=ResumeAnalysis)
async def analyze_resume(
    resume_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Analyze a resume to get insights and recommendations
    
    - **resume_id**: Resume ID
    - Returns analysis results
    """
    try:
        resume = await resume_repository.get_resume_by_id(resume_id)
        
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )
        
        # Check if user owns this resume
        if resume.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Analyze the resume
        analysis = await resume_service.analyze_resume(resume.parsed_content)
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze resume: {str(e)}"
        )


@router.delete("/{resume_id}")
async def delete_resume(
    resume_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Delete a resume
    
    - **resume_id**: Resume ID
    - Returns success message
    """
    try:
        resume = await resume_repository.get_resume_by_id(resume_id)
        
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )
        
        # Check if user owns this resume
        if resume.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Delete the resume
        success = await resume_repository.delete_resume(resume_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete resume"
            )
        
        return {"message": "Resume deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete resume: {str(e)}"
        )


@router.post("/{resume_id}/reparse")
async def reparse_resume(
    resume_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Reparse an existing resume with updated AI models
    
    - **resume_id**: Resume ID
    - Returns updated resume data
    """
    try:
        resume_with_content = await resume_repository.get_resume_with_content(resume_id)
        
        if not resume_with_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )
        
        # Check if user owns this resume
        if resume_with_content.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Re-extract text from stored file content
        # This is a simplified approach - in production you might want to store the raw text
        raw_text = resume_with_content.parsed_content.raw_text
        
        if not raw_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No raw text available for reparsing. Please re-upload the file."
            )
        
        # Reparse with AI
        new_parsed_content = await resume_service.parse_resume_with_ai(raw_text)
        
        # Update in database
        updated_resume = await resume_repository.update_resume_content(
            resume_id=resume_id,
            parsed_content=new_parsed_content
        )
        
        return ResumeUploadResponse(
            id=updated_resume.id,
            filename=updated_resume.original_filename,
            status="success",
            message="Resume reparsed successfully",
            parsed_content=updated_resume.parsed_content
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reparse resume: {str(e)}"
        )