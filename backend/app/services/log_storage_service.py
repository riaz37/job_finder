"""
Log storage and retrieval service for managing application logs in the database.

This service provides capabilities to store, search, and retrieve log entries
with filtering and pagination support.
"""
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4

from prisma import Prisma
from prisma.models import LogEntry as DBLogEntry

from app.core.logging import LogEntry, LogLevel, ActivityType, get_logger
from app.db.database import get_db_service


logger = get_logger(__name__)


class LogSearchCriteria:
    """Criteria for searching log entries."""
    
    def __init__(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        levels: Optional[List[LogLevel]] = None,
        activity_types: Optional[List[ActivityType]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        component: Optional[str] = None,
        message_contains: Optional[str] = None,
        has_errors: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ):
        self.start_date = start_date
        self.end_date = end_date
        self.levels = levels or []
        self.activity_types = activity_types or []
        self.user_id = user_id
        self.session_id = session_id
        self.correlation_id = correlation_id
        self.component = component
        self.message_contains = message_contains
        self.has_errors = has_errors
        self.limit = limit
        self.offset = offset


class LogStorageService:
    """Service for storing and retrieving log entries."""
    
    def __init__(self):
        self.db_service = get_db_service()
        self.logger = get_logger(__name__)
    
    async def store_log_entry(self, log_entry: LogEntry) -> bool:
        """
        Store a log entry in the database.
        
        Args:
            log_entry: The log entry to store
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            async with self.db_service.get_transaction() as db:
                await db.logentry.create({
                    'id': log_entry.id,
                    'timestamp': log_entry.timestamp,
                    'level': log_entry.level.value,
                    'activityType': log_entry.activity_type.value,
                    'message': log_entry.message,
                    'userId': log_entry.user_id,
                    'sessionId': log_entry.session_id,
                    'correlationId': log_entry.correlation_id,
                    'component': log_entry.component,
                    'metadata': json.dumps(log_entry.metadata) if log_entry.metadata else None,
                    'errorDetails': json.dumps(log_entry.error_details) if log_entry.error_details else None,
                    'performanceMetrics': json.dumps(log_entry.performance_metrics) if log_entry.performance_metrics else None
                })
            
            return True
            
        except Exception as e:
            # Use standard logging here to avoid recursion
            self.logger.error(
                f"Failed to store log entry {log_entry.id}",
                metadata={"log_entry_id": log_entry.id, "error": str(e)}
            )
            return False
    
    async def search_logs(self, criteria: LogSearchCriteria) -> Tuple[List[LogEntry], int]:
        """
        Search log entries based on criteria.
        
        Args:
            criteria: Search criteria
            
        Returns:
            Tuple of (log entries, total count)
        """
        try:
            async with self.db_service.get_transaction() as db:
                # Build where clause
                where_conditions = {}
                
                if criteria.start_date:
                    where_conditions['timestamp'] = {'gte': criteria.start_date}
                
                if criteria.end_date:
                    if 'timestamp' in where_conditions:
                        where_conditions['timestamp']['lte'] = criteria.end_date
                    else:
                        where_conditions['timestamp'] = {'lte': criteria.end_date}
                
                if criteria.levels:
                    where_conditions['level'] = {'in': [level.value for level in criteria.levels]}
                
                if criteria.activity_types:
                    where_conditions['activityType'] = {'in': [at.value for at in criteria.activity_types]}
                
                if criteria.user_id:
                    where_conditions['userId'] = criteria.user_id
                
                if criteria.session_id:
                    where_conditions['sessionId'] = criteria.session_id
                
                if criteria.correlation_id:
                    where_conditions['correlationId'] = criteria.correlation_id
                
                if criteria.component:
                    where_conditions['component'] = {'contains': criteria.component}
                
                if criteria.message_contains:
                    where_conditions['message'] = {'contains': criteria.message_contains}
                
                if criteria.has_errors is not None:
                    if criteria.has_errors:
                        where_conditions['errorDetails'] = {'not': None}
                    else:
                        where_conditions['errorDetails'] = None
                
                # Get total count
                total_count = await db.logentry.count(where=where_conditions)
                
                # Get log entries
                db_entries = await db.logentry.find_many(
                    where=where_conditions,
                    order={'timestamp': 'desc'},
                    skip=criteria.offset,
                    take=criteria.limit
                )
                
                # Convert to LogEntry objects
                log_entries = []
                for db_entry in db_entries:
                    log_entry = LogEntry(
                        id=db_entry.id,
                        timestamp=db_entry.timestamp,
                        level=LogLevel(db_entry.level),
                        activity_type=ActivityType(db_entry.activityType),
                        message=db_entry.message,
                        user_id=db_entry.userId,
                        session_id=db_entry.sessionId,
                        correlation_id=db_entry.correlationId,
                        component=db_entry.component,
                        metadata=json.loads(db_entry.metadata) if db_entry.metadata else {},
                        error_details=json.loads(db_entry.errorDetails) if db_entry.errorDetails else None,
                        performance_metrics=json.loads(db_entry.performanceMetrics) if db_entry.performanceMetrics else None
                    )
                    log_entries.append(log_entry)
                
                return log_entries, total_count
                
        except Exception as e:
            self.logger.error(
                f"Failed to search logs",
                metadata={"criteria": criteria.__dict__, "error": str(e)}
            )
            return [], 0
    
    async def get_log_entry(self, log_id: str) -> Optional[LogEntry]:
        """
        Get a specific log entry by ID.
        
        Args:
            log_id: The log entry ID
            
        Returns:
            The log entry if found, None otherwise
        """
        try:
            async with self.db_service.get_transaction() as db:
                db_entry = await db.logentry.find_unique(where={'id': log_id})
                
                if not db_entry:
                    return None
                
                return LogEntry(
                    id=db_entry.id,
                    timestamp=db_entry.timestamp,
                    level=LogLevel(db_entry.level),
                    activity_type=ActivityType(db_entry.activityType),
                    message=db_entry.message,
                    user_id=db_entry.userId,
                    session_id=db_entry.sessionId,
                    correlation_id=db_entry.correlationId,
                    component=db_entry.component,
                    metadata=json.loads(db_entry.metadata) if db_entry.metadata else {},
                    error_details=json.loads(db_entry.errorDetails) if db_entry.errorDetails else None,
                    performance_metrics=json.loads(db_entry.performanceMetrics) if db_entry.performanceMetrics else None
                )
                
        except Exception as e:
            self.logger.error(
                f"Failed to get log entry {log_id}",
                metadata={"log_id": log_id, "error": str(e)}
            )
            return None
    
    async def get_user_activity_summary(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get activity summary for a user.
        
        Args:
            user_id: The user ID
            start_date: Start date for the summary
            end_date: End date for the summary
            
        Returns:
            Activity summary dictionary
        """
        try:
            # Default to last 30 days if no dates provided
            if not end_date:
                end_date = datetime.now(timezone.utc)
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            criteria = LogSearchCriteria(
                start_date=start_date,
                end_date=end_date,
                user_id=user_id,
                limit=1000  # Get more entries for summary
            )
            
            log_entries, total_count = await self.search_logs(criteria)
            
            # Calculate summary statistics
            activity_counts = {}
            error_count = 0
            job_searches = 0
            job_applications = 0
            
            for entry in log_entries:
                # Count by activity type
                activity_type = entry.activity_type.value
                activity_counts[activity_type] = activity_counts.get(activity_type, 0) + 1
                
                # Count errors
                if entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
                    error_count += 1
                
                # Count specific activities
                if entry.activity_type == ActivityType.JOB_SEARCH:
                    job_searches += 1
                elif entry.activity_type == ActivityType.JOB_APPLICATION:
                    job_applications += 1
            
            return {
                "user_id": user_id,
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "total_activities": total_count,
                "activity_breakdown": activity_counts,
                "error_count": error_count,
                "job_searches": job_searches,
                "job_applications": job_applications,
                "error_rate": error_count / total_count if total_count > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(
                f"Failed to get user activity summary for {user_id}",
                metadata={"user_id": user_id, "error": str(e)}
            )
            return {}
    
    async def get_system_health_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get system health metrics based on logs.
        
        Args:
            start_date: Start date for metrics
            end_date: End date for metrics
            
        Returns:
            System health metrics dictionary
        """
        try:
            # Default to last 24 hours if no dates provided
            if not end_date:
                end_date = datetime.now(timezone.utc)
            if not start_date:
                start_date = end_date - timedelta(hours=24)
            
            criteria = LogSearchCriteria(
                start_date=start_date,
                end_date=end_date,
                limit=10000  # Get more entries for metrics
            )
            
            log_entries, total_count = await self.search_logs(criteria)
            
            # Calculate metrics
            error_count = 0
            warning_count = 0
            component_errors = {}
            performance_metrics = []
            
            for entry in log_entries:
                if entry.level == LogLevel.ERROR:
                    error_count += 1
                    component = entry.component
                    component_errors[component] = component_errors.get(component, 0) + 1
                elif entry.level == LogLevel.WARNING:
                    warning_count += 1
                
                if entry.performance_metrics:
                    performance_metrics.append(entry.performance_metrics)
            
            # Calculate average response times
            avg_response_times = {}
            if performance_metrics:
                operation_times = {}
                for metrics in performance_metrics:
                    if 'operation' in metrics and 'duration_ms' in metrics:
                        op = metrics['operation']
                        duration = metrics['duration_ms']
                        if op not in operation_times:
                            operation_times[op] = []
                        operation_times[op].append(duration)
                
                for op, times in operation_times.items():
                    avg_response_times[op] = sum(times) / len(times)
            
            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "total_log_entries": total_count,
                "error_count": error_count,
                "warning_count": warning_count,
                "error_rate": error_count / total_count if total_count > 0 else 0,
                "component_error_breakdown": component_errors,
                "average_response_times": avg_response_times,
                "health_score": max(0, 100 - (error_count * 2) - warning_count) if total_count > 0 else 100
            }
            
        except Exception as e:
            self.logger.error(
                f"Failed to get system health metrics",
                metadata={"error": str(e)}
            )
            return {}
    
    async def cleanup_old_logs(self, days_to_keep: int = 90) -> int:
        """
        Clean up old log entries.
        
        Args:
            days_to_keep: Number of days of logs to keep
            
        Returns:
            Number of log entries deleted
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            async with self.db_service.get_transaction() as db:
                # Count entries to be deleted
                count = await db.logentry.count(
                    where={'timestamp': {'lt': cutoff_date}}
                )
                
                # Delete old entries
                await db.logentry.delete_many(
                    where={'timestamp': {'lt': cutoff_date}}
                )
                
                self.logger.info(
                    f"Cleaned up {count} old log entries",
                    metadata={"cutoff_date": cutoff_date.isoformat(), "deleted_count": count}
                )
                
                return count
                
        except Exception as e:
            self.logger.error(
                f"Failed to cleanup old logs",
                metadata={"days_to_keep": days_to_keep, "error": str(e)}
            )
            return 0


# Global service instance
log_storage_service = LogStorageService()