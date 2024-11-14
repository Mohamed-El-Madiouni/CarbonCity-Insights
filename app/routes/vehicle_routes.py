"""
Vehicle Emissions API Endpoint

This module provides an endpoint to retrieve vehicle emissions data from the database.
Supports optional filtering by vehicle make and year, with pagination.
"""

from typing import Optional

from fastapi import APIRouter, Query

from app.database import database

router = APIRouter()


@router.get("/vehicle_emissions")
async def get_vehicle_emissions(
    vehicle_make_name: Optional[str] = Query(
        None, description="Filter by vehicle make"
    ),
    year: Optional[int] = Query(None, description="Filter by vehicle model year"),
    limit: int = Query(10, description="Number of results per page", gt=0),
    offset: int = Query(
        0, description="Number of results to skip for pagination", ge=0
    ),
):
    """
    Retrieve vehicle emissions data with optional filters and pagination.

    :param vehicle_make_name: (str) Filter results by the vehicle make name.
    :param year: (int) Filter results by the vehicle model year.
    :param limit: (int) Limit the number of results returned.
    :param offset: (int) Skip a number of results for pagination.

    :return: List of dictionaries containing vehicle emissions data.
    """
    # Base query
    base_query = "SELECT * FROM vehicle_emissions"
    conditions = []
    values = {"limit": limit, "offset": offset}

    # Add filters conditionally
    if vehicle_make_name:
        conditions.append("vehicle_make_name = :vehicle_make_name")
        values["vehicle_make_name"] = vehicle_make_name
    if year:
        conditions.append("year = :year")
        values["year"] = year

    # Combine base query with conditions if any
    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    # Add limit and offset
    base_query += " LIMIT :limit OFFSET :offset"

    # Execute query
    results = await database.fetch_all(query=base_query, values=values)

    # Ensure a 200 response with an empty list if no data is found
    return results if results else []
