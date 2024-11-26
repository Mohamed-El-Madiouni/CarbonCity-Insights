"""
Vehicle Emissions API Endpoint

This module provides endpoints for vehicle emissions data.
It includes functionalities for retrieving, filtering, and comparing vehicle emissions data.

Endpoints:
- Retrieval of vehicle makes, models, and years.
- Comparison of vehicle emissions.
"""

import logging
import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.database import database
from app.redis_cache import redis_cache
from app.utils import decode_access_token, serialize_data

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


@router.get(
    "/vehicle_emissions/makes",
    summary="Get vehicle makes",
    description="Retrieve a list of all available vehicle manufacturers.",
    tags=["Vehicle Emissions"],
)
async def get_vehicle_makes(token: Optional[str] = None):
    """
    Fetch unique vehicle makes from the database.

    :return: A list of all vehicle makes sorted alphabetically.
    """
    payload = await validate_token(token)
    routes_logger.info(
        "GET /vehicle_emissions/makes called for user %s", payload["sub"]
    )

    cache_key = "vehicle_makes"
    query = """
            SELECT DISTINCT vehicle_make_name
            FROM vehicle_emissions
            ORDER BY vehicle_make_name ASC
        """
    return await fetch_and_cache(cache_key, query, result_key="makes")


@router.get(
    "/vehicle_emissions/models",
    summary="Get vehicle models",
    description="Retrieve the list of models for a specific manufacturer.",
    tags=["Vehicle Emissions"],
)
async def get_vehicle_models(
    make: str = Query(..., description="The manufacturer name (e.g., 'Ferrari')."),
    token: Optional[str] = None,
):
    """
    Fetch unique vehicle models for a given make.

    :param make: Vehicle make name (e.g., 'Ferrari').
    :return: A list of vehicle models for the given make.
    """
    payload = await validate_token(token)
    routes_logger.info(
        "GET /vehicle_emissions/models called for user %s with make %s",
        payload["sub"],
        make,
    )

    cache_key = f"vehicle_models_{make}"
    query = """
            SELECT DISTINCT vehicle_model_name
            FROM vehicle_emissions
            WHERE vehicle_make_name = :make
            ORDER BY vehicle_model_name ASC
        """
    return await fetch_and_cache(
        cache_key, query, db_params={"make": make}, result_key="models"
    )


@router.get(
    "/vehicle_emissions/years",
    summary="Get vehicle years",
    description="Retrieve the available years for a specific vehicle make and model.",
    tags=["Vehicle Emissions"],
)
async def get_vehicle_years(
    make: str = Query(..., description="The manufacturer name (e.g., 'Ferrari')."),
    model: str = Query(..., description="The vehicle model name (e.g., 'F40')."),
    token: Optional[str] = None,
):
    """
    Fetch unique years for a given make and model.

    :param make: Vehicle make name.
    :param model: Vehicle model name.
    :return: A list of years for the given make and model.
    """
    payload = await validate_token(token)
    routes_logger.info(
        "GET /vehicle_emissions/years called for user %s with make %s, model %s",
        payload["sub"],
        make,
        model,
    )

    cache_key = f"vehicle_years_{make}_{model}"
    query = """
            SELECT DISTINCT year
            FROM vehicle_emissions
            WHERE vehicle_make_name = :make AND vehicle_model_name = :model
            ORDER BY year ASC
        """
    return await fetch_and_cache(
        cache_key, query, db_params={"make": make, "model": model}, result_key="years"
    )


@router.get(
    "/vehicle_emissions",
    summary="Get vehicle emissions data",
    description="Retrieve vehicle emissions "
    "data with optional filters and cursor-based pagination.",
    tags=["Vehicle Emissions"],
)
async def get_vehicle_emissions(
    vehicle_make_name: Optional[str] = Query(
        None, description="Filter by vehicle make"
    ),
    year: Optional[int] = Query(None, description="Filter by vehicle model year"),
    cursor: Optional[str] = Query(
        None, description="ID of the last record from the previous page"
    ),
    limit: int = Query(10, le=100, description="Maximum number of results to retrieve"),
    token: Optional[str] = None,
):
    """
    Retrieve vehicle emissions data with optional filters and pagination.
    """
    if not token:
        routes_logger.info("Not authenticated, No token provided")
        raise HTTPException(
            status_code=401, detail="Not authenticated, No token provided"
        )

    # Validate token
    payload = await validate_token(token)
    routes_logger.info("Valid token, user %s", {payload["sub"]})

    # Log request details
    log_request_details(vehicle_make_name, year, cursor, limit)

    # Fetch from cache if available
    cache_key = generate_cache_key(vehicle_make_name, year, cursor, limit)
    cached_response = await fetch_from_cache(cache_key)
    if cached_response:
        return cached_response

    # Build and execute query
    base_query, values = build_query(vehicle_make_name, year, cursor, limit)
    results, next_cursor = await execute_query(base_query, values)

    # Serialize results and cache the response
    response = await prepare_response(results, next_cursor, cache_key)
    return response


