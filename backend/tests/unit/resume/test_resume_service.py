"""
Unit tests for resume service
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import HTTPException, UploadFile
import io

from app.services.resume_service import ResumeService
from app.models.resume import ParsedResumeContent


class TestResumeService:
    """Test cases for ResumeService"""
    
    @pytest.fixture
    def resume_service(self):
        """Create ResumeService instance for testing"""
        return ResumeService()
    
    @pytest.fixture
    def mock_pdf_file(self):
        """Create mock PDF file"""
        file_content = b"Mock PDF content"
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test_resume.pdf"
        mock_file.size = len(file_content)
        mock_file.read = AsyncMock(return_value=file_content)
        mock_file.seek = AsyncMock()
        return mock_file
    
    @pytest.fixture
    def mock_docx_file(self):
        """Create mock DOCX file"""
        file_content = b"Mock DOCX content"
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test_resume.docx"
        mock_file.size = len(file_content)
        mock_file.read = AsyncMock(return_value=file_content)
        mock_file.seek = AsyncMock()
        return mock_file
    
    @pytest.fixture
    def sample_parsed_content(self):
        """Sample parsed resume content"""
        return ParsedResumeContent(
            personal_info={"name": "John Doe", "title": "Software Engineer"},
            contact_info={"email": "john@example.com", "phone": "123-456-7890"},
            summary="Experienced software engineer with 5 years of experience",
            skills=["Python", "JavaScript", "React", "FastAPI"],
            experience=[
                {
                    "title": "Senior Software Engineer",
                    "company": "Tech Corp",
                    "start_date": "2020-01-01",
                    "end_date": "Present",
                    "description": "Led development of web applications"
                }
            ],
            education=[
                {
                    "degree": "Bachelor of Science",
                    "field": "Computer Science",
                    "institution": "University of Technology",
                    "graduation_date": "2018-05-01"
                }
            ],
            raw_text="John Doe Software Engineer..."
        )
    
    @pytest.mark.asyncio
    async def test_validate_file_success(self, resume_service, mock_pdf_file):
        """Test successful file validation"""
        with patch('magic.from_buffer', return_value='application/pdf'):
            is_valid, error_message = await resume_service.validate_file(mock_pdf_file)
            
            assert is_valid is True
            assert error_message == ""
    
    @pytest.mark.asyncio
    async def test_validate_file_size_too_large(self, resume_service):
        """Test file validation with oversized file"""
        large_file = Mock(spec=UploadFile)
        large_file.size = 20 * 1024 * 1024  # 20MB
        large_file.read = AsyncMock(return_value=b"content")
        
        is_valid, error_message = await resume_service.validate_file(large_file)
        
        assert is_valid is False
        assert "exceeds maximum allowed size" in error_message
    
    @pytest.mark.asyncio
    async def test_validate_file_unsupported_type(self, resume_service):
        """Test file validation with unsupported file type"""
        unsupported_file = Mock(spec=UploadFile)
        unsupported_file.size = 1024
        unsupported_file.read = AsyncMock(return_value=b"content")
        
        with patch('magic.from_buffer', return_value='text/plain'):
            is_valid, error_message = await resume_service.validate_file(unsupported_file)
            
            assert is_valid is False
            assert "Unsupported file type" in error_message
    
    @pytest.mark.asyncio
    async def test_extract_text_from_pdf_success(self, resume_service):
        """Test successful PDF text extraction"""
        # Mock PDF content
        mock_pdf_content = b"Mock PDF binary content"
        
        with patch('PyPDF2.PdfReader') as mock_pdf_reader:
            # Mock PDF reader and pages
            mock_page = Mock()
            mock_page.extract_text.return_value = "Sample resume text"
            
            mock_reader_instance = Mock()
            mock_reader_instance.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader_instance
            
            result = await resume_service.extract_text_from_pdf(mock_pdf_content)
            
            assert result == "Sample resume text"
            mock_pdf_reader.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extract_text_from_pdf_failure(self, resume_service):
        """Test PDF text extraction failure"""
        mock_pdf_content = b"Invalid PDF content"
        
        with patch('PyPDF2.PdfReader', side_effect=Exception("PDF parsing error")):
            with pytest.raises(HTTPException) as exc_info:
                await resume_service.extract_text_from_pdf(mock_pdf_content)
            
            assert exc_info.value.status_code == 400
            assert "Failed to extract text from PDF" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_extract_text_from_docx_success(self, resume_service):
        """Test successful DOCX text extraction"""
        mock_docx_content = b"Mock DOCX binary content"
        
        with patch('tempfile.NamedTemporaryFile') as mock_temp_file, \
             patch('app.services.resume_service.Document') as mock_document, \
             patch('os.unlink'):
            
            # Mock temporary file
            mock_temp_file.return_value.__enter__.return_value.name = "/tmp/test.docx"
            
            # Mock document and paragraphs
            mock_paragraph = Mock()
            mock_paragraph.text = "Sample resume text"
            
            mock_doc_instance = Mock()
            mock_doc_instance.paragraphs = [mock_paragraph]
            mock_document.return_value = mock_doc_instance
            
            result = await resume_service.extract_text_from_docx(mock_docx_content)
            
            assert result == "Sample resume text"
    
    @pytest.mark.asyncio
    async def test_extract_text_from_doc_not_supported(self, resume_service):
        """Test DOC format not supported"""
        mock_doc_content = b"Mock DOC content"
        
        with pytest.raises(HTTPException) as exc_info:
            await resume_service.extract_text_from_doc(mock_doc_content)
        
        assert exc_info.value.status_code == 400
        assert "DOC format not fully supported" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_extract_text_pdf(self, resume_service, mock_pdf_file):
        """Test text extraction from PDF file"""
        with patch('magic.from_buffer', return_value='application/pdf'), \
             patch.object(resume_service, 'extract_text_from_pdf', return_value="Extracted text"):
            
            result = await resume_service.extract_text(mock_pdf_file)
            
            assert result == "Extracted text"
    
    @pytest.mark.asyncio
    async def test_extract_text_docx(self, resume_service, mock_docx_file):
        """Test text extraction from DOCX file"""
        with patch('magic.from_buffer', return_value='application/vnd.openxmlformats-officedocument.wordprocessingml.document'), \
             patch.object(resume_service, 'extract_text_from_docx', return_value="Extracted text"):
            
            result = await resume_service.extract_text(mock_docx_file)
            
            assert result == "Extracted text"
    
    @pytest.mark.asyncio
    async def test_extract_text_unsupported_type(self, resume_service):
        """Test text extraction with unsupported file type"""
        mock_file = Mock(spec=UploadFile)
        mock_file.read = AsyncMock(return_value=b"content")
        
        with patch('magic.from_buffer', return_value='text/plain'):
            with pytest.raises(HTTPException) as exc_info:
                await resume_service.extract_text(mock_file)
            
            assert exc_info.value.status_code == 400
            assert "Unsupported file type" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_parse_resume_with_ai_success(self, resume_service):
        """Test successful AI resume parsing"""
        text_content = "John Doe Software Engineer..."
        
        mock_ai_response = {
            "personal_info": {"name": "John Doe", "title": "Software Engineer"},
            "contact_info": {"email": "john@example.com"},
            "skills": ["Python", "JavaScript"],
            "experience": [],
            "education": []
        }
        
        with patch.object(resume_service.ai_service, 'parse_resume_content', return_value=mock_ai_response):
            result = await resume_service.parse_resume_with_ai(text_content)
            
            assert isinstance(result, ParsedResumeContent)
            assert result.personal_info["name"] == "John Doe"
            assert result.skills == ["Python", "JavaScript"]
            assert result.raw_text == text_content
    
    @pytest.mark.asyncio
    async def test_parse_resume_with_ai_failure_fallback(self, resume_service):
        """Test AI parsing failure with fallback"""
        text_content = "John Doe Software Engineer..."
        
        with patch.object(resume_service.ai_service, 'parse_resume_content', side_effect=Exception("AI error")):
            result = await resume_service.parse_resume_with_ai(text_content)
            
            assert isinstance(result, ParsedResumeContent)
            assert result.raw_text == text_content
            assert result.skills == []
    
    @pytest.mark.asyncio
    async def test_analyze_resume_success(self, resume_service, sample_parsed_content):
        """Test successful resume analysis"""
        mock_analysis = {
            "skills_extracted": ["Python", "JavaScript", "React"],
            "experience_years": 5,
            "education_level": "Bachelor's",
            "key_strengths": ["Full-stack development", "Team leadership"],
            "suggested_improvements": ["Add more quantifiable achievements"]
        }
        
        with patch.object(resume_service.ai_service, 'analyze_resume', return_value=mock_analysis):
            result = await resume_service.analyze_resume(sample_parsed_content)
            
            assert result.skills_extracted == ["Python", "JavaScript", "React"]
            assert result.experience_years == 5
            assert result.education_level == "Bachelor's"
    
    @pytest.mark.asyncio
    async def test_analyze_resume_failure_fallback(self, resume_service, sample_parsed_content):
        """Test resume analysis failure with fallback"""
        with patch.object(resume_service.ai_service, 'analyze_resume', side_effect=Exception("AI error")):
            result = await resume_service.analyze_resume(sample_parsed_content)
            
            assert result.skills_extracted == sample_parsed_content.skills
            assert result.key_strengths == []
    
    @pytest.mark.asyncio
    async def test_process_resume_success(self, resume_service, mock_pdf_file, sample_parsed_content):
        """Test complete resume processing pipeline"""
        with patch.object(resume_service, 'validate_file', return_value=(True, "")), \
             patch.object(resume_service, 'extract_text', return_value="Sample text"), \
             patch.object(resume_service, 'parse_resume_with_ai', return_value=sample_parsed_content):
            
            text, parsed = await resume_service.process_resume(mock_pdf_file)
            
            assert text == "Sample text"
            assert parsed == sample_parsed_content
    
    @pytest.mark.asyncio
    async def test_process_resume_validation_failure(self, resume_service, mock_pdf_file):
        """Test resume processing with validation failure"""
        with patch.object(resume_service, 'validate_file', return_value=(False, "Invalid file")):
            with pytest.raises(HTTPException) as exc_info:
                await resume_service.process_resume(mock_pdf_file)
            
            assert exc_info.value.status_code == 400
            assert "Invalid file" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_process_resume_empty_text(self, resume_service, mock_pdf_file):
        """Test resume processing with empty text extraction"""
        with patch.object(resume_service, 'validate_file', return_value=(True, "")), \
             patch.object(resume_service, 'extract_text', return_value="   "):
            
            with pytest.raises(HTTPException) as exc_info:
                await resume_service.process_resume(mock_pdf_file)
            
            assert exc_info.value.status_code == 400
            assert "No text content found" in str(exc_info.value.detail)