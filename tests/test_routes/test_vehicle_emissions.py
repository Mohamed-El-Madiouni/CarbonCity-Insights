"""
Tests for the vehicle emissions endpoint.

This module includes test cases to verify that the vehicle emissions endpoint
returns data correctly and that pagination and filtering functionality work as expected.
"""

import pytest


@pytest.mark.asyncio
async def test_get_vehicle_emissions_default_response(test_client, test_token):
    """
    Test the default response of the /vehicle_emissions endpoint.

    This test verifies that the /vehicle_emissions endpoint returns a 200 status code
    and that the response format is a dictionary.
    """
    response = await test_client.get(f"/vehicle_emissions?token={test_token}")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_get_vehicle_emissions_response_schema(test_client, test_token):
    """
    Test that the response schema contains expected keys.

    This test checks that each item in the data returned by /vehicle_emissions
    includes the expected fields.
    """
    response = await test_client.get(f"/vehicle_emissions?token={test_token}")
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
async def test_get_vehicle_emissions_pagination(test_client, test_token):
    """
    Test pagination functionality of the /vehicle_emissions endpoint.

    This test verifies that the endpoint returns the correct number of results
    when using the limit and offset query parameters.
    """
    response_paginated = await test_client.get(
        f"/vehicle_emissions?limit=5&token={test_token}"
    )
    assert response_paginated.status_code == 200
    # Validate that the number of returned items does not exceed the limit
    assert len(response_paginated.json()["data"]) <= 5


@pytest.mark.asyncio
async def test_filter_by_vehicle_make(test_client, test_token):
    """
    Test filtering results by vehicle_make_name.

    This test verifies that the /vehicle_emissions endpoint filters results
    correctly when a specific vehicle make (e.g., Ferrari) is provided.
    """
    response_filtered_make = await test_client.get(
        f"/vehicle_emissions?vehicle_make_name=Ferrari&token={test_token}"
    )
    assert response_filtered_make.status_code == 200
    for item in response_filtered_make.json()["data"]:
        assert item["vehicle_make_name"] == "Ferrari"


@pytest.mark.asyncio
async def test_filter_by_year(test_client, test_token):
    """
    Test filtering results by year.

    This test verifies that the /vehicle_emissions endpoint correctly filters results
    when a specific year (e.g., 2010) is provided.
    """
    response_filtered_year = await test_client.get(
        f"/vehicle_emissions?" f"year=2010&token={test_token}"
    )
    assert response_filtered_year.status_code == 200
    for item in response_filtered_year.json()["data"]:
        assert item["year"] == 2010


@pytest.mark.asyncio
async def test_pagination_last_page(test_client, test_token):
    """
    Test pagination when reaching the last page of results.

    This test verifies that the pagination system correctly identifies when
    there are no additional pages.
    """
    response_last_page = await test_client.get(
        f"/vehicle_emissions?year=2010&vehicle_make_name=Ferrari&limit=100&token={test_token}"
    )
    # Assuming offset is set high enough to be the last page or return fewer than limit
    assert response_last_page.status_code == 200
    assert response_last_page.json()["next_cursor"] is None


@pytest.mark.asyncio
async def test_empty_result_with_non_existent_filter(test_client, test_token):
    """
    Test the response for non-existent filter values.

    This test verifies that when a non-existent vehicle make is provided,
    the response returns an empty list or equivalent.
    """
    response_non_existent = await test_client.get(
        f"/vehicle_emissions?vehicle_make_name=NonExistentMake&token={test_token}"
    )
    assert response_non_existent.status_code == 200
    # Assuming the API returns an empty list for no results found
    assert response_non_existent.json()["data"] == []


@pytest.mark.asyncio
async def test_next_cursor_type(test_client, test_token):
    """
    Test the next_cursor field type in the /vehicle_emissions response.

    This test checks that the next_cursor field, if present in the response,
    is of type string, indicating more pages are available.
    """
    response = await test_client.get(f"/vehicle_emissions?limit=1&token={test_token}")
    assert response.status_code == 200
    # Check if "next_cursor" is of type str
    assert isinstance(response.json()["next_cursor"], str)


