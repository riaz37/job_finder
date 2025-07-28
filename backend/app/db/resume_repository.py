"""
Resume repository for database operations
"""
from typing import Optional, List
from prisma import Prisma
from prisma.models import Resume as PrismaResume

from app.models.resume import ParsedResumeContent, Resume, ResumeInDB
from app.db.database import get_database


class ResumeRepository:
    """Repository for resume database operations"""
    
    async def create_resume(
        self,
        user_id: str,
        original_filename: str,
        file_content: bytes,
        parsed_content: ParsedResumeContent,
        embedding_id: str
    ) -> Resume:
        """
        Create a new resume record in the database
        
        Args:
            user_id: ID of the user who owns the resume
            original_filename: Original filename of the uploaded file
            file_content: Binary content of the uploaded file
            parsed_content: Structured parsed content
            embedding_id: ID of the vector embedding in Pinecone
            
        Returns:
            Created resume object
        """
        db = await get_database()
        
        # Convert parsed content to JSON-serializable format
        parsed_content_dict = self._serialize_parsed_content(parsed_content)
        
        resume_data = await db.resume.create(
            data={
                'userId': user_id,
                'originalFilename': original_filename,
                'fileContent': file_content,
                'parsedContent': parsed_content_dict,
                'embeddingId': embedding_id
            }
        )
        
        return self._prisma_to_resume(resume_data)
    
    async def get_resume_by_id(self, resume_id: str) -> Optional[Resume]:
        """
        Get resume by ID
        
        Args:
            resume_id: Resume ID
            
        Returns:
            Resume object or None if not found
        """
        db = await get_database()
        
        resume_data = await db.resume.find_unique(
            where={'id': resume_id}
        )
        
        if not resume_data:
            return None
        
        return self._prisma_to_resume(resume_data)
    
    async def get_resume_with_content(self, resume_id: str) -> Optional[ResumeInDB]:
        """
        Get resume with file content by ID
        
        Args:
            resume_id: Resume ID
            
        Returns:
            Resume object with file content or None if not found
        """
        db = await get_database()
        
        resume_data = await db.resume.find_unique(
            where={'id': resume_id}
        )
        
        if not resume_data:
            return None
        
        return self._prisma_to_resume_with_content(resume_data)
    
    async def get_resumes_by_user_id(self, user_id: str) -> List[Resume]:
        """
        Get all resumes for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of resume objects
        """
        db = await get_database()
        
        resumes_data = await db.resume.find_many(
            where={'userId': user_id},
            order_by={'createdAt': 'desc'}
        )
        
        return [self._prisma_to_resume(resume) for resume in resumes_data]
    
    async def update_resume_content(
        self,
        resume_id: str,
        parsed_content: ParsedResumeContent,
        embedding_id: Optional[str] = None
    ) -> Optional[Resume]:
        """
        Update resume parsed content and optionally embedding ID
        
        Args:
            resume_id: Resume ID
            parsed_content: Updated parsed content
            embedding_id: Updated embedding ID (optional)
            
        Returns:
            Updated resume object or None if not found
        """
        db = await get_database()
        
        # Convert parsed content to JSON-serializable format
        parsed_content_dict = self._serialize_parsed_content(parsed_content)
        
        update_data = {'parsedContent': parsed_content_dict}
        if embedding_id:
            update_data['embeddingId'] = embedding_id
        
        resume_data = await db.resume.update(
            where={'id': resume_id},
            data=update_data
        )
        
        if not resume_data:
            return None
        
        return self._prisma_to_resume(resume_data)
    
    async def delete_resume(self, resume_id: str) -> bool:
        """
        Delete resume by ID
        
        Args:
            resume_id: Resume ID
            
        Returns:
            True if deleted, False if not found
        """
        db = await get_database()
        
        try:
            await db.resume.delete(
                where={'id': resume_id}
            )
            return True
        except Exception:
            return False
    
    async def get_user_resume_count(self, user_id: str) -> int:
        """
        Get count of resumes for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Number of resumes
        """
        db = await get_database()
        
        return await db.resume.count(
            where={'userId': user_id}
        )
    
    def _prisma_to_resume(self, prisma_resume: PrismaResume) -> Resume:
        """Convert Prisma resume model to Resume model"""
        return Resume(
            id=prisma_resume.id,
            user_id=prisma_resume.userId,
            original_filename=prisma_resume.originalFilename,
            parsed_content=ParsedResumeContent(**prisma_resume.parsedContent),
            embedding_id=prisma_resume.embeddingId,
            created_at=prisma_resume.createdAt
        )
    
    def _prisma_to_resume_with_content(self, prisma_resume: PrismaResume) -> ResumeInDB:
        """Convert Prisma resume model to ResumeInDB model with file content"""
        return ResumeInDB(
            id=prisma_resume.id,
            user_id=prisma_resume.userId,
            original_filename=prisma_resume.originalFilename,
            file_content=prisma_resume.fileContent,
            parsed_content=ParsedResumeContent(**prisma_resume.parsedContent),
            embedding_id=prisma_resume.embeddingId,
            created_at=prisma_resume.createdAt
        )
    
    def _serialize_parsed_content(self, parsed_content: ParsedResumeContent) -> dict:
        """
        Serialize parsed content to ensure it's JSON-serializable
        
        Args:
            parsed_content: ParsedResumeContent object
            
        Returns:
            JSON-serializable dictionary
        """
        import json
        
        def serialize_value(value):
            """Recursively serialize values to ensure JSON compatibility"""
            if isinstance(value, bytes):
                # Convert bytes to base64 string
                import base64
                return base64.b64encode(value).decode('utf-8')
            elif isinstance(value, dict):
                return {k: serialize_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [serialize_value(item) for item in value]
            elif hasattr(value, '__dict__'):
                # Handle objects with __dict__ attribute
                return serialize_value(value.__dict__)
            else:
                # For basic types (str, int, float, bool, None)
                try:
                    json.dumps(value)  # Test if it's JSON serializable
                    return value
                except (TypeError, ValueError):
                    # If not serializable, convert to string
                    return str(value)
        
        try:
            # First try the normal dict() method
            content_dict = parsed_content.dict()
            # Then ensure all values are serializable
            return serialize_value(content_dict)
        except Exception as e:
            # Fallback: manually construct the dictionary
            return {
                'personal_info': serialize_value(parsed_content.personal_info),
                'contact_info': serialize_value(parsed_content.contact_info),
                'summary': serialize_value(parsed_content.summary),
                'skills': serialize_value(parsed_content.skills),
                'experience': serialize_value(parsed_content.experience),
                'education': serialize_value(parsed_content.education),
                'certifications': serialize_value(parsed_content.certifications),
                'languages': serialize_value(parsed_content.languages),
                'raw_text': serialize_value(parsed_content.raw_text)
            }


# Global instance
resume_repository = ResumeRepository()