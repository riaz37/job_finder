"""
Unit tests for AI service
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch

from app.services.ai_service import AIService


class TestAIService:
    """Test cases for AIService"""
    
    @pytest.fixture
    def ai_service(self):
        """Create AIService instance for testing"""
        with patch('app.services.ai_service.settings') as mock_settings:
            mock_settings.GEMINI_API_KEY = "test_api_key"
            return AIService()
    
    @pytest.fixture
    def ai_service_no_key(self):
        """Create AIService instance without API key"""
        with patch('app.services.ai_service.settings') as mock_settings:
            mock_settings.GEMINI_API_KEY = ""
            return AIService()
    
    @pytest.fixture
    def sample_resume_text(self):
        """Sample resume text for testing"""
        return """
        John Doe
        Software Engineer
        Email: john.doe@example.com
        Phone: (555) 123-4567
        
        EXPERIENCE
        Senior Software Engineer - Tech Corp (2020-Present)
        - Led development of web applications using Python and React
        - Managed team of 5 developers
        
        EDUCATION
        Bachelor of Science in Computer Science
        University of Technology (2018)
        
        SKILLS
        Python, JavaScript, React, FastAPI, PostgreSQL
        """
    
    @pytest.fixture
    def sample_parsed_content(self):
        """Sample parsed resume content"""
        return {
            "personal_info": {"name": "John Doe", "title": "Software Engineer"},
            "contact_info": {"email": "john.doe@example.com", "phone": "(555) 123-4567"},
            "summary": "Experienced software engineer",
            "skills": ["Python", "JavaScript", "React", "FastAPI", "PostgreSQL"],
            "experience": [
                {
                    "title": "Senior Software Engineer",
                    "company": "Tech Corp",
                    "start_date": "2020",
                    "end_date": "Present",
                    "description": "Led development of web applications"
                }
            ],
            "education": [
                {
                    "degree": "Bachelor of Science",
                    "field": "Computer Science",
                    "institution": "University of Technology",
                    "graduation_date": "2018"
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_parse_resume_content_success(self, ai_service, sample_resume_text):
        """Test successful resume content parsing"""
        mock_response_content = json.dumps({
            "personal_info": {"name": "John Doe", "title": "Software Engineer"},
            "contact_info": {"email": "john.doe@example.com"},
            "skills": ["Python", "JavaScript", "React"],
            "experience": [],
            "education": []
        })
        
        mock_response = Mock()
        mock_response.content = mock_response_content
        
        with patch.object(ai_service.llm, 'ainvoke', return_value=mock_response):
            result = await ai_service.parse_resume_content(sample_resume_text)
            
            assert result["personal_info"]["name"] == "John Doe"
            assert result["contact_info"]["email"] == "john.doe@example.com"
            assert "Python" in result["skills"]
    
    @pytest.mark.asyncio
    async def test_parse_resume_content_no_api_key(self, ai_service_no_key, sample_resume_text):
        """Test resume parsing without API key"""
        with pytest.raises(Exception) as exc_info:
            await ai_service_no_key.parse_resume_content(sample_resume_text)
        
        assert "Gemini API key not configured" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_parse_resume_content_json_error_fallback(self, ai_service, sample_resume_text):
        """Test resume parsing with JSON parsing error and fallback"""
        mock_response = Mock()
        mock_response.content = "Invalid JSON response"
        
        with patch.object(ai_service.llm, 'ainvoke', return_value=mock_response), \
             patch.object(ai_service, '_fallback_parsing') as mock_fallback:
            
            mock_fallback.return_value = {"skills": ["python"], "personal_info": {}}
            
            result = await ai_service.parse_resume_content(sample_resume_text)
            
            mock_fallback.assert_called_once_with(sample_resume_text)
            assert result["skills"] == ["python"]
    
    @pytest.mark.asyncio
    async def test_parse_resume_content_llm_error(self, ai_service, sample_resume_text):
        """Test resume parsing with LLM error"""
        with patch.object(ai_service.llm, 'ainvoke', side_effect=Exception("LLM error")):
            with pytest.raises(Exception) as exc_info:
                await ai_service.parse_resume_content(sample_resume_text)
            
            assert "Failed to parse resume with AI" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_analyze_resume_success(self, ai_service, sample_parsed_content):
        """Test successful resume analysis"""
        mock_response_content = json.dumps({
            "skills_extracted": ["Python", "JavaScript", "React", "Leadership"],
            "experience_years": 5,
            "education_level": "Bachelor's",
            "key_strengths": ["Full-stack development", "Team leadership"],
            "suggested_improvements": ["Add more quantifiable achievements"],
            "career_level": "senior",
            "industry_focus": ["Technology", "Software Development"]
        })
        
        mock_response = Mock()
        mock_response.content = mock_response_content
        
        with patch.object(ai_service.llm, 'ainvoke', return_value=mock_response):
            result = await ai_service.analyze_resume(sample_parsed_content)
            
            assert result["experience_years"] == 5
            assert result["education_level"] == "Bachelor's"
            assert "Full-stack development" in result["key_strengths"]
            assert result["career_level"] == "senior"
    
    @pytest.mark.asyncio
    async def test_analyze_resume_no_api_key(self, ai_service_no_key, sample_parsed_content):
        """Test resume analysis without API key"""
        with pytest.raises(Exception) as exc_info:
            await ai_service_no_key.analyze_resume(sample_parsed_content)
        
        assert "Gemini API key not configured" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_analyze_resume_json_error_fallback(self, ai_service, sample_parsed_content):
        """Test resume analysis with JSON parsing error and fallback"""
        mock_response = Mock()
        mock_response.content = "Invalid JSON response"
        
        with patch.object(ai_service.llm, 'ainvoke', return_value=mock_response), \
             patch.object(ai_service, '_fallback_analysis') as mock_fallback:
            
            mock_fallback.return_value = {"skills_extracted": ["Python"], "experience_years": 3}
            
            result = await ai_service.analyze_resume(sample_parsed_content)
            
            mock_fallback.assert_called_once_with(sample_parsed_content)
            assert result["skills_extracted"] == ["Python"]
    
    @pytest.mark.asyncio
    async def test_analyze_resume_llm_error(self, ai_service, sample_parsed_content):
        """Test resume analysis with LLM error"""
        with patch.object(ai_service.llm, 'ainvoke', side_effect=Exception("LLM error")):
            with pytest.raises(Exception) as exc_info:
                await ai_service.analyze_resume(sample_parsed_content)
            
            assert "Failed to analyze resume with AI" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_fallback_parsing(self, ai_service):
        """Test fallback parsing method"""
        text_content = """
        John Doe
        john.doe@example.com
        Python developer with experience in JavaScript, React, and SQL
        """
        
        result = await ai_service._fallback_parsing(text_content)
        
        assert result["contact_info"]["email"] == "john.doe@example.com"
        assert "python" in result["skills"]
        assert "javascript" in result["skills"]
        assert "react" in result["skills"]
        assert "sql" in result["skills"]
    
    @pytest.mark.asyncio
    async def test_fallback_parsing_no_email(self, ai_service):
        """Test fallback parsing without email"""
        text_content = "John Doe Software Engineer Python JavaScript"
        
        result = await ai_service._fallback_parsing(text_content)
        
        assert result["contact_info"]["email"] == ""
        assert "python" in result["skills"]
        assert "javascript" in result["skills"]
    
    @pytest.mark.asyncio
    async def test_fallback_analysis(self, ai_service):
        """Test fallback analysis method"""
        parsed_content = {
            "skills": ["Python", "JavaScript", "React"],
            "experience": [
                {"title": "Senior Engineer", "company": "Tech Corp"},
                {"title": "Junior Engineer", "company": "StartupCo"}
            ]
        }
        
        result = await ai_service._fallback_analysis(parsed_content)
        
        assert result["skills_extracted"] == ["Python", "JavaScript", "React"]
        assert result["experience_years"] == 4  # 2 experiences * 2 years each
        assert result["career_level"] == "mid-level"
        assert len(result["suggested_improvements"]) > 0
    
    @pytest.mark.asyncio
    async def test_fallback_analysis_no_experience(self, ai_service):
        """Test fallback analysis with no experience"""
        parsed_content = {
            "skills": ["Python"],
            "experience": []
        }
        
        result = await ai_service._fallback_analysis(parsed_content)
        
        assert result["experience_years"] == 0
        assert result["career_level"] == "entry-level"
        assert result["key_strengths"] == ["Python"]