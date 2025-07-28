"""
Unit tests for cover letter service
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.services.cover_letter_service import CoverLetterService, CoverLetterTemplateManager
from app.models.cover_letter import (
    CoverLetterGenerationRequest, CoverLetterTone, CoverLetterPersonalization,
    CoverLetterTemplate, CoverLetterContent, CoverLetterValidation
)
from app.models.resume import ParsedResumeContent


class TestCoverLetterTemplateManager:
    """Test cover letter template management"""
    
    def test_initialize_default_templates(self):
        """Test that default templates are properly initialized"""
        manager = CoverLetterTemplateManager()
        
        templates = manager.get_all_templates()
        assert len(templates) >= 3
        
        # Check that we have templates for different tones
        tones = {template.tone for template in templates}
        assert CoverLetterTone.PROFESSIONAL in tones
        assert CoverLetterTone.ENTHUSIASTIC in tones
        assert CoverLetterTone.CONFIDENT in tones
    
    def test_get_template_by_id(self):
        """Test retrieving template by ID"""
        manager = CoverLetterTemplateManager()
        
        template = manager.get_template("professional_standard")
        assert template is not None
        assert template.id == "professional_standard"
        assert template.tone == CoverLetterTone.PROFESSIONAL
        
        # Test non-existent template
        assert manager.get_template("non_existent") is None
    
    def test_get_templates_by_tone(self):
        """Test retrieving templates by tone"""
        manager = CoverLetterTemplateManager()
        
        professional_templates = manager.get_templates_by_tone(CoverLetterTone.PROFESSIONAL)
        assert len(professional_templates) >= 1
        assert all(t.tone == CoverLetterTone.PROFESSIONAL for t in professional_templates)
        
        enthusiastic_templates = manager.get_templates_by_tone(CoverLetterTone.ENTHUSIASTIC)
        assert len(enthusiastic_templates) >= 1
        assert all(t.tone == CoverLetterTone.ENTHUSIASTIC for t in enthusiastic_templates)


class TestCoverLetterService:
    """Test cover letter generation service"""
    
    @pytest.fixture
    def mock_llm(self):
        """Mock LLM for testing"""
        mock = AsyncMock()
        return mock
    
    @pytest.fixture
    def cover_letter_service(self, mock_llm):
        """Create cover letter service with mocked LLM"""
        service = CoverLetterService()
        service.llm = mock_llm
        return service
    
    @pytest.fixture
    def sample_resume_data(self):
        """Sample resume data for testing"""
        return ParsedResumeContent(
            personal_info={
                "name": "John Doe",
                "title": "Software Engineer"
            },
            contact_info={
                "email": "john.doe@example.com",
                "phone": "555-0123"
            },
            summary="Experienced software engineer with 5 years in web development",
            skills=["Python", "JavaScript", "React", "Django", "AWS"],
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
                    "institution": "University of Technology"
                }
            ]
        )
    
    @pytest.fixture
    def sample_generation_request(self):
        """Sample cover letter generation request"""
        return CoverLetterGenerationRequest(
            job_title="Full Stack Developer",
            company_name="Innovative Tech Solutions",
            job_description="We are looking for a full stack developer to join our team",
            job_requirements=["Python", "React", "AWS", "5+ years experience"],
            tone=CoverLetterTone.PROFESSIONAL,
            max_word_count=300
        )
    
    def test_extract_personalization_data_with_provided_data(self, cover_letter_service, sample_generation_request, sample_resume_data):
        """Test extracting personalization data when provided in request"""
        personalization_data = CoverLetterPersonalization(
            company_name="Custom Company",
            job_title="Custom Title",
            hiring_manager_name="Jane Smith"
        )
        
        sample_generation_request.personalization_data = personalization_data
        
        result = cover_letter_service._extract_personalization_data(
            sample_generation_request, sample_resume_data
        )
        
        assert result.company_name == "Custom Company"
        assert result.job_title == "Custom Title"
        assert result.hiring_manager_name == "Jane Smith"
    
    def test_extract_personalization_data_from_request(self, cover_letter_service, sample_generation_request, sample_resume_data):
        """Test extracting personalization data from request when not provided"""
        result = cover_letter_service._extract_personalization_data(
            sample_generation_request, sample_resume_data
        )
        
        assert result.company_name == "Innovative Tech Solutions"
        assert result.job_title == "Full Stack Developer"
        assert result.role_specific_requirements == ["Python", "React", "AWS", "5+ years experience"]
    
    def test_create_resume_summary(self, cover_letter_service, sample_resume_data):
        """Test creating resume summary for AI context"""
        summary = cover_letter_service._create_resume_summary(sample_resume_data)
        
        assert "John Doe" in summary
        assert "Software Engineer" in summary
        assert "Python" in summary
        assert "Tech Corp" in summary
        assert "Computer Science" in summary
    
    def test_create_job_context(self, cover_letter_service, sample_generation_request):
        """Test creating job context for AI generation"""
        personalization = CoverLetterPersonalization(
            company_name="Test Company",
            job_title="Test Role",
            company_culture_keywords=["innovation", "collaboration"]
        )
        
        context = cover_letter_service._create_job_context(sample_generation_request, personalization)
        
        assert "Test Company" in context
        assert "Test Role" in context
        assert "Python" in context
        assert "innovation" in context
    
    @pytest.mark.asyncio
    async def test_generate_ai_content_success(self, cover_letter_service, mock_llm, sample_generation_request, sample_resume_data):
        """Test successful AI content generation"""
        # Mock AI response
        mock_response = Mock()
        mock_response.content = '''
        {
            "header": "Date: January 15, 2024",
            "opening_paragraph": "Dear Hiring Manager, I am writing to express my interest in the Full Stack Developer position at Innovative Tech Solutions.",
            "body_paragraphs": [
                "With 5 years of experience in software development, I have developed expertise in Python, React, and AWS.",
                "In my current role at Tech Corp, I have led the development of several web applications."
            ],
            "closing_paragraph": "I am excited about the opportunity to contribute to your team and would welcome the chance to discuss my qualifications further.",
            "signature": "Sincerely, John Doe",
            "full_content": "Complete cover letter content here..."
        }
        '''
        mock_llm.ainvoke.return_value = mock_response
        
        personalization = CoverLetterPersonalization(
            company_name="Innovative Tech Solutions",
            job_title="Full Stack Developer"
        )
        
        result = await cover_letter_service._generate_ai_content(
            sample_generation_request, sample_resume_data, personalization
        )
        
        assert isinstance(result, CoverLetterContent)
        assert result.opening_paragraph.startswith("Dear Hiring Manager")
        assert len(result.body_paragraphs) == 2
        assert result.tone_used == CoverLetterTone.PROFESSIONAL
        assert mock_llm.ainvoke.called
    
    @pytest.mark.asyncio
    async def test_generate_ai_content_json_error_fallback(self, cover_letter_service, mock_llm, sample_generation_request, sample_resume_data):
        """Test fallback to template when AI returns invalid JSON"""
        # Mock AI response with invalid JSON
        mock_response = Mock()
        mock_response.content = "Invalid JSON response"
        mock_llm.ainvoke.return_value = mock_response
        
        personalization = CoverLetterPersonalization(
            company_name="Innovative Tech Solutions",
            job_title="Full Stack Developer"
        )
        
        result = await cover_letter_service._generate_ai_content(
            sample_generation_request, sample_resume_data, personalization
        )
        
        assert isinstance(result, CoverLetterContent)
        assert result.full_content is not None
        assert len(result.full_content) > 0
    
    @pytest.mark.asyncio
    async def test_generate_template_content(self, cover_letter_service, sample_generation_request, sample_resume_data):
        """Test template-based content generation"""
        personalization = CoverLetterPersonalization(
            company_name="Test Company",
            job_title="Test Role",
            hiring_manager_name="Jane Smith"
        )
        
        result = await cover_letter_service._generate_template_content(
            sample_generation_request, sample_resume_data, personalization
        )
        
        assert isinstance(result, CoverLetterContent)
        assert "Test Company" in result.full_content
        assert "Test Role" in result.full_content
        assert "Jane Smith" in result.full_content
        assert result.word_count > 0
    
    @pytest.mark.asyncio
    async def test_validate_cover_letter_with_ai(self, cover_letter_service, mock_llm, sample_generation_request):
        """Test cover letter validation with AI"""
        content = CoverLetterContent(
            header="Date: January 15, 2024",
            opening_paragraph="Dear Hiring Manager,",
            body_paragraphs=["Body paragraph 1", "Body paragraph 2"],
            closing_paragraph="Thank you for your consideration.",
            signature="Sincerely, John Doe",
            full_content="Complete cover letter content",
            word_count=250,
            tone_used=CoverLetterTone.PROFESSIONAL
        )
        
        # Mock AI validation response
        mock_response = Mock()
        mock_response.content = '''
        {
            "is_valid": true,
            "tone_score": 0.9,
            "grammar_score": 0.95,
            "personalization_score": 0.8,
            "relevance_score": 0.85,
            "overall_score": 0.87,
            "issues": [],
            "suggestions": ["Consider adding specific achievements"],
            "word_count": 250,
            "estimated_reading_time": 83
        }
        '''
        mock_llm.ainvoke.return_value = mock_response
        
        result = await cover_letter_service._validate_cover_letter(content, sample_generation_request)
        
        assert isinstance(result, CoverLetterValidation)
        assert result.is_valid is True
        assert result.tone_score == 0.9
        assert result.overall_score == 0.87
        assert mock_llm.ainvoke.called
    
    def test_basic_validation(self, cover_letter_service, sample_generation_request):
        """Test basic validation without AI"""
        content = CoverLetterContent(
            header="Date: January 15, 2024",
            opening_paragraph="Dear Hiring Manager,",
            body_paragraphs=["Body paragraph with Full Stack Developer role at Innovative Tech Solutions"],
            closing_paragraph="Thank you for your consideration.",
            signature="Sincerely, John Doe",
            full_content="Dear Hiring Manager, I am interested in the Full Stack Developer position at Innovative Tech Solutions.",
            word_count=200,
            tone_used=CoverLetterTone.PROFESSIONAL
        )
        
        result = cover_letter_service._basic_validation(content, sample_generation_request)
        
        assert isinstance(result, CoverLetterValidation)
        assert result.is_valid is True
        assert result.personalization_score == 1.0  # Both company and job mentioned
        assert result.word_count == 200
    
    def test_basic_validation_with_issues(self, cover_letter_service, sample_generation_request):
        """Test basic validation with content issues"""
        content = CoverLetterContent(
            header="",
            opening_paragraph="",
            body_paragraphs=[],
            closing_paragraph="",
            signature="",
            full_content="Generic cover letter without company or job title",
            word_count=400,  # Exceeds max
            tone_used=CoverLetterTone.PROFESSIONAL
        )
        
        result = cover_letter_service._basic_validation(content, sample_generation_request)
        
        assert isinstance(result, CoverLetterValidation)
        assert result.is_valid is False
        assert len(result.issues) > 0
        assert any("exceeds maximum word count" in issue for issue in result.issues)
        assert any("Missing opening paragraph" in issue for issue in result.issues)
    
    @pytest.mark.asyncio
    async def test_generate_cover_letter_success(self, cover_letter_service, mock_llm, sample_generation_request, sample_resume_data):
        """Test complete cover letter generation process"""
        # Mock AI responses
        content_response = Mock()
        content_response.content = '''
        {
            "header": "Date: January 15, 2024",
            "opening_paragraph": "Dear Hiring Manager, I am writing to express my interest in the Full Stack Developer position.",
            "body_paragraphs": ["Body paragraph 1", "Body paragraph 2"],
            "closing_paragraph": "Thank you for your consideration.",
            "signature": "Sincerely, John Doe",
            "full_content": "Complete professional cover letter content for Full Stack Developer at Innovative Tech Solutions."
        }
        '''
        
        validation_response = Mock()
        validation_response.content = '''
        {
            "is_valid": true,
            "tone_score": 0.9,
            "grammar_score": 0.95,
            "personalization_score": 0.8,
            "relevance_score": 0.85,
            "overall_score": 0.87,
            "issues": [],
            "suggestions": [],
            "word_count": 250,
            "estimated_reading_time": 83
        }
        '''
        
        mock_llm.ainvoke.side_effect = [content_response, validation_response]
        
        result = await cover_letter_service.generate_cover_letter(
            sample_generation_request, sample_resume_data, "user123"
        )
        
        assert result.user_id == "user123"
        assert result.content.tone_used == CoverLetterTone.PROFESSIONAL
        assert result.validation.is_valid is True
        assert result.personalization.company_name == "Innovative Tech Solutions"
        assert result.personalization.job_title == "Full Stack Developer"
        assert "generation_timestamp" in result.generation_metadata
    
    @pytest.mark.asyncio
    async def test_generate_cover_letter_no_llm(self):
        """Test cover letter generation when LLM is not configured"""
        service = CoverLetterService()
        service.llm = None
        
        request = CoverLetterGenerationRequest(
            job_title="Developer",
            company_name="Test Company",
            job_description="Test description"
        )
        
        resume_data = ParsedResumeContent()
        
        with pytest.raises(Exception, match="Gemini API key not configured"):
            await service.generate_cover_letter(request, resume_data, "user123")
    
    @pytest.mark.asyncio
    async def test_analyze_cover_letter_with_ai(self, cover_letter_service, mock_llm):
        """Test cover letter analysis with AI"""
        content = CoverLetterContent(
            header="Date: January 15, 2024",
            opening_paragraph="Dear Hiring Manager,",
            body_paragraphs=["Body paragraph 1"],
            closing_paragraph="Thank you.",
            signature="Sincerely, John Doe",
            full_content="Professional cover letter content",
            word_count=100,
            tone_used=CoverLetterTone.PROFESSIONAL
        )
        
        # Mock AI analysis response
        mock_response = Mock()
        mock_response.content = '''
        {
            "keyword_density": {"experience": 0.05, "skills": 0.03},
            "readability_score": 0.8,
            "sentiment_score": 0.2,
            "professional_language_score": 0.9,
            "company_alignment_score": 0.7,
            "job_relevance_score": 0.8,
            "uniqueness_score": 0.6,
            "call_to_action_strength": 0.7,
            "strengths": ["Professional tone", "Clear structure"],
            "weaknesses": ["Could be more specific"],
            "recommendations": ["Add quantifiable achievements"],
            "competitive_advantages_highlighted": ["Technical expertise"],
            "missing_elements": ["Company research insights"]
        }
        '''
        mock_llm.ainvoke.return_value = mock_response
        
        result = await cover_letter_service.analyze_cover_letter(content)
        
        assert result.readability_score == 0.8
        assert result.professional_language_score == 0.9
        assert "Professional tone" in result.strengths
        assert "Add quantifiable achievements" in result.recommendations
        assert mock_llm.ainvoke.called
    
    def test_basic_analysis(self, cover_letter_service):
        """Test basic analysis without AI"""
        content = CoverLetterContent(
            header="Date: January 15, 2024",
            opening_paragraph="Dear Hiring Manager,",
            body_paragraphs=["I have experience working with teams in various company roles."],
            closing_paragraph="Thank you.",
            signature="Sincerely, John Doe",
            full_content="I have experience working with teams in various company roles and positions.",
            word_count=100,
            tone_used=CoverLetterTone.PROFESSIONAL
        )
        
        result = cover_letter_service._basic_analysis(content)
        
        assert result.keyword_density["experience"] > 0
        assert result.keyword_density["company"] > 0
        assert result.readability_score == 0.7
        assert "Professional tone" in result.strengths
        assert len(result.recommendations) > 0


if __name__ == "__main__":
    pytest.main([__file__])