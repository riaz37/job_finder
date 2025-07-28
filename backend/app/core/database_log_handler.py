"""
Database log handler for storing structured logs in the database.
"""
import asyncio
import json
import logging
import threading
from datetime import datetime, timezone
from queue import Queue
from typing import Optional

from app.core.config import settings
from app.core.logging import LogEntry, LogLevel, ActivityType


class DatabaseLogHandler(logging.Handler):
    """
    Custom logging handler that stores structured logs in the database.
    Uses a background thread to avoid blocking the main application.
    """
    
    def __init__(self):
        super().__init__()
        self.log_queue = Queue()
        self.worker_thread = None
        self.shutdown_event = threading.Event()
        
        if settings.LOG_TO_DATABASE:
            self._start_worker_thread()
    
    def _start_worker_thread(self):
        """Start the background worker thread for database logging."""
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="DatabaseLogWorker"
        )
        self.worker_thread.start()
    
    def _worker_loop(self):
        """Background worker loop that processes log entries."""
        # Import here to avoid circular imports
        from app.services.log_storage_service import log_storage_service
        
        while not self.shutdown_event.is_set():
            try:
                # Get log entry from queue with timeout
                try:
                    log_entry = self.log_queue.get(timeout=1.0)
                except:
                    continue
                
                # Store in database using asyncio
                loop = None
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                if loop:
                    try:
                        loop.run_until_complete(
                            log_storage_service.store_log_entry(log_entry)
                        )
                    except Exception as e:
                        # Use standard logging to avoid recursion
                        print(f"Failed to store log entry in database: {e}")
                
                self.log_queue.task_done()
                
            except Exception as e:
                # Use standard logging to avoid recursion
                print(f"Error in database log worker: {e}")
    
    def emit(self, record: logging.LogRecord):
        """
        Emit a log record to the database.
        
        Args:
            record: The log record to emit
        """
        if not settings.LOG_TO_DATABASE or not self.worker_thread:
            return
        
        try:
            # Try to parse the message as JSON (for structured log entries)
            try:
                log_data = json.loads(record.getMessage())
                
                # Convert to LogEntry object
                log_entry = LogEntry(
                    id=log_data.get('id'),
                    timestamp=datetime.fromisoformat(log_data.get('timestamp', datetime.now(timezone.utc).isoformat())),
                    level=LogLevel(log_data.get('level', record.levelname)),
                    activity_type=ActivityType(log_data.get('activity_type', 'system_event')),
                    message=log_data.get('message', ''),
                    user_id=log_data.get('user_id'),
                    session_id=log_data.get('session_id'),
                    correlation_id=log_data.get('correlation_id'),
                    component=log_data.get('component', record.name),
                    metadata=log_data.get('metadata', {}),
                    error_details=log_data.get('error_details'),
                    performance_metrics=log_data.get('performance_metrics')
                )
                
            except (json.JSONDecodeError, ValueError, KeyError):
                # Fallback to simple log entry
                log_entry = LogEntry(
                    level=LogLevel(record.levelname),
                    activity_type=ActivityType.SYSTEM_EVENT,
                    message=record.getMessage(),
                    component=record.name,
                    metadata={
                        'filename': record.filename,
                        'lineno': record.lineno,
                        'funcName': record.funcName
                    }
                )
                
                # Add exception info if present
                if record.exc_info:
                    log_entry.error_details = {
                        'exception': self.format(record)
                    }
            
            # Add to queue for background processing
            try:
                self.log_queue.put_nowait(log_entry)
            except:
                # Queue is full, skip this log entry
                pass
                
        except Exception as e:
            # Use standard logging to avoid recursion
            print(f"Error in database log handler: {e}")
    
    def close(self):
        """Close the handler and clean up resources."""
        if self.worker_thread:
            self.shutdown_event.set()
            
            # Wait for queue to be processed
            try:
                self.log_queue.join()
            except:
                pass
            
            # Wait for worker thread to finish
            if self.worker_thread.is_alive():
                self.worker_thread.join(timeout=5.0)
        
        super().close()


# Global instance
database_log_handler = DatabaseLogHandler()