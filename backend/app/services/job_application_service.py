"""
Job Application Automation Service

This service handles the automated submission of job applications across different platforms.
It includes web automation, form filling, document attachment, and application tracking.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
import tempfile
import json

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    WebDriverException,
    ElementNotInteractableException
)

from app.models.job import JobPost, JobSite
from app.models.resume import ResumeData
from app.models.cover_letter import CoverLetterResult
from app.models.preferences import UserPreferencesData


logger = logging.getLogger(__name__)


class ApplicationStatus(str, Enum):
    """Application submission status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    FAILED = "failed"
    REQUIRES_MANUAL_REVIEW = "requires_manual_review"
    RATE_LIMITED = "rate_limited"
    SITE_ERROR = "site_error"


class ApplicationError(str, Enum):
    """Types of application errors"""
    SITE_UNAVAILABLE = "site_unavailable"
    LOGIN_REQUIRED = "login_required"
    FORM_NOT_FOUND = "form_not_found"
    UPLOAD_FAILED = "upload_failed"
    CAPTCHA_REQUIRED = "captcha_required"
    RATE_LIMITED = "rate_limited"
    INVALID_CREDENTIALS = "invalid_credentials"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ApplicationResult:
    """Result of a job application submission"""
    job_id: str
    status: ApplicationStatus
    application_url: Optional[str] = None
    confirmation_id: Optional[str] = None
    error_message: Optional[str] = None
    error_type: Optional[ApplicationError] = None
    submitted_at: Optional[datetime] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ApplicationCredentials:
    """Credentials for job site login"""
    site: JobSite
    username: str
    password: str
    additional_info: Dict[str, str] = None
    
    def __post_init__(self):
        if self.additional_info is None:
            self.additional_info = {}


