"""
Redis service for caching and session management
"""
import json
from typing import Optional, Any, List
from datetime import datetime, timedelta
import redis.asyncio as redis
from app.core.config import settings


class RedisService:
    """Redis service for caching and session management"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Connect to Redis"""
        self.redis_client = redis.from_url(settings.REDIS_URL)
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None):
        """Set a value in Redis"""
        if self.redis_client:
            serialized_value = json.dumps(value) if not isinstance(value, str) else value
            await self.redis_client.set(key, serialized_value, ex=expire)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from Redis"""
        if self.redis_client:
            value = await self.redis_client.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value.decode('utf-8')
        return None
    
    async def delete(self, key: str):
        """Delete a key from Redis"""
        if self.redis_client:
            await self.redis_client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis"""
        if self.redis_client:
            return await self.redis_client.exists(key)
        return False
    
    async def get_keys_pattern(self, pattern: str) -> List[str]:
        """Get all keys matching a pattern"""
        if self.redis_client:
            keys = await self.redis_client.keys(pattern)
            return [key.decode('utf-8') for key in keys]
        return []
    
    async def set_hash(self, key: str, field: str, value: Any):
        """Set a field in a Redis hash"""
        if self.redis_client:
            serialized_value = json.dumps(value) if not isinstance(value, str) else value
            await self.redis_client.hset(key, field, serialized_value)
    
    async def get_hash(self, key: str, field: str) -> Optional[Any]:
        """Get a field from a Redis hash"""
        if self.redis_client:
            value = await self.redis_client.hget(key, field)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value.decode('utf-8')
        return None
    
    async def get_all_hash(self, key: str) -> dict:
        """Get all fields from a Redis hash"""
        if self.redis_client:
            hash_data = await self.redis_client.hgetall(key)
            result = {}
            for field, value in hash_data.items():
                field_str = field.decode('utf-8')
                try:
                    result[field_str] = json.loads(value)
                except json.JSONDecodeError:
                    result[field_str] = value.decode('utf-8')
            return result
        return {}
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a value in Redis"""
        if self.redis_client:
            return await self.redis_client.incrby(key, amount)
        return 0
    
    async def expire(self, key: str, seconds: int):
        """Set expiration time for a key"""
        if self.redis_client:
            await self.redis_client.expire(key, seconds)
    
    async def ttl(self, key: str) -> int:
        """Get time to live for a key"""
        if self.redis_client:
            return await self.redis_client.ttl(key)
        return -1
    
    # Session management specific methods
    async def create_session(self, user_id: str, session_data: dict, expire_seconds: int = 60 * 60 * 24 * 8):
        """Create a user session"""
        session_key = f"session:{user_id}"
        await self.set(session_key, session_data, expire=expire_seconds)
    
    async def get_session(self, user_id: str) -> Optional[dict]:
        """Get user session"""
        session_key = f"session:{user_id}"
        return await self.get(session_key)
    
    async def update_session(self, user_id: str, updates: dict):
        """Update session data"""
        session_key = f"session:{user_id}"
        session_data = await self.get(session_key)
        if session_data:
            session_data.update(updates)
            # Get current TTL to preserve expiration
            ttl = await self.ttl(session_key)
            if ttl > 0:
                await self.set(session_key, session_data, expire=ttl)
            else:
                await self.set(session_key, session_data)
    
    async def delete_session(self, user_id: str):
        """Delete user session"""
        session_key = f"session:{user_id}"
        await self.delete(session_key)
    
    async def get_all_user_sessions(self) -> List[dict]:
        """Get all active user sessions"""
        session_keys = await self.get_keys_pattern("session:*")
        sessions = []
        for key in session_keys:
            session_data = await self.get(key)
            if session_data:
                sessions.append(session_data)
        return sessions
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions (Redis handles this automatically, but useful for monitoring)"""
        session_keys = await self.get_keys_pattern("session:*")
        active_sessions = 0
        for key in session_keys:
            if await self.exists(key):
                active_sessions += 1
        return active_sessions


# Global Redis service instance
redis_service = RedisService()