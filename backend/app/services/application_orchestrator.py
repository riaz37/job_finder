"""
Application Orchestrator Service

This service orchestrates the complete job application process by coordinating
between job matching, resume customization, cover letter generation, and
automated application submission.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from app.services.job_application_service import (
    JobApplicationService, 
    ApplicationResult, 
    ApplicationStatus,
    ApplicationCredentials
)
from app.services.automation_service import AutomationService
from app.models.job import JobPost, JobSite
from app.models.resume import ResumeData
from app.models.cover_letter import CoverLetterResult
from app.models.preferences import UserPreferencesData


logger = logging.getLogger(__name__)


class OrchestrationStatus(str, Enum):
    """Status of the orchestration process"""
    PENDING = "pending"
    ANALYZING_JOBS = "analyzing_jobs"
    CUSTOMIZING_RESUME = "customizing_resume"
    GENERATING_COVER_LETTER = "generating_cover_letter"
    SUBMITTING_APPLICATION = "submitting_application"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class ApplicationOrchestrationResult:
    """Result of the complete application orchestration"""
    job_id: str
    user_id: str
    status: OrchestrationStatus
    application_result: Optional[ApplicationResult] = None
    resume_customization_id: Optional[str] = None
    cover_letter_id: Optional[str] = None
    match_score: Optional[float] = None
    processing_time: Optional[float] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ApplicationOrchestrator:
    """Orchestrates the complete job application process"""
    
    def __init__(
        self,
        job_application_service: JobApplicationService,
        automation_service: AutomationService
    ):
        self.job_application_service = job_application_service
        self.automation_service = automation_service
        self.max_concurrent_applications = 3
        self.application_delay = 30  # seconds between applications
        
    async def orchestrate_single_application(
        self,
        job: JobPost,
        user_id: str,
        resume: ResumeData,
        user_preferences: UserPreferencesData,
        credentials: Optional[Dict[JobSite, ApplicationCredentials]] = None,
        force_apply: bool = False
    ) -> ApplicationOrchestrationResult:
        """
        Orchestrate a single job application from start to finish
        
        Args:
            job: Job post to apply to
            user_id: User ID
            resume: User's resume data
            user_preferences: User preferences
            credentials: Site credentials for login
            force_apply: Skip automation checks if True
            
        Returns:
            ApplicationOrchestrationResult with complete process results
        """
        result = ApplicationOrchestrationResult(
            job_id=job.id,
            user_id=user_id,
            status=OrchestrationStatus.PENDING,
            started_at=datetime.now()
        )
        
        try:
            logger.info(f"Starting application orchestration for job {job.id} and user {user_id}")
            
            # Step 1: Check automation rules (unless forced)
            if not force_apply:
                automation_decision = await self._check_automation_rules(
                    job, user_preferences, user_id
                )
                
                if not automation_decision["should_apply"]:
                    result.status = OrchestrationStatus.PAUSED
                    result.error_message = automation_decision["reason"]
                    result.completed_at = datetime.now()
                    logger.info(f"Application paused for job {job.id}: {automation_decision['reason']}")
                    return result
                
                if automation_decision["requires_approval"]:
                    result.status = OrchestrationStatus.PAUSED
                    result.error_message = "Manual approval required"
                    result.completed_at = datetime.now()
                    logger.info(f"Application requires manual approval for job {job.id}")
                    return result
            
            # Step 2: Analyze job and calculate match score
            result.status = OrchestrationStatus.ANALYZING_JOBS
            match_analysis = await self._analyze_job_match(job, resume, user_preferences)
            result.match_score = match_analysis["match_score"]
            result.metadata["match_analysis"] = match_analysis
            
            logger.info(f"Job match score: {result.match_score:.2f} for job {job.id}")
            
            # Step 3: Customize resume for the job
            result.status = OrchestrationStatus.CUSTOMIZING_RESUME
            customized_resume = await self._customize_resume_for_job(job, resume)
            result.resume_customization_id = customized_resume.get("id")
            result.metadata["resume_customization"] = customized_resume
            
            logger.info(f"Resume customized for job {job.id}")
            
            # Step 4: Generate cover letter
            result.status = OrchestrationStatus.GENERATING_COVER_LETTER
            cover_letter = await self._generate_cover_letter(job, resume, user_preferences)
            result.cover_letter_id = cover_letter.id
            result.metadata["cover_letter"] = {
                "id": cover_letter.id,
                "word_count": cover_letter.content.word_count,
                "tone": cover_letter.content.tone_used
            }
            
            logger.info(f"Cover letter generated for job {job.id}")
            
            # Step 5: Submit application
            result.status = OrchestrationStatus.SUBMITTING_APPLICATION
            site_credentials = None
            if credentials and job.site in credentials:
                site_credentials = credentials[job.site]
            
            application_result = await self.job_application_service.submit_application(
                job, resume, cover_letter, user_preferences, site_credentials
            )
            
            result.application_result = application_result
            result.metadata["application_submission"] = {
                "status": application_result.status,
                "retry_count": application_result.retry_count,
                "confirmation_id": application_result.confirmation_id
            }
            
            # Step 6: Determine final status
            if application_result.status == ApplicationStatus.SUBMITTED:
                result.status = OrchestrationStatus.COMPLETED
                logger.info(f"Application successfully submitted for job {job.id}")
            else:
                result.status = OrchestrationStatus.FAILED
                result.error_message = application_result.error_message
                logger.error(f"Application failed for job {job.id}: {application_result.error_message}")
            
            result.completed_at = datetime.now()
            result.processing_time = (result.completed_at - result.started_at).total_seconds()
            
            return result
            
        except Exception as e:
            logger.error(f"Error in application orchestration for job {job.id}: {str(e)}")
            result.status = OrchestrationStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.now()
            if result.started_at:
                result.processing_time = (result.completed_at - result.started_at).total_seconds()
            return result
    
    async def orchestrate_batch_applications(
        self,
        jobs: List[JobPost],
        user_id: str,
        resume: ResumeData,
        user_preferences: UserPreferencesData,
        credentials: Optional[Dict[JobSite, ApplicationCredentials]] = None,
        max_applications: Optional[int] = None
    ) -> List[ApplicationOrchestrationResult]:
        """
        Orchestrate multiple job applications with rate limiting and error handling
        
        Args:
            jobs: List of job posts to apply to
            user_id: User ID
            resume: User's resume data
            user_preferences: User preferences
            credentials: Site credentials for login
            max_applications: Maximum number of applications to submit
            
        Returns:
            List of ApplicationOrchestrationResult objects
        """
        results = []
        
        # Apply max applications limit
        if max_applications:
            jobs = jobs[:max_applications]
        
        logger.info(f"Starting batch application orchestration for {len(jobs)} jobs")
        
        # Process applications in batches to respect rate limits
        batch_size = min(self.max_concurrent_applications, len(jobs))
        
        for i in range(0, len(jobs), batch_size):
            batch_jobs = jobs[i:i + batch_size]
            
            # Process batch concurrently
            batch_tasks = []
            for job in batch_jobs:
                task = self.orchestrate_single_application(
                    job, user_id, resume, user_preferences, credentials
                )
                batch_tasks.append(task)
            
            # Wait for batch to complete
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Process results and handle exceptions
            for j, batch_result in enumerate(batch_results):
                if isinstance(batch_result, Exception):
                    logger.error(f"Exception in batch application {i+j}: {str(batch_result)}")
                    error_result = ApplicationOrchestrationResult(
                        job_id=batch_jobs[j].id,
                        user_id=user_id,
                        status=OrchestrationStatus.FAILED,
                        error_message=str(batch_result),
                        started_at=datetime.now(),
                        completed_at=datetime.now()
                    )
                    results.append(error_result)
                else:
                    results.append(batch_result)
            
            # Rate limiting: wait between batches
            if i + batch_size < len(jobs):
                await asyncio.sleep(self.application_delay)
        
        # Log summary
        successful = sum(1 for r in results if r.status == OrchestrationStatus.COMPLETED)
        failed = sum(1 for r in results if r.status == OrchestrationStatus.FAILED)
        paused = sum(1 for r in results if r.status == OrchestrationStatus.PAUSED)
        
        logger.info(f"Batch application orchestration completed: {successful} successful, {failed} failed, {paused} paused")
        
        return results
    
    async def _check_automation_rules(
        self,
        job: JobPost,
        user_preferences: UserPreferencesData,
        user_id: str
    ) -> Dict[str, Any]:
        """Check if automation rules allow applying to this job"""
        try:
            # Get current application counts (this would typically query the database)
            daily_count = await self._get_daily_application_count(user_id)
            weekly_count = await self._get_weekly_application_count(user_id)
            
            # Use automation service to check rules
            decision = self.automation_service.should_apply_to_job(
                job.match_score or 0.0,
                user_preferences.automation_settings,
                daily_count,
                weekly_count
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"Error checking automation rules: {str(e)}")
            return {
                "should_apply": False,
                "reason": f"Error checking automation rules: {str(e)}",
                "requires_approval": True
            }
    
    async def _analyze_job_match(
        self,
        job: JobPost,
        resume: ResumeData,
        user_preferences: UserPreferencesData
    ) -> Dict[str, Any]:
        """Analyze how well the job matches the user's profile"""
        try:
            # This would typically use the job matching service
            # For now, return a mock analysis
            match_analysis = {
                "match_score": 0.85,  # This would be calculated by the matching service
                "matching_skills": ["Python", "JavaScript", "React"],
                "missing_skills": ["Docker", "Kubernetes"],
                "salary_match": True,
                "location_match": True,
                "title_relevance": 0.9,
                "company_preference": "neutral"
            }
            
            return match_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing job match: {str(e)}")
            return {
                "match_score": 0.0,
                "error": str(e)
            }
    
    async def _customize_resume_for_job(
        self,
        job: JobPost,
        resume: ResumeData
    ) -> Dict[str, Any]:
        """Customize resume for the specific job"""
        try:
            # This would typically use the resume customization service
            # For now, return a mock customization
            customization = {
                "id": f"custom_{job.id}_{resume.id}",
                "original_resume_id": resume.id,
                "job_id": job.id,
                "modifications": [
                    "Added relevant keywords from job description",
                    "Emphasized matching skills and experience",
                    "Adjusted summary to align with role requirements"
                ],
                "keyword_density_improvement": 0.25,
                "ats_score_improvement": 0.15,
                "created_at": datetime.now().isoformat()
            }
            
            return customization
            
        except Exception as e:
            logger.error(f"Error customizing resume: {str(e)}")
            return {
                "id": None,
                "error": str(e)
            }
    
    async def _generate_cover_letter(
        self,
        job: JobPost,
        resume: ResumeData,
        user_preferences: UserPreferencesData
    ) -> CoverLetterResult:
        """Generate cover letter for the job"""
        try:
            # This would typically use the cover letter service
            # For now, return a mock cover letter
            from app.models.cover_letter import CoverLetterContent
            
            content = CoverLetterContent(
                header=f"{user_preferences.personal_info.get('first_name', 'John')} {user_preferences.personal_info.get('last_name', 'Doe')}\n{user_preferences.personal_info.get('email', 'john.doe@example.com')}",
                opening_paragraph=f"Dear {job.company_name} Hiring Team,",
                body_paragraphs=[
                    f"I am excited to apply for the {job.title} position at {job.company_name}.",
                    "My experience and skills align well with your requirements.",
                    "I would welcome the opportunity to discuss how I can contribute to your team."
                ],
                closing_paragraph="Thank you for your consideration. I look forward to hearing from you.",
                signature=f"Sincerely,\n{user_preferences.personal_info.get('first_name', 'John')} {user_preferences.personal_info.get('last_name', 'Doe')}",
                full_content="",  # Would be assembled from parts
                word_count=150,
                tone_used="professional"
            )
            
            # Assemble full content
            content.full_content = f"{content.header}\n\n{content.opening_paragraph}\n\n" + \
                                 "\n\n".join(content.body_paragraphs) + \
                                 f"\n\n{content.closing_paragraph}\n\n{content.signature}"
            
            cover_letter = CoverLetterResult(
                id=f"cover_{job.id}_{resume.id}",
                user_id=user_preferences.user_id if hasattr(user_preferences, 'user_id') else "user123",
                job_id=job.id,
                content=content,
                personalization=None,  # Mock object
                validation=None,  # Mock object
                created_at=datetime.now()
            )
            
            return cover_letter
            
        except Exception as e:
            logger.error(f"Error generating cover letter: {str(e)}")
            raise
    
    async def _get_daily_application_count(self, user_id: str) -> int:
        """Get the number of applications submitted today"""
        # This would typically query the database
        # For now, return a mock count
        return 2
    
    async def _get_weekly_application_count(self, user_id: str) -> int:
        """Get the number of applications submitted this week"""
        # This would typically query the database
        # For now, return a mock count
        return 8
    
    async def get_orchestration_status(self, job_id: str, user_id: str) -> Dict[str, Any]:
        """Get the current status of an application orchestration"""
        try:
            # This would typically query the database for the current status
            # For now, return a mock status
            return {
                "job_id": job_id,
                "user_id": user_id,
                "status": "completed",
                "progress": 100,
                "current_step": "Application submitted",
                "estimated_completion": None,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting orchestration status: {str(e)}")
            return {
                "job_id": job_id,
                "user_id": user_id,
                "status": "error",
                "error": str(e),
                "last_updated": datetime.now().isoformat()
            }
    
    async def cancel_orchestration(self, job_id: str, user_id: str) -> bool:
        """Cancel an ongoing application orchestration"""
        try:
            # This would typically update the database and stop any running processes
            logger.info(f"Cancelling application orchestration for job {job_id} and user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling orchestration: {str(e)}")
            return False
    
    async def retry_failed_application(
        self,
        job: JobPost,
        user_id: str,
        resume: ResumeData,
        user_preferences: UserPreferencesData,
        credentials: Optional[Dict[JobSite, ApplicationCredentials]] = None
    ) -> ApplicationOrchestrationResult:
        """Retry a failed application with force apply"""
        logger.info(f"Retrying failed application for job {job.id}")
        
        return await self.orchestrate_single_application(
            job, user_id, resume, user_preferences, credentials, force_apply=True
        )
    
    async def get_application_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get application statistics for a user"""
        try:
            # This would typically query the database for statistics
            # For now, return mock statistics
            return {
                "user_id": user_id,
                "total_applications": 25,
                "successful_applications": 20,
                "failed_applications": 3,
                "pending_applications": 2,
                "success_rate": 0.8,
                "average_processing_time": 45.5,  # seconds
                "applications_today": 2,
                "applications_this_week": 8,
                "most_common_failure_reason": "Rate limited",
                "last_application": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting application statistics: {str(e)}")
            return {
                "user_id": user_id,
                "error": str(e)
            }