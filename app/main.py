"""
Main module for the CarbonCity Insights API.

This module initializes the FastAPI application and defines the root endpoint.
The API provides insights into city-level carbon emissions and energy consumption.

Attributes:
    app (FastAPI): The main application instance for CarbonCity Insights.
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import database
from app.routes import vehicle_routes

# Configure log directory
log_dir = os.path.abspath(os.path.join(__file__, "../../log"))
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Configure logger
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
    Lifespan context manager to manage database connection.

    This function handles the lifecycle events of the FastAPI app.
    It connects to the database when the app starts and disconnects when the app stops.

    :param _app: FastAPI application instance.
    """
    # Connect to the database at startup
    try:
        main_logger.info("Connecting to the database...")
        await database.connect()
        main_logger.info("Database connection established.")
        yield
    except Exception as e:
        main_logger.error("Error during startup: %s", e)
        raise
    # Disconnect from the database at shutdown
    finally:
        main_logger.info("Disconnecting from the database...")
        await database.disconnect()
        main_logger.info("Database connection closed.")


# Initialize FastAPI application with lifespan handler
app = FastAPI(lifespan=lifespan)

# Include the routes
app.include_router(vehicle_routes.router)
main_logger.info("Router for vehicle_routes included in the app.")

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