@pytest.mark.asyncio
async def test_get_vehicle_makes(test_client, test_token):
    """
    Test the /vehicle_emissions/makes endpoint.
    Verifies that the endpoint returns a 200 status code and a list of vehicle makes.
    """
    response = await test_client.get(f"/vehicle_emissions/makes?token={test_token}")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)  # Assuming the response is a dict
    assert len(response.json()["makes"]) > 0  # Ensure the list is not empty


@pytest.mark.asyncio
async def test_get_vehicle_models(test_client, test_token):
    """
    Test the /vehicle_emissions/models endpoint.
    Verifies that the endpoint returns models for a valid make
    and responds correctly to invalid input.
    """
    valid_make = "Toyota"
    response = await test_client.get(
        f"/vehicle_emissions/models?" f"make={valid_make}&token={test_token}"
    )
    assert response.status_code == 200
    assert isinstance(response.json(), dict)  # Assuming the response is a dict
    assert len(response.json()) > 0  # Ensure the list is not empty

    # Test for an invalid make
    invalid_make = "NonExistentMake"
    response_invalid = await test_client.get(
        f"/vehicle_emissions/models?make={invalid_make}&token={test_token}"
    )
    assert response_invalid.status_code == 200
    assert (
        response_invalid.json()["models"] == []
    )  # Expect an empty list for invalid input


@pytest.mark.asyncio
async def test_get_vehicle_years(test_client, test_token):
    """
    Test the /vehicle_emissions/years endpoint.
    Verifies that the endpoint returns years for a valid make and model, and handles invalid input.
    """
    valid_make = "Toyota"
    valid_model = "Corolla"
    response = await test_client.get(
        f"/vehicle_emissions/years?make={valid_make}&model={valid_model}&token={test_token}"
    )
    assert response.status_code == 200
    assert isinstance(response.json(), dict)  # Assuming the response is a dict
    assert len(response.json()) > 0  # Ensure the list is not empty

    # Test for invalid make and model
    response_invalid = await test_client.get(
        f"/vehicle_emissions/years?make=InvalidMake&model=InvalidModel&token={test_token}"
    )
    assert response_invalid.status_code == 200
    assert (
        response_invalid.json()["years"] == []
    )  # Expect an empty list for invalid input


@pytest.mark.asyncio
async def test_get_compare_endpoint(test_client, test_token):
    """
    Test the GET /vehicle_emissions/compare endpoint.
    Verifies that the endpoint renders an HTML page.
    """
    response = await test_client.get(f"/vehicle_emissions/compare?token={test_token}")
    assert response.status_code == 200
    assert "text/html" in response.headers["Content-Type"]  # Verify HTML content


@pytest.mark.asyncio
async def test_post_compare_endpoint(test_client, test_token):
    """
    Test the POST /vehicle_emissions/compare endpoint.
    Verifies the comparison functionality with valid and invalid payloads.
    """
    valid_payload = {
        "vehicle_1": {"make": "Alfa Romeo", "model": "164", "year": 1994},
        "vehicle_2": {"make": "Ferrari", "model": "Testarossa", "year": 1985},
    }
    response = await test_client.post(
        f"/vehicle_emissions/compare?" f"token={test_token}", json=valid_payload
    )
    assert response.status_code == 200
    assert (
        "comparison" in response.json()
    )  # Assuming the response contains a "comparison" key

    invalid_payload = {
        "vehicle_1": {"make": "InvalidMake", "model": "InvalidModel", "year": 2020},
        "vehicle_2": {"make": "InvalidMake", "model": "InvalidModel", "year": 2020},
    }
    response_invalid = await test_client.post(
        f"/vehicle_emissions/compare?token={test_token}", json=invalid_payload
    )
    assert (
        response_invalid.status_code == 404
    )  # Assuming invalid payloads return a 404 error
