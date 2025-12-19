# open_webui/metaweb/services/cache.py
# Redis Cache Service

import os
import json
import redis
from typing import Optional, Any
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class CacheService:
    """Redis Cache Service"""

    def __init__(self):
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        self.client = redis.from_url(redis_url, decode_responses=True)
        self.default_ttl = int(os.getenv('CACHE_DEFAULT_TTL', 3600))  # 1 hour

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache"""
        try:
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value, default=str)
            return self.client.setex(key, ttl, serialized)
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False

    def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        try:
            return self.client.incr(key, amount)
        except Exception as e:
            logger.error(f"Cache increment error: {e}")
            return 0

    def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time"""
        try:
            return self.client.expire(key, ttl)
        except Exception as e:
            logger.error(f"Cache expire error: {e}")
            return False

    def get_many(self, keys: list) -> dict:
        """Get multiple values"""
        try:
            pipeline = self.client.pipeline()
            for key in keys:
                pipeline.get(key)
            values = pipeline.execute()

            result = {}
            for key, value in zip(keys, values):
                if value:
                    try:
                        result[key] = json.loads(value)
                    except:
                        result[key] = value

            return result
        except Exception as e:
            logger.error(f"Cache get_many error: {e}")
            return {}

    def set_many(self, mapping: dict, ttl: Optional[int] = None) -> bool:
        """Set multiple values"""
        try:
            ttl = ttl or self.default_ttl
            pipeline = self.client.pipeline()

            for key, value in mapping.items():
                serialized = json.dumps(value, default=str)
                pipeline.setex(key, ttl, serialized)

            pipeline.execute()
            return True
        except Exception as e:
            logger.error(f"Cache set_many error: {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern"""
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear_pattern error: {e}")
            return 0

    # Queue operations for AI task queue
    def queue_push(self, queue_name: str, item: dict) -> bool:
        """Push item to queue"""
        try:
            serialized = json.dumps(item, default=str)
            self.client.rpush(queue_name, serialized)
            return True
        except Exception as e:
            logger.error(f"Queue push error: {e}")
            return False

    def queue_pop(self, queue_name: str, timeout: int = 0) -> Optional[dict]:
        """Pop item from queue"""
        try:
            result = self.client.blpop(queue_name, timeout)
            if result:
                _, value = result
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Queue pop error: {e}")
            return None

    def queue_length(self, queue_name: str) -> int:
        """Get queue length"""
        try:
            return self.client.llen(queue_name)
        except Exception as e:
            logger.error(f"Queue length error: {e}")
            return 0


# Global instance
cache = None  # Initialize when needed
