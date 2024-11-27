"""
Configuration module for test suite.

Provides pytest fixtures and configuration for running tests against the FastAPI application,
including database setup, test environment configuration, and HTTP client initialization.
"""

import asyncio
import importlib
import os
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import database
from app.main import app
from app.redis_cache import RedisCache
from app.routes import auth_routes, vehicle_routes
from app.utils import create_access_token

pytestmark = pytest.mark.asyncio(scope="session")  # Sets the scope for all tests


@pytest.fixture(autouse=True)
async def redis_cache():
    """
    Mock the RedisCache instance for tests.
    """
    redis_mock = RedisCache()
    redis_mock.redis = AsyncMock()
    redis_mock.redis.get.return_value = None  # Simulates a lack of cached data
    redis_mock.redis.set.return_value = True  # Simulates cache success

    vehicle_routes.redis_cache = redis_mock

    # Track tasks for managing expirations
    redis_storage = {}
    expiration_tasks = []  # Track tasks for managing expirations

    async def incr_side_effect(key):
        if key not in redis_storage:
            redis_storage[key] = 0
        redis_storage[key] += 1
        return redis_storage[key]

    async def ttl_side_effect(key):
        """
        Simulates retrieving the TTL of a key. Returns -2 if the key has expired.
        """
        if key in redis_storage:
            return 3  # Initially set TTL
        return -2  # Indicates that the key has expired

    async def expire_side_effect(key, ttl):
        """
        Simulates setting a TTL on a key. Deletes the key after expiration.
        """
        ttl_to_use = 3 if os.getenv("APP_ENV") == "test" else ttl
        if key in redis_storage:
            # Launch an asynchronous task to delete the key after the TTL
            task = asyncio.create_task(simulate_key_expiration(key, ttl_to_use))
            expiration_tasks.append(task)

    async def simulate_key_expiration(key, ttl):
        """
        Deletes a key after a certain delay (TTL) to simulate expiration.
        """
        await asyncio.sleep(ttl)
        if key in redis_storage:
            del redis_storage[key]

    redis_mock.redis.incr.side_effect = incr_side_effect
    redis_mock.redis.ttl.side_effect = ttl_side_effect
    redis_mock.redis.expire.side_effect = expire_side_effect

    yield redis_mock

    # Clean up the simulated storage after the test
    redis_storage.clear()

    # Cancel remaining expiration tasks
    for task in expiration_tasks:
        if not task.done():
            task.cancel()
    await asyncio.gather(*expiration_tasks, return_exceptions=True)


# Dictionary to simulate Redis storage
mock_redis_storage = {}


def mock_redis_incr(key: str) -> int:
    """
    Simulate the Redis `incr` operation.
    """
    if key not in mock_redis_storage:
        mock_redis_storage[key] = 0
    mock_redis_storage[key] += 1
    return mock_redis_storage[key]


@pytest.fixture(autouse=True)
def reset_mock_redis_storage():
    """
    Reset the mock Redis storage before each test.
    """
    mock_redis_storage.clear()


@pytest.fixture(scope="session", autouse=True)
def set_test_environment():
    """
    Configure test environment and handle module reloading.

    Sets APP_ENV to 'test' and reloads affected modules to ensure proper test isolation.
    Restores original environment after tests complete.
    """
    original_env = os.getenv("APP_ENV", "production")
    os.environ["APP_ENV"] = "test"
    importlib.reload(auth_routes)
    importlib.reload(vehicle_routes)
    yield
    os.environ["APP_ENV"] = original_env
    importlib.reload(auth_routes)
    importlib.reload(vehicle_routes)


@pytest.fixture(autouse=True)
async def setup_test_database():
    """Initialize test database with unique schema name"""
    schema_name = f"test_schema_{os.getpid()}"  # Uses PID to create a unique name
    os.environ["APP_ENV"] = "test"
    async with database:
        await database.execute(f"SET search_path TO {schema_name};")
        await database.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;")
        await database.execute(f"CREATE SCHEMA {schema_name};")
        await database.execute(
            f"""
            CREATE TABLE {schema_name}.vehicle_emissions (
                id UUID PRIMARY KEY,
                vehicle_model_id UUID,
                vehicle_make_name TEXT,
                vehicle_model_name TEXT,
                year INTEGER,
                distance_value FLOAT,
                distance_unit TEXT,
                carbon_emission_g FLOAT
            );
        """
        )
        await database.execute(
            f"""
            CREATE TABLE {schema_name}.users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) NOT NULL UNIQUE,
                email VARCHAR(255) NOT NULL UNIQUE,
                hashed_password TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE
            );
            """
        )
        await database.execute(
            f"""
            INSERT INTO {schema_name}.vehicle_emissions VALUES
            ('123e4567-e89b-12d3-a456-426614174000', '123e4567-e89b-12d3-a456-426614174001', 
            'Make A', 'Model A', 2020, 100, 'km', 150);
        """
        )
        await database.execute(
            f"""
            INSERT INTO {schema_name}.vehicle_emissions VALUES
            ('223e4567-e89b-12d3-a456-426614174000', '223e4567-e89b-12d3-a456-426614174001',
            'Make B', 'Model B', 2021, 200, 'km', 300);
        """
        )
        yield
        await database.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;")


@pytest.fixture
async def test_client():
    """
    Provide a configured HTTP test client.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture(scope="session")
def database_test_url():
    """
    Provide the database test URL.
    """
    schema_name = f"test_schema_{os.getpid()}"  # Uses PID to create a unique name
    return os.getenv("DATABASE_URL") + f"?options=-csearch_path={schema_name}"


@pytest.fixture
def user_test():
    """
    Fixture to provide test user data.
    """
    return {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "securepassword",
    }


@pytest.fixture
def test_token():
    """
    Fixture to generate a valid token for testing purposes.
    """
    data = {"sub": "test_user"}  # Payload with a test user
    token = create_access_token(data)
    data = {"sub": "other_user"}  # Payload with a test user
    other_token = create_access_token(data)
    return token, other_token


@pytest.fixture
async def clear_redis(mock_redis_cache):
    """
    Clear Redis data for a clean state before tests.
    """
    await mock_redis_cache.redis.delete("rate_limit:test_user:vehicle_emissions")
    yield