async def validate_token(token: str):
    """
    Validate the provided token.
    """
    routes_logger.info("Token provided by URL")
    payload = decode_access_token(token)
    if not payload:
        routes_logger.info("Invalid or expired token")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


def log_request_details(vehicle_make_name, year, cursor, limit):
    """
    Log details about the incoming request.
    """
    routes_logger.info(
        "Received request for vehicle emissions with filters - Make: %s, Year: %s, "
        "cursor: %s, Limit: %d",
        vehicle_make_name,
        year,
        cursor,
        limit,
    )


def generate_cache_key(vehicle_make_name, year, cursor, limit):
    """
    Generate a unique cache key based on the query parameters.
    """
    return (
        f"vehicle_emissions_{vehicle_make_name or 'all'}_{year or 'all'}_"
        f"{cursor or 'start'}_{limit}"
    )


async def fetch_from_cache(cache_key):
    """
    Fetch cached data if available.
    """
    cached_data = await redis_cache.get(cache_key)
    if cached_data:
        routes_logger.info("Cache hit for vehicle emissions")
        return cached_data
    routes_logger.info("Cache miss for vehicle emissions. Fetching from database.")
    return None


def build_query(vehicle_make_name, year, cursor, limit):
    """
    Build the database query and its parameters.
    """
    if APP_ENV == "production":
        base_query = "SELECT * FROM vehicle_emissions"
    else:
        schema_name = f"test_schema_{os.getpid()}"
        base_query = f"SELECT * FROM {schema_name}.vehicle_emissions"

    conditions = []
    values = {"limit": limit + 1}

    if vehicle_make_name:
        conditions.append("vehicle_make_name = :vehicle_make_name")
        values["vehicle_make_name"] = vehicle_make_name
        routes_logger.debug("Filter applied for vehicle make: %s", vehicle_make_name)
    if year:
        conditions.append("year = :year")
        values["year"] = year
        routes_logger.debug("Filter applied for year: %d", year)
    if cursor:
        conditions.append("id > :cursor")
        values["cursor"] = cursor

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    base_query += " ORDER BY id ASC LIMIT :limit"
    return base_query, values


async def execute_query(base_query, values):
    """
    Execute the database query and return results along with the next cursor.
    """
    routes_logger.debug("Executing query: %s with values %s", base_query, values)
    results = await database.fetch_all(query=base_query, values=values)
    routes_logger.info(
        "Query executed successfully. Number of results: %d", len(results)
    )

    if len(results) > values["limit"] - 1:
        next_cursor = results[-2]["id"]
        results = results[:-1]
    else:
        next_cursor = None

    return results, next_cursor


async def prepare_response(results, next_cursor, cache_key):
    """
    Serialize results, prepare the response, and cache it.
    """
    results_serializable = [dict(record) for record in results]
    results_serializable = serialize_data(results_serializable)
    routes_logger.debug("Serialized data before caching: %s", results_serializable)

    response = {"data": results_serializable, "next_cursor": next_cursor}
    await redis_cache.set(cache_key, response)
    return response


class CompareRequest(BaseModel):
    """
    Data model for vehicle comparison requests.

    Attributes:
        vehicle_1: Details of the first vehicle, including make, model, and year.
        vehicle_2: Details of the second vehicle, including make, model, and year.
    """

    vehicle_1: dict
    vehicle_2: dict


