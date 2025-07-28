"""
Tests for the logging and monitoring system.
"""
import asyncio
import json
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, AsyncMock

from app.core.logging import (
    StructuredLogger, LogEntry, LogLevel, ActivityType, 
    get_logger, JsonFormatter
)
from app.services.log_storage_service import (
    LogStorageService, LogSearchCriteria, log_storage_service
)
from app.services.monitoring_service import (
    MonitoringService, HealthStatus, HealthCheck, SystemMetrics,
    monitoring_service
)


class TestStructuredLogger:
    """Test cases for StructuredLogger."""
    
    def test_logger_initialization(self):
        """Test logger initialization."""
        logger = StructuredLogger("test_logger")
        assert logger.name == "test_logger"
        assert logger.logger is not None
    
    def test_log_activity(self):
        """Test basic log activity functionality."""
        logger = StructuredLogger("test_logger")
        
        log_id = logger.log_activity(
            level=LogLevel.INFO,
            activity_type=ActivityType.USER_ACTION,
            message="Test message",
            user_id="user123",
            metadata={"key": "value"}
        )
        
        assert log_id is not None
        assert isinstance(log_id, str)
    
    def test_convenience_methods(self):
        """Test convenience logging methods."""
        logger = StructuredLogger("test_logger")
        
        # Test each convenience method
        debug_id = logger.debug("Debug message")
        info_id = logger.info("Info message")
        warning_id = logger.warning("Warning message")
        error_id = logger.error("Error message")
        critical_id = logger.critical("Critical message")
        
        assert all(isinstance(log_id, str) for log_id in [
            debug_id, info_id, warning_id, error_id, critical_id
        ])
    
    def test_log_user_action(self):
        """Test user action logging."""
        logger = StructuredLogger("test_logger")
        
        log_id = logger.log_user_action(
            action="login",
            user_id="user123",
            session_id="session456",
            metadata={"ip": "192.168.1.1"}
        )
        
        assert log_id is not None
    
    def test_log_job_search(self):
        """Test job search logging."""
        logger = StructuredLogger("test_logger")
        
        log_id = logger.log_job_search(
            search_criteria={"title": "developer", "location": "remote"},
            results_count=25,
            user_id="user123",
            duration_ms=1500.0
        )
        
        assert log_id is not None
    
    def test_log_error_with_context(self):
        """Test error logging with context."""
        logger = StructuredLogger("test_logger")
        
        try:
            raise ValueError("Test error")
        except ValueError as e:
            log_id = logger.log_error_with_context(
                error=e,
                context="test_function",
                user_id="user123",
                additional_metadata={"function": "test_func"}
            )
            
            assert log_id is not None


class TestJsonFormatter:
    """Test cases for JsonFormatter."""
    
    def test_format_structured_log(self):
        """Test formatting structured log entries."""
        formatter = JsonFormatter()
        
        # Create a mock log record with JSON message
        log_entry = LogEntry(
            level=LogLevel.INFO,
            activity_type=ActivityType.USER_ACTION,
            message="Test message",
            user_id="user123"
        )
        
        record = Mock()
        record.getMessage.return_value = log_entry.model_dump_json()
        
        formatted = formatter.format(record)
        parsed = json.loads(formatted)
        
        assert parsed["level"] == "INFO"
        assert parsed["activity_type"] == "user_action"
        assert parsed["message"] == "Test message"
        assert parsed["user_id"] == "user123"
    
    def test_format_simple_log(self):
        """Test formatting simple log messages."""
        formatter = JsonFormatter()
        
        record = Mock()
        record.getMessage.return_value = "Simple log message"
        record.levelname = "INFO"
        record.name = "test_logger"
        record.exc_info = None
        
        formatted = formatter.format(record)
        parsed = json.loads(formatted)
        
        assert parsed["level"] == "INFO"
        assert parsed["component"] == "test_logger"
        assert parsed["message"] == "Simple log message"
        assert parsed["activity_type"] == "system_event"


