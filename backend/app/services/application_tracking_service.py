"""
Application Tracking and Status Management Service

This service handles tracking job applications, managing status updates,
maintaining application history, and calculating metrics and statistics.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
from dataclasses import dataclass

from prisma import Prisma
from prisma.models import Application as DBApplication, User, JobPost
from prisma.enums import ApplicationStatus

from app.models.job import JobPost as JobPostModel
from app.services.job_application_service import ApplicationResult


logger = logging.getLogger(__name__)


class StatusChangeReason(str, Enum):
    """Reasons for application status changes"""
    AUTOMATIC_UPDATE = "automatic_update"
    MANUAL_UPDATE = "manual_update"
    SYSTEM_CHECK = "system_check"
    USER_ACTION = "user_action"
    EXTERNAL_NOTIFICATION = "external_notification"


@dataclass
class ApplicationStatusUpdate:
    """Data class for application status updates"""
    application_id: str
    old_status: ApplicationStatus
    new_status: ApplicationStatus
    reason: StatusChangeReason
    notes: Optional[str] = None
    updated_by: Optional[str] = None
    updated_at: datetime = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ApplicationMetrics:
    """Application metrics and statistics"""
    total_applications: int
    applications_by_status: Dict[ApplicationStatus, int]
    applications_this_week: int
    applications_this_month: int
    average_response_time: Optional[float]  # in days
    success_rate: float  # percentage of successful applications
    top_companies: List[Tuple[str, int]]  # company name and application count
    applications_by_date: Dict[str, int]  # date string and count
    match_score_distribution: Dict[str, int]  # score range and count
    
    def __post_init__(self):
        if not hasattr(self, 'applications_by_status'):
            self.applications_by_status = {}
        if not hasattr(self, 'top_companies'):
            self.top_companies = []
        if not hasattr(self, 'applications_by_date'):
            self.applications_by_date = {}
        if not hasattr(self, 'match_score_distribution'):
            self.match_score_distribution = {}


@dataclass
class ApplicationTimelineEvent:
    """Timeline event for application history"""
    event_id: str
    application_id: str
    event_type: str
    event_description: str
    event_timestamp: datetime
    status_before: Optional[ApplicationStatus] = None
    status_after: Optional[ApplicationStatus] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ApplicationTrackingService:
    """Service for tracking and managing job applications"""
    
    def __init__(self, db: Prisma):
        self.db = db
        self.status_history: List[ApplicationStatusUpdate] = []
        
    async def create_application_record(
        self,
        user_id: str,
        job_post_id: str,
        resume_id: str,
        application_result: ApplicationResult,
        match_score: float,
        customized_resume_content: str,
        cover_letter_content: str
    ) -> DBApplication:
        """
        Create a new application record in the database
        
        Args:
            user_id: ID of the user who applied
            job_post_id: ID of the job post
            resume_id: ID of the resume used
            application_result: Result from application submission
            match_score: Job-resume match score
            customized_resume_content: Customized resume content
            cover_letter_content: Cover letter content
            
        Returns:
            Created application record
        """
        try:
            # Determine initial status based on application result
            initial_status = self._map_application_result_to_status(application_result)
            
            application = await self.db.application.create({
                "userId": user_id,
                "jobPostId": job_post_id,
                "resumeId": resume_id,
                "status": initial_status,
                "matchScore": match_score,
                "customizedResumeContent": customized_resume_content,
                "coverLetterContent": cover_letter_content,
                "applicationUrl": application_result.application_url
            })
            
            # Log the creation event
            await self._log_status_change(
                application.id,
                None,
                initial_status,
                StatusChangeReason.AUTOMATIC_UPDATE,
                f"Application created with status {initial_status.value}",
                metadata={
                    "confirmation_id": application_result.confirmation_id,
                    "retry_count": application_result.retry_count,
                    "submission_metadata": application_result.metadata
                }
            )
            
            logger.info(f"Created application record {application.id} for user {user_id}")
            return application
            
        except Exception as e:
            logger.error(f"Error creating application record: {str(e)}")
            raise
    
    async def update_application_status(
        self,
        application_id: str,
        new_status: ApplicationStatus,
        reason: StatusChangeReason,
        notes: Optional[str] = None,
        updated_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DBApplication:
        """
        Update application status with logging and notifications
        
        Args:
            application_id: ID of the application to update
            new_status: New status to set
            reason: Reason for the status change
            notes: Optional notes about the change
            updated_by: ID of user who made the change (if manual)
            metadata: Additional metadata about the change
            
        Returns:
            Updated application record
        """
        try:
            # Get current application
            current_app = await self.db.application.find_unique(
                where={"id": application_id}
            )
            
            if not current_app:
                raise ValueError(f"Application {application_id} not found")
            
            old_status = current_app.status
            
            # Update the application
            updated_app = await self.db.application.update(
                where={"id": application_id},
                data={"status": new_status}
            )
            
            # Log the status change
            await self._log_status_change(
                application_id,
                old_status,
                new_status,
                reason,
                notes,
                updated_by,
                metadata
            )
            
            # Send notifications if needed
            await self._send_status_change_notification(
                updated_app, old_status, new_status, reason
            )
            
            logger.info(f"Updated application {application_id} status from {old_status} to {new_status}")
            return updated_app
            
        except Exception as e:
            logger.error(f"Error updating application status: {str(e)}")
            raise
    
    async def get_application_history(
        self,
        user_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
        status_filter: Optional[List[ApplicationStatus]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[DBApplication]:
        """
        Get application history for a user with filtering options
        
        Args:
            user_id: ID of the user
            limit: Maximum number of applications to return
            offset: Number of applications to skip
            status_filter: Filter by application statuses
            date_from: Filter applications from this date
            date_to: Filter applications to this date
            
        Returns:
            List of application records
        """
        try:
            # Build where clause
            where_clause = {"userId": user_id}
            
            if status_filter:
                where_clause["status"] = {"in": status_filter}
            
            if date_from or date_to:
                date_filter = {}
                if date_from:
                    date_filter["gte"] = date_from
                if date_to:
                    date_filter["lte"] = date_to
                where_clause["appliedAt"] = date_filter
            
            # Query applications with related data
            applications = await self.db.application.find_many(
                where=where_clause,
                include={
                    "jobPost": True,
                    "resume": True,
                    "user": True
                },
                order_by={"appliedAt": "desc"},
                take=limit,
                skip=offset
            )
            
            logger.debug(f"Retrieved {len(applications)} applications for user {user_id}")
            return applications
            
        except Exception as e:
            logger.error(f"Error getting application history: {str(e)}")
            raise
    
    async def get_application_timeline(
        self,
        application_id: str
    ) -> List[ApplicationTimelineEvent]:
        """
        Get timeline of events for a specific application
        
        Args:
            application_id: ID of the application
            
        Returns:
            List of timeline events
        """
        try:
            # Get status change history for this application
            status_changes = [
                update for update in self.status_history 
                if update.application_id == application_id
            ]
            
            # Convert to timeline events
            timeline_events = []
            for i, change in enumerate(status_changes):
                event = ApplicationTimelineEvent(
                    event_id=f"status_change_{i}",
                    application_id=application_id,
                    event_type="status_change",
                    event_description=f"Status changed from {change.old_status} to {change.new_status}",
                    event_timestamp=change.updated_at,
                    status_before=change.old_status,
                    status_after=change.new_status,
                    metadata={
                        "reason": change.reason.value,
                        "notes": change.notes,
                        "updated_by": change.updated_by,
                        **change.metadata
                    }
                )
                timeline_events.append(event)
            
            # Sort by timestamp
            timeline_events.sort(key=lambda x: x.event_timestamp)
            
            logger.debug(f"Retrieved {len(timeline_events)} timeline events for application {application_id}")
            return timeline_events
            
        except Exception as e:
            logger.error(f"Error getting application timeline: {str(e)}")
            raise
    
    async def calculate_application_metrics(
        self,
        user_id: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> ApplicationMetrics:
        """
        Calculate comprehensive application metrics for a user
        
        Args:
            user_id: ID of the user
            date_from: Calculate metrics from this date
            date_to: Calculate metrics to this date
            
        Returns:
            Application metrics and statistics
        """
        try:
            # Build date filter
            date_filter = {}
            if date_from:
                date_filter["gte"] = date_from
            if date_to:
                date_filter["lte"] = date_to
            
            where_clause = {"userId": user_id}
            if date_filter:
                where_clause["appliedAt"] = date_filter
            
            # Get all applications for the user
            applications = await self.db.application.find_many(
                where=where_clause,
                include={"jobPost": True},
                order_by={"appliedAt": "desc"}
            )
            
            # Calculate basic metrics
            total_applications = len(applications)
            
            # Applications by status
            applications_by_status = {}
            for status in ApplicationStatus:
                applications_by_status[status] = sum(
                    1 for app in applications if app.status == status
                )
            
            # Time-based metrics
            now = datetime.now()
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)
            
            applications_this_week = sum(
                1 for app in applications if app.appliedAt >= week_ago
            )
            applications_this_month = sum(
                1 for app in applications if app.appliedAt >= month_ago
            )
            
            # Success rate (interviews + offers + accepted)
            successful_statuses = [
                ApplicationStatus.INTERVIEW_SCHEDULED,
                ApplicationStatus.OFFER_RECEIVED,
                ApplicationStatus.ACCEPTED
            ]
            successful_applications = sum(
                1 for app in applications if app.status in successful_statuses
            )
            success_rate = (successful_applications / total_applications * 100) if total_applications > 0 else 0.0
            
            # Average response time (for applications that got responses)
            response_times = []
            for app in applications:
                if app.status not in [ApplicationStatus.PENDING, ApplicationStatus.SUBMITTED]:
                    # Calculate days between application and status update
                    response_time = (app.lastStatusUpdate - app.appliedAt).days
                    response_times.append(response_time)
            
            average_response_time = sum(response_times) / len(response_times) if response_times else None
            
            # Top companies
            company_counts = {}
            for app in applications:
                company = app.jobPost.companyName
                company_counts[company] = company_counts.get(company, 0) + 1
            
            top_companies = sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # Applications by date
            applications_by_date = {}
            for app in applications:
                date_str = app.appliedAt.strftime("%Y-%m-%d")
                applications_by_date[date_str] = applications_by_date.get(date_str, 0) + 1
            
            # Match score distribution
            match_score_distribution = {
                "0.0-0.2": 0,
                "0.2-0.4": 0,
                "0.4-0.6": 0,
                "0.6-0.8": 0,
                "0.8-1.0": 0
            }
            
            for app in applications:
                score = app.matchScore
                if score < 0.2:
                    match_score_distribution["0.0-0.2"] += 1
                elif score < 0.4:
                    match_score_distribution["0.2-0.4"] += 1
                elif score < 0.6:
                    match_score_distribution["0.4-0.6"] += 1
                elif score < 0.8:
                    match_score_distribution["0.6-0.8"] += 1
                else:
                    match_score_distribution["0.8-1.0"] += 1
            
            metrics = ApplicationMetrics(
                total_applications=total_applications,
                applications_by_status=applications_by_status,
                applications_this_week=applications_this_week,
                applications_this_month=applications_this_month,
                average_response_time=average_response_time,
                success_rate=success_rate,
                top_companies=top_companies,
                applications_by_date=applications_by_date,
                match_score_distribution=match_score_distribution
            )
            
            logger.info(f"Calculated metrics for user {user_id}: {total_applications} total applications")
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating application metrics: {str(e)}")
            raise
    
    async def bulk_update_application_statuses(
        self,
        status_updates: List[Tuple[str, ApplicationStatus, StatusChangeReason, Optional[str]]]
    ) -> List[DBApplication]:
        """
        Bulk update multiple application statuses
        
        Args:
            status_updates: List of tuples (application_id, new_status, reason, notes)
            
        Returns:
            List of updated application records
        """
        try:
            updated_applications = []
            
            for application_id, new_status, reason, notes in status_updates:
                try:
                    updated_app = await self.update_application_status(
                        application_id, new_status, reason, notes
                    )
                    updated_applications.append(updated_app)
                except Exception as e:
                    logger.error(f"Error updating application {application_id}: {str(e)}")
                    continue
            
            logger.info(f"Bulk updated {len(updated_applications)} application statuses")
            return updated_applications
            
        except Exception as e:
            logger.error(f"Error in bulk status update: {str(e)}")
            raise
    
    async def get_applications_by_status(
        self,
        user_id: str,
        status: ApplicationStatus,
        limit: Optional[int] = None
    ) -> List[DBApplication]:
        """
        Get applications filtered by status
        
        Args:
            user_id: ID of the user
            status: Status to filter by
            limit: Maximum number of applications to return
            
        Returns:
            List of applications with the specified status
        """
        try:
            applications = await self.db.application.find_many(
                where={
                    "userId": user_id,
                    "status": status
                },
                include={
                    "jobPost": True,
                    "resume": True
                },
                order_by={"appliedAt": "desc"},
                take=limit
            )
            
            logger.debug(f"Retrieved {len(applications)} applications with status {status} for user {user_id}")
            return applications
            
        except Exception as e:
            logger.error(f"Error getting applications by status: {str(e)}")
            raise
    
    async def check_and_update_stale_applications(
        self,
        user_id: str,
        stale_days: int = 7
    ) -> List[DBApplication]:
        """
        Check for stale applications and update their status
        
        Args:
            user_id: ID of the user
            stale_days: Number of days after which to consider applications stale
            
        Returns:
            List of updated applications
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=stale_days)
            
            # Find applications that are still pending/submitted but are old
            stale_applications = await self.db.application.find_many(
                where={
                    "userId": user_id,
                    "status": {"in": [ApplicationStatus.PENDING, ApplicationStatus.SUBMITTED]},
                    "appliedAt": {"lt": cutoff_date}
                }
            )
            
            updated_applications = []
            for app in stale_applications:
                # Check actual status from job site if possible
                # For now, we'll just mark as viewed (assuming no response means viewed)
                updated_app = await self.update_application_status(
                    app.id,
                    ApplicationStatus.VIEWED,
                    StatusChangeReason.SYSTEM_CHECK,
                    f"Automatically updated after {stale_days} days with no response"
                )
                updated_applications.append(updated_app)
            
            logger.info(f"Updated {len(updated_applications)} stale applications for user {user_id}")
            return updated_applications
            
        except Exception as e:
            logger.error(f"Error checking stale applications: {str(e)}")
            raise
    
    def _map_application_result_to_status(self, result: ApplicationResult) -> ApplicationStatus:
        """Map ApplicationResult status to database ApplicationStatus"""
        from app.services.job_application_service import ApplicationStatus as ServiceStatus
        
        status_mapping = {
            ServiceStatus.PENDING: ApplicationStatus.PENDING,
            ServiceStatus.IN_PROGRESS: ApplicationStatus.PENDING,
            ServiceStatus.SUBMITTED: ApplicationStatus.SUBMITTED,
            ServiceStatus.FAILED: ApplicationStatus.PENDING,  # Keep as pending for retry
            ServiceStatus.REQUIRES_MANUAL_REVIEW: ApplicationStatus.PENDING,
            ServiceStatus.RATE_LIMITED: ApplicationStatus.PENDING,
            ServiceStatus.SITE_ERROR: ApplicationStatus.PENDING
        }
        
        return status_mapping.get(result.status, ApplicationStatus.PENDING)
    
    async def _log_status_change(
        self,
        application_id: str,
        old_status: Optional[ApplicationStatus],
        new_status: ApplicationStatus,
        reason: StatusChangeReason,
        notes: Optional[str] = None,
        updated_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log application status change"""
        try:
            status_update = ApplicationStatusUpdate(
                application_id=application_id,
                old_status=old_status,
                new_status=new_status,
                reason=reason,
                notes=notes,
                updated_by=updated_by,
                metadata=metadata or {}
            )
            
            # Store in memory (in production, this would go to a persistent log store)
            self.status_history.append(status_update)
            
            # Log to application logger
            logger.info(
                f"Application {application_id} status changed: "
                f"{old_status} -> {new_status} (reason: {reason.value})"
            )
            
        except Exception as e:
            logger.error(f"Error logging status change: {str(e)}")
    
    async def _send_status_change_notification(
        self,
        application: DBApplication,
        old_status: ApplicationStatus,
        new_status: ApplicationStatus,
        reason: StatusChangeReason
    ) -> None:
        """Send notification for status change (placeholder for future implementation)"""
        try:
            # This would integrate with a notification service
            # For now, just log the notification
            logger.info(
                f"Notification: Application for {application.jobPost.title if hasattr(application, 'jobPost') else 'job'} "
                f"status changed from {old_status} to {new_status}"
            )
            
            # Future implementation could include:
            # - Email notifications
            # - Push notifications
            # - Webhook calls
            # - Slack/Discord notifications
            
        except Exception as e:
            logger.error(f"Error sending status change notification: {str(e)}")