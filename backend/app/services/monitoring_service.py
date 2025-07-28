"""
Monitoring service for system health checks, metrics collection,
and alerting capabilities.
"""
import asyncio
import psutil
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from app.core.logging import get_logger, ActivityType, LogLevel
from app.services.log_storage_service import log_storage_service, LogSearchCriteria
from app.db.database import get_db_service
from app.services.redis_service import redis_service


logger = get_logger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Health check result."""
    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    response_time_ms: Optional[float] = None


@dataclass
class SystemMetrics:
    """System performance metrics."""
    timestamp: datetime
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float
    active_connections: int
    response_time_avg_ms: float
    error_rate_percent: float
    uptime_seconds: float


class MonitoringService:
    """Service for monitoring system health and collecting metrics."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.db_service = get_db_service()
        self.start_time = time.time()
        self._health_checks = {}
        self._metrics_history = []
        self._max_metrics_history = 1000
    
    async def perform_health_check(self, component: str = "all") -> Dict[str, HealthCheck]:
        """
        Perform health checks on system components.
        
        Args:
            component: Specific component to check or "all" for all components
            
        Returns:
            Dictionary of health check results
        """
        health_checks = {}
        
        try:
            if component in ["all", "database"]:
                health_checks["database"] = await self._check_database_health()
            
            if component in ["all", "redis"]:
                health_checks["redis"] = await self._check_redis_health()
            
            if component in ["all", "disk"]:
                health_checks["disk"] = await self._check_disk_health()
            
            if component in ["all", "memory"]:
                health_checks["memory"] = await self._check_memory_health()
            
            if component in ["all", "logs"]:
                health_checks["logs"] = await self._check_logs_health()
            
            # Store health check results
            self._health_checks = health_checks
            
            # Log overall health status
            overall_status = self._calculate_overall_health(health_checks)
            self.logger.log_activity(
                level=LogLevel.INFO,
                activity_type=ActivityType.SYSTEM_EVENT,
                message=f"Health check completed - Overall status: {overall_status.value}",
                metadata={
                    "component": component,
                    "overall_status": overall_status.value,
                    "checks_performed": list(health_checks.keys())
                }
            )
            
            return health_checks
            
        except Exception as e:
            self.logger.log_error_with_context(
                error=e,
                context="perform_health_check",
                additional_metadata={"component": component}
            )
            return {}
    
    async def _check_database_health(self) -> HealthCheck:
        """Check database connectivity and performance."""
        start_time = time.time()
        
        try:
            # Test database connection
            is_healthy = await self.db_service.health_check()
            response_time = (time.time() - start_time) * 1000
            
            if is_healthy:
                # Get additional database metrics
                async with self.db_service.get_transaction() as db:
                    # Count total users (as a basic connectivity test)
                    user_count = await db.user.count()
                    
                status = HealthStatus.HEALTHY
                message = "Database is healthy and responsive"
                details = {
                    "connected": True,
                    "user_count": user_count,
                    "response_time_ms": response_time
                }
            else:
                status = HealthStatus.CRITICAL
                message = "Database connection failed"
                details = {"connected": False}
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            status = HealthStatus.CRITICAL
            message = f"Database health check failed: {str(e)}"
            details = {"error": str(e), "connected": False}
        
        return HealthCheck(
            name="database",
            status=status,
            message=message,
            details=details,
            timestamp=datetime.now(timezone.utc),
            response_time_ms=response_time
        )
    
    async def _check_redis_health(self) -> HealthCheck:
        """Check Redis connectivity and performance."""
        start_time = time.time()
        
        try:
            # Test Redis connection with ping
            await redis_service.ping()
            response_time = (time.time() - start_time) * 1000
            
            # Get Redis info
            info = await redis_service.get_info()
            
            status = HealthStatus.HEALTHY
            message = "Redis is healthy and responsive"
            details = {
                "connected": True,
                "response_time_ms": response_time,
                "memory_usage": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0)
            }
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            status = HealthStatus.CRITICAL
            message = f"Redis health check failed: {str(e)}"
            details = {"error": str(e), "connected": False}
        
        return HealthCheck(
            name="redis",
            status=status,
            message=message,
            details=details,
            timestamp=datetime.now(timezone.utc),
            response_time_ms=response_time
        )
    
    async def _check_disk_health(self) -> HealthCheck:
        """Check disk usage and availability."""
        try:
            disk_usage = psutil.disk_usage('/')
            usage_percent = (disk_usage.used / disk_usage.total) * 100
            
            if usage_percent > 90:
                status = HealthStatus.CRITICAL
                message = f"Disk usage critical: {usage_percent:.1f}%"
            elif usage_percent > 80:
                status = HealthStatus.WARNING
                message = f"Disk usage high: {usage_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk usage normal: {usage_percent:.1f}%"
            
            details = {
                "usage_percent": usage_percent,
                "total_gb": disk_usage.total / (1024**3),
                "used_gb": disk_usage.used / (1024**3),
                "free_gb": disk_usage.free / (1024**3)
            }
            
        except Exception as e:
            status = HealthStatus.UNKNOWN
            message = f"Could not check disk usage: {str(e)}"
            details = {"error": str(e)}
        
        return HealthCheck(
            name="disk",
            status=status,
            message=message,
            details=details,
            timestamp=datetime.now(timezone.utc)
        )
    
    async def _check_memory_health(self) -> HealthCheck:
        """Check memory usage."""
        try:
            memory = psutil.virtual_memory()
            usage_percent = memory.percent
            
            if usage_percent > 90:
                status = HealthStatus.CRITICAL
                message = f"Memory usage critical: {usage_percent:.1f}%"
            elif usage_percent > 80:
                status = HealthStatus.WARNING
                message = f"Memory usage high: {usage_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage normal: {usage_percent:.1f}%"
            
            details = {
                "usage_percent": usage_percent,
                "total_gb": memory.total / (1024**3),
                "used_gb": memory.used / (1024**3),
                "available_gb": memory.available / (1024**3)
            }
            
        except Exception as e:
            status = HealthStatus.UNKNOWN
            message = f"Could not check memory usage: {str(e)}"
            details = {"error": str(e)}
        
        return HealthCheck(
            name="memory",
            status=status,
            message=message,
            details=details,
            timestamp=datetime.now(timezone.utc)
        )
    
    async def _check_logs_health(self) -> HealthCheck:
        """Check logging system health."""
        try:
            # Check recent error rate
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=1)
            
            criteria = LogSearchCriteria(
                start_date=start_time,
                end_date=end_time,
                levels=[LogLevel.ERROR, LogLevel.CRITICAL],
                limit=100
            )
            
            error_logs, error_count = await log_storage_service.search_logs(criteria)
            
            # Get total logs in the same period
            total_criteria = LogSearchCriteria(
                start_date=start_time,
                end_date=end_time,
                limit=1000
            )
            _, total_count = await log_storage_service.search_logs(total_criteria)
            
            error_rate = (error_count / total_count * 100) if total_count > 0 else 0
            
            if error_rate > 10:
                status = HealthStatus.CRITICAL
                message = f"High error rate in logs: {error_rate:.1f}%"
            elif error_rate > 5:
                status = HealthStatus.WARNING
                message = f"Elevated error rate in logs: {error_rate:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Log error rate normal: {error_rate:.1f}%"
            
            details = {
                "error_count_1h": error_count,
                "total_logs_1h": total_count,
                "error_rate_percent": error_rate
            }
            
        except Exception as e:
            status = HealthStatus.UNKNOWN
            message = f"Could not check logs health: {str(e)}"
            details = {"error": str(e)}
        
        return HealthCheck(
            name="logs",
            status=status,
            message=message,
            details=details,
            timestamp=datetime.now(timezone.utc)
        )
    
    def _calculate_overall_health(self, health_checks: Dict[str, HealthCheck]) -> HealthStatus:
        """Calculate overall system health from individual checks."""
        if not health_checks:
            return HealthStatus.UNKNOWN
        
        statuses = [check.status for check in health_checks.values()]
        
        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            return HealthStatus.WARNING
        elif HealthStatus.UNKNOWN in statuses:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
    
    async def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system performance metrics."""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get network connections (approximate active connections)
            connections = len(psutil.net_connections())
            
            # Calculate uptime
            uptime = time.time() - self.start_time
            
            # Get recent performance metrics from logs
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(minutes=5)
            
            criteria = LogSearchCriteria(
                start_date=start_time,
                end_date=end_time,
                activity_types=[ActivityType.PERFORMANCE_METRIC],
                limit=100
            )
            
            perf_logs, _ = await log_storage_service.search_logs(criteria)
            
            # Calculate average response time
            response_times = []
            for log in perf_logs:
                if log.performance_metrics and 'duration_ms' in log.performance_metrics:
                    response_times.append(log.performance_metrics['duration_ms'])
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            # Calculate error rate
            error_criteria = LogSearchCriteria(
                start_date=start_time,
                end_date=end_time,
                levels=[LogLevel.ERROR, LogLevel.CRITICAL],
                limit=100
            )
            
            _, error_count = await log_storage_service.search_logs(error_criteria)
            
            total_criteria = LogSearchCriteria(
                start_date=start_time,
                end_date=end_time,
                limit=1000
            )
            
            _, total_count = await log_storage_service.search_logs(total_criteria)
            
            error_rate = (error_count / total_count * 100) if total_count > 0 else 0
            
            metrics = SystemMetrics(
                timestamp=datetime.now(timezone.utc),
                cpu_usage_percent=cpu_percent,
                memory_usage_percent=memory.percent,
                disk_usage_percent=(disk.used / disk.total) * 100,
                active_connections=connections,
                response_time_avg_ms=avg_response_time,
                error_rate_percent=error_rate,
                uptime_seconds=uptime
            )
            
            # Store metrics in history
            self._metrics_history.append(metrics)
            if len(self._metrics_history) > self._max_metrics_history:
                self._metrics_history.pop(0)
            
            # Log metrics
            self.logger.log_performance_metric(
                operation="system_metrics_collection",
                duration_ms=0,  # This is instantaneous
                additional_metrics={
                    "cpu_usage_percent": cpu_percent,
                    "memory_usage_percent": memory.percent,
                    "disk_usage_percent": (disk.used / disk.total) * 100,
                    "error_rate_percent": error_rate
                }
            )
            
            return metrics
            
        except Exception as e:
            self.logger.log_error_with_context(
                error=e,
                context="collect_system_metrics"
            )
            # Return default metrics on error
            return SystemMetrics(
                timestamp=datetime.now(timezone.utc),
                cpu_usage_percent=0,
                memory_usage_percent=0,
                disk_usage_percent=0,
                active_connections=0,
                response_time_avg_ms=0,
                error_rate_percent=0,
                uptime_seconds=time.time() - self.start_time
            )
    
    def get_metrics_history(self, minutes: int = 60) -> List[SystemMetrics]:
        """
        Get system metrics history for the specified time period.
        
        Args:
            minutes: Number of minutes of history to return
            
        Returns:
            List of system metrics
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        return [
            metrics for metrics in self._metrics_history
            if metrics.timestamp >= cutoff_time
        ]
    
    async def check_alert_conditions(self) -> List[Dict[str, Any]]:
        """
        Check for conditions that should trigger alerts.
        
        Returns:
            List of alert conditions that are currently active
        """
        alerts = []
        
        try:
            # Perform health checks
            health_checks = await self.perform_health_check()
            
            # Check for critical health issues
            for name, check in health_checks.items():
                if check.status == HealthStatus.CRITICAL:
                    alerts.append({
                        "type": "health_critical",
                        "component": name,
                        "message": check.message,
                        "details": check.details,
                        "timestamp": check.timestamp.isoformat()
                    })
                elif check.status == HealthStatus.WARNING:
                    alerts.append({
                        "type": "health_warning",
                        "component": name,
                        "message": check.message,
                        "details": check.details,
                        "timestamp": check.timestamp.isoformat()
                    })
            
            # Check recent error rate
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(minutes=15)
            
            criteria = LogSearchCriteria(
                start_date=start_time,
                end_date=end_time,
                levels=[LogLevel.ERROR, LogLevel.CRITICAL],
                limit=50
            )
            
            error_logs, error_count = await log_storage_service.search_logs(criteria)
            
            if error_count > 10:  # More than 10 errors in 15 minutes
                alerts.append({
                    "type": "high_error_rate",
                    "message": f"High error rate detected: {error_count} errors in 15 minutes",
                    "error_count": error_count,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            
            return alerts
            
        except Exception as e:
            self.logger.log_error_with_context(
                error=e,
                context="check_alert_conditions"
            )
            return []


# Global service instance
monitoring_service = MonitoringService()