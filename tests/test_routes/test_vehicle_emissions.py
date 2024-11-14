"""
Tests for the vehicle emissions endpoint.

This module includes test cases to verify that the vehicle emissions endpoint
returns data correctly and that pagination and filtering functionality work as expected.
"""

import pytest
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport

from app.main import app, lifespan


@pytest.mark.asyncio
async def test_get_vehicle_emissions():
    """
    Test the /vehicle_emissions endpoint.

    This test verifies that the vehicle emissions endpoint returns a 200 status code
    and that the data returned is in the correct format. It also tests pagination
    by limiting the number of results and verifies if the filtering by vehicle make
    and year works as expected.
    """
    # Launch app within lifespan context to activate DB connection
    async with lifespan(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Test default request without filters
            response = await client.get("/vehicle_emissions")
            assert response.status_code == 200
            assert isinstance(response.json(), dict)

            # Validate schema of each item in response
            expected_keys = {
                "id",
                "vehicle_model_id",
                "year",
                "vehicle_model_name",
                "vehicle_make_name",
                "distance_value",
                "distance_unit",
                "carbon_emission_g",
            }
            for item in response.json()["data"]:
                assert expected_keys.issubset(item.keys())

            # Test pagination limit and offset
            response_paginated = await client.get("/vehicle_emissions?limit=5&offset=0")
            assert response_paginated.status_code == 200
            assert len(response_paginated.json()) <= 5

            # Test filtering by vehicle_make_name
            response_filtered_make = await client.get(
                "/vehicle_emissions?vehicle_make_name=Ferrari"
            )
            assert response_filtered_make.status_code == 200
            for item in response_filtered_make.json()["data"]:
                assert item["vehicle_make_name"] == "Ferrari"

            # Test filtering by year
            response_filtered_year = await client.get("/vehicle_emissions?year=2010")
            assert response_filtered_year.status_code == 200
            for item in response_filtered_year.json()["data"]:
                assert item["year"] == 2010

            # Test non-existent filter
            response_non_existent = await client.get(
                "/vehicle_emissions?vehicle_make_name=NonExistentMake"
            )
            assert response_non_existent.status_code == 200
            assert response_non_existent.json() == {}
