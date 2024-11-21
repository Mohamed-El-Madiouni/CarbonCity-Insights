"""
Vehicle Emissions API Endpoint

This module provides an endpoint to retrieve vehicle emissions data from the database.
Supports optional filtering by vehicle make and year, with pagination.
"""

import logging
import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Query

from app.database import database

# Configure log directory
log_dir = os.path.abspath(os.path.join(__file__, "../../../log"))
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Configure logger
log_path = os.path.join(log_dir, "routes.log")
routes_logger = logging.getLogger("routes_logger")
routes_logger.setLevel(logging.INFO)

# File and console handlers for routes_logger
file_handler = logging.FileHandler(log_path)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
console_handler = logging.StreamHandler()

# Adding handlers to routes_logger
routes_logger.addHandler(file_handler)
routes_logger.addHandler(console_handler)

routes_logger.info("Vehicle Routes API initialized.")

# Load environment variables
load_dotenv()

# Determine the application environment
APP_ENV = os.getenv("APP_ENV", "production")

router = APIRouter()


@router.get("/vehicle_emissions/makes")
async def get_vehicle_makes():
    """
    Fetch unique vehicle makes from the database.

    :return: A list of all vehicle makes sorted alphabetically.
    """
    query = ("SELECT DISTINCT vehicle_make_name FROM vehicle_emissions "
             "ORDER BY vehicle_make_name ASC")
    makes = await database.fetch_all(query)
    return {"makes": [make["vehicle_make_name"] for make in makes]}


@router.get("/vehicle_emissions/models")
async def get_vehicle_models(make: str):
    """
    Fetch unique vehicle models for a given make.

    :param make: Vehicle make name (e.g., 'Toyota').
    :return: A list of vehicle models for the given make.
    """
    query = """
        SELECT DISTINCT vehicle_model_name 
        FROM vehicle_emissions 
        WHERE vehicle_make_name = :make 
        ORDER BY vehicle_model_name ASC
    """
    models = await database.fetch_all(query, values={"make": make})
    return {"models": [model["vehicle_model_name"] for model in models]}


@router.get("/vehicle_emissions")
async def get_vehicle_emissions(
    vehicle_make_name: Optional[str] = Query(
        None, description="Filter by vehicle make"
    ),
    year: Optional[int] = Query(None, description="Filter by vehicle model year"),
    cursor: Optional[str] = Query(
        None, description="ID of the last record from the previous page"
    ),
    limit: int = Query(10, le=100, description="Maximum number of results to retrieve"),
):
    """
    Retrieve vehicle emissions data with optional filters and pagination.

    :param vehicle_make_name: (str) Filter results by the vehicle make name.
    :param year: (int) Filter results by the vehicle model year.
    :param cursor: (str) ID of the last record from the previous page.
    :param limit: (int) Maximum number of results to retrieve per page (default is 10, max is 100).

    :return: List of vehicle emissions data with pagination metadata.
    """
    routes_logger.info(
        "Received request for vehicle emissions with filters - Make: %s, Year: %s, "
        "cursor: %s, Limit: %d",
        vehicle_make_name,
        year,
        cursor,
        limit,
    )

    # Base query
    if APP_ENV == "production":
        base_query = "SELECT * FROM vehicle_emissions"
    else:
        schema_name = f"test_schema_{os.getpid()}"
        base_query = f"SELECT * FROM {schema_name}.vehicle_emissions"
    conditions = []
    values = {"limit": limit}

    # Add filters conditionally
    if vehicle_make_name:
        conditions.append("vehicle_make_name = :vehicle_make_name")
        values["vehicle_make_name"] = vehicle_make_name
        routes_logger.debug("Filter applied for vehicle make: %s", vehicle_make_name)
    if year:
        conditions.append("year = :year")
        values["year"] = year
        routes_logger.debug("Filter applied for year: %d", year)

    # Add cursor-based pagination condition
    if cursor:
        conditions.append("id > :cursor")
        values["cursor"] = cursor

    # Combine base query with conditions if any
    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    # Order by ID for consistent cursor behavior and apply limit
    base_query += " ORDER BY id ASC LIMIT :limit"
    values["limit"] = limit + 1
    routes_logger.debug("Executing query: %s with values %s", base_query, values)

    # Execute query
    results = await database.fetch_all(query=base_query, values=values)
    routes_logger.info(
        "Query executed successfully. Number of results: %d", len(results) - 1
    )

    # Set next cursor to the last item's ID in the current result set if results exist
    if len(results) == limit + 1:
        next_cursor = results[-2]["id"]
        results = results[:-1]
    else:
        next_cursor = None

    # Ensure a 200 response with an empty list if no data is found
    return (
        {"data": results, "next_cursor": next_cursor}
        if results
        else {"data": [], "next_cursor": None}
    )
