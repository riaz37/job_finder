"""
Comprehensive logging and monitoring system for the AI Job Agent.

This module provides structured logging, activity tracking, error monitoring,
and log storage/retrieval capabilities.
"""
import json
import logging
import logging.handlers
import sys
import traceback
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.config import settings


class LogLevel(str, Enum):
    """Log levels for structured logging."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ActivityType(str, Enum):
    """Types of activities that can be logged."""
    USER_ACTION = "user_action"
    JOB_SEARCH = "job_search"
    JOB_APPLICATION = "job_application"
    RESUME_PROCESSING = "resume_processing"
    AI_PROCESSING = "ai_processing"
    SYSTEM_EVENT = "system_event"
    ERROR_EVENT = "error_event"
    PERFORMANCE_METRIC = "performance_metric"


class LogEntry(BaseModel):
    """Structured log entry model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    level: LogLevel
    activity_type: ActivityType
    message: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    component: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error_details: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, Any]] = None


class StructuredLogger:
    """
    Structured logger that provides comprehensive logging capabilities
    with JSON formatting and activity tracking.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """Set up the logger with appropriate handlers and formatters."""
        if not self.logger.handlers:
            # Set log level based on configuration
            log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
            self.logger.setLevel(log_level)
            
            # Create console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            
            # Create file handler for all logs
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_dir / "ai_job_agent.log",
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(logging.DEBUG)
            
            # Create error file handler
            error_handler = logging.handlers.RotatingFileHandler(
                log_dir / "errors.log",
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            error_handler.setLevel(logging.ERROR)
            
            # Create JSON formatter
            json_formatter = JsonFormatter()
            
            # Set formatters
            console_handler.setFormatter(json_formatter)
            file_handler.setFormatter(json_formatter)
            error_handler.setFormatter(json_formatter)
            
            # Add handlers
            self.logger.addHandler(console_handler)
            self.logger.addHandler(file_handler)
            self.logger.addHandler(error_handler)
            
            # Add database handler if enabled
            if settings.LOG_TO_DATABASE:
                try:
                    from app.core.database_log_handler import database_log_handler
                    self.logger.addHandler(database_log_handler)
                except ImportError:
                    # Database handler not available, continue without it
                    pass
    
    def log_activity(
        self,
        level: LogLevel,
        activity_type: ActivityType,
        message: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error_details: Optional[Dict[str, Any]] = None,
        performance_metrics: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a structured activity entry.
        
        Args:
            level: Log level
            activity_type: Type of activity being logged
            message: Human-readable message
            user_id: ID of the user associated with this activity
            session_id: Session ID for request tracking
            correlation_id: Correlation ID for distributed tracing
            metadata: Additional metadata
            error_details: Error information if applicable
            performance_metrics: Performance metrics if applicable
            
        Returns:
            Log entry ID for reference
        """
        log_entry = LogEntry(
            level=level,
            activity_type=activity_type,
            message=message,
            user_id=user_id,
            session_id=session_id,
            correlation_id=correlation_id,
            component=self.name,
            metadata=metadata or {},
            error_details=error_details,
            performance_metrics=performance_metrics
        )
        
        # Log the entry
        log_level = getattr(logging, level.value)
        self.logger.log(log_level, log_entry.model_dump_json())
        
        return log_entry.id
    
    def debug(self, message: str, **kwargs) -> str:
        """Log debug message."""
        return self.log_activity(LogLevel.DEBUG, ActivityType.SYSTEM_EVENT, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> str:
        """Log info message."""
        return self.log_activity(LogLevel.INFO, ActivityType.SYSTEM_EVENT, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> str:
        """Log warning message."""
        return self.log_activity(LogLevel.WARNING, ActivityType.SYSTEM_EVENT, message, **kwargs)
    
    def error(self, message: str, **kwargs) -> str:
        """Log error message."""
        return self.log_activity(LogLevel.ERROR, ActivityType.ERROR_EVENT, message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> str:
        """Log critical message."""
        return self.log_activity(LogLevel.CRITICAL, ActivityType.ERROR_EVENT, message, **kwargs)
    
    def log_user_action(
        self,
        action: str,
        user_id: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log user action."""
        return self.log_activity(
            LogLevel.INFO,
            ActivityType.USER_ACTION,
            f"User action: {action}",
            user_id=user_id,
            session_id=session_id,
            metadata=metadata
        )
    
    def log_job_search(
        self,
        search_criteria: Dict[str, Any],
        results_count: int,
        user_id: str,
        session_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        duration_ms: Optional[float] = None
    ) -> str:
        """Log job search activity."""
        metadata = {
            "search_criteria": search_criteria,
            "results_count": results_count
        }
        
        performance_metrics = None
        if duration_ms is not None:
            performance_metrics = {"duration_ms": duration_ms}
        
        return self.log_activity(
            LogLevel.INFO,
            ActivityType.JOB_SEARCH,
            f"Job search completed: {results_count} results found",
            user_id=user_id,
            session_id=session_id,
            correlation_id=correlation_id,
            metadata=metadata,
            performance_metrics=performance_metrics
        )
    
    def log_job_application(
        self,
        job_id: str,
        job_title: str,
        company: str,
        status: str,
        user_id: str,
        session_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log job application activity."""
        application_metadata = {
            "job_id": job_id,
            "job_title": job_title,
            "company": company,
            "status": status
        }
        if metadata:
            application_metadata.update(metadata)
        
        return self.log_activity(
            LogLevel.INFO,
            ActivityType.JOB_APPLICATION,
            f"Job application {status}: {job_title} at {company}",
            user_id=user_id,
            session_id=session_id,
            correlation_id=correlation_id,
            metadata=application_metadata
        )
    
    def log_error_with_context(
        self,
        error: Exception,
        context: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log error with full context and stack trace."""
        error_details = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "stack_trace": traceback.format_exc(),
            "context": context
        }
        
        metadata = additional_metadata or {}
        
        return self.log_activity(
            LogLevel.ERROR,
            ActivityType.ERROR_EVENT,
            f"Error in {context}: {str(error)}",
            user_id=user_id,
            session_id=session_id,
            correlation_id=correlation_id,
            metadata=metadata,
            error_details=error_details
        )
    
    def log_performance_metric(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        additional_metrics: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log performance metrics."""
        performance_metrics = {
            "operation": operation,
            "duration_ms": duration_ms,
            "success": success
        }
        if additional_metrics:
            performance_metrics.update(additional_metrics)
        
        return self.log_activity(
            LogLevel.INFO,
            ActivityType.PERFORMANCE_METRIC,
            f"Performance metric: {operation} took {duration_ms:.2f}ms",
            user_id=user_id,
            session_id=session_id,
            correlation_id=correlation_id,
            performance_metrics=performance_metrics
        )


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        try:
            # Try to parse the message as JSON (for structured log entries)
            log_data = json.loads(record.getMessage())
        except (json.JSONDecodeError, ValueError):
            # Fallback to simple message format
            log_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "component": record.name,
                "message": record.getMessage(),
                "activity_type": "system_event"
            }
            
            # Add exception info if present
            if record.exc_info:
                log_data["error_details"] = {
                    "exception": self.formatException(record.exc_info)
                }
        
        return json.dumps(log_data, default=str, ensure_ascii=False)


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name)


# Global logger instance for the application
app_logger = get_logger("ai_job_agent")