@router.post(
    "/vehicle_emissions/compare",
    summary="Compare two vehicles",
    description="Compare carbon emissions between two vehicles using their make, model, and year.",
    tags=["Vehicle Emissions"],
)
async def compare_vehicles(request: CompareRequest):
    """
    Compare carbon emissions between two vehicles.

    :param request: A JSON payload containing details of the two vehicles to compare.
    :return: Comparison results, including a percentage difference and a summary message.
    """
    routes_logger.info("POST /vehicle_emissions/compare called")
    query = """
        SELECT vehicle_make_name, vehicle_model_name, year, carbon_emission_g
        FROM vehicle_emissions
        WHERE vehicle_make_name = :make AND vehicle_model_name = :model AND year = :year
    """
    # Convert year fields to integers
    try:
        request.vehicle_1["year"] = int(request.vehicle_1["year"])
        request.vehicle_2["year"] = int(request.vehicle_2["year"])
    except ValueError as e:
        routes_logger.error("Year must be a valid integer.")
        raise HTTPException(
            status_code=400, detail="Year must be a valid integer."
        ) from e

    # Fetch details for vehicle 1
    try:
        vehicle_1 = await database.fetch_one(query, values=request.vehicle_1)
        if not vehicle_1:
            routes_logger.error("Vehicle 1 not found.")
            raise HTTPException(status_code=404, detail="Vehicle 1 not found.")

        # Fetch details for vehicle 2
        vehicle_2 = await database.fetch_one(query, values=request.vehicle_2)
        if not vehicle_2:
            routes_logger.error("Vehicle 2 not found.")
            raise HTTPException(status_code=404, detail="Vehicle 2 not found.")

        # Calculate percentage difference
        emissions_1 = vehicle_1["carbon_emission_g"]
        emissions_2 = vehicle_2["carbon_emission_g"]
        if emissions_2 == 0:
            routes_logger.error("Vehicle 2 emissions data invalid.")
            raise HTTPException(
                status_code=400, detail="Vehicle 2 emissions data invalid."
            )

        percentage_difference = round(
            ((emissions_1 - emissions_2) / abs(emissions_2)) * 100, 2
        )
        # Construct a summary message
        message = (
            f"{vehicle_1['vehicle_make_name']} {vehicle_1['vehicle_model_name']} "
            f"({vehicle_1['year']}) consumption : {vehicle_1['carbon_emission_g']} g/100km.<br><br>"
            f"{vehicle_2['vehicle_make_name']} {vehicle_2['vehicle_model_name']} "
            f"({vehicle_2['year']}) consumption : {vehicle_2['carbon_emission_g']} g/100km.<br><br>"
            f"So the {vehicle_1['vehicle_make_name']} {vehicle_1['vehicle_model_name']} "
            f"({vehicle_1['year']}) emits {abs(percentage_difference)}% "
            f"{'more' if emissions_1 > emissions_2 else 'less'} carbon compared "
            f"to the {vehicle_2['vehicle_make_name']} {vehicle_2['vehicle_model_name']} "
            f"({vehicle_2['year']})."
        )
        routes_logger.info("Comparison calculated successfully")

        return {
            "vehicle_1": vehicle_1,
            "vehicle_2": vehicle_2,
            "comparison": {
                "message": message,
                "percentage_difference": abs(percentage_difference),
            },
        }
    except Exception as e:
        routes_logger.error("Error in vehicle comparison: %s", e)
        raise HTTPException(status_code=404, detail="Not Found") from e


@router.get(
    "/vehicle_emissions/compare",
    summary="Get comparison page",
    description="Serve an interactive HTML page to compare two vehicles.",
    response_class=HTMLResponse,
    tags=["Vehicle Emissions"],
)
async def get_compare_page(token: Optional[str] = None):
    """
    Endpoint to serve the interactive comparison page.
    """
    if token:
        routes_logger.info("Token provided by URL")
        payload = decode_access_token(token)
        if not payload:
            routes_logger.info("Invalid or expired token")
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        routes_logger.info("GET /vehicle_emissions/compare called")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        index_path = os.path.join(current_dir, "../static/index.html")
        try:
            with open(index_path, "r", encoding="utf-8") as file:
                html_content = file.read()
            return HTMLResponse(content=html_content)
        except FileNotFoundError as e:
            routes_logger.error("Error: index.html not found: %s", e)
            return HTMLResponse(content="Error: index.html not found", status_code=404)
    routes_logger.info("Not authenticated, No token provided")
    raise HTTPException(status_code=401, detail="Not authenticated, No token provided")


async def set_cache(cache_key: str, data):
    """
    Set data in cache.
    """
    await redis_cache.set(cache_key, data)
    routes_logger.info("Cache updated for %s", cache_key)


async def fetch_data_from_db(query: str, values: Optional[dict] = None):
    """
    Execute a database query and return the results.
    """
    try:
        results = await database.fetch_all(query, values=values or {})
        routes_logger.info(
            "Query executed successfully. Number of results: %d", len(results)
        )
        return results
    except Exception as e:
        routes_logger.error("Database query failed: %s", e)
        raise HTTPException(status_code=500, detail="Database Error") from e


async def fetch_and_cache(
    cache_key: str,
    query: str,
    db_params: Optional[dict] = None,
    result_key: str = "results",
):
    """
    Fetch data from cache or database and update the cache if needed.
    :param cache_key: The key to look up in cache.
    :param query: The SQL query to execute if the cache is empty.
    :param db_params: Parameters for the SQL query.
    :param cache_key_prefix: Prefix for cache keys.
    :param result_key: Key for the results in the response.
    :return: Data retrieved from cache or database.
    """
    cached_data = await fetch_from_cache(cache_key)
    if cached_data:
        return {result_key: cached_data}

    # Fetch from database if not cached
    results = await fetch_data_from_db(query, values=db_params)
    result_list = [record[next(iter(record))] for record in results]

    # Update cache
    await set_cache(cache_key, result_list)
    return {result_key: result_list}
