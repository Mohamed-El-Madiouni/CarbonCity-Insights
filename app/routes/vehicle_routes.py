"""
Routes for Vehicle Emissions Data

This module provides API endpoints to access vehicle emissions data.
"""

from fastapi import APIRouter, HTTPException
from app.database import database

router = APIRouter()


@router.get("/vehicle_emissions")
async def get_vehicle_emissions():
    """
    Retrieve all vehicle emissions records from the database.

    :return: List of vehicle emissions data
    """
    query = "SELECT * FROM vehicle_emissions"
    results = await database.fetch_all(query=query)

    if not results:
        raise HTTPException(status_code=404, detail="No vehicle emissions data found.")

    return results