class JobApplicationService:
    """Service for automated job application submission"""
    
    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.application_timeout = 300  # 5 minutes per application
        self.page_load_timeout = 30
        self.retry_attempts = 3
        self.retry_delay = 5  # seconds
        
        # Site-specific configurations
        self.site_configs = {
            JobSite.LINKEDIN: {
                "login_url": "https://www.linkedin.com/login",
                "easy_apply_selector": "[data-easy-apply-button]",
                "form_selectors": {
                    "first_name": "input[name='firstName'], input[id*='firstName']",
                    "last_name": "input[name='lastName'], input[id*='lastName']",
                    "email": "input[name='email'], input[type='email']",
                    "phone": "input[name='phone'], input[type='tel']",
                    "resume_upload": "input[type='file'][accept*='pdf'], input[type='file'][accept*='doc']",
                    "cover_letter": "textarea[name='coverLetter'], textarea[id*='coverLetter']",
                    "submit_button": "button[type='submit'], button[aria-label*='Submit']"
                }
            },
            JobSite.INDEED: {
                "login_url": "https://secure.indeed.com/account/login",
                "apply_button_selector": "[data-jk] .jobsearch-IndeedApplyButton-buttonWrapper button",
                "form_selectors": {
                    "first_name": "input[name='firstName']",
                    "last_name": "input[name='lastName']",
                    "email": "input[name='email']",
                    "phone": "input[name='phoneNumber']",
                    "resume_upload": "input[type='file']",
                    "cover_letter": "textarea[name='coverLetter']",
                    "submit_button": "button[type='submit']"
                }
            },
            JobSite.ZIP_RECRUITER: {
                "login_url": "https://www.ziprecruiter.com/login",
                "apply_button_selector": ".apply_button, .quick_apply_button",
                "form_selectors": {
                    "first_name": "input[name='first_name']",
                    "last_name": "input[name='last_name']",
                    "email": "input[name='email']",
                    "phone": "input[name='phone']",
                    "resume_upload": "input[type='file']",
                    "cover_letter": "textarea[name='cover_letter']",
                    "submit_button": "button[type='submit'], input[type='submit']"
                }
            }
        }
    
    async def initialize_driver(self) -> None:
        """Initialize Chrome WebDriver with appropriate options"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # Run in background
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            
            # Disable images and CSS for faster loading
            prefs = {
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_setting_values.notifications": 2
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(self.page_load_timeout)
            self.wait = WebDriverWait(self.driver, 10)
            
            logger.info("WebDriver initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {str(e)}")
            raise
    
    async def cleanup_driver(self) -> None:
        """Clean up WebDriver resources"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver cleaned up successfully")
            except Exception as e:
                logger.error(f"Error cleaning up WebDriver: {str(e)}")
            finally:
                self.driver = None
                self.wait = None
    
    async def submit_application(
        self,
        job: JobPost,
        resume: ResumeData,
        cover_letter: CoverLetterResult,
        user_preferences: UserPreferencesData,
        credentials: Optional[ApplicationCredentials] = None
    ) -> ApplicationResult:
        """
        Submit a job application with retry logic and error handling
        
        Args:
            job: Job post to apply to
            resume: User's resume data
            cover_letter: Generated cover letter
            user_preferences: User preferences for application
            credentials: Site credentials if login required
            
        Returns:
            ApplicationResult with submission status and details
        """
        result = ApplicationResult(
            job_id=job.id,
            status=ApplicationStatus.PENDING,
            metadata={"attempts": []}
        )
        
        for attempt in range(self.retry_attempts):
            try:
                result.retry_count = attempt + 1
                
                # Initialize driver if not already done
                if not self.driver:
                    await self.initialize_driver()
                
                # Attempt application submission
                attempt_result = await self._submit_single_application(
                    job, resume, cover_letter, user_preferences, credentials
                )
                
                # Log attempt details
                result.metadata["attempts"].append({
                    "attempt": attempt + 1,
                    "timestamp": datetime.now().isoformat(),
                    "status": attempt_result.status,
                    "error": attempt_result.error_message
                })
                
                # If successful, return result
                if attempt_result.status == ApplicationStatus.SUBMITTED:
                    result.status = ApplicationStatus.SUBMITTED
                    result.application_url = attempt_result.application_url
                    result.confirmation_id = attempt_result.confirmation_id
                    result.submitted_at = datetime.now()
                    logger.info(f"Successfully submitted application for job {job.id}")
                    return result
                
                # If rate limited, wait longer before retry
                if attempt_result.error_type == ApplicationError.RATE_LIMITED:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Rate limited, waiting {wait_time} seconds before retry")
                    await asyncio.sleep(wait_time)
                    continue
                
                # If requires manual review, don't retry
                if attempt_result.status == ApplicationStatus.REQUIRES_MANUAL_REVIEW:
                    result.status = ApplicationStatus.REQUIRES_MANUAL_REVIEW
                    result.error_message = attempt_result.error_message
                    result.error_type = attempt_result.error_type
                    return result
                
                # For other errors, wait before retry
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay)
                
            except Exception as e:
                logger.error(f"Unexpected error in application attempt {attempt + 1}: {str(e)}")
                result.metadata["attempts"].append({
                    "attempt": attempt + 1,
                    "timestamp": datetime.now().isoformat(),
                    "status": "error",
                    "error": str(e)
                })
                
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay)
        
        # All attempts failed
        result.status = ApplicationStatus.FAILED
        result.error_message = "All application attempts failed"
        result.error_type = ApplicationError.UNKNOWN_ERROR
        
        logger.error(f"Failed to submit application for job {job.id} after {self.retry_attempts} attempts")
        return result
    
    async def _submit_single_application(
        self,
        job: JobPost,
        resume: ResumeData,
        cover_letter: CoverLetterResult,
        user_preferences: UserPreferencesData,
        credentials: Optional[ApplicationCredentials]
    ) -> ApplicationResult:
        """Submit a single application attempt"""
        
        result = ApplicationResult(
            job_id=job.id,
            status=ApplicationStatus.IN_PROGRESS
        )
        
        try:
            # Navigate to job posting
            logger.info(f"Navigating to job URL: {job.job_url}")
            self.driver.get(job.job_url)
            
            # Wait for page to load
            await asyncio.sleep(2)
            
            # Check if login is required
            if await self._is_login_required():
                if not credentials:
                    result.status = ApplicationStatus.REQUIRES_MANUAL_REVIEW
                    result.error_message = "Login required but no credentials provided"
                    result.error_type = ApplicationError.LOGIN_REQUIRED
                    return result
                
                # Perform login
                login_success = await self._perform_login(credentials)
                if not login_success:
                    result.status = ApplicationStatus.FAILED
                    result.error_message = "Login failed"
                    result.error_type = ApplicationError.INVALID_CREDENTIALS
                    return result
            
            # Find and click apply button
            apply_button = await self._find_apply_button(job.site)
            if not apply_button:
                result.status = ApplicationStatus.REQUIRES_MANUAL_REVIEW
                result.error_message = "Apply button not found"
                result.error_type = ApplicationError.FORM_NOT_FOUND
                return result
            
            # Click apply button
            self.driver.execute_script("arguments[0].click();", apply_button)
            await asyncio.sleep(3)
            
            # Fill application form
            form_filled = await self._fill_application_form(
                job, resume, cover_letter, user_preferences
            )
            
            if not form_filled:
                result.status = ApplicationStatus.REQUIRES_MANUAL_REVIEW
                result.error_message = "Failed to fill application form"
                result.error_type = ApplicationError.FORM_NOT_FOUND
                return result
            
            # Submit application
            submission_result = await self._submit_application_form()
            
            if submission_result["success"]:
                result.status = ApplicationStatus.SUBMITTED
                result.application_url = self.driver.current_url
                result.confirmation_id = submission_result.get("confirmation_id")
                result.submitted_at = datetime.now()
            else:
                result.status = ApplicationStatus.FAILED
                result.error_message = submission_result.get("error", "Submission failed")
                result.error_type = ApplicationError.UNKNOWN_ERROR
            
            return result
            
        except TimeoutException:
            result.status = ApplicationStatus.FAILED
            result.error_message = "Page load timeout"
            result.error_type = ApplicationError.TIMEOUT
            return result
            
        except Exception as e:
            logger.error(f"Error in single application submission: {str(e)}")
            result.status = ApplicationStatus.FAILED
            result.error_message = str(e)
            result.error_type = ApplicationError.UNKNOWN_ERROR
            return result
    
    async def _is_login_required(self) -> bool:
        """Check if login is required on current page"""
        try:
            # Common login indicators
            login_indicators = [
                "login", "sign in", "log in", "signin",
                "authentication", "account", "password"
            ]
            
            page_text = self.driver.page_source.lower()
            return any(indicator in page_text for indicator in login_indicators)
            
        except Exception:
            return False
    
    async def _perform_login(self, credentials: ApplicationCredentials) -> bool:
        """Perform login to job site"""
        try:
            site_config = self.site_configs.get(credentials.site)
            if not site_config:
                logger.error(f"No configuration found for site: {credentials.site}")
                return False
            
            # Navigate to login page
            self.driver.get(site_config["login_url"])
            await asyncio.sleep(3)
            
            # Find and fill username/email field
            username_selectors = [
                "input[name='username']", "input[name='email']", 
                "input[type='email']", "input[id*='username']", "input[id*='email']"
            ]
            
            username_field = None
            for selector in username_selectors:
                try:
                    username_field = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    break
                except TimeoutException:
                    continue
            
            if not username_field:
                logger.error("Username field not found")
                return False
            
            username_field.clear()
            username_field.send_keys(credentials.username)
            
            # Find and fill password field
            password_field = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
            password_field.clear()
            password_field.send_keys(credentials.password)
            
            # Find and click login button
            login_button_selectors = [
                "button[type='submit']", "input[type='submit']",
                "button[id*='login']", "button[id*='signin']"
            ]
            
            login_button = None
            for selector in login_button_selectors:
                try:
                    login_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if not login_button:
                logger.error("Login button not found")
                return False
            
            login_button.click()
            await asyncio.sleep(5)
            
            # Check if login was successful
            return not await self._is_login_required()
            
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False
    
    async def _find_apply_button(self, site: JobSite) -> Optional[Any]:
        """Find the apply button for the specific job site"""
        try:
            site_config = self.site_configs.get(site)
            if not site_config:
                # Generic apply button selectors
                selectors = [
                    "button[data-apply]", "a[data-apply]",
                    "button:contains('Apply')", "a:contains('Apply')",
                    ".apply-button", ".apply-btn", "#apply-button"
                ]
            else:
                selectors = [
                    site_config.get("easy_apply_selector", ""),
                    site_config.get("apply_button_selector", "")
                ]
            
            for selector in selectors:
                if not selector:
                    continue
                    
                try:
                    element = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    return element
                except TimeoutException:
                    continue
            
            # Fallback: look for buttons/links with "apply" text
            try:
                elements = self.driver.find_elements(By.XPATH, "//button[contains(translate(text(), 'APPLY', 'apply'), 'apply')] | //a[contains(translate(text(), 'APPLY', 'apply'), 'apply')]")
                if elements:
                    return elements[0]
            except Exception:
                pass
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding apply button: {str(e)}")
            return None
    
    async def _fill_application_form(
        self,
        job: JobPost,
        resume: ResumeData,
        cover_letter: CoverLetterResult,
        user_preferences: UserPreferencesData
    ) -> bool:
        """Fill out the application form with user data"""
        try:
            site_config = self.site_configs.get(job.site, {})
            form_selectors = site_config.get("form_selectors", {})
            
            # Extract user info from preferences
            user_info = user_preferences.personal_info
            
            # Fill basic information fields
            form_fields = {
                "first_name": user_info.get("first_name", ""),
                "last_name": user_info.get("last_name", ""),
                "email": user_info.get("email", ""),
                "phone": user_info.get("phone", "")
            }
            
            for field_name, value in form_fields.items():
                if not value:
                    continue
                    
                selector = form_selectors.get(field_name)
                if not selector:
                    continue
                
                try:
                    field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    field.clear()
                    field.send_keys(value)
                    logger.debug(f"Filled {field_name} field")
                except NoSuchElementException:
                    logger.debug(f"Field {field_name} not found")
                    continue
            
            # Upload resume
            await self._upload_resume(resume, form_selectors.get("resume_upload"))
            
            # Fill cover letter
            await self._fill_cover_letter(cover_letter, form_selectors.get("cover_letter"))
            
            # Fill additional fields if present
            await self._fill_additional_fields(user_preferences)
            
            return True
            
        except Exception as e:
            logger.error(f"Error filling application form: {str(e)}")
            return False
    
    async def _upload_resume(self, resume: ResumeData, upload_selector: Optional[str]) -> bool:
        """Upload resume file to application form"""
        if not upload_selector:
            logger.debug("No resume upload selector provided")
            return False
        
        try:
            # Create temporary file with resume content
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(resume.file_content)
                temp_file_path = temp_file.name
            
            # Find upload field
            upload_field = self.driver.find_element(By.CSS_SELECTOR, upload_selector)
            upload_field.send_keys(temp_file_path)
            
            # Wait for upload to complete
            await asyncio.sleep(3)
            
            # Clean up temporary file
            Path(temp_file_path).unlink(missing_ok=True)
            
            logger.debug("Resume uploaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading resume: {str(e)}")
            return False
    
    async def _fill_cover_letter(self, cover_letter: CoverLetterResult, textarea_selector: Optional[str]) -> bool:
        """Fill cover letter text area"""
        if not textarea_selector or not cover_letter:
            logger.debug("No cover letter selector or content provided")
            return False
        
        try:
            textarea = self.driver.find_element(By.CSS_SELECTOR, textarea_selector)
            textarea.clear()
            textarea.send_keys(cover_letter.content.full_content)
            
            logger.debug("Cover letter filled successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error filling cover letter: {str(e)}")
            return False
    
    async def _fill_additional_fields(self, user_preferences: UserPreferencesData) -> None:
        """Fill additional form fields based on common patterns"""
        try:
            # Common additional fields
            additional_fields = {
                "linkedin": user_preferences.personal_info.get("linkedin_url", ""),
                "portfolio": user_preferences.personal_info.get("portfolio_url", ""),
                "website": user_preferences.personal_info.get("website_url", ""),
                "github": user_preferences.personal_info.get("github_url", "")
            }
            
            for field_name, value in additional_fields.items():
                if not value:
                    continue
                
                # Try to find field by various selectors
                selectors = [
                    f"input[name='{field_name}']",
                    f"input[id*='{field_name}']",
                    f"input[placeholder*='{field_name}']"
                ]
                
                for selector in selectors:
                    try:
                        field = self.driver.find_element(By.CSS_SELECTOR, selector)
                        field.clear()
                        field.send_keys(value)
                        logger.debug(f"Filled additional field: {field_name}")
                        break
                    except NoSuchElementException:
                        continue
                        
        except Exception as e:
            logger.error(f"Error filling additional fields: {str(e)}")
    
    async def _submit_application_form(self) -> Dict[str, Any]:
        """Submit the filled application form"""
        try:
            # Find submit button
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button[id*='submit']",
                "button[class*='submit']",
                "button:contains('Submit')",
                "button:contains('Apply')"
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if not submit_button:
                return {"success": False, "error": "Submit button not found"}
            
            # Click submit button
            self.driver.execute_script("arguments[0].click();", submit_button)
            
            # Wait for submission to complete
            await asyncio.sleep(5)
            
            # Check for confirmation
            confirmation_id = await self._extract_confirmation_id()
            
            return {
                "success": True,
                "confirmation_id": confirmation_id,
                "submitted_url": self.driver.current_url
            }
            
        except Exception as e:
            logger.error(f"Error submitting application form: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _extract_confirmation_id(self) -> Optional[str]:
        """Extract confirmation ID from success page"""
        try:
            # Common confirmation patterns
            confirmation_patterns = [
                r"confirmation[:\s]+([A-Z0-9-]+)",
                r"application[:\s]+([A-Z0-9-]+)",
                r"reference[:\s]+([A-Z0-9-]+)",
                r"id[:\s]+([A-Z0-9-]+)"
            ]
            
            page_text = self.driver.page_source
            
            import re
            for pattern in confirmation_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    return match.group(1)
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting confirmation ID: {str(e)}")
            return None
    
    async def batch_submit_applications(
        self,
        applications: List[Dict[str, Any]],
        credentials: Optional[Dict[JobSite, ApplicationCredentials]] = None
    ) -> List[ApplicationResult]:
        """
        Submit multiple applications in batch with rate limiting
        
        Args:
            applications: List of application data dictionaries
            credentials: Site credentials mapping
            
        Returns:
            List of ApplicationResult objects
        """
        results = []
        
        try:
            # Initialize driver once for batch
            await self.initialize_driver()
            
            for i, app_data in enumerate(applications):
                try:
                    job = app_data["job"]
                    resume = app_data["resume"]
                    cover_letter = app_data["cover_letter"]
                    user_preferences = app_data["user_preferences"]
                    
                    # Get credentials for this site
                    site_credentials = None
                    if credentials and job.site in credentials:
                        site_credentials = credentials[job.site]
                    
                    logger.info(f"Submitting application {i+1}/{len(applications)} for job: {job.title}")
                    
                    # Submit application
                    result = await self.submit_application(
                        job, resume, cover_letter, user_preferences, site_credentials
                    )
                    
                    results.append(result)
                    
                    # Rate limiting: wait between applications
                    if i < len(applications) - 1:
                        await asyncio.sleep(30)  # 30 seconds between applications
                    
                except Exception as e:
                    logger.error(f"Error in batch application {i+1}: {str(e)}")
                    results.append(ApplicationResult(
                        job_id=app_data.get("job", {}).get("id", "unknown"),
                        status=ApplicationStatus.FAILED,
                        error_message=str(e),
                        error_type=ApplicationError.UNKNOWN_ERROR
                    ))
            
        finally:
            # Clean up driver
            await self.cleanup_driver()
        
        return results
    
    async def get_application_status(self, application_url: str) -> Dict[str, Any]:
        """
        Check the status of a submitted application
        
        Args:
            application_url: URL of the submitted application
            
        Returns:
            Dictionary with status information
        """
        try:
            if not self.driver:
                await self.initialize_driver()
            
            self.driver.get(application_url)
            await asyncio.sleep(3)
            
            # Look for status indicators
            status_indicators = {
                "submitted": ["submitted", "received", "under review"],
                "viewed": ["viewed", "opened", "reviewed"],
                "rejected": ["rejected", "declined", "not selected"],
                "interview": ["interview", "phone screen", "next round"],
                "offer": ["offer", "congratulations", "selected"]
            }
            
            page_text = self.driver.page_source.lower()
            
            for status, keywords in status_indicators.items():
                if any(keyword in page_text for keyword in keywords):
                    return {
                        "status": status,
                        "last_checked": datetime.now().isoformat(),
                        "url": application_url
                    }
            
            return {
                "status": "unknown",
                "last_checked": datetime.now().isoformat(),
                "url": application_url
            }
            
        except Exception as e:
            logger.error(f"Error checking application status: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "last_checked": datetime.now().isoformat(),
                "url": application_url
            }