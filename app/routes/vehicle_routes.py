"""
Vehicle Emissions API Endpoint

This module provides endpoints for user authentication and vehicle emissions data.
It includes functionalities for registering and logging in users, as well as
retrieving, filtering, and comparing vehicle emissions data.

Endpoints:
- User registration and login.
- Protected endpoints requiring authentication.
- Retrieval of vehicle makes, models, and years.
- Comparison of vehicle emissions.
"""

import logging
import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel

from app.database import database
from app.redis_cache import redis_cache
from app.utils import create_access_token, decode_access_token, serialize_data

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

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserCreate(BaseModel):
    """
    Schema for user registration payload.

    Attributes:
        username (str): The username of the user.
        email (str): The email address of the user.
        password (str): The password of the user.
    """

    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    """
    Schema for user login payload.

    Attributes:
        username (str): The username of the user.
        password (str): The password of the user.
    """

    username: str
    password: str


@router.post("/register")
async def register_user(user: UserCreate):
    """
    Register a new user in the system.

    Args:
        user (UserCreate): The user registration data.

    Returns:
        dict: Success message.
    """
    query = "SELECT * FROM users WHERE username = :username OR email = :email"
    existing_user = await database.fetch_one(
        query, values={"username": user.username, "email": user.email}
    )
    if existing_user:
        routes_logger.info("Username or email already registered")
        raise HTTPException(
            status_code=400, detail="Username or email already registered"
        )

    hashed_password = pwd_context.hash(user.password)
    query = (
        "INSERT INTO users (username, email, hashed_password) VALUES "
        "(:username, :email, :hashed_password)"
    )
    await database.execute(
        query,
        values={
            "username": user.username,
            "email": user.email,
            "hashed_password": hashed_password,
        },
    )
    routes_logger.info("User registered successfully")
    return {"message": "User registered successfully"}


