"""
Unit tests for embedding service
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any

from app.services.embedding_service import EmbeddingService, embedding_service
from app.models.resume import ResumeData, ParsedResume
from jobspy.model import JobPost


class TestEmbeddingService:
    """Test cases for EmbeddingService"""
    
    @pytest.fixture
    def mock_vector_service(self):
        """Mock vector service"""
        with patch('app.services.embedding_service.vector_service') as mock_vs:
            mock_vs.store_resume_embedding = AsyncMock(return_value="vector_123")
            mock_vs.store_job_embedding = AsyncMock(return_value="vector_456")
            mock_vs.find_similar_jobs = AsyncMock(return_value=[])
            mock_vs.calculate_similarity_score = AsyncMock(return_value=0.8)
            yield mock_vs
    
    @pytest.fixture
    def sample_resume_data(self):
        """Sample resume data"""
        return ResumeData(
            id="resume_123",
            user_id="user_456",
            original_filename="john_doe_resume.pdf",
            created_at=datetime.now()
        )
    
    @pytest.fixture
    def sample_parsed_resume(self):
        """Sample parsed resume"""
        return ParsedResume(
            personal_info={"name": "John Doe", "email": "john@example.com"},
            summary="Experienced software engineer with 5 years in Python development",
            skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
            work_experience=[
                {
                    "title": "Senior Software Engineer",
                    "company": "TechCorp",
                    "duration": "2020-2023",
                    "description": "Led development of microservices architecture"
                }
            ],
            education=[
                {
                    "degree": "Bachelor of Computer Science",
                    "institution": "University of Technology",
                    "year": "2018"
                }
            ],
            certifications=["AWS Certified Developer", "Python Professional"],
            experience_years=5,
            education_level="Bachelor's",
            job_titles=["Software Engineer", "Senior Software Engineer"],
            industries=["Technology", "Software Development"]
        )
    
    @pytest.fixture
    def sample_job_post(self):
        """Sample job posting"""
        job = Mock(spec=JobPost)
        job.id = "job_789"
        job.title = "Python Developer"
        job.company = "StartupCorp"
        job.location = "San Francisco, CA"
        job.description = "Looking for a Python developer with FastAPI experience"
        job.job_url = "https://example.com/job/789"
        job.site = Mock()
        job.site.value = "indeed"
        job.job_type = "full-time"
        job.min_amount = 80000
        job.max_amount = 120000
        job.currency = "USD"
        return job
    
    @pytest.fixture
    def embedding_service_instance(self, mock_vector_service):
        """Create embedding service instance with mocked dependencies"""
        return EmbeddingService()
    
    @pytest.mark.asyncio
    async def test_process_resume_embedding(
        self, 
        embedding_service_instance, 
        sample_resume_data, 
        sample_parsed_resume,
        mock_vector_service
    ):
        """Test processing resume embedding"""
        vector_id = await embedding_service_instance.process_resume_embedding(
            sample_resume_data, sample_parsed_resume
        )
        
        assert vector_id == "vector_123"
        
        # Verify vector service was called with correct parameters
        mock_vector_service.store_resume_embedding.assert_called_once()
        call_args = mock_vector_service.store_resume_embedding.call_args
        
        assert call_args[1]["resume_id"] == "resume_123"
        assert call_args[1]["user_id"] == "user_456"
        assert "resume_content" in call_args[1]
        assert "metadata" in call_args[1]
        
        # Check metadata content
        metadata = call_args[1]["metadata"]
        assert metadata["skills"] == ["Python", "FastAPI", "PostgreSQL", "Docker"]
        assert metadata["experience_years"] == 5
        assert metadata["education_level"] == "Bachelor's"
        assert metadata["filename"] == "john_doe_resume.pdf"
    
    def test_prepare_resume_text(self, embedding_service_instance, sample_parsed_resume):
        """Test resume text preparation"""
        text = embedding_service_instance._prepare_resume_text(sample_parsed_resume)
        
        assert "Name: John Doe" in text
        assert "Email: john@example.com" in text
        assert "Summary: Experienced software engineer" in text
        assert "Skills: Python, FastAPI, PostgreSQL, Docker" in text
        assert "Work Experience:" in text
        assert "Senior Software Engineer at TechCorp" in text
        assert "Education:" in text
        assert "Bachelor of Computer Science from University of Technology" in text
        assert "Certifications: AWS Certified Developer, Python Professional" in text
    
    def test_prepare_resume_text_minimal(self, embedding_service_instance):
        """Test resume text preparation with minimal data"""
        minimal_resume = ParsedResume(
            skills=["Python"],
            summary="Software developer"
        )
        
        text = embedding_service_instance._prepare_resume_text(minimal_resume)
        
        assert "Summary: Software developer" in text
        assert "Skills: Python" in text
        assert len(text.strip()) > 0
    
    @pytest.mark.asyncio
    async def test_process_job_embedding(
        self, 
        embedding_service_instance, 
        sample_job_post,
        mock_vector_service
    ):
        """Test processing job embedding"""
        vector_id = await embedding_service_instance.process_job_embedding(sample_job_post)
        
        assert vector_id == "vector_456"
        
        # Verify vector service was called with correct parameters
        mock_vector_service.store_job_embedding.assert_called_once()
        call_args = mock_vector_service.store_job_embedding.call_args
        
        assert "job_content" in call_args[1]
        assert "metadata" in call_args[1]
        
        # Check metadata content
        metadata = call_args[1]["metadata"]
        assert metadata["company"] == "StartupCorp"
        assert metadata["title"] == "Python Developer"
        assert metadata["location"] == "San Francisco, CA"
        assert metadata["job_type"] == "full-time"
        assert metadata["salary_min"] == 80000
        assert metadata["salary_max"] == 120000
        assert metadata["currency"] == "USD"
        assert metadata["site"] == "indeed"
    
    def test_prepare_job_text(self, embedding_service_instance, sample_job_post):
        """Test job text preparation"""
        text = embedding_service_instance._prepare_job_text(sample_job_post)
        
        assert "Job Title: Python Developer" in text
        assert "Company: StartupCorp" in text
        assert "Location: San Francisco, CA" in text
        assert "Job Type: full-time" in text
        assert "Salary: 80000 - 120000 USD" in text
        assert "Description: Looking for a Python developer" in text
    
    def test_prepare_job_text_minimal(self, embedding_service_instance):
        """Test job text preparation with minimal data"""
        minimal_job = Mock(spec=JobPost)
        minimal_job.title = "Developer"
        minimal_job.company = "Company"
        minimal_job.location = None
        minimal_job.description = "Job description"
        minimal_job.job_url = "https://example.com/job"
        
        text = embedding_service_instance._prepare_job_text(minimal_job)
        
        assert "Job Title: Developer" in text
        assert "Company: Company" in text
        assert "Description: Job description" in text
        assert len(text.strip()) > 0
    
    @pytest.mark.asyncio
    async def test_find_matching_jobs(
        self, 
        embedding_service_instance,
        mock_vector_service
    ):
        """Test finding matching jobs"""
        # Mock similar jobs response
        mock_similar_jobs = [
            {
                "job_id": "job_123",
                "score": 0.85,
                "metadata": {"title": "Python Developer", "company": "TechCorp"}
            },
            {
                "job_id": "job_456", 
                "score": 0.75,
                "metadata": {"title": "Software Engineer", "company": "StartupCorp"}
            }
        ]
        mock_vector_service.find_similar_jobs.return_value = mock_similar_jobs
        
        matching_jobs = await embedding_service_instance.find_matching_jobs(
            resume_id="resume_123",
            limit=10,
            min_score=0.7
        )
        
        assert len(matching_jobs) == 2
        
        # Check enhanced results
        for job in matching_jobs:
            assert "match_reasons" in job
            assert isinstance(job["match_reasons"], list)
            assert len(job["match_reasons"]) > 0
        
        # Verify vector service was called correctly
        mock_vector_service.find_similar_jobs.assert_called_once_with(
            resume_id="resume_123",
            top_k=10,
            score_threshold=0.7
        )
    
    def test_generate_match_reasons(self, embedding_service_instance):
        """Test match reason generation"""
        metadata = {
            "title": "Senior Python Developer",
            "company": "TechCorp"
        }
        
        # Test excellent match
        reasons = embedding_service_instance._generate_match_reasons(metadata, 0.95)
        assert "Excellent overall match" in reasons
        assert "Title: Senior Python Developer" in reasons
        assert "Company: TechCorp" in reasons
        
        # Test very good match
        reasons = embedding_service_instance._generate_match_reasons(metadata, 0.85)
        assert "Very good match" in reasons
        
        # Test good match
        reasons = embedding_service_instance._generate_match_reasons(metadata, 0.75)
        assert "Good match" in reasons
    
    @pytest.mark.asyncio
    async def test_calculate_job_resume_match(
        self, 
        embedding_service_instance,
        mock_vector_service
    ):
        """Test calculating job-resume match"""
        mock_vector_service.calculate_similarity_score.return_value = 0.85
        
        match_result = await embedding_service_instance.calculate_job_resume_match(
            resume_id="resume_123",
            job_id="job_456"
        )
        
        assert match_result["score"] == 0.85
        assert match_result["match_quality"] == "very_good"
        assert match_result["recommendation"] is True
        
        # Verify vector service was called correctly
        mock_vector_service.calculate_similarity_score.assert_called_once_with(
            resume_id="resume_123",
            job_id="job_456"
        )
    
    @pytest.mark.asyncio
    async def test_calculate_job_resume_match_quality_levels(
        self, 
        embedding_service_instance,
        mock_vector_service
    ):
        """Test different match quality levels"""
        test_cases = [
            (0.95, "excellent", True),
            (0.85, "very_good", True),
            (0.75, "good", True),
            (0.65, "fair", False),
            (0.5, "poor", False)
        ]
        
        for score, expected_quality, expected_recommendation in test_cases:
            mock_vector_service.calculate_similarity_score.return_value = score
            
            result = await embedding_service_instance.calculate_job_resume_match(
                "resume_123", "job_456"
            )
            
            assert result["score"] == score
            assert result["match_quality"] == expected_quality
            assert result["recommendation"] == expected_recommendation
    
    @pytest.mark.asyncio
    async def test_process_resume_embedding_error_handling(
        self, 
        embedding_service_instance,
        sample_resume_data,
        sample_parsed_resume,
        mock_vector_service
    ):
        """Test error handling in resume embedding processing"""
        mock_vector_service.store_resume_embedding.side_effect = Exception("Vector store error")
        
        with pytest.raises(Exception, match="Vector store error"):
            await embedding_service_instance.process_resume_embedding(
                sample_resume_data, sample_parsed_resume
            )
    
    @pytest.mark.asyncio
    async def test_process_job_embedding_error_handling(
        self, 
        embedding_service_instance,
        sample_job_post,
        mock_vector_service
    ):
        """Test error handling in job embedding processing"""
        mock_vector_service.store_job_embedding.side_effect = Exception("Vector store error")
        
        with pytest.raises(Exception, match="Vector store error"):
            await embedding_service_instance.process_job_embedding(sample_job_post)
    
    @pytest.mark.asyncio
    async def test_find_matching_jobs_error_handling(
        self, 
        embedding_service_instance,
        mock_vector_service
    ):
        """Test error handling in finding matching jobs"""
        mock_vector_service.find_similar_jobs.side_effect = Exception("Search error")
        
        with pytest.raises(Exception, match="Search error"):
            await embedding_service_instance.find_matching_jobs("resume_123")
    
    @pytest.mark.asyncio
    async def test_calculate_job_resume_match_error_handling(
        self, 
        embedding_service_instance,
        mock_vector_service
    ):
        """Test error handling in match calculation"""
        mock_vector_service.calculate_similarity_score.side_effect = Exception("Calculation error")
        
        with pytest.raises(Exception, match="Calculation error"):
            await embedding_service_instance.calculate_job_resume_match(
                "resume_123", "job_456"
            )