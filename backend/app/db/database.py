"""
Database connection and session management with connection pooling
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from prisma import Prisma
from app.core.config import settings

logger = logging.getLogger(__name__)


class DatabaseService:
    """Database service for managing Prisma client connections with connection pooling"""
    
    def __init__(self):
        self.db: Optional[Prisma] = None
        self._connected = False
        self._connection_lock = asyncio.Lock()
    
    async def connect(self) -> None:
        """Connect to the database with connection pooling"""
        async with self._connection_lock:
            if not self._connected:
                try:
                    self.db = Prisma()
                    await self.db.connect()
                    self._connected = True
                    logger.info("Database connection established successfully")
                except Exception as e:
                    logger.error(f"Failed to connect to database: {e}")
                    raise
    
    async def disconnect(self) -> None:
        """Disconnect from the database"""
        async with self._connection_lock:
            if self._connected and self.db:
                try:
                    await self.db.disconnect()
                    self._connected = False
                    self.db = None
                    logger.info("Database connection closed successfully")
                except Exception as e:
                    logger.error(f"Error disconnecting from database: {e}")
                    raise
    
    async def ensure_connected(self) -> None:
        """Ensure database connection is active"""
        if not self._connected or not self.db:
            await self.connect()
    
    def get_client(self) -> Prisma:
        """Get the Prisma client instance"""
        if not self.db:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.db
    
    async def health_check(self) -> bool:
        """Check if database connection is healthy"""
        try:
            await self.ensure_connected()
            # Simple query to test connection
            await self.db.user.count()
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database service instance
db_service = DatabaseService()


async def get_database() -> Prisma:
    """Dependency to get database client"""
    await db_service.ensure_connected()
    return db_service.get_client()


@asynccontextmanager
async def get_db_transaction() -> AsyncGenerator[Prisma, None]:
    """Context manager for database transactions"""
    await db_service.ensure_connected()
    db = db_service.get_client()
    
    async with db.tx() as transaction:
        try:
            yield transaction
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            raise


async def init_database() -> None:
    """Initialize database connection on startup"""
    try:
        await db_service.connect()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_database() -> None:
    """Close database connection on shutdown"""
    try:
        await db_service.disconnect()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")
        raise