@router.post("/login")
async def login_user(user: UserLogin):
    """
    Authenticate a user and generate a JWT token.

    Args:
        user (UserLogin): The user login data.

    Returns:
        dict: A JWT access token and token type.
    """
    query = "SELECT * FROM users WHERE username = :username"
    db_user = await database.fetch_one(query, values={"username": user.username})
    if not db_user or not pwd_context.verify(user.password, db_user["hashed_password"]):
        routes_logger.info("Invalid credentials")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create a JWT token
    access_token = create_access_token(data={"sub": db_user["username"]})
    routes_logger.info("Valid login credentials")
    return {"access_token": access_token, "token_type": "bearer"}


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Validate and decode the current user's token.

    Args:
        token (str): The JWT token from the request.

    Returns:
        str: The username of the authenticated user.
    """
    payload = decode_access_token(token)
    if not payload:
        routes_logger.info("Invalid or expired token")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    routes_logger.info("Valid token")
    return payload["sub"]


@router.get("/protected-endpoint")
async def protected_endpoint(token: Optional[str] = None):
    """
    A protected endpoint that validates a token passed via URL.

    Args:
        token (Optional[str]): The token passed as a query parameter.

    Returns:
        dict: A greeting message with the username.
    """
    if token:
        routes_logger.info("Token provided by URL")
        payload = decode_access_token(token)
        if not payload:
            routes_logger.info("Invalid or expired token")
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        routes_logger.info("Valid token, user %s", {payload["sub"]})
        return {"message": f"Hello, {payload['sub']}"}

    routes_logger.info("Not authenticated, No token provided")
    raise HTTPException(status_code=401, detail="Not authenticated, No token provided")


@router.get(
    "/vehicle_emissions/makes",
    summary="Get vehicle makes",
    description="Retrieve a list of all available vehicle manufacturers.",
    tags=["Vehicle Emissions"],
)
async def get_vehicle_makes():
    """
    Fetch unique vehicle makes from the database.

    :return: A list of all vehicle makes sorted alphabetically.
    """
    routes_logger.info("GET /vehicle_emissions/makes called")

    cache_key = "vehicle_makes"
    cached_data = await redis_cache.get(cache_key)
    if cached_data:
        routes_logger.info("Cache hit for vehicle makes")
        return {"makes": cached_data}
    routes_logger.info("Cache miss for vehicle makes. Fetching from database.")

    query = (
        "SELECT DISTINCT vehicle_make_name FROM vehicle_emissions "
        "ORDER BY vehicle_make_name ASC"
    )
    try:
        makes = await database.fetch_all(query)
        makes_list = [make["vehicle_make_name"] for make in makes]
        routes_logger.info(
            "Query executed successfully. Number of makes: %d", len(makes)
        )
        await redis_cache.set(cache_key, makes_list)
        return {"makes": makes_list}
    except Exception as e:
        routes_logger.error("Failed to retrieve vehicle makes: %s", e)
        raise HTTPException(status_code=404, detail="Vehicle Makes Not Found") from e


@router.get(
    "/vehicle_emissions/models",
    summary="Get vehicle models",
    description="Retrieve the list of models for a specific manufacturer.",
    tags=["Vehicle Emissions"],
)
async def get_vehicle_models(
    make: str = Query(..., description="The manufacturer name (e.g., 'Ferrari').")
):
    """
    Fetch unique vehicle models for a given make.

    :param make: Vehicle make name (e.g., 'Ferrari').
    :return: A list of vehicle models for the given make.
    """
    routes_logger.info("GET /vehicle_emissions/models called with make: %s", make)

    cache_key = f"vehicle_models_{make}"
    cached_data = await redis_cache.get(cache_key)
    if cached_data:
        routes_logger.info("Cache hit for vehicle models")
        return {"models": cached_data}
    routes_logger.info("Cache miss for vehicle models. Fetching from database.")

    query = """
        SELECT DISTINCT vehicle_model_name 
        FROM vehicle_emissions 
        WHERE vehicle_make_name = :make 
        ORDER BY vehicle_model_name ASC
    """
    try:
        models = await database.fetch_all(query, values={"make": make})
        models_list = [model["vehicle_model_name"] for model in models]
        routes_logger.info(
            "Query executed successfully. Number of models: %d", len(models)
        )
        await redis_cache.set(cache_key, models_list)
        return {"models": models_list}
    except Exception as e:
        routes_logger.error(
            "Failed to retrieve vehicle models for make %s: %s", make, e
        )
        raise HTTPException(status_code=404, detail="Vehicle Models Not Found") from e


@router.get(
    "/vehicle_emissions/years",
    summary="Get vehicle years",
    description="Retrieve the available years for a specific vehicle make and model.",
    tags=["Vehicle Emissions"],
)
async def get_vehicle_years(
    make: str = Query(..., description="The manufacturer name (e.g., 'Ferrari')."),
    model: str = Query(..., description="The vehicle model name (e.g., 'F40')."),
):
    """
    Fetch unique years for a given make and model.

    :param make: Vehicle make name.
    :param model: Vehicle model name.
    :return: A list of years for the given make and model.
    """
    routes_logger.info(
        "GET /vehicle_emissions/years called with make: %s, model: %s", make, model
    )

    cache_key = f"vehicle_years_{make}_{model}"
    cached_data = await redis_cache.get(cache_key)
    if cached_data:
        routes_logger.info("Cache hit for vehicle years")
        return {"years": cached_data}
    routes_logger.info("Cache miss for vehicle years. Fetching from database.")

    query = """
        SELECT DISTINCT year
        FROM vehicle_emissions
        WHERE vehicle_make_name = :make AND vehicle_model_name = :model
        ORDER BY year ASC
    """
    try:
        years = await database.fetch_all(query, values={"make": make, "model": model})
        years_list = [year["year"] for year in years]
        routes_logger.info(
            "Query executed successfully. Number of years: %d", len(years)
        )
        await redis_cache.set(cache_key, years_list)
        return {"years": years_list}
    except Exception as e:
        routes_logger.error(
            "Failed to retrieve years for make %s and model %s: %s", make, model, e
        )
        raise HTTPException(status_code=404, detail="Vehicle Years Not Found") from e


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

    cache_key = (
        f"vehicle_emissions_{vehicle_make_name or 'all'}_{year or 'all'}_"
        f"{cursor or 'start'}_{limit}"
    )
    cached_data = await redis_cache.get(cache_key)
    if cached_data:
        routes_logger.info("Cache hit for vehicle emissions")
        return {"emissions": cached_data}
    routes_logger.info("Cache miss for vehicle emissions. Fetching from database.")

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

    results_serializable = [dict(record) for record in results]

    # Serialize the data (handle UUIDs and other non-serializable types)
    results_serializable = serialize_data(results_serializable)
    routes_logger.debug("Serialized data before caching: %s", results_serializable)

    if results_serializable:
        response = {"data": results_serializable, "next_cursor": next_cursor}
    else:
        response = {"data": [], "next_cursor": None}

    await redis_cache.set(cache_key, response)

    # Ensure a 200 response with an empty list if no data is found
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
async def get_compare_page():
    """
    Endpoint to serve the interactive comparison page.
    """
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
