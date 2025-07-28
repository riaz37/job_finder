"""
Automated Job Application Workflow Service

This service implements the complete automated job application workflow including:
- Scheduled job search and application process
- Automation rules engine respecting user preferences
- Rate limiting and application frequency controls
- Automated workflow monitoring and error handling
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from contextlib import asynccontextmanager

from app.services.job_service import JobService
from app.services.job_matching_service import JobMatchingService
from app.services.application_orchestrator import ApplicationOrchestrator, OrchestrationStatus
from app.services.automation_service import AutomationService
from app.services.monitoring_service import MonitoringService
from app.services.preferences_service import PreferencesService
from app.services.resume_service import ResumeService
from app.models.job import JobPost, JobSearchCriteria
from app.models.preferences import UserPreferencesData
from app.models.resume import ResumeData
from app.core.logging import get_logger


logger = get_logger(__name__)


class WorkflowStatus(str, Enum):
    """Status of automated workflow execution"""
    IDLE = "idle"
    SEARCHING_JOBS = "searching_jobs"
    MATCHING_JOBS = "matching_jobs"
    APPLYING_TO_JOBS = "applying_to_jobs"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    PAUSED = "paused"
    STOPPED = "stopped"


class AutomationTrigger(str, Enum):
    """Triggers for automated workflow execution"""
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    NEW_JOBS_AVAILABLE = "new_jobs_available"
    RETRY_FAILED = "retry_failed"


@dataclass
class WorkflowExecution:
    """Represents a single workflow execution"""
    id: str
    user_id: str
    trigger: AutomationTrigger
    status: WorkflowStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    jobs_found: int = 0
    jobs_matched: int = 0
    applications_submitted: int = 0
    applications_failed: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserWorkflowState:
    """Tracks the workflow state for a specific user"""
    user_id: str
    is_active: bool = False
    current_execution: Optional[WorkflowExecution] = None
    last_execution: Optional[WorkflowExecution] = None
    daily_applications: int = 0
    weekly_applications: int = 0
    last_application_time: Optional[datetime] = None
    rate_limit_until: Optional[datetime] = None
    consecutive_failures: int = 0
    next_scheduled_run: Optional[datetime] = None


class AutomatedWorkflowService:
    """Service for managing automated job application workflows"""
    
    def __init__(
        self,
        job_service: JobService,
        job_matching_service: JobMatchingService,
        application_orchestrator: ApplicationOrchestrator,
        automation_service: AutomationService,
        monitoring_service: MonitoringService,
        preferences_service: PreferencesService,
        resume_service: ResumeService
    ):
        self.job_service = job_service
        self.job_matching_service = job_matching_service
        self.application_orchestrator = application_orchestrator
        self.automation_service = automation_service
        self.monitoring_service = monitoring_service
        self.preferences_service = preferences_service
        self.resume_service = resume_service
        
        # Workflow state management
        self.user_states: Dict[str, UserWorkflowState] = {}
        self.active_executions: Dict[str, WorkflowExecution] = {}
        
        # Configuration
        self.max_concurrent_workflows = 5
        self.workflow_timeout = 3600  # 1 hour
        self.rate_limit_backoff_minutes = 60
        self.max_consecutive_failures = 3
        self.cleanup_interval = 300  # 5 minutes
        
        # Background task management
        self._background_tasks: set = set()
        self._shutdown_event = asyncio.Event()
    
    async def start_service(self) -> None:
        """Start the automated workflow service"""
        logger.info("Starting automated workflow service")
        
        # Start background tasks
        cleanup_task = asyncio.create_task(self._cleanup_task())
        self._background_tasks.add(cleanup_task)
        cleanup_task.add_done_callback(self._background_tasks.discard)
        
        logger.info("Automated workflow service started")
    
    async def stop_service(self) -> None:
        """Stop the automated workflow service"""
        logger.info("Stopping automated workflow service")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel all background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        # Stop all active workflows
        for execution in list(self.active_executions.values()):
            await self.stop_workflow(execution.user_id)
        
        logger.info("Automated workflow service stopped")
    
    async def enable_automation_for_user(
        self,
        user_id: str,
        schedule_next_run: bool = True
    ) -> Dict[str, Any]:
        """Enable automated workflow for a user"""
        try:
            logger.info(f"Enabling automation for user {user_id}")
            
            # Get user preferences
            preferences = await self.preferences_service.get_preferences(user_id)
            if not preferences:
                raise ValueError("User preferences not found")
            
            # Validate automation settings
            validation = self.automation_service.validate_automation_rules(
                preferences.automation_settings
            )
            
            if not validation["is_valid"]:
                raise ValueError(f"Invalid automation settings: {validation['errors']}")
            
            # Initialize or update user state
            if user_id not in self.user_states:
                self.user_states[user_id] = UserWorkflowState(user_id=user_id)
            
            user_state = self.user_states[user_id]
            user_state.is_active = True
            user_state.consecutive_failures = 0
            
            # Schedule next run if requested
            if schedule_next_run:
                next_run = datetime.now() + timedelta(
                    minutes=preferences.automation_settings.application_delay_minutes
                )
                user_state.next_scheduled_run = next_run
                
                # Start scheduled workflow task
                task = asyncio.create_task(
                    self._scheduled_workflow_task(user_id)
                )
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)
            
            # Log automation enabled
            await self.monitoring_service.log_activity(
                user_id=user_id,
                activity_type="automation_enabled",
                details={
                    "automation_settings": preferences.automation_settings.dict(),
                    "validation_warnings": validation.get("warnings", []),
                    "next_scheduled_run": user_state.next_scheduled_run.isoformat() if user_state.next_scheduled_run else None
                }
            )
            
            logger.info(f"Automation enabled for user {user_id}")
            
            return {
                "status": "enabled",
                "user_id": user_id,
                "next_scheduled_run": user_state.next_scheduled_run,
                "validation_warnings": validation.get("warnings", []),
                "recommendations": validation.get("recommendations", [])
            }
            
        except Exception as e:
            logger.error(f"Failed to enable automation for user {user_id}: {str(e)}")
            raise
    
    async def disable_automation_for_user(self, user_id: str) -> Dict[str, Any]:
        """Disable automated workflow for a user"""
        try:
            logger.info(f"Disabling automation for user {user_id}")
            
            # Update user state
            if user_id in self.user_states:
                self.user_states[user_id].is_active = False
                self.user_states[user_id].next_scheduled_run = None
            
            # Stop any active workflow
            await self.stop_workflow(user_id)
            
            # Log automation disabled
            await self.monitoring_service.log_activity(
                user_id=user_id,
                activity_type="automation_disabled",
                details={"disabled_at": datetime.now().isoformat()}
            )
            
            logger.info(f"Automation disabled for user {user_id}")
            
            return {
                "status": "disabled",
                "user_id": user_id,
                "disabled_at": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Failed to disable automation for user {user_id}: {str(e)}")
            raise
    
    async def start_workflow(
        self,
        user_id: str,
        trigger: AutomationTrigger = AutomationTrigger.MANUAL,
        force: bool = False
    ) -> Dict[str, Any]:
        """Start an automated workflow for a user"""
        try:
            logger.info(f"Starting workflow for user {user_id} with trigger {trigger}")
            
            # Check if user has active automation
            user_state = self.user_states.get(user_id)
            if not user_state or not user_state.is_active:
                if not force:
                    raise ValueError("Automation not enabled for user")
            
            # Check if workflow is already running
            if user_state and user_state.current_execution:
                if user_state.current_execution.status not in [WorkflowStatus.ERROR, WorkflowStatus.STOPPED]:
                    raise ValueError("Workflow already running for user")
            
            # Check rate limiting
            if not force and user_state:
                if user_state.rate_limit_until and datetime.now() < user_state.rate_limit_until:
                    raise ValueError(f"Rate limited until {user_state.rate_limit_until}")
            
            # Check concurrent workflow limit
            if len(self.active_executions) >= self.max_concurrent_workflows:
                raise ValueError("Maximum concurrent workflows reached")
            
            # Create workflow execution
            execution_id = f"workflow_{user_id}_{datetime.now().timestamp()}"
            execution = WorkflowExecution(
                id=execution_id,
                user_id=user_id,
                trigger=trigger,
                status=WorkflowStatus.IDLE,
                started_at=datetime.now()
            )
            
            # Update state
            if not user_state:
                user_state = UserWorkflowState(user_id=user_id)
                self.user_states[user_id] = user_state
            
            user_state.current_execution = execution
            self.active_executions[execution_id] = execution
            
            # Start workflow task
            task = asyncio.create_task(self._execute_workflow(execution))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
            
            logger.info(f"Workflow {execution_id} started for user {user_id}")
            
            return {
                "execution_id": execution_id,
                "user_id": user_id,
                "status": execution.status,
                "started_at": execution.started_at,
                "trigger": trigger
            }
            
        except Exception as e:
            logger.error(f"Failed to start workflow for user {user_id}: {str(e)}")
            raise
    
    async def stop_workflow(self, user_id: str) -> Dict[str, Any]:
        """Stop an active workflow for a user"""
        try:
            logger.info(f"Stopping workflow for user {user_id}")
            
            user_state = self.user_states.get(user_id)
            if not user_state or not user_state.current_execution:
                return {"status": "no_active_workflow", "user_id": user_id}
            
            execution = user_state.current_execution
            execution.status = WorkflowStatus.STOPPED
            execution.completed_at = datetime.now()
            
            # Move to last execution
            user_state.last_execution = execution
            user_state.current_execution = None
            
            # Remove from active executions
            if execution.id in self.active_executions:
                del self.active_executions[execution.id]
            
            # Log workflow stopped
            await self.monitoring_service.log_activity(
                user_id=user_id,
                activity_type="workflow_stopped",
                details={
                    "execution_id": execution.id,
                    "stopped_at": execution.completed_at.isoformat(),
                    "applications_submitted": execution.applications_submitted
                }
            )
            
            logger.info(f"Workflow {execution.id} stopped for user {user_id}")
            
            return {
                "status": "stopped",
                "execution_id": execution.id,
                "user_id": user_id,
                "stopped_at": execution.completed_at,
                "applications_submitted": execution.applications_submitted
            }
            
        except Exception as e:
            logger.error(f"Failed to stop workflow for user {user_id}: {str(e)}")
            raise
    
    async def get_workflow_status(self, user_id: str) -> Dict[str, Any]:
        """Get the current workflow status for a user"""
        try:
            user_state = self.user_states.get(user_id)
            if not user_state:
                return {
                    "user_id": user_id,
                    "automation_enabled": False,
                    "current_execution": None,
                    "last_execution": None
                }
            
            current_execution = None
            if user_state.current_execution:
                current_execution = {
                    "id": user_state.current_execution.id,
                    "status": user_state.current_execution.status,
                    "started_at": user_state.current_execution.started_at,
                    "jobs_found": user_state.current_execution.jobs_found,
                    "jobs_matched": user_state.current_execution.jobs_matched,
                    "applications_submitted": user_state.current_execution.applications_submitted,
                    "applications_failed": user_state.current_execution.applications_failed,
                    "error_message": user_state.current_execution.error_message
                }
            
            last_execution = None
            if user_state.last_execution:
                last_execution = {
                    "id": user_state.last_execution.id,
                    "status": user_state.last_execution.status,
                    "started_at": user_state.last_execution.started_at,
                    "completed_at": user_state.last_execution.completed_at,
                    "jobs_found": user_state.last_execution.jobs_found,
                    "jobs_matched": user_state.last_execution.jobs_matched,
                    "applications_submitted": user_state.last_execution.applications_submitted,
                    "applications_failed": user_state.last_execution.applications_failed,
                    "error_message": user_state.last_execution.error_message
                }
            
            return {
                "user_id": user_id,
                "automation_enabled": user_state.is_active,
                "current_execution": current_execution,
                "last_execution": last_execution,
                "daily_applications": user_state.daily_applications,
                "weekly_applications": user_state.weekly_applications,
                "last_application_time": user_state.last_application_time,
                "rate_limit_until": user_state.rate_limit_until,
                "consecutive_failures": user_state.consecutive_failures,
                "next_scheduled_run": user_state.next_scheduled_run
            }
            
        except Exception as e:
            logger.error(f"Failed to get workflow status for user {user_id}: {str(e)}")
            raise
    
    async def _execute_workflow(self, execution: WorkflowExecution) -> None:
        """Execute the complete automated workflow"""
        try:
            logger.info(f"Executing workflow {execution.id} for user {execution.user_id}")
            
            # Get user data
            user_preferences = await self.preferences_service.get_preferences(execution.user_id)
            if not user_preferences:
                raise ValueError("User preferences not found")
            
            user_resume = await self.resume_service.get_user_resume(execution.user_id)
            if not user_resume:
                raise ValueError("User resume not found")
            
            # Step 1: Search for jobs
            execution.status = WorkflowStatus.SEARCHING_JOBS
            jobs = await self._search_jobs(execution, user_preferences)
            execution.jobs_found = len(jobs)
            
            if not jobs:
                logger.info(f"No jobs found for user {execution.user_id}")
                execution.status = WorkflowStatus.IDLE
                execution.completed_at = datetime.now()
                return
            
            # Step 2: Match and filter jobs
            execution.status = WorkflowStatus.MATCHING_JOBS
            matched_jobs = await self._match_and_filter_jobs(
                execution, jobs, user_preferences, user_resume
            )
            execution.jobs_matched = len(matched_jobs)
            
            if not matched_jobs:
                logger.info(f"No matching jobs found for user {execution.user_id}")
                execution.status = WorkflowStatus.IDLE
                execution.completed_at = datetime.now()
                return
            
            # Step 3: Apply to jobs with rate limiting
            execution.status = WorkflowStatus.APPLYING_TO_JOBS
            await self._apply_to_jobs(execution, matched_jobs, user_preferences, user_resume)
            
            # Complete workflow
            execution.status = WorkflowStatus.IDLE
            execution.completed_at = datetime.now()
            
            # Update user state
            user_state = self.user_states[execution.user_id]
            user_state.last_execution = execution
            user_state.current_execution = None
            user_state.consecutive_failures = 0
            
            # Schedule next run if automation is still active
            if user_state.is_active:
                await self._schedule_next_run(execution.user_id, user_preferences)
            
            # Remove from active executions
            if execution.id in self.active_executions:
                del self.active_executions[execution.id]
            
            logger.info(f"Workflow {execution.id} completed successfully")
            
        except Exception as e:
            logger.error(f"Workflow {execution.id} failed: {str(e)}")
            
            execution.status = WorkflowStatus.ERROR
            execution.error_message = str(e)
            execution.completed_at = datetime.now()
            
            # Update user state
            user_state = self.user_states.get(execution.user_id)
            if user_state:
                user_state.last_execution = execution
                user_state.current_execution = None
                user_state.consecutive_failures += 1
                
                # Apply rate limiting for consecutive failures
                if user_state.consecutive_failures >= self.max_consecutive_failures:
                    user_state.rate_limit_until = datetime.now() + timedelta(
                        minutes=self.rate_limit_backoff_minutes
                    )
                    logger.warning(f"Rate limiting user {execution.user_id} due to consecutive failures")
            
            # Remove from active executions
            if execution.id in self.active_executions:
                del self.active_executions[execution.id]
            
            # Log error
            await self.monitoring_service.log_activity(
                user_id=execution.user_id,
                activity_type="workflow_error",
                details={
                    "execution_id": execution.id,
                    "error": str(e),
                    "consecutive_failures": user_state.consecutive_failures if user_state else 0
                }
            )
    
    async def _search_jobs(
        self,
        execution: WorkflowExecution,
        user_preferences: UserPreferencesData
    ) -> List[JobPost]:
        """Search for jobs based on user preferences"""
        try:
            # Create search criteria from user preferences
            search_criteria = JobSearchCriteria(
                search_terms=user_preferences.job_titles,
                locations=user_preferences.locations,
                is_remote=user_preferences.remote_work_preference,
                job_types=[jt.value for jt in user_preferences.employment_types],
                results_per_site=20,
                hours_old=24  # Only jobs posted in last 24 hours
            )
            
            # Search for jobs
            search_result = await self.job_service.search_jobs(search_criteria)
            
            # Log search results
            await self.monitoring_service.log_activity(
                user_id=execution.user_id,
                activity_type="job_search",
                details={
                    "execution_id": execution.id,
                    "search_criteria": search_criteria.dict(),
                    "jobs_found": len(search_result.jobs),
                    "sites_searched": search_result.sites_searched
                }
            )
            
            return search_result.jobs
            
        except Exception as e:
            logger.error(f"Job search failed for execution {execution.id}: {str(e)}")
            raise
    
    async def _match_and_filter_jobs(
        self,
        execution: WorkflowExecution,
        jobs: List[JobPost],
        user_preferences: UserPreferencesData,
        user_resume: ResumeData
    ) -> List[JobPost]:
        """Match and filter jobs based on user preferences and resume"""
        try:
            matched_jobs = []
            user_state = self.user_states[execution.user_id]
            
            for job in jobs:
                # Calculate match score
                match_result = await self.job_matching_service.calculate_match_score(
                    job, user_resume, user_preferences
                )
                
                job.match_score = match_result.match_score
                
                # Check automation rules
                automation_decision = self.automation_service.should_apply_to_job(
                    match_result.match_score,
                    user_preferences.automation_settings,
                    user_state.daily_applications,
                    user_state.weekly_applications
                )
                
                if automation_decision["should_apply"]:
                    matched_jobs.append(job)
                else:
                    logger.debug(f"Job {job.id} filtered out: {automation_decision['reason']}")
            
            # Sort by match score
            matched_jobs.sort(key=lambda j: j.match_score or 0, reverse=True)
            
            # Apply daily limit
            remaining_daily = (
                user_preferences.automation_settings.max_applications_per_day - 
                user_state.daily_applications
            )
            
            if len(matched_jobs) > remaining_daily:
                matched_jobs = matched_jobs[:remaining_daily]
            
            # Log matching results
            await self.monitoring_service.log_activity(
                user_id=execution.user_id,
                activity_type="job_matching",
                details={
                    "execution_id": execution.id,
                    "total_jobs": len(jobs),
                    "matched_jobs": len(matched_jobs),
                    "average_match_score": sum(j.match_score or 0 for j in matched_jobs) / len(matched_jobs) if matched_jobs else 0
                }
            )
            
            return matched_jobs
            
        except Exception as e:
            logger.error(f"Job matching failed for execution {execution.id}: {str(e)}")
            raise
    
    async def _apply_to_jobs(
        self,
        execution: WorkflowExecution,
        jobs: List[JobPost],
        user_preferences: UserPreferencesData,
        user_resume: ResumeData
    ) -> None:
        """Apply to jobs with rate limiting and error handling"""
        try:
            user_state = self.user_states[execution.user_id]
            delay_minutes = user_preferences.automation_settings.application_delay_minutes
            
            for i, job in enumerate(jobs):
                try:
                    # Check if workflow should continue
                    if execution.status == WorkflowStatus.STOPPED:
                        break
                    
                    # Apply rate limiting delay
                    if i > 0:
                        await asyncio.sleep(delay_minutes * 60)  # Convert to seconds
                    
                    # Check rate limits again before applying
                    if user_state.daily_applications >= user_preferences.automation_settings.max_applications_per_day:
                        logger.info(f"Daily application limit reached for user {execution.user_id}")
                        break
                    
                    if user_state.weekly_applications >= user_preferences.automation_settings.max_applications_per_week:
                        logger.info(f"Weekly application limit reached for user {execution.user_id}")
                        break
                    
                    # Submit application
                    logger.info(f"Applying to job {job.id} for user {execution.user_id}")
                    
                    result = await self.application_orchestrator.orchestrate_single_application(
                        job=job,
                        user_id=execution.user_id,
                        resume=user_resume,
                        user_preferences=user_preferences,
                        credentials=None,  # Would be retrieved from user settings
                        force_apply=False
                    )
                    
                    # Update counters based on result
                    if result.status == OrchestrationStatus.COMPLETED:
                        execution.applications_submitted += 1
                        user_state.daily_applications += 1
                        user_state.weekly_applications += 1
                        user_state.last_application_time = datetime.now()
                        
                        logger.info(f"Successfully applied to job {job.id}")
                        
                    elif result.status == OrchestrationStatus.FAILED:
                        execution.applications_failed += 1
                        logger.warning(f"Failed to apply to job {job.id}: {result.error_message}")
                        
                    elif result.status == OrchestrationStatus.PAUSED:
                        logger.info(f"Application paused for job {job.id}: {result.error_message}")
                    
                    # Log application attempt
                    await self.monitoring_service.log_activity(
                        user_id=execution.user_id,
                        activity_type="job_application",
                        details={
                            "execution_id": execution.id,
                            "job_id": job.id,
                            "job_title": job.title,
                            "company_name": job.company_name,
                            "match_score": job.match_score,
                            "status": result.status,
                            "error_message": result.error_message,
                            "processing_time": result.processing_time
                        }
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to apply to job {job.id}: {str(e)}")
                    execution.applications_failed += 1
                    
                    # Log application error
                    await self.monitoring_service.log_activity(
                        user_id=execution.user_id,
                        activity_type="application_error",
                        details={
                            "execution_id": execution.id,
                            "job_id": job.id,
                            "error": str(e)
                        }
                    )
            
            logger.info(f"Application process completed for execution {execution.id}")
            
        except Exception as e:
            logger.error(f"Application process failed for execution {execution.id}: {str(e)}")
            raise
    
    async def _schedule_next_run(
        self,
        user_id: str,
        user_preferences: UserPreferencesData
    ) -> None:
        """Schedule the next automated workflow run"""
        try:
            user_state = self.user_states[user_id]
            
            # Calculate next run time based on automation settings
            delay_minutes = user_preferences.automation_settings.application_delay_minutes
            next_run = datetime.now() + timedelta(minutes=delay_minutes * 2)  # Double delay between workflow runs
            
            user_state.next_scheduled_run = next_run
            
            # Start scheduled task
            task = asyncio.create_task(self._scheduled_workflow_task(user_id))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
            
            logger.info(f"Next workflow run scheduled for user {user_id} at {next_run}")
            
        except Exception as e:
            logger.error(f"Failed to schedule next run for user {user_id}: {str(e)}")
    
    async def _scheduled_workflow_task(self, user_id: str) -> None:
        """Background task for scheduled workflow execution"""
        try:
            user_state = self.user_states.get(user_id)
            if not user_state or not user_state.next_scheduled_run:
                return
            
            # Wait until scheduled time
            now = datetime.now()
            if user_state.next_scheduled_run > now:
                wait_seconds = (user_state.next_scheduled_run - now).total_seconds()
                await asyncio.sleep(wait_seconds)
            
            # Check if automation is still active
            if not user_state.is_active:
                return
            
            # Check if shutdown was requested
            if self._shutdown_event.is_set():
                return
            
            # Start workflow
            await self.start_workflow(user_id, AutomationTrigger.SCHEDULED)
            
        except asyncio.CancelledError:
            logger.info(f"Scheduled workflow task cancelled for user {user_id}")
        except Exception as e:
            logger.error(f"Scheduled workflow task failed for user {user_id}: {str(e)}")
    
    async def _cleanup_task(self) -> None:
        """Background task for cleaning up old workflow data"""
        try:
            while not self._shutdown_event.is_set():
                try:
                    await self._cleanup_old_executions()
                    await self._reset_daily_counters()
                    await self._reset_weekly_counters()
                    
                    # Wait for next cleanup cycle
                    await asyncio.sleep(self.cleanup_interval)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Cleanup task error: {str(e)}")
                    await asyncio.sleep(60)  # Wait before retrying
                    
        except asyncio.CancelledError:
            logger.info("Cleanup task cancelled")
    
    async def _cleanup_old_executions(self) -> None:
        """Clean up old workflow executions"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            # Clean up completed executions older than 24 hours
            for user_id, user_state in self.user_states.items():
                if (user_state.last_execution and 
                    user_state.last_execution.completed_at and
                    user_state.last_execution.completed_at < cutoff_time):
                    
                    logger.debug(f"Cleaning up old execution for user {user_id}")
                    user_state.last_execution = None
            
        except Exception as e:
            logger.error(f"Failed to cleanup old executions: {str(e)}")
    
    async def _reset_daily_counters(self) -> None:
        """Reset daily application counters at midnight"""
        try:
            now = datetime.now()
            
            for user_id, user_state in self.user_states.items():
                if (user_state.last_application_time and
                    user_state.last_application_time.date() < now.date()):
                    
                    logger.debug(f"Resetting daily counter for user {user_id}")
                    user_state.daily_applications = 0
            
        except Exception as e:
            logger.error(f"Failed to reset daily counters: {str(e)}")
    
    async def _reset_weekly_counters(self) -> None:
        """Reset weekly application counters on Monday"""
        try:
            now = datetime.now()
            
            # Check if it's Monday (weekday 0)
            if now.weekday() != 0:
                return
            
            for user_id, user_state in self.user_states.items():
                if (user_state.last_application_time and
                    (now - user_state.last_application_time).days >= 7):
                    
                    logger.debug(f"Resetting weekly counter for user {user_id}")
                    user_state.weekly_applications = 0
            
        except Exception as e:
            logger.error(f"Failed to reset weekly counters: {str(e)}")
    
    async def get_automation_statistics(self) -> Dict[str, Any]:
        """Get overall automation statistics"""
        try:
            active_users = sum(1 for state in self.user_states.values() if state.is_active)
            running_workflows = len(self.active_executions)
            
            total_applications_today = sum(
                state.daily_applications for state in self.user_states.values()
            )
            
            total_applications_week = sum(
                state.weekly_applications for state in self.user_states.values()
            )
            
            rate_limited_users = sum(
                1 for state in self.user_states.values() 
                if state.rate_limit_until and state.rate_limit_until > datetime.now()
            )
            
            return {
                "active_users": active_users,
                "running_workflows": running_workflows,
                "total_applications_today": total_applications_today,
                "total_applications_week": total_applications_week,
                "rate_limited_users": rate_limited_users,
                "background_tasks": len(self._background_tasks),
                "service_uptime": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get automation statistics: {str(e)}")
            raise