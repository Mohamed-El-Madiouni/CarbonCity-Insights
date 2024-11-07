"""
Main module for the CarbonCity Insights API.

This module initializes the FastAPI application and defines the root endpoint.
The API provides insights into city-level carbon emissions and energy consumption.

Attributes:
    app (FastAPI): The main application instance for CarbonCity Insights.
"""

from fastapi import FastAPI

# Initialize FastAPI application
app = FastAPI()


# Root endpoint
@app.get("/")
def read_root():
    """
    Root endpoint of the CarbonCity Insights API.

    :returns:
        A dictionary with a welcome message indicating the API is active.
    """
    # Returning a welcome message for the root endpoint
    return {"message": "Welcome to CarbonCity Insights API!"}
