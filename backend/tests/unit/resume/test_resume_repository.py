"""
Unit tests for resume repository
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.db.resume_repository import ResumeRepository
from app.models.resume import ParsedResumeContent, Resume, ResumeInDB


class TestResumeRepository:
    """Test cases for ResumeRepository"""
    
    @pytest.fixture
    def resume_repository(self):
        """Create ResumeRepository instance for testing"""
        return ResumeRepository()
    
    @pytest.fixture
    def sample_parsed_content(self):
        """Sample parsed resume content"""
        return ParsedResumeContent(
            personal_info={"name": "John Doe", "title": "Software Engineer"},
            contact_info={"email": "john@example.com", "phone": "123-456-7890"},
            summary="Experienced software engineer",
            skills=["Python", "JavaScript", "React"],
            experience=[
                {
                    "title": "Senior Software Engineer",
                    "company": "Tech Corp",
                    "start_date": "2020-01-01",
                    "end_date": "Present"
                }
            ],
            education=[
                {
                    "degree": "Bachelor of Science",
                    "field": "Computer Science",
                    "institution": "University of Technology"
                }
            ],
            raw_text="John Doe Software Engineer..."
        )
    
    @pytest.fixture
    def mock_prisma_resume(self):
        """Mock Prisma resume object"""
        mock_resume = Mock()
        mock_resume.id = "resume_123"
        mock_resume.userId = "user_123"
        mock_resume.originalFilename = "test_resume.pdf"
        mock_resume.fileContent = b"mock file content"
        mock_resume.parsedContent = {
            "personal_info": {"name": "John Doe"},
            "contact_info": {"email": "john@example.com"},
            "skills": ["Python", "JavaScript"],
            "experience": [],
            "education": [],
            "raw_text": "John Doe..."
        }
        mock_resume.embeddingId = "embedding_123"
        mock_resume.createdAt = datetime(2024, 1, 1, 12, 0, 0)
        return mock_resume
    
    @pytest.mark.asyncio
    async def test_create_resume_success(self, resume_repository, sample_parsed_content):
        """Test successful resume creation"""
        mock_db = AsyncMock()
        mock_created_resume = Mock()
        mock_created_resume.id = "resume_123"
        mock_created_resume.userId = "user_123"
        mock_created_resume.originalFilename = "test_resume.pdf"
        mock_created_resume.parsedContent = sample_parsed_content.dict()
        mock_created_resume.embeddingId = "embedding_123"
        mock_created_resume.createdAt = datetime.now()
        
        mock_db.resume.create.return_value = mock_created_resume
        
        with patch('app.db.resume_repository.get_database', return_value=mock_db):
            result = await resume_repository.create_resume(
                user_id="user_123",
                original_filename="test_resume.pdf",
                file_content=b"file content",
                parsed_content=sample_parsed_content,
                embedding_id="embedding_123"
            )
            
            assert isinstance(result, Resume)
            assert result.id == "resume_123"
            assert result.user_id == "user_123"
            assert result.original_filename == "test_resume.pdf"
            
            # Verify database call
            mock_db.resume.create.assert_called_once()
            call_args = mock_db.resume.create.call_args[1]['data']
            assert call_args['userId'] == "user_123"
            assert call_args['originalFilename'] == "test_resume.pdf"
            assert call_args['embeddingId'] == "embedding_123"
    
    @pytest.mark.asyncio
    async def test_get_resume_by_id_found(self, resume_repository, mock_prisma_resume):
        """Test getting resume by ID when found"""
        mock_db = AsyncMock()
        mock_db.resume.find_unique.return_value = mock_prisma_resume
        
        with patch('app.db.resume_repository.get_database', return_value=mock_db):
            result = await resume_repository.get_resume_by_id("resume_123")
            
            assert isinstance(result, Resume)
            assert result.id == "resume_123"
            assert result.user_id == "user_123"
            
            mock_db.resume.find_unique.assert_called_once_with(
                where={'id': "resume_123"}
            )
    
    @pytest.mark.asyncio
    async def test_get_resume_by_id_not_found(self, resume_repository):
        """Test getting resume by ID when not found"""
        mock_db = AsyncMock()
        mock_db.resume.find_unique.return_value = None
        
        with patch('app.db.resume_repository.get_database', return_value=mock_db):
            result = await resume_repository.get_resume_by_id("nonexistent_id")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_resume_with_content_found(self, resume_repository, mock_prisma_resume):
        """Test getting resume with content when found"""
        mock_db = AsyncMock()
        mock_db.resume.find_unique.return_value = mock_prisma_resume
        
        with patch('app.db.resume_repository.get_database', return_value=mock_db):
            result = await resume_repository.get_resume_with_content("resume_123")
            
            assert isinstance(result, ResumeInDB)
            assert result.id == "resume_123"
            assert result.file_content == b"mock file content"
    
    @pytest.mark.asyncio
    async def test_get_resume_with_content_not_found(self, resume_repository):
        """Test getting resume with content when not found"""
        mock_db = AsyncMock()
        mock_db.resume.find_unique.return_value = None
        
        with patch('app.db.resume_repository.get_database', return_value=mock_db):
            result = await resume_repository.get_resume_with_content("nonexistent_id")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_resumes_by_user_id(self, resume_repository, mock_prisma_resume):
        """Test getting all resumes for a user"""
        mock_db = AsyncMock()
        mock_db.resume.find_many.return_value = [mock_prisma_resume]
        
        with patch('app.db.resume_repository.get_database', return_value=mock_db):
            result = await resume_repository.get_resumes_by_user_id("user_123")
            
            assert len(result) == 1
            assert isinstance(result[0], Resume)
            assert result[0].id == "resume_123"
            
            mock_db.resume.find_many.assert_called_once_with(
                where={'userId': "user_123"},
                order_by={'createdAt': 'desc'}
            )
    
    @pytest.mark.asyncio
    async def test_get_resumes_by_user_id_empty(self, resume_repository):
        """Test getting resumes for user with no resumes"""
        mock_db = AsyncMock()
        mock_db.resume.find_many.return_value = []
        
        with patch('app.db.resume_repository.get_database', return_value=mock_db):
            result = await resume_repository.get_resumes_by_user_id("user_123")
            
            assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_update_resume_content_success(self, resume_repository, sample_parsed_content, mock_prisma_resume):
        """Test successful resume content update"""
        mock_db = AsyncMock()
        mock_db.resume.update.return_value = mock_prisma_resume
        
        with patch('app.db.resume_repository.get_database', return_value=mock_db):
            result = await resume_repository.update_resume_content(
                resume_id="resume_123",
                parsed_content=sample_parsed_content,
                embedding_id="new_embedding_123"
            )
            
            assert isinstance(result, Resume)
            assert result.id == "resume_123"
            
            mock_db.resume.update.assert_called_once()
            call_args = mock_db.resume.update.call_args[1]
            assert call_args['where'] == {'id': "resume_123"}
            assert 'parsedContent' in call_args['data']
            assert call_args['data']['embeddingId'] == "new_embedding_123"
    
    @pytest.mark.asyncio
    async def test_update_resume_content_without_embedding(self, resume_repository, sample_parsed_content, mock_prisma_resume):
        """Test resume content update without embedding ID"""
        mock_db = AsyncMock()
        mock_db.resume.update.return_value = mock_prisma_resume
        
        with patch('app.db.resume_repository.get_database', return_value=mock_db):
            result = await resume_repository.update_resume_content(
                resume_id="resume_123",
                parsed_content=sample_parsed_content
            )
            
            assert isinstance(result, Resume)
            
            call_args = mock_db.resume.update.call_args[1]
            assert 'embeddingId' not in call_args['data']
    
    @pytest.mark.asyncio
    async def test_update_resume_content_not_found(self, resume_repository, sample_parsed_content):
        """Test resume content update when resume not found"""
        mock_db = AsyncMock()
        mock_db.resume.update.return_value = None
        
        with patch('app.db.resume_repository.get_database', return_value=mock_db):
            result = await resume_repository.update_resume_content(
                resume_id="nonexistent_id",
                parsed_content=sample_parsed_content
            )
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_resume_success(self, resume_repository):
        """Test successful resume deletion"""
        mock_db = AsyncMock()
        mock_db.resume.delete.return_value = Mock()  # Successful deletion
        
        with patch('app.db.resume_repository.get_database', return_value=mock_db):
            result = await resume_repository.delete_resume("resume_123")
            
            assert result is True
            mock_db.resume.delete.assert_called_once_with(
                where={'id': "resume_123"}
            )
    
    @pytest.mark.asyncio
    async def test_delete_resume_failure(self, resume_repository):
        """Test resume deletion failure"""
        mock_db = AsyncMock()
        mock_db.resume.delete.side_effect = Exception("Delete failed")
        
        with patch('app.db.resume_repository.get_database', return_value=mock_db):
            result = await resume_repository.delete_resume("resume_123")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_user_resume_count(self, resume_repository):
        """Test getting user resume count"""
        mock_db = AsyncMock()
        mock_db.resume.count.return_value = 3
        
        with patch('app.db.resume_repository.get_database', return_value=mock_db):
            result = await resume_repository.get_user_resume_count("user_123")
            
            assert result == 3
            mock_db.resume.count.assert_called_once_with(
                where={'userId': "user_123"}
            )
    
    def test_prisma_to_resume_conversion(self, resume_repository, mock_prisma_resume):
        """Test conversion from Prisma model to Resume model"""
        result = resume_repository._prisma_to_resume(mock_prisma_resume)
        
        assert isinstance(result, Resume)
        assert result.id == "resume_123"
        assert result.user_id == "user_123"
        assert result.original_filename == "test_resume.pdf"
        assert isinstance(result.parsed_content, ParsedResumeContent)
    
    def test_prisma_to_resume_with_content_conversion(self, resume_repository, mock_prisma_resume):
        """Test conversion from Prisma model to ResumeInDB model"""
        result = resume_repository._prisma_to_resume_with_content(mock_prisma_resume)
        
        assert isinstance(result, ResumeInDB)
        assert result.id == "resume_123"
        assert result.user_id == "user_123"
        assert result.file_content == b"mock file content"
        assert isinstance(result.parsed_content, ParsedResumeContent)