class TestLogStorageService:
    """Test cases for LogStorageService."""
    
    @pytest.fixture
    def log_service(self):
        """Create a log storage service for testing."""
        return LogStorageService()
    
    @pytest.fixture
    def sample_log_entry(self):
        """Create a sample log entry for testing."""
        return LogEntry(
            level=LogLevel.INFO,
            activity_type=ActivityType.USER_ACTION,
            message="Test log entry",
            user_id="user123",
            session_id="session456",
            metadata={"test": "data"}
        )
    
    @pytest.mark.asyncio
    async def test_store_log_entry(self, log_service, sample_log_entry):
        """Test storing a log entry."""
        with patch.object(log_service.db_service, 'get_transaction') as mock_transaction:
            mock_db = AsyncMock()
            mock_transaction.return_value.__aenter__.return_value = mock_db
            mock_db.logentry.create = AsyncMock()
            
            result = await log_service.store_log_entry(sample_log_entry)
            
            assert result is True
            mock_db.logentry.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_logs(self, log_service):
        """Test searching log entries."""
        criteria = LogSearchCriteria(
            levels=[LogLevel.INFO],
            user_id="user123",
            limit=10
        )
        
        with patch.object(log_service.db_service, 'get_transaction') as mock_transaction:
            mock_db = AsyncMock()
            mock_transaction.return_value.__aenter__.return_value = mock_db
            
            # Mock database response
            mock_db_entry = Mock()
            mock_db_entry.id = "log123"
            mock_db_entry.timestamp = datetime.now(timezone.utc)
            mock_db_entry.level = "INFO"
            mock_db_entry.activityType = "user_action"
            mock_db_entry.message = "Test message"
            mock_db_entry.userId = "user123"
            mock_db_entry.sessionId = "session456"
            mock_db_entry.correlationId = None
            mock_db_entry.component = "test"
            mock_db_entry.metadata = '{"test": "data"}'
            mock_db_entry.errorDetails = None
            mock_db_entry.performanceMetrics = None
            
            mock_db.logentry.count.return_value = 1
            mock_db.logentry.find_many.return_value = [mock_db_entry]
            
            log_entries, total_count = await log_service.search_logs(criteria)
            
            assert total_count == 1
            assert len(log_entries) == 1
            assert log_entries[0].id == "log123"
            assert log_entries[0].level == LogLevel.INFO
    
    @pytest.mark.asyncio
    async def test_get_user_activity_summary(self, log_service):
        """Test getting user activity summary."""
        with patch.object(log_service, 'search_logs') as mock_search:
            # Mock log entries
            mock_entries = [
                LogEntry(
                    level=LogLevel.INFO,
                    activity_type=ActivityType.JOB_SEARCH,
                    message="Job search",
                    user_id="user123"
                ),
                LogEntry(
                    level=LogLevel.ERROR,
                    activity_type=ActivityType.ERROR_EVENT,
                    message="Error occurred",
                    user_id="user123"
                )
            ]
            mock_search.return_value = (mock_entries, 2)
            
            summary = await log_service.get_user_activity_summary("user123")
            
            assert summary["user_id"] == "user123"
            assert summary["total_activities"] == 2
            assert summary["error_count"] == 1
            assert summary["job_searches"] == 1
            assert summary["error_rate"] == 0.5


