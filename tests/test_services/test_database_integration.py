"""
Integration tests for database interactions and vehicle emissions endpoint.

This module verifies that the database queries, schema manipulations, and
API interactions work as expected. It ensures data insertion, retrieval,
filtering, and pagination align with the specifications.
"""

import os

import pytest

from app.database import database


@pytest.mark.asyncio
async def test_database_query():
    """
    Test database query execution.

    Verifies that data can be queried correctly from the test schema
    and matches the inserted test data.
    """
    schema_name = f"test_schema_{os.getpid()}"  # Uses PID to create a unique name
    results = await database.fetch_all(
        f"SELECT * FROM {schema_name}.vehicle_emissions;"
    )
    assert len(results) == 2
    assert results[0]["vehicle_make_name"] == "Make A"
    assert results[1]["vehicle_make_name"] == "Make B"


@pytest.mark.asyncio
async def test_vehicle_emissions_endpoint(test_client):
    """
    Test the /vehicle_emissions endpoint for default data retrieval.

    Verifies that the endpoint interacts with the database correctly and
    returns the expected results with proper HTTP status codes.
    """
    response = await test_client.get("/vehicle_emissions")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2
    assert data["data"][0]["vehicle_make_name"] == "Make A"
    assert data["data"][1]["vehicle_make_name"] == "Make B"


@pytest.mark.asyncio
async def test_vehicle_emissions_with_filters(test_client):
    """
    Test filtering functionality for the /vehicle_emissions endpoint.

    Ensures that the endpoint filters results correctly based on the
    provided query parameters (e.g., vehicle_make_name).
    """
    response = await test_client.get("/vehicle_emissions?vehicle_make_name=Make A")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["vehicle_make_name"] == "Make A"
    assert data["data"][0]["vehicle_model_name"] == "Model A"


@pytest.mark.asyncio
async def test_empty_schema_behavior(test_client):
    """
    Test behavior when the schema is empty.

    Ensures that the database and endpoint handle empty schemas gracefully.
    """
    schema_name = f"test_schema_{os.getpid()}"  # Uses PID to create a unique name
    await database.execute(f"DELETE FROM {schema_name}.vehicle_emissions; ")
    response = await test_client.get("/vehicle_emissions")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 0


@pytest.mark.asyncio
async def test_redis_cache_mock(mock_redis_cache):
    """
    Test that the mock RedisCache works as expected.
    """
    # Test cache retrieval with a JSON value
    mock_redis_cache.redis.get.return_value = '{"key": "cached_value"}'
    value = await mock_redis_cache.get("test_key")
    assert value == {"key": "cached_value"}

    # Testing caching
    await mock_redis_cache.set("test_key", {"key": "new_value"})
    mock_redis_cache.redis.set.assert_called_with(
        "test_key", '{"key": "new_value"}', ex=2160000
    )
