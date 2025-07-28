"""
Unit tests for ApplicationTrackingService
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import List, Dict, Any

from prisma.models import Application as DBApplication, JobPost, User, Resume
from prisma.enums import ApplicationStatus

from app.services.application_tracking_service import (
    ApplicationTrackingService,
    StatusChangeReason,
    ApplicationStatusUpdate,
    ApplicationMetrics,
    ApplicationTimelineEvent
)
from app.services.job_application_service import (
    ApplicationResult,
    ApplicationStatus as ServiceStatus
)


@pytest.fixture
def mock_db():
    """Create mock database instance"""
    return Mock()


@pytest.fixture
def tracking_service(mock_db):
    """Create ApplicationTrackingService instance for testing"""
    return ApplicationTrackingService(mock_db)


@pytest.fixture
def sample_application_result():
    """Create sample ApplicationResult for testing"""
    return ApplicationResult(
        job_id="job123",
        status=ServiceStatus.SUBMITTED,
        application_url="https://example.com/applied",
        confirmation_id="CONF123",
        submitted_at=datetime.now(),
        retry_count=1,
        metadata={"attempts": [{"attempt": 1, "status": "submitted"}]}
    )


@pytest.fixture
def sample_db_application():
    """Create sample database application for testing"""
    return DBApplication(
        id="app123",
        userId="user123",
        jobPostId="job123",
        resumeId="resume123",
        status=ApplicationStatus.SUBMITTED,
        matchScore=0.85,
        customizedResumeContent="Customized resume content",
        coverLetterContent="Cover letter content",
        applicationUrl="https://example.com/applied",
        appliedAt=datetime.now(),
        lastStatusUpdate=datetime.now()
    )


@pytest.fixture
def sample_job_post():
    """Create sample job post for testing"""
    return JobPost(
        id="job123",
        title="Software Engineer",
        companyName="Tech Corp",
        jobUrl="https://example.com/job/123",
        location={"city": "San Francisco"},
        description="Great job",
        requirements={"skills": ["Python"]},
        salaryInfo={"min": 100000},
        embeddingId="embed123",
        scrapedAt=datetime.now()
    )


class TestApplicationTrackingService:
    """Test cases for ApplicationTrackingService"""
    
    @pytest.mark.asyncio
    async def test_create_application_record_success(
        self, 
        tracking_service, 
        mock_db, 
        sample_application_result,
        sample_db_application
    ):
        """Test successful application record creation"""
        # Mock database create
        mock_db.application.create = AsyncMock(return_value=sample_db_application)
        
        result = await tracking_service.create_application_record(
            user_id="user123",
            job_post_id="job123",
            resume_id="resume123",
            application_result=sample_application_result,
            match_score=0.85,
            customized_resume_content="Customized resume",
            cover_letter_content="Cover letter"
        )
        
        assert result == sample_db_application
        mock_db.application.create.assert_called_once()
        
        # Check that status change was logged
        assert len(tracking_service.status_history) == 1
        status_change = tracking_service.status_history[0]
        assert status_change.application_id == sample_db_application.id
        assert status_change.new_status == ApplicationStatus.SUBMITTED
        assert status_change.reason == StatusChangeReason.AUTOMATIC_UPDATE
    
    @pytest.mark.asyncio
    async def test_create_application_record_error(
        self, 
        tracking_service, 
        mock_db, 
        sample_application_result
    ):
        """Test application record creation with database error"""
        # Mock database error
        mock_db.application.create = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(Exception, match="Database error"):
            await tracking_service.create_application_record(
                user_id="user123",
                job_post_id="job123",
                resume_id="resume123",
                application_result=sample_application_result,
                match_score=0.85,
                customized_resume_content="Customized resume",
                cover_letter_content="Cover letter"
            )
    
    @pytest.mark.asyncio
    async def test_update_application_status_success(
        self, 
        tracking_service, 
        mock_db, 
        sample_db_application
    ):
        """Test successful application status update"""
        # Mock database operations
        mock_db.application.find_unique = AsyncMock(return_value=sample_db_application)
        
        updated_app = sample_db_application.model_copy()
        updated_app.status = ApplicationStatus.INTERVIEW_SCHEDULED
        mock_db.application.update = AsyncMock(return_value=updated_app)
        
        result = await tracking_service.update_application_status(
            application_id="app123",
            new_status=ApplicationStatus.INTERVIEW_SCHEDULED,
            reason=StatusChangeReason.MANUAL_UPDATE,
            notes="Interview scheduled for next week",
            updated_by="user123"
        )
        
        assert result.status == ApplicationStatus.INTERVIEW_SCHEDULED
        mock_db.application.find_unique.assert_called_once_with(where={"id": "app123"})
        mock_db.application.update.assert_called_once()
        
        # Check that status change was logged
        assert len(tracking_service.status_history) == 1
        status_change = tracking_service.status_history[0]
        assert status_change.application_id == "app123"
        assert status_change.old_status == ApplicationStatus.SUBMITTED
        assert status_change.new_status == ApplicationStatus.INTERVIEW_SCHEDULED
        assert status_change.reason == StatusChangeReason.MANUAL_UPDATE
        assert status_change.notes == "Interview scheduled for next week"
        assert status_change.updated_by == "user123"
    
    @pytest.mark.asyncio
    async def test_update_application_status_not_found(
        self, 
        tracking_service, 
        mock_db
    ):
        """Test application status update when application not found"""
        # Mock application not found
        mock_db.application.find_unique = AsyncMock(return_value=None)
        
        with pytest.raises(ValueError, match="Application app123 not found"):
            await tracking_service.update_application_status(
                application_id="app123",
                new_status=ApplicationStatus.INTERVIEW_SCHEDULED,
                reason=StatusChangeReason.MANUAL_UPDATE
            )
    
    @pytest.mark.asyncio
    async def test_get_application_history_success(
        self, 
        tracking_service, 
        mock_db, 
        sample_db_application
    ):
        """Test successful application history retrieval"""
        applications = [sample_db_application]
        mock_db.application.find_many = AsyncMock(return_value=applications)
        
        result = await tracking_service.get_application_history(
            user_id="user123",
            limit=10,
            offset=0
        )
        
        assert result == applications
        mock_db.application.find_many.assert_called_once()
        
        # Check the where clause
        call_args = mock_db.application.find_many.call_args
        assert call_args[1]["where"]["userId"] == "user123"
        assert call_args[1]["take"] == 10
        assert call_args[1]["skip"] == 0
    
    @pytest.mark.asyncio
    async def test_get_application_history_with_filters(
        self, 
        tracking_service, 
        mock_db, 
        sample_db_application
    ):
        """Test application history retrieval with filters"""
        applications = [sample_db_application]
        mock_db.application.find_many = AsyncMock(return_value=applications)
        
        date_from = datetime.now() - timedelta(days=30)
        date_to = datetime.now()
        status_filter = [ApplicationStatus.SUBMITTED, ApplicationStatus.INTERVIEW_SCHEDULED]
        
        result = await tracking_service.get_application_history(
            user_id="user123",
            status_filter=status_filter,
            date_from=date_from,
            date_to=date_to
        )
        
        assert result == applications
        
        # Check the where clause includes filters
        call_args = mock_db.application.find_many.call_args
        where_clause = call_args[1]["where"]
        assert where_clause["userId"] == "user123"
        assert where_clause["status"]["in"] == status_filter
        assert where_clause["appliedAt"]["gte"] == date_from
        assert where_clause["appliedAt"]["lte"] == date_to
    
    @pytest.mark.asyncio
    async def test_get_application_timeline(
        self, 
        tracking_service
    ):
        """Test application timeline retrieval"""
        # Add some status changes to history
        tracking_service.status_history = [
            ApplicationStatusUpdate(
                application_id="app123",
                old_status=None,
                new_status=ApplicationStatus.SUBMITTED,
                reason=StatusChangeReason.AUTOMATIC_UPDATE,
                updated_at=datetime.now() - timedelta(days=2)
            ),
            ApplicationStatusUpdate(
                application_id="app123",
                old_status=ApplicationStatus.SUBMITTED,
                new_status=ApplicationStatus.VIEWED,
                reason=StatusChangeReason.SYSTEM_CHECK,
                updated_at=datetime.now() - timedelta(days=1)
            ),
            ApplicationStatusUpdate(
                application_id="other_app",
                old_status=ApplicationStatus.PENDING,
                new_status=ApplicationStatus.SUBMITTED,
                reason=StatusChangeReason.AUTOMATIC_UPDATE,
                updated_at=datetime.now()
            )
        ]
        
        timeline = await tracking_service.get_application_timeline("app123")
        
        # Should only return events for app123
        assert len(timeline) == 2
        
        # Check events are sorted by timestamp
        assert timeline[0].event_timestamp < timeline[1].event_timestamp
        
        # Check event details
        assert timeline[0].status_after == ApplicationStatus.SUBMITTED
        assert timeline[1].status_before == ApplicationStatus.SUBMITTED
        assert timeline[1].status_after == ApplicationStatus.VIEWED
    
    @pytest.mark.asyncio
    async def test_calculate_application_metrics(
        self, 
        tracking_service, 
        mock_db, 
        sample_job_post
    ):
        """Test application metrics calculation"""
        # Create sample applications with different statuses and dates
        now = datetime.now()
        applications = [
            DBApplication(
                id="app1",
                userId="user123",
                jobPostId="job1",
                resumeId="resume123",
                status=ApplicationStatus.SUBMITTED,
                matchScore=0.8,
                appliedAt=now - timedelta(days=1),
                lastStatusUpdate=now - timedelta(days=1),
                jobPost=sample_job_post
            ),
            DBApplication(
                id="app2",
                userId="user123",
                jobPostId="job2",
                resumeId="resume123",
                status=ApplicationStatus.INTERVIEW_SCHEDULED,
                matchScore=0.9,
                appliedAt=now - timedelta(days=5),
                lastStatusUpdate=now - timedelta(days=3),
                jobPost=sample_job_post
            ),
            DBApplication(
                id="app3",
                userId="user123",
                jobPostId="job3",
                resumeId="resume123",
                status=ApplicationStatus.REJECTED,
                matchScore=0.6,
                appliedAt=now - timedelta(days=10),
                lastStatusUpdate=now - timedelta(days=8),
                jobPost=sample_job_post
            )
        ]
        
        mock_db.application.find_many = AsyncMock(return_value=applications)
        
        metrics = await tracking_service.calculate_application_metrics("user123")
        
        assert metrics.total_applications == 3
        assert metrics.applications_by_status[ApplicationStatus.SUBMITTED] == 1
        assert metrics.applications_by_status[ApplicationStatus.INTERVIEW_SCHEDULED] == 1
        assert metrics.applications_by_status[ApplicationStatus.REJECTED] == 1
        assert metrics.applications_this_week == 2  # app1 and app2
        assert metrics.success_rate == 33.33  # 1 out of 3 successful (interview scheduled)
        assert metrics.average_response_time == 2.5  # (2 + 3) / 2 days average
        assert len(metrics.top_companies) == 1
        assert metrics.top_companies[0] == ("Tech Corp", 3)
    
    @pytest.mark.asyncio
    async def test_bulk_update_application_statuses(
        self, 
        tracking_service, 
        mock_db, 
        sample_db_application
    ):
        """Test bulk application status updates"""
        # Mock the update_application_status method
        updated_app = sample_db_application.model_copy()
        updated_app.status = ApplicationStatus.VIEWED
        
        with patch.object(tracking_service, 'update_application_status') as mock_update:
            mock_update.return_value = updated_app
            
            status_updates = [
                ("app1", ApplicationStatus.VIEWED, StatusChangeReason.SYSTEM_CHECK, "Auto-updated"),
                ("app2", ApplicationStatus.REJECTED, StatusChangeReason.EXTERNAL_NOTIFICATION, "Rejection email received")
            ]
            
            results = await tracking_service.bulk_update_application_statuses(status_updates)
            
            assert len(results) == 2
            assert mock_update.call_count == 2
            
            # Check the calls were made with correct parameters
            mock_update.assert_any_call("app1", ApplicationStatus.VIEWED, StatusChangeReason.SYSTEM_CHECK, "Auto-updated")
            mock_update.assert_any_call("app2", ApplicationStatus.REJECTED, StatusChangeReason.EXTERNAL_NOTIFICATION, "Rejection email received")
    
    @pytest.mark.asyncio
    async def test_get_applications_by_status(
        self, 
        tracking_service, 
        mock_db, 
        sample_db_application
    ):
        """Test getting applications filtered by status"""
        applications = [sample_db_application]
        mock_db.application.find_many = AsyncMock(return_value=applications)
        
        result = await tracking_service.get_applications_by_status(
            user_id="user123",
            status=ApplicationStatus.SUBMITTED,
            limit=5
        )
        
        assert result == applications
        
        # Check the query parameters
        call_args = mock_db.application.find_many.call_args
        where_clause = call_args[1]["where"]
        assert where_clause["userId"] == "user123"
        assert where_clause["status"] == ApplicationStatus.SUBMITTED
        assert call_args[1]["take"] == 5
    
    @pytest.mark.asyncio
    async def test_check_and_update_stale_applications(
        self, 
        tracking_service, 
        mock_db, 
        sample_db_application
    ):
        """Test checking and updating stale applications"""
        # Create stale application
        stale_app = sample_db_application.model_copy()
        stale_app.appliedAt = datetime.now() - timedelta(days=10)
        stale_app.status = ApplicationStatus.SUBMITTED
        
        mock_db.application.find_many = AsyncMock(return_value=[stale_app])
        
        # Mock the update_application_status method
        updated_app = stale_app.model_copy()
        updated_app.status = ApplicationStatus.VIEWED
        
        with patch.object(tracking_service, 'update_application_status') as mock_update:
            mock_update.return_value = updated_app
            
            results = await tracking_service.check_and_update_stale_applications(
                user_id="user123",
                stale_days=7
            )
            
            assert len(results) == 1
            assert results[0].status == ApplicationStatus.VIEWED
            
            # Check the update was called correctly
            mock_update.assert_called_once_with(
                stale_app.id,
                ApplicationStatus.VIEWED,
                StatusChangeReason.SYSTEM_CHECK,
                "Automatically updated after 7 days with no response"
            )
    
    def test_map_application_result_to_status(self, tracking_service):
        """Test mapping ApplicationResult status to database status"""
        # Test various status mappings
        test_cases = [
            (ServiceStatus.PENDING, ApplicationStatus.PENDING),
            (ServiceStatus.IN_PROGRESS, ApplicationStatus.PENDING),
            (ServiceStatus.SUBMITTED, ApplicationStatus.SUBMITTED),
            (ServiceStatus.FAILED, ApplicationStatus.PENDING),
            (ServiceStatus.REQUIRES_MANUAL_REVIEW, ApplicationStatus.PENDING),
            (ServiceStatus.RATE_LIMITED, ApplicationStatus.PENDING),
            (ServiceStatus.SITE_ERROR, ApplicationStatus.PENDING)
        ]
        
        for service_status, expected_db_status in test_cases:
            result = ApplicationResult(job_id="test", status=service_status)
            mapped_status = tracking_service._map_application_result_to_status(result)
            assert mapped_status == expected_db_status
    
    @pytest.mark.asyncio
    async def test_log_status_change(self, tracking_service):
        """Test status change logging"""
        await tracking_service._log_status_change(
            application_id="app123",
            old_status=ApplicationStatus.SUBMITTED,
            new_status=ApplicationStatus.VIEWED,
            reason=StatusChangeReason.SYSTEM_CHECK,
            notes="Automatically detected as viewed",
            updated_by="system",
            metadata={"source": "automated_check"}
        )
        
        assert len(tracking_service.status_history) == 1
        
        status_change = tracking_service.status_history[0]
        assert status_change.application_id == "app123"
        assert status_change.old_status == ApplicationStatus.SUBMITTED
        assert status_change.new_status == ApplicationStatus.VIEWED
        assert status_change.reason == StatusChangeReason.SYSTEM_CHECK
        assert status_change.notes == "Automatically detected as viewed"
        assert status_change.updated_by == "system"
        assert status_change.metadata["source"] == "automated_check"
    
    @pytest.mark.asyncio
    async def test_send_status_change_notification(
        self, 
        tracking_service, 
        sample_db_application
    ):
        """Test status change notification (placeholder implementation)"""
        # This test just ensures the method doesn't raise an exception
        # In a real implementation, this would test actual notification sending
        await tracking_service._send_status_change_notification(
            application=sample_db_application,
            old_status=ApplicationStatus.SUBMITTED,
            new_status=ApplicationStatus.VIEWED,
            reason=StatusChangeReason.SYSTEM_CHECK
        )
        
        # No assertion needed - just ensuring no exception is raised


class TestApplicationStatusUpdate:
    """Test cases for ApplicationStatusUpdate dataclass"""
    
    def test_application_status_update_creation(self):
        """Test ApplicationStatusUpdate creation with defaults"""
        update = ApplicationStatusUpdate(
            application_id="app123",
            old_status=ApplicationStatus.SUBMITTED,
            new_status=ApplicationStatus.VIEWED,
            reason=StatusChangeReason.SYSTEM_CHECK
        )
        
        assert update.application_id == "app123"
        assert update.old_status == ApplicationStatus.SUBMITTED
        assert update.new_status == ApplicationStatus.VIEWED
        assert update.reason == StatusChangeReason.SYSTEM_CHECK
        assert update.notes is None
        assert update.updated_by is None
        assert update.updated_at is not None
        assert update.metadata == {}
    
    def test_application_status_update_with_all_fields(self):
        """Test ApplicationStatusUpdate creation with all fields"""
        updated_at = datetime.now()
        metadata = {"source": "manual", "ip_address": "192.168.1.1"}
        
        update = ApplicationStatusUpdate(
            application_id="app123",
            old_status=ApplicationStatus.SUBMITTED,
            new_status=ApplicationStatus.INTERVIEW_SCHEDULED,
            reason=StatusChangeReason.MANUAL_UPDATE,
            notes="Interview scheduled for Monday",
            updated_by="user456",
            updated_at=updated_at,
            metadata=metadata
        )
        
        assert update.application_id == "app123"
        assert update.old_status == ApplicationStatus.SUBMITTED
        assert update.new_status == ApplicationStatus.INTERVIEW_SCHEDULED
        assert update.reason == StatusChangeReason.MANUAL_UPDATE
        assert update.notes == "Interview scheduled for Monday"
        assert update.updated_by == "user456"
        assert update.updated_at == updated_at
        assert update.metadata == metadata


class TestApplicationMetrics:
    """Test cases for ApplicationMetrics dataclass"""
    
    def test_application_metrics_creation(self):
        """Test ApplicationMetrics creation with defaults"""
        metrics = ApplicationMetrics(
            total_applications=10,
            applications_by_status={},
            applications_this_week=3,
            applications_this_month=8,
            average_response_time=5.5,
            success_rate=20.0,
            top_companies=[],
            applications_by_date={},
            match_score_distribution={}
        )
        
        assert metrics.total_applications == 10
        assert metrics.applications_this_week == 3
        assert metrics.applications_this_month == 8
        assert metrics.average_response_time == 5.5
        assert metrics.success_rate == 20.0
        assert metrics.applications_by_status == {}
        assert metrics.top_companies == []
        assert metrics.applications_by_date == {}
        assert metrics.match_score_distribution == {}


class TestApplicationTimelineEvent:
    """Test cases for ApplicationTimelineEvent dataclass"""
    
    def test_application_timeline_event_creation(self):
        """Test ApplicationTimelineEvent creation with defaults"""
        event_timestamp = datetime.now()
        
        event = ApplicationTimelineEvent(
            event_id="event123",
            application_id="app123",
            event_type="status_change",
            event_description="Status changed from SUBMITTED to VIEWED",
            event_timestamp=event_timestamp
        )
        
        assert event.event_id == "event123"
        assert event.application_id == "app123"
        assert event.event_type == "status_change"
        assert event.event_description == "Status changed from SUBMITTED to VIEWED"
        assert event.event_timestamp == event_timestamp
        assert event.status_before is None
        assert event.status_after is None
        assert event.metadata == {}
    
    def test_application_timeline_event_with_all_fields(self):
        """Test ApplicationTimelineEvent creation with all fields"""
        event_timestamp = datetime.now()
        metadata = {"user_agent": "Mozilla/5.0", "ip": "192.168.1.1"}
        
        event = ApplicationTimelineEvent(
            event_id="event123",
            application_id="app123",
            event_type="status_change",
            event_description="Status changed from SUBMITTED to VIEWED",
            event_timestamp=event_timestamp,
            status_before=ApplicationStatus.SUBMITTED,
            status_after=ApplicationStatus.VIEWED,
            metadata=metadata
        )
        
        assert event.event_id == "event123"
        assert event.application_id == "app123"
        assert event.event_type == "status_change"
        assert event.event_description == "Status changed from SUBMITTED to VIEWED"
        assert event.event_timestamp == event_timestamp
        assert event.status_before == ApplicationStatus.SUBMITTED
        assert event.status_after == ApplicationStatus.VIEWED
        assert event.metadata == metadata