class TestMonitoringService:
    """Test cases for MonitoringService."""
    
    @pytest.fixture
    def monitoring_service_instance(self):
        """Create a monitoring service for testing."""
        return MonitoringService()
    
    @pytest.mark.asyncio
    async def test_database_health_check(self, monitoring_service_instance):
        """Test database health check."""
        with patch.object(monitoring_service_instance.db_service, 'health_check') as mock_health:
            mock_health.return_value = True
            
            with patch.object(monitoring_service_instance.db_service, 'get_transaction') as mock_transaction:
                mock_db = AsyncMock()
                mock_transaction.return_value.__aenter__.return_value = mock_db
                mock_db.user.count.return_value = 10
                
                health_check = await monitoring_service_instance._check_database_health()
                
                assert health_check.name == "database"
                assert health_check.status == HealthStatus.HEALTHY
                assert health_check.details["connected"] is True
                assert health_check.details["user_count"] == 10
    
    @pytest.mark.asyncio
    async def test_redis_health_check(self, monitoring_service_instance):
        """Test Redis health check."""
        with patch('app.services.monitoring_service.redis_service') as mock_redis:
            mock_redis.ping = AsyncMock()
            mock_redis.get_info.return_value = {
                "used_memory_human": "1.5MB",
                "connected_clients": 5
            }
            
            health_check = await monitoring_service_instance._check_redis_health()
            
            assert health_check.name == "redis"
            assert health_check.status == HealthStatus.HEALTHY
            assert health_check.details["connected"] is True
    
    @pytest.mark.asyncio
    async def test_perform_health_check(self, monitoring_service_instance):
        """Test performing comprehensive health check."""
        with patch.object(monitoring_service_instance, '_check_database_health') as mock_db_check:
            with patch.object(monitoring_service_instance, '_check_redis_health') as mock_redis_check:
                with patch.object(monitoring_service_instance, '_check_disk_health') as mock_disk_check:
                    with patch.object(monitoring_service_instance, '_check_memory_health') as mock_memory_check:
                        with patch.object(monitoring_service_instance, '_check_logs_health') as mock_logs_check:
                            
                            # Mock health check results
                            mock_db_check.return_value = HealthCheck(
                                name="database",
                                status=HealthStatus.HEALTHY,
                                message="Database is healthy",
                                details={},
                                timestamp=datetime.now(timezone.utc)
                            )
                            
                            mock_redis_check.return_value = HealthCheck(
                                name="redis",
                                status=HealthStatus.HEALTHY,
                                message="Redis is healthy",
                                details={},
                                timestamp=datetime.now(timezone.utc)
                            )
                            
                            mock_disk_check.return_value = HealthCheck(
                                name="disk",
                                status=HealthStatus.HEALTHY,
                                message="Disk is healthy",
                                details={},
                                timestamp=datetime.now(timezone.utc)
                            )
                            
                            mock_memory_check.return_value = HealthCheck(
                                name="memory",
                                status=HealthStatus.HEALTHY,
                                message="Memory is healthy",
                                details={},
                                timestamp=datetime.now(timezone.utc)
                            )
                            
                            mock_logs_check.return_value = HealthCheck(
                                name="logs",
                                status=HealthStatus.HEALTHY,
                                message="Logs are healthy",
                                details={},
                                timestamp=datetime.now(timezone.utc)
                            )
                            
                            health_checks = await monitoring_service_instance.perform_health_check()
                            
                            assert len(health_checks) == 5
                            assert all(check.status == HealthStatus.HEALTHY for check in health_checks.values())
    
    @pytest.mark.asyncio
    async def test_collect_system_metrics(self, monitoring_service_instance):
        """Test collecting system metrics."""
        with patch('app.services.monitoring_service.psutil') as mock_psutil:
            with patch('app.services.monitoring_service.log_storage_service') as mock_log_service:
                
                # Mock system metrics
                mock_psutil.cpu_percent.return_value = 25.5
                mock_psutil.virtual_memory.return_value = Mock(percent=60.0)
                mock_psutil.disk_usage.return_value = Mock(
                    used=50 * 1024**3,
                    total=100 * 1024**3
                )
                mock_psutil.net_connections.return_value = [Mock()] * 10
                
                # Mock log service responses
                mock_log_service.search_logs.return_value = ([], 0)
                
                metrics = await monitoring_service_instance.collect_system_metrics()
                
                assert isinstance(metrics, SystemMetrics)
                assert metrics.cpu_usage_percent == 25.5
                assert metrics.memory_usage_percent == 60.0
                assert metrics.disk_usage_percent == 50.0
                assert metrics.active_connections == 10
    
    def test_get_metrics_history(self, monitoring_service_instance):
        """Test getting metrics history."""
        # Add some mock metrics to history
        now = datetime.now(timezone.utc)
        old_metric = SystemMetrics(
            timestamp=now - timedelta(hours=2),
            cpu_usage_percent=30.0,
            memory_usage_percent=50.0,
            disk_usage_percent=40.0,
            active_connections=5,
            response_time_avg_ms=100.0,
            error_rate_percent=1.0,
            uptime_seconds=7200
        )
        
        recent_metric = SystemMetrics(
            timestamp=now - timedelta(minutes=30),
            cpu_usage_percent=25.0,
            memory_usage_percent=45.0,
            disk_usage_percent=42.0,
            active_connections=8,
            response_time_avg_ms=120.0,
            error_rate_percent=0.5,
            uptime_seconds=9000
        )
        
        monitoring_service_instance._metrics_history = [old_metric, recent_metric]
        
        # Get last 60 minutes of history
        history = monitoring_service_instance.get_metrics_history(minutes=60)
        
        assert len(history) == 1  # Only recent_metric should be included
        assert history[0].cpu_usage_percent == 25.0


class TestGlobalInstances:
    """Test global service instances."""
    
    def test_get_logger(self):
        """Test getting logger instance."""
        logger = get_logger("test_component")
        assert isinstance(logger, StructuredLogger)
        assert logger.name == "test_component"
    
    def test_log_storage_service_instance(self):
        """Test log storage service global instance."""
        assert log_storage_service is not None
        assert isinstance(log_storage_service, LogStorageService)
    
    def test_monitoring_service_instance(self):
        """Test monitoring service global instance."""
        assert monitoring_service is not None
        assert isinstance(monitoring_service, MonitoringService)


if __name__ == "__main__":
    pytest.main([__file__])