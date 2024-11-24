"""
Configuration module for test suite.

Provides pytest fixtures and configuration for running tests against the FastAPI application,
including database setup, test environment configuration, and HTTP client initialization.
"""

import importlib
import os
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import database
from app.main import app
from app.redis_cache import RedisCache
from app.routes import vehicle_routes

pytestmark = pytest.mark.asyncio(scope="session")  # Sets the scope for all tests


@pytest.fixture(autouse=True)
async def mock_redis_cache():
    """
    Mock the RedisCache instance for tests.
    """
    redis_mock = RedisCache()
    redis_mock.redis = AsyncMock()
    redis_mock.redis.get.return_value = None  # Simulates a lack of cached data
    redis_mock.redis.set.return_value = True  # Simulates cache success

    vehicle_routes.redis_cache = redis_mock

    yield redis_mock


@pytest.fixture(scope="session", autouse=True)
def set_test_environment():
    """
    Configure test environment and handle module reloading.

    Sets APP_ENV to 'test' and reloads affected modules to ensure proper test isolation.
    Restores original environment after tests complete.
    """
    original_env = os.getenv("APP_ENV", "production")
    os.environ["APP_ENV"] = "test"
    importlib.reload(vehicle_routes)
    yield
    os.environ["APP_ENV"] = original_env
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
