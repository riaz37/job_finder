"""
Resume processing service for file upload, parsing, and AI analysis
"""
import io
import os
import tempfile
from typing import Optional, Tuple, List
import magic
from fastapi import HTTPException, UploadFile
import PyPDF2
from docx import Document
import json

from app.models.resume import ParsedResumeContent, ResumeAnalysis
from app.core.config import settings
from app.services.ai_service import AIService


class ResumeService:
    """Service for handling resume upload, parsing, and analysis"""
    
    def __init__(self):
        self.ai_service = AIService()
        self.allowed_mime_types = {
            'application/pdf': '.pdf',
            'application/msword': '.doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx'
        }
    
    async def validate_file(self, file: UploadFile) -> Tuple[bool, str]:
        """
        Validate uploaded file format and size
        
        Args:
            file: Uploaded file object
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file size
        if file.size and file.size > settings.MAX_FILE_SIZE:
            return False, f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE / (1024*1024):.1f}MB"
        
        # Read file content for MIME type detection
        content = await file.read()
        await file.seek(0)  # Reset file pointer
        
        # Detect MIME type
        mime_type = magic.from_buffer(content, mime=True)
        
        if mime_type not in self.allowed_mime_types:
            return False, f"Unsupported file type. Allowed types: {', '.join(settings.ALLOWED_FILE_TYPES)}"
        
        return True, ""
    
    async def extract_text_from_pdf(self, file_content: bytes) -> str:
        """
        Extract text from PDF file
        
        Args:
            file_content: PDF file content as bytes
            
        Returns:
            Extracted text content
        """
        try:
            pdf_file = io.BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text_content = []
            for page in pdf_reader.pages:
                text_content.append(page.extract_text())
            
            return "\n".join(text_content)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to extract text from PDF: {str(e)}")
    
    async def extract_text_from_docx(self, file_content: bytes) -> str:
        """
        Extract text from DOCX file
        
        Args:
            file_content: DOCX file content as bytes
            
        Returns:
            Extracted text content
        """
        try:
            # Create temporary file for docx processing
            with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            try:
                doc = Document(temp_file_path)
                text_content = []
                
                for paragraph in doc.paragraphs:
                    text_content.append(paragraph.text)
                
                return "\n".join(text_content)
            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)
                
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to extract text from DOCX: {str(e)}")
    
    async def extract_text_from_doc(self, file_content: bytes) -> str:
        """
        Extract text from DOC file (legacy Word format)
        Note: This is a simplified implementation. For production, consider using python-docx2txt or antiword
        
        Args:
            file_content: DOC file content as bytes
            
        Returns:
            Extracted text content
        """
        # For now, return a placeholder. In production, you'd use a proper DOC parser
        # like python-docx2txt or antiword
        raise HTTPException(
            status_code=400, 
            detail="DOC format not fully supported yet. Please convert to DOCX or PDF format."
        )
    
    async def extract_text(self, file: UploadFile) -> str:
        """
        Extract text from uploaded resume file
        
        Args:
            file: Uploaded file object
            
        Returns:
            Extracted text content
        """
        content = await file.read()
        await file.seek(0)  # Reset file pointer
        
        # Detect file type
        mime_type = magic.from_buffer(content, mime=True)
        
        if mime_type == 'application/pdf':
            return await self.extract_text_from_pdf(content)
        elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            return await self.extract_text_from_docx(content)
        elif mime_type == 'application/msword':
            return await self.extract_text_from_doc(content)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {mime_type}")
    
    async def parse_resume_with_ai(self, text_content: str) -> ParsedResumeContent:
        """
        Parse resume text using AI to extract structured information
        
        Args:
            text_content: Raw text extracted from resume
            
        Returns:
            Structured resume content
        """
        try:
            # Use AI service to parse resume content
            parsed_data = await self.ai_service.parse_resume_content(text_content)
            
            return ParsedResumeContent(
                personal_info=parsed_data.get('personal_info', {}),
                contact_info=parsed_data.get('contact_info', {}),
                summary=parsed_data.get('summary'),
                skills=parsed_data.get('skills', []),
                experience=parsed_data.get('experience', []),
                education=parsed_data.get('education', []),
                certifications=parsed_data.get('certifications', []),
                languages=parsed_data.get('languages', []),
                raw_text=text_content
            )
        except Exception as e:
            # If AI parsing fails, return basic structure with raw text
            return ParsedResumeContent(
                raw_text=text_content,
                skills=[],  # Could implement basic keyword extraction as fallback
                experience=[],
                education=[]
            )
    
    async def analyze_resume(self, parsed_content: ParsedResumeContent) -> ResumeAnalysis:
        """
        Analyze parsed resume content to extract insights
        
        Args:
            parsed_content: Structured resume content
            
        Returns:
            Resume analysis results
        """
        try:
            analysis_data = await self.ai_service.analyze_resume(parsed_content.dict())
            
            return ResumeAnalysis(
                skills_extracted=analysis_data.get('skills_extracted', parsed_content.skills),
                experience_years=analysis_data.get('experience_years'),
                education_level=analysis_data.get('education_level'),
                key_strengths=analysis_data.get('key_strengths', []),
                suggested_improvements=analysis_data.get('suggested_improvements', [])
            )
        except Exception as e:
            # Return basic analysis if AI analysis fails
            return ResumeAnalysis(
                skills_extracted=parsed_content.skills,
                key_strengths=[],
                suggested_improvements=[]
            )
    
    async def process_resume(self, file: UploadFile) -> Tuple[str, ParsedResumeContent]:
        """
        Complete resume processing pipeline
        
        Args:
            file: Uploaded resume file
            
        Returns:
            Tuple of (raw_text, parsed_content)
        """
        # Validate file
        is_valid, error_message = await self.validate_file(file)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_message)
        
        # Extract text
        text_content = await self.extract_text(file)
        
        if not text_content.strip():
            raise HTTPException(status_code=400, detail="No text content found in the uploaded file")
        
        # Parse with AI
        parsed_content = await self.parse_resume_with_ai(text_content)
        
        return text_content, parsed_content


# Global instance
resume_service = ResumeService()