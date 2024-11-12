"""
Main module for the CarbonCity Insights API.

This module initializes the FastAPI application and defines the root endpoint.
The API provides insights into city-level carbon emissions and energy consumption.

Attributes:
    app (FastAPI): The main application instance for CarbonCity Insights.
"""

import os
from contextlib import asynccontextmanager

from databases import Database
from dotenv import load_dotenv
from fastapi import FastAPI

# Load environment variables from .env file in local development
load_dotenv()

# Database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")
database = Database(DATABASE_URL)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Lifespan context manager to manage database connection.

    This function handles the lifecycle events of the FastAPI app.
    It connects to the database when the app starts and disconnects when the app stops.

    :param _app: FastAPI application instance.
    """
    # Connect to the database at startup
    await database.connect()
    yield
    # Disconnect from the database at shutdown
    await database.disconnect()


# Initialize FastAPI application with lifespan handler
app = FastAPI(lifespan=lifespan)


# Root endpoint
@app.get("/")
async def read_root():
    """
    Root endpoint of the CarbonCity Insights API.

    :returns:
        A dictionary with a welcome message indicating the API is active.
    """
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
    query = "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
    tables = await database.fetch_all(query)
    table_names = [table["table_name"] for table in tables]
    return {"tables": table_names}
