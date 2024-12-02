"""
Test Suite for Rate Limiting Functionality.

This module contains test cases to validate the rate limiting logic for API endpoints.
The tests ensure that rate limits are enforced correctly, reset after the appropriate
time window, and work independently for different users and endpoints.

Test cases:
- `test_rate_limit_exceeded`: Validates that exceeding the rate limit returns a 429 response.
- `test_rate_limit_reset`: Verifies that the rate limit resets after the configured window.
- `test_rate_limit_multiple_users`: Ensures rate limiting is applied independently for different
    users.
- `test_rate_limit_independent_endpoints`: Confirms rate limiting works independently for
    different endpoints.

Dependencies:
- `pytest`: Used as the testing framework.
- `asyncio`: Handles asynchronous operations in tests.
"""

import asyncio

import pytest


@pytest.mark.asyncio
async def test_rate_limit_exceeded(test_client, test_token):
    """
    Test that the rate limit returns a 429 response when exceeded.
    """
    test_token, _ = test_token
    # Simulate requests until exceeding the limit
    for _ in range(10):
        response = await test_client.get(f"/vehicle_emissions?token={test_token}")
        assert response.status_code == 200  # The first requests succeed

    # The 10th request should return a 429
    response = await test_client.get(f"/vehicle_emissions?token={test_token}")
    assert response.status_code == 429
    assert response.json()["detail"] == (
        "You have reached the limit of requests allowed per minute. "
        "Please wait one minute and try again later."
    )


@pytest.mark.asyncio
async def test_rate_limit_reset(test_client, test_token, redis_cache):
    """
    Test that the rate limit resets after the window expires.
    """
    test_token, _ = test_token
    # Simulate requests until reaching the limit
    for _ in range(10):
        response = await test_client.get(f"/vehicle_emissions?token={test_token}")
        assert response.status_code == 200

    # The limit is reached
    response = await test_client.get(f"/vehicle_emissions?token={test_token}")
    assert response.status_code == 429

    # Wait for the window to reset (5 seconds)
    await asyncio.sleep(5)

    # Check that the key has expired (TTL should be -2 or the key should be absent)
    ttl_after_sleep = await redis_cache.redis.ttl(
        "rate_limit:test_user:vehicle_emissions"
    )
    assert ttl_after_sleep == -2

    # Verify that the limit has been reset
    response = await test_client.get(f"/vehicle_emissions?token={test_token}")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_multiple_users(test_client, test_token):
    """
    Test that rate limiting works independently for multiple users.
    """
    test_token, other_token = test_token
    # Simulate requests for user 1
    for _ in range(10):
        response = await test_client.get(f"/vehicle_emissions?token={test_token}")
        assert response.status_code == 200

    # The limit is reached for user 1
    response = await test_client.get(f"/vehicle_emissions?token={test_token}")
    assert response.status_code == 429

    # Simulate requests for another user
    for _ in range(10):
        response = await test_client.get(f"/vehicle_emissions?token={other_token}")
        assert response.status_code == 200

    # The limit does not affect this user
    response = await test_client.get(f"/vehicle_emissions?token={other_token}")
    assert response.status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_independent_endpoints(test_client, test_token):
    """
    Test that rate limiting is independent for different endpoints.
    """
    test_token, _ = test_token
    # Simulate requests for the first endpoint
    for _ in range(10):
        response = await test_client.get(f"/vehicle_emissions?token={test_token}")
        assert response.status_code == 200

    # The limit is reached for /vehicle_emissions
    response = await test_client.get(f"/vehicle_emissions?token={test_token}")
    assert response.status_code == 429

    # Verify that the second endpoint is not affected
    for _ in range(5):
        response = await test_client.post(
            f"/vehicle_emissions/compare?token={test_token}",
            json={
                "vehicle_1": {"make": "Ferrari", "model": "308", "year": 1985},
                "vehicle_2": {"make": "Ferrari", "model": "F40", "year": 1991},
            },
        )
        assert response.status_code == 200
