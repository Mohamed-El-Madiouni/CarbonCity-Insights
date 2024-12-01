"""
Redis Cache Utility Module

This module provides a RedisCache class for managing interactions with a Redis
database, including connecting, setting, retrieving, and closing connections.
It also includes a global instance `redis_cache` for use throughout the application.
"""

import json
import logging
import os

import redis.asyncio as redis
from dotenv import load_dotenv
from fastapi import HTTPException

from app.utils import serialize_data

# Configure log directory
log_dir = os.path.abspath(os.path.join(__file__, "../../../log"))
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Configure logger
log_path = os.path.join(log_dir, "routes.log")
logger = logging.getLogger("routes_logger")
logger.setLevel(logging.INFO)

# File and console handlers for routes_logger
file_handler = logging.FileHandler(log_path)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
console_handler = logging.StreamHandler()

# Adding handlers to routes_logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Load environment variables
load_dotenv()

# Configuration for Redis connection and cache expiration
REDIS_URL = os.getenv("REDIS_URL", None)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_CACHE_EXPIRE = int(os.getenv("REDIS_CACHE_EXPIRE", "600"))


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

    async def rate_limit(self, token: str, limit: int, window: int, endpoint: str):
        """
        Implement rate limiting based on a token.
        :param token: Unique token for the user.
        :param limit: Maximum number of requests allowed.
        :param window: Time window in seconds.
        """
        key = f"rate_limit:{token}:{endpoint}"
        # Increment the request count
        current = await self.redis.incr(key)
        if current == 1:
            # Set expiration on first request
            await self.redis.expire(key, window)
            logger.info(
                "Rate limit initialized for user: %s. Window: %s seconds.",
                token,
                window,
            )
        if current > limit:
            # Log the violation
            logger.warning(
                "Rate limit exceeded for user: %s. "
                "Limit: %s, Window: %s seconds, Requests: %s.",
                token,
                limit,
                window,
                current,
            )
            raise HTTPException(
                status_code=429,
                detail="You have reached the limit of requests allowed per minute. "
                "Please wait one minute and try again later.",
            )
        # Log valid requests
        logger.info(
            "Request %s/%s for user: '%s' within %s seconds.",
            current,
            limit,
            token,
            window,
        )


# Global RedisCache instance for application-wide use
redis_cache = RedisCache()
