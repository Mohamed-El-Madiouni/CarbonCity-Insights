"""
Redis Cache Utility Module

This module provides a RedisCache class for managing interactions with a Redis
database, including connecting, setting, retrieving, and closing connections.
It also includes a global instance `redis_cache` for use throughout the application.
"""

import json
import os

import redis.asyncio as redis
from dotenv import load_dotenv

from app.utils import serialize_data

# Load environment variables
load_dotenv()

# Configuration for Redis connection and cache expiration
REDIS_URL = os.getenv("REDIS_URL", None)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_CACHE_EXPIRE = int(os.getenv("REDIS_CACHE_EXPIRE", "2160000"))  # 25 days


class RedisCache:
    """
    A class to manage Redis cache operations.

    Provides methods for connecting to Redis, storing data, retrieving data,
    and closing the connection.
    """

    def __init__(self):
        """
        Initialize the RedisCache instance.

        Sets the Redis client instance to None initially.
        """
        self.redis = None

    async def connect(self):
        """
        Establish a connection to the Redis server.

        Uses the REDIS_URL environment variable if defined, otherwise falls back
        to REDIS_HOST and REDIS_PORT. Enables `decode_responses` to work with string data.
        """
        if REDIS_URL:
            self.redis = redis.from_url(REDIS_URL, decode_responses=True)
        else:
            self.redis = redis.Redis(
                host=REDIS_HOST, port=REDIS_PORT, decode_responses=True
            )
        print("Connected to Redis")

    async def set(self, key, value):
        """
        Store a key-value pair in the Redis cache.

        The value is serialized and stored with an expiration time defined
        by `REDIS_CACHE_EXPIRE`.

        Args:
            key (str): The key under which the value will be stored.
            value (Any): The value to be stored, which will be serialized.

        Raises:
            redis.exceptions.RedisError: If an error occurs during the set operation.
        """
        serialized_value = serialize_data(value)
        await self.redis.set(key, json.dumps(serialized_value), ex=REDIS_CACHE_EXPIRE)

    async def get(self, key):
        """
        Retrieve a value from the Redis cache by its key.

        The value is deserialized before being returned.

        Args:
            key (str): The key of the value to retrieve.

        Returns:
            Any: The deserialized value associated with the key, or None if not found.

        Raises:
            redis.exceptions.RedisError: If an error occurs during the get operation.
        """
        value = await self.redis.get(key)
        return json.loads(value) if value else None

    async def close(self):
        """
        Close the connection to the Redis server.

        This should be called when the application shuts down to cleanly release resources.

        Raises:
            redis.exceptions.RedisError: If an error occurs during the close operation.
        """
        await self.redis.close()


# Global RedisCache instance for application-wide use
redis_cache = RedisCache()
