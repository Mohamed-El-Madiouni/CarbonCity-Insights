"""
Main module for the CarbonCity Insights API.

This module initializes the FastAPI application and defines the root endpoint.
The API provides insights into city-level carbon emissions and energy consumption.

Attributes:
    app (FastAPI): The main application instance for CarbonCity Insights.
"""

import logging
import os
import time
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import database
from app.redis_cache import redis_cache
from app.routes import vehicle_routes
from app.routes import auth_routes

# Configure log directory
log_dir = os.path.abspath(os.path.join(__file__, "../../log"))
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Configure main logger
log_path = os.path.join(log_dir, "app.log")
main_logger = logging.getLogger("main_logger")
main_logger.setLevel(logging.INFO)

# File and console handlers for main_logger
file_handler = logging.FileHandler(log_path)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
console_handler = logging.StreamHandler()

# Adding handlers to main_logger
main_logger.addHandler(file_handler)
main_logger.addHandler(console_handler)

# Configure middleware logger
log_path2 = os.path.join(log_dir, "middleware.log")
middleware_logger = logging.getLogger("middleware_logger")
middleware_logger.setLevel(logging.INFO)

# File and console handlers for middleware_logger
file_handler = logging.FileHandler(log_path2)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
console_handler = logging.StreamHandler()

# Adding handlers to middleware_logger
middleware_logger.addHandler(file_handler)
middleware_logger.addHandler(logging.StreamHandler())

main_logger.info("Starting CarbonCity Insights API...")

# Load environment variables
load_dotenv()

# Determine the application environment
APP_ENV = os.getenv("APP_ENV", "production")

if APP_ENV not in {"production", "test"}:
    main_logger.error("Invalid APP_ENV: %s. Must be 'production', or 'test'.", APP_ENV)

main_logger.info("APP_ENV: %s", APP_ENV)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Lifespan context manager to manage the lifecycle events.

    This function handles the lifecycle events of the FastAPI app.
    It connects to the database and Redis cache when the app starts
    and disconnects when the app stops.

    :param _app: FastAPI application instance.
    """
    try:
        # Connect to the database
        main_logger.info("Connecting to the database...")
        await database.connect()
        main_logger.info("Database connection established.")

        # Connect to Redis
        main_logger.info("Connecting to Redis...")
        await redis_cache.connect()
        main_logger.info("Redis connection established.")

        yield
    except Exception as e:
        main_logger.error("Error during startup: %s", e)
        raise
    finally:
        # Disconnect from the database
        main_logger.info("Disconnecting from the database...")
        await database.disconnect()
        main_logger.info("Database connection closed.")

        # Disconnect from Redis
        main_logger.info("Disconnecting from Redis...")
        await redis_cache.close()
        main_logger.info("Redis connection closed.")


# Initialize FastAPI application with lifespan handler
app = FastAPI(
    title="CarbonCity Insights API",
    description="An API providing vehicle emissions data and comparison features.",
    version="1.0.0",
    lifespan=lifespan,
)

# Include the routes
app.include_router(vehicle_routes.router)
main_logger.info("Router for vehicle_routes included in the app.")
app.include_router(auth_routes.auth_router)
main_logger.info("Router for auth_routes included in the app.")

# Serve static files from the "static" directory
current_dir = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(current_dir, "static")

app.mount(path, StaticFiles(directory=path), name="static")

# Configure CORS
origins = ["*"]  # Allows all origins (includes file://)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure middleware logger
middleware_logger = logging.getLogger("middleware_logger")
middleware_logger.setLevel(logging.INFO)


# Middleware for response time
class TimingMiddleware(BaseHTTPMiddleware):  # pylint: disable=too-few-public-methods
    """
    Middleware to measure and log the time taken to process each request.
    Adds the 'X-Process-Time' header to the response.
    """

    async def dispatch(self, request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        middleware_logger.info(
            "Request: %s %s completed in %.2f seconds",
            request.method,
            request.url,
            process_time,
        )
        response.headers["X-Process-Time"] = f"{process_time:.2f}"
        return response


# Add middleware to the application
app.add_middleware(TimingMiddleware)


# Root endpoint
@app.get("/")
async def read_root():
    """
    Root endpoint of the CarbonCity Insights API.

    :returns:
        A dictionary with a welcome message indicating the API is active.
    """
    main_logger.info("Received request on root endpoint.")
    return {"message": "Welcome to CarbonCity Insights API!"}


# Test database connection endpoint
@app.get("/db_test")
async def db_test():
    """
    Test endpoint to check the presence of tables in the database.

    This endpoint queries the database for existing tables in the public schema
    and returns a list of table names, confirming successful database connection.

    :returns:
        A dictionary with a list of table names in the public schema.
    """
    query = (
        "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
    )
    try:
        main_logger.info("Executing query to fetch table names.")
        tables = await database.fetch_all(query)
        table_names = [table["table_name"] for table in tables]
        main_logger.info("Successfully retrieved table names: %s", table_names)
        return {"tables": table_names}
    except Exception as e:
        main_logger.error("Failed to retrieve table names: %s", e)
        raise HTTPException(status_code=500, detail=f"Database query failed.{e}") from e
