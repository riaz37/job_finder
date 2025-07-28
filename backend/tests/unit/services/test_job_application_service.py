"""
Unit tests for JobApplicationService
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any

from app.services.job_application_service import (
    JobApplicationService,
    ApplicationStatus,
    ApplicationError,
    ApplicationResult,
    ApplicationCredentials
)
from app.models.job import JobPost, JobSite
from app.models.resume import ResumeData
from app.models.cover_letter import CoverLetterResult, CoverLetterContent
from app.models.preferences import UserPreferencesData


@pytest.fixture
def job_application_service():
    """Create JobApplicationService instance for testing"""
    return JobApplicationService()


@pytest.fixture
def sample_job():
    """Create sample job post for testing"""
    return JobPost(
        id="job123",
        title="Software Engineer",
        company_name="Tech Corp",
        job_url="https://example.com/job/123",
        location={"city": "San Francisco", "state": "CA"},
        description="Great software engineering role",
        requirements={"skills": ["Python", "JavaScript"]},
        salary_info={"min": 100000, "max": 150000},
        embedding_id="embed123",
        scraped_at=datetime.now(),
        site=JobSite.LINKEDIN,
        job_types=["fulltime"],
        is_remote=False
    )


@pytest.fixture
def sample_resume():
    """Create sample resume data for testing"""
    return ResumeData(
        id="resume123",
        user_id="user123",
        original_filename="resume.pdf",
        file_content=b"fake pdf content",
        parsed_content={"skills": ["Python", "JavaScript"], "experience": "5 years"},
        embedding_id="embed456",
        created_at=datetime.now()
    )


@pytest.fixture
def sample_cover_letter():
    """Create sample cover letter for testing"""
    content = CoverLetterContent(
        header="John Doe\n123 Main St",
        opening_paragraph="Dear Hiring Manager,",
        body_paragraphs=["I am excited to apply for this position."],
        closing_paragraph="Thank you for your consideration.",
        signature="Sincerely, John Doe",
        full_content="Complete cover letter content here",
        word_count=50,
        tone_used="professional"
    )
    
    return CoverLetterResult(
        id="cover123",
        user_id="user123",
        content=content,
        personalization=Mock(),
        validation=Mock(),
        created_at=datetime.now()
    )


@pytest.fixture
def sample_user_preferences():
    """Create sample user preferences for testing"""
    return UserPreferencesData(
        job_titles=["Software Engineer"],
        locations=["San Francisco"],
        salary_range={"min": 100000, "max": 150000},
        employment_types=["fulltime"],
        personal_info={
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone": "555-0123",
            "linkedin_url": "https://linkedin.com/in/johndoe"
        },
        automation_settings=Mock()
    )


@pytest.fixture
def sample_credentials():
    """Create sample application credentials for testing"""
    return ApplicationCredentials(
        site=JobSite.LINKEDIN,
        username="john.doe@example.com",
        password="password123"
    )


class TestJobApplicationService:
    """Test cases for JobApplicationService"""
    
    @pytest.mark.asyncio
    async def test_initialize_driver(self, job_application_service):
        """Test WebDriver initialization"""
        with patch('app.services.job_application_service.webdriver.Chrome') as mock_chrome:
            mock_driver = Mock()
            mock_chrome.return_value = mock_driver
            
            await job_application_service.initialize_driver()
            
            assert job_application_service.driver == mock_driver
            mock_driver.set_page_load_timeout.assert_called_once()
            mock_chrome.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_driver(self, job_application_service):
        """Test WebDriver cleanup"""
        mock_driver = Mock()
        job_application_service.driver = mock_driver
        
        await job_application_service.cleanup_driver()
        
        mock_driver.quit.assert_called_once()
        assert job_application_service.driver is None
    
    @pytest.mark.asyncio
    async def test_submit_application_success(
        self, 
        job_application_service, 
        sample_job, 
        sample_resume, 
        sample_cover_letter, 
        sample_user_preferences
    ):
        """Test successful application submission"""
        with patch.object(job_application_service, 'initialize_driver') as mock_init, \
             patch.object(job_application_service, '_submit_single_application') as mock_submit:
            
            # Mock successful submission
            mock_submit.return_value = ApplicationResult(
                job_id=sample_job.id,
                status=ApplicationStatus.SUBMITTED,
                application_url="https://example.com/applied",
                confirmation_id="CONF123",
                submitted_at=datetime.now()
            )
            
            result = await job_application_service.submit_application(
                sample_job, sample_resume, sample_cover_letter, sample_user_preferences
            )
            
            assert result.status == ApplicationStatus.SUBMITTED
            assert result.job_id == sample_job.id
            assert result.application_url == "https://example.com/applied"
            assert result.confirmation_id == "CONF123"
            assert result.retry_count == 1
    
    @pytest.mark.asyncio
    async def test_submit_application_retry_on_failure(
        self, 
        job_application_service, 
        sample_job, 
        sample_resume, 
        sample_cover_letter, 
        sample_user_preferences
    ):
        """Test application submission with retry on failure"""
        with patch.object(job_application_service, 'initialize_driver') as mock_init, \
             patch.object(job_application_service, '_submit_single_application') as mock_submit, \
             patch('asyncio.sleep') as mock_sleep:
            
            # Mock first two attempts fail, third succeeds
            mock_submit.side_effect = [
                ApplicationResult(job_id=sample_job.id, status=ApplicationStatus.FAILED, error_type=ApplicationError.NETWORK_ERROR),
                ApplicationResult(job_id=sample_job.id, status=ApplicationStatus.FAILED, error_type=ApplicationError.TIMEOUT),
                ApplicationResult(job_id=sample_job.id, status=ApplicationStatus.SUBMITTED, confirmation_id="CONF123")
            ]
            
            result = await job_application_service.submit_application(
                sample_job, sample_resume, sample_cover_letter, sample_user_preferences
            )
            
            assert result.status == ApplicationStatus.SUBMITTED
            assert result.retry_count == 3
            assert len(result.metadata["attempts"]) == 3
            assert mock_sleep.call_count == 2  # Sleep between retries
    
    @pytest.mark.asyncio
    async def test_submit_application_rate_limited(
        self, 
        job_application_service, 
        sample_job, 
        sample_resume, 
        sample_cover_letter, 
        sample_user_preferences
    ):
        """Test application submission with rate limiting"""
        with patch.object(job_application_service, 'initialize_driver') as mock_init, \
             patch.object(job_application_service, '_submit_single_application') as mock_submit, \
             patch('asyncio.sleep') as mock_sleep:
            
            # Mock rate limited response
            mock_submit.return_value = ApplicationResult(
                job_id=sample_job.id,
                status=ApplicationStatus.FAILED,
                error_type=ApplicationError.RATE_LIMITED,
                error_message="Rate limited"
            )
            
            result = await job_application_service.submit_application(
                sample_job, sample_resume, sample_cover_letter, sample_user_preferences
            )
            
            assert result.status == ApplicationStatus.FAILED
            assert result.error_type == ApplicationError.UNKNOWN_ERROR  # After all retries fail
            # Should use exponential backoff for rate limiting
            assert mock_sleep.call_count >= job_application_service.retry_attempts - 1
    
    @pytest.mark.asyncio
    async def test_submit_application_requires_manual_review(
        self, 
        job_application_service, 
        sample_job, 
        sample_resume, 
        sample_cover_letter, 
        sample_user_preferences
    ):
        """Test application submission that requires manual review"""
        with patch.object(job_application_service, 'initialize_driver') as mock_init, \
             patch.object(job_application_service, '_submit_single_application') as mock_submit:
            
            # Mock manual review required
            mock_submit.return_value = ApplicationResult(
                job_id=sample_job.id,
                status=ApplicationStatus.REQUIRES_MANUAL_REVIEW,
                error_message="CAPTCHA required",
                error_type=ApplicationError.CAPTCHA_REQUIRED
            )
            
            result = await job_application_service.submit_application(
                sample_job, sample_resume, sample_cover_letter, sample_user_preferences
            )
            
            assert result.status == ApplicationStatus.REQUIRES_MANUAL_REVIEW
            assert result.error_type == ApplicationError.CAPTCHA_REQUIRED
            assert result.retry_count == 1  # Should not retry manual review cases
    
    @pytest.mark.asyncio
    async def test_is_login_required(self, job_application_service):
        """Test login requirement detection"""
        mock_driver = Mock()
        mock_driver.page_source = "Please log in to continue"
        job_application_service.driver = mock_driver
        
        result = await job_application_service._is_login_required()
        assert result is True
        
        mock_driver.page_source = "Welcome to our job board"
        result = await job_application_service._is_login_required()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_perform_login_success(self, job_application_service, sample_credentials):
        """Test successful login"""
        mock_driver = Mock()
        mock_wait = Mock()
        
        # Mock form elements
        mock_username_field = Mock()
        mock_password_field = Mock()
        mock_login_button = Mock()
        
        mock_wait.until.side_effect = [mock_username_field, mock_password_field]
        mock_driver.find_element.return_value = mock_login_button
        
        job_application_service.driver = mock_driver
        job_application_service.wait = mock_wait
        
        with patch.object(job_application_service, '_is_login_required', side_effect=[True, False]), \
             patch('asyncio.sleep'):
            
            result = await job_application_service._perform_login(sample_credentials)
            
            assert result is True
            mock_username_field.clear.assert_called_once()
            mock_username_field.send_keys.assert_called_once_with(sample_credentials.username)
            mock_password_field.clear.assert_called_once()
            mock_password_field.send_keys.assert_called_once_with(sample_credentials.password)
            mock_login_button.click.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_perform_login_failure(self, job_application_service, sample_credentials):
        """Test login failure"""
        mock_driver = Mock()
        mock_wait = Mock()
        
        # Mock timeout exception when finding username field
        from selenium.common.exceptions import TimeoutException
        mock_wait.until.side_effect = TimeoutException()
        
        job_application_service.driver = mock_driver
        job_application_service.wait = mock_wait
        
        result = await job_application_service._perform_login(sample_credentials)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_find_apply_button_success(self, job_application_service):
        """Test finding apply button successfully"""
        mock_driver = Mock()
        mock_wait = Mock()
        mock_button = Mock()
        
        mock_wait.until.return_value = mock_button
        
        job_application_service.driver = mock_driver
        job_application_service.wait = mock_wait
        
        result = await job_application_service._find_apply_button(JobSite.LINKEDIN)
        
        assert result == mock_button
        mock_wait.until.assert_called()
    
    @pytest.mark.asyncio
    async def test_find_apply_button_fallback(self, job_application_service):
        """Test apply button fallback search"""
        mock_driver = Mock()
        mock_wait = Mock()
        mock_button = Mock()
        
        # Mock timeout on primary selector, success on fallback
        from selenium.common.exceptions import TimeoutException
        mock_wait.until.side_effect = TimeoutException()
        mock_driver.find_elements.return_value = [mock_button]
        
        job_application_service.driver = mock_driver
        job_application_service.wait = mock_wait
        
        result = await job_application_service._find_apply_button(JobSite.LINKEDIN)
        
        assert result == mock_button
    
    @pytest.mark.asyncio
    async def test_fill_application_form_success(
        self, 
        job_application_service, 
        sample_job, 
        sample_resume, 
        sample_cover_letter, 
        sample_user_preferences
    ):
        """Test successful form filling"""
        mock_driver = Mock()
        mock_field = Mock()
        
        mock_driver.find_element.return_value = mock_field
        job_application_service.driver = mock_driver
        
        with patch.object(job_application_service, '_upload_resume', return_value=True), \
             patch.object(job_application_service, '_fill_cover_letter', return_value=True), \
             patch.object(job_application_service, '_fill_additional_fields'):
            
            result = await job_application_service._fill_application_form(
                sample_job, sample_resume, sample_cover_letter, sample_user_preferences
            )
            
            assert result is True
            # Should have attempted to fill basic fields
            assert mock_field.clear.call_count >= 1
            assert mock_field.send_keys.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_upload_resume_success(self, job_application_service, sample_resume):
        """Test successful resume upload"""
        mock_driver = Mock()
        mock_upload_field = Mock()
        
        mock_driver.find_element.return_value = mock_upload_field
        job_application_service.driver = mock_driver
        
        with patch('tempfile.NamedTemporaryFile') as mock_temp, \
             patch('pathlib.Path.unlink'), \
             patch('asyncio.sleep'):
            
            # Mock temporary file
            mock_file = Mock()
            mock_file.name = "/tmp/test_resume.pdf"
            mock_temp.return_value.__enter__.return_value = mock_file
            
            result = await job_application_service._upload_resume(sample_resume, "input[type='file']")
            
            assert result is True
            mock_upload_field.send_keys.assert_called_once_with("/tmp/test_resume.pdf")
            mock_file.write.assert_called_once_with(sample_resume.file_content)
    
    @pytest.mark.asyncio
    async def test_upload_resume_no_selector(self, job_application_service, sample_resume):
        """Test resume upload with no selector"""
        result = await job_application_service._upload_resume(sample_resume, None)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_fill_cover_letter_success(self, job_application_service, sample_cover_letter):
        """Test successful cover letter filling"""
        mock_driver = Mock()
        mock_textarea = Mock()
        
        mock_driver.find_element.return_value = mock_textarea
        job_application_service.driver = mock_driver
        
        result = await job_application_service._fill_cover_letter(sample_cover_letter, "textarea[name='coverLetter']")
        
        assert result is True
        mock_textarea.clear.assert_called_once()
        mock_textarea.send_keys.assert_called_once_with(sample_cover_letter.content.full_content)
    
    @pytest.mark.asyncio
    async def test_fill_cover_letter_no_selector(self, job_application_service, sample_cover_letter):
        """Test cover letter filling with no selector"""
        result = await job_application_service._fill_cover_letter(sample_cover_letter, None)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_submit_application_form_success(self, job_application_service):
        """Test successful form submission"""
        mock_driver = Mock()
        mock_submit_button = Mock()
        
        mock_driver.find_element.return_value = mock_submit_button
        mock_driver.current_url = "https://example.com/success"
        job_application_service.driver = mock_driver
        
        with patch.object(job_application_service, '_extract_confirmation_id', return_value="CONF123"), \
             patch('asyncio.sleep'):
            
            result = await job_application_service._submit_application_form()
            
            assert result["success"] is True
            assert result["confirmation_id"] == "CONF123"
            assert result["submitted_url"] == "https://example.com/success"
            mock_driver.execute_script.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_submit_application_form_no_button(self, job_application_service):
        """Test form submission when submit button not found"""
        mock_driver = Mock()
        
        from selenium.common.exceptions import NoSuchElementException
        mock_driver.find_element.side_effect = NoSuchElementException()
        job_application_service.driver = mock_driver
        
        result = await job_application_service._submit_application_form()
        
        assert result["success"] is False
        assert "Submit button not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_extract_confirmation_id(self, job_application_service):
        """Test confirmation ID extraction"""
        mock_driver = Mock()
        mock_driver.page_source = "Your application confirmation ID: CONF-12345"
        job_application_service.driver = mock_driver
        
        result = await job_application_service._extract_confirmation_id()
        
        assert result == "CONF-12345"
    
    @pytest.mark.asyncio
    async def test_extract_confirmation_id_not_found(self, job_application_service):
        """Test confirmation ID extraction when not found"""
        mock_driver = Mock()
        mock_driver.page_source = "Thank you for your application"
        job_application_service.driver = mock_driver
        
        result = await job_application_service._extract_confirmation_id()
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_batch_submit_applications(
        self, 
        job_application_service, 
        sample_job, 
        sample_resume, 
        sample_cover_letter, 
        sample_user_preferences
    ):
        """Test batch application submission"""
        applications = [
            {
                "job": sample_job,
                "resume": sample_resume,
                "cover_letter": sample_cover_letter,
                "user_preferences": sample_user_preferences
            }
        ]
        
        with patch.object(job_application_service, 'initialize_driver'), \
             patch.object(job_application_service, 'cleanup_driver'), \
             patch.object(job_application_service, 'submit_application') as mock_submit, \
             patch('asyncio.sleep'):
            
            mock_submit.return_value = ApplicationResult(
                job_id=sample_job.id,
                status=ApplicationStatus.SUBMITTED
            )
            
            results = await job_application_service.batch_submit_applications(applications)
            
            assert len(results) == 1
            assert results[0].status == ApplicationStatus.SUBMITTED
            mock_submit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_application_status(self, job_application_service):
        """Test application status checking"""
        mock_driver = Mock()
        mock_driver.page_source = "Your application has been submitted and is under review"
        job_application_service.driver = mock_driver
        
        with patch.object(job_application_service, 'initialize_driver'), \
             patch('asyncio.sleep'):
            
            result = await job_application_service.get_application_status("https://example.com/application/123")
            
            assert result["status"] == "submitted"
            assert "last_checked" in result
            assert result["url"] == "https://example.com/application/123"
    
    @pytest.mark.asyncio
    async def test_get_application_status_error(self, job_application_service):
        """Test application status checking with error"""
        with patch.object(job_application_service, 'initialize_driver', side_effect=Exception("Driver error")):
            
            result = await job_application_service.get_application_status("https://example.com/application/123")
            
            assert result["status"] == "error"
            assert "Driver error" in result["error"]


class TestApplicationResult:
    """Test cases for ApplicationResult dataclass"""
    
    def test_application_result_creation(self):
        """Test ApplicationResult creation with defaults"""
        result = ApplicationResult(job_id="job123", status=ApplicationStatus.PENDING)
        
        assert result.job_id == "job123"
        assert result.status == ApplicationStatus.PENDING
        assert result.application_url is None
        assert result.confirmation_id is None
        assert result.error_message is None
        assert result.error_type is None
        assert result.submitted_at is None
        assert result.retry_count == 0
        assert result.metadata == {}
    
    def test_application_result_with_metadata(self):
        """Test ApplicationResult creation with metadata"""
        metadata = {"attempts": [{"attempt": 1, "status": "failed"}]}
        result = ApplicationResult(
            job_id="job123",
            status=ApplicationStatus.FAILED,
            error_message="Network error",
            error_type=ApplicationError.NETWORK_ERROR,
            metadata=metadata
        )
        
        assert result.job_id == "job123"
        assert result.status == ApplicationStatus.FAILED
        assert result.error_message == "Network error"
        assert result.error_type == ApplicationError.NETWORK_ERROR
        assert result.metadata == metadata


class TestApplicationCredentials:
    """Test cases for ApplicationCredentials dataclass"""
    
    def test_application_credentials_creation(self):
        """Test ApplicationCredentials creation with defaults"""
        credentials = ApplicationCredentials(
            site=JobSite.LINKEDIN,
            username="test@example.com",
            password="password123"
        )
        
        assert credentials.site == JobSite.LINKEDIN
        assert credentials.username == "test@example.com"
        assert credentials.password == "password123"
        assert credentials.additional_info == {}
    
    def test_application_credentials_with_additional_info(self):
        """Test ApplicationCredentials creation with additional info"""
        additional_info = {"security_question": "What is your pet's name?", "answer": "Fluffy"}
        credentials = ApplicationCredentials(
            site=JobSite.INDEED,
            username="test@example.com",
            password="password123",
            additional_info=additional_info
        )
        
        assert credentials.site == JobSite.INDEED
        assert credentials.additional_info == additional_info