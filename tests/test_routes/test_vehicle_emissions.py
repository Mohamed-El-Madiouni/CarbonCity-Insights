"""
Tests for the vehicle emissions endpoint.

This module includes test cases to verify that the vehicle emissions endpoint
returns data correctly and that pagination and filtering functionality work as expected.
"""

import pytest


@pytest.mark.asyncio
async def test_get_vehicle_emissions_default_response(test_client):
    """
    Test the default response of the /vehicle_emissions endpoint.

    This test verifies that the /vehicle_emissions endpoint returns a 200 status code
    and that the response format is a dictionary.
    """
    response = await test_client.get("/vehicle_emissions")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_get_vehicle_emissions_response_schema(test_client):
    """
    Test that the response schema contains expected keys.

    This test checks that each item in the data returned by /vehicle_emissions
    includes the expected fields.
    """
    response = await test_client.get("/vehicle_emissions")
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


@pytest.mark.asyncio
async def test_get_vehicle_emissions_pagination(test_client):
    """
    Test pagination functionality of the /vehicle_emissions endpoint.

    This test verifies that the endpoint returns the correct number of results
    when using the limit and offset query parameters.
    """
    response_paginated = await test_client.get("/vehicle_emissions?limit=5")
    assert response_paginated.status_code == 200
    # Validate that the number of returned items does not exceed the limit
    assert len(response_paginated.json()["data"]) <= 5


@pytest.mark.asyncio
async def test_filter_by_vehicle_make(test_client):
    """
    Test filtering results by vehicle_make_name.

    This test verifies that the /vehicle_emissions endpoint filters results
    correctly when a specific vehicle make (e.g., Ferrari) is provided.
    """
    response_filtered_make = await test_client.get(
        "/vehicle_emissions?vehicle_make_name=Ferrari"
    )
    assert response_filtered_make.status_code == 200
    for item in response_filtered_make.json()["data"]:
        assert item["vehicle_make_name"] == "Ferrari"


@pytest.mark.asyncio
async def test_filter_by_year(test_client):
    """
    Test filtering results by year.

    This test verifies that the /vehicle_emissions endpoint correctly filters results
    when a specific year (e.g., 2010) is provided.
    """
    response_filtered_year = await test_client.get("/vehicle_emissions?year=2010")
    assert response_filtered_year.status_code == 200
    for item in response_filtered_year.json()["data"]:
        assert item["year"] == 2010


@pytest.mark.asyncio
async def test_pagination_last_page(test_client):
    """
    Test pagination when reaching the last page of results.

    This test verifies that the pagination system correctly identifies when
    there are no additional pages.
    """
    response_last_page = await test_client.get(
        "/vehicle_emissions?year=2010&vehicle_make_name=Ferrari&limit=100"
    )
    # Assuming offset is set high enough to be the last page or return fewer than limit
    assert response_last_page.status_code == 200
    assert response_last_page.json()["next_cursor"] is None


@pytest.mark.asyncio
async def test_empty_result_with_non_existent_filter(test_client):
    """
    Test the response for non-existent filter values.

    This test verifies that when a non-existent vehicle make is provided,
    the response returns an empty list or equivalent.
    """
    response_non_existent = await test_client.get(
        "/vehicle_emissions?vehicle_make_name=NonExistentMake"
    )
    assert response_non_existent.status_code == 200
    # Assuming the API returns an empty list for no results found
    assert response_non_existent.json()["data"] == []


@pytest.mark.asyncio
async def test_next_cursor_type(test_client):
    """
    Test the next_cursor field type in the /vehicle_emissions response.

    This test checks that the next_cursor field, if present in the response,
    is of type string, indicating more pages are available.
    """
    response = await test_client.get("/vehicle_emissions?limit=1")
    assert response.status_code == 200
    # Check if "next_cursor" is of type str
    assert isinstance(response.json()["next_cursor"], str)
