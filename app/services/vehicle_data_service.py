"""
Vehicle Data Service for CarbonCity Insights

This module provides functions to fetch vehicle data from the Carbon Interface API,
compute carbon emissions for specific trips, and store the results in PostgreSQL,
ensuring no duplicate entries.
"""

import os
import smtplib
import uuid
from email.message import EmailMessage

import requests
from databases import Database
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
CARBON_INTERFACE_API_KEY = os.getenv("CARBON_INTERFACE_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL")  # Email for notifications
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  # SMTP password for email notifications

# Database connection
database = Database(DATABASE_URL)

# Set up headers for API requests
HEADERS = {
    "Authorization": f"Bearer {CARBON_INTERFACE_API_KEY}",
    "Content-Type": "application/json",
}


def send_notification(subject, body):
    """
    Send a notification email with the specified subject and body.

    :param subject: str, subject of the email
    :param body: str, body content of the email
    """
    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = NOTIFICATION_EMAIL
    msg["To"] = NOTIFICATION_EMAIL

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(NOTIFICATION_EMAIL, EMAIL_PASSWORD)
        smtp.send_message(msg)


async def fetch_vehicle_makes():
    """
    Fetch all vehicle makes from the Carbon Interface API.

    :returns: list of dict: A list containing vehicle make data, each with 'id' and 'name'.
    """
    url = "https://www.carboninterface.com/api/v1/vehicle_makes"
    response = requests.get(url, headers=HEADERS, timeout=60)

    if response.status_code == 200:
        return response.json()
    print(
        f"Failed to fetch vehicle makes. Status: {response.status_code}, "
        f"Message: {response.text}"
    )
    return []


async def fetch_and_store_vehicle_emissions():
    """
    Fetch vehicle models, compute emissions estimates, and store them in the PostgreSQL database.
    Ensures no duplicate entries based on 'year', 'vehicle_model_name', and 'vehicle_make_name'.
    """
    await database.connect()
    vehicle_makes = await fetch_vehicle_makes()

    for vehicle_make in vehicle_makes:
        make_id = vehicle_make["data"]["id"]
        make_name = vehicle_make["data"]["attributes"]["name"]
        print(f"Fetching models for make: {make_name}")

        vehicle_models = await fetch_vehicle_models(make_id)
        if vehicle_models:
            for model in vehicle_models:
                model_id = model["data"]["id"]
                model_name = model["data"]["attributes"]["name"]
                year = model["data"]["attributes"].get("year")

                if not await check_duplicate_entry(year, model_name, make_name):
                    estimate_data = await fetch_emission_estimate(model_id)
                    if estimate_data:
                        await insert_vehicle_emission_record(
                            model_id, make_name, model_name, year, estimate_data
                        )
                        print(
                            f"Inserted emission estimate for model: "
                            f"{model_name} ({year}) for make: {make_name}"
                        )
                    else:
                        print(
                            f"Failed to fetch emission estimate for model {model_name}."
                        )
                else:
                    print(
                        f"Duplicate model skipped: {model_name} ({year}) for make: {make_name}"
                    )

    await database.disconnect()
    print(
        "All vehicle models have been fetched, emissions estimated, and stored successfully."
    )


async def fetch_vehicle_models(make_id):
    """
    Fetch all vehicle models for a given make ID from the Carbon Interface API.
    """
    models_url = (
        f"https://www.carboninterface.com/api/v1/vehicle_makes/{make_id}/vehicle_models"
    )
    response = requests.get(models_url, headers=HEADERS, timeout=60)
    if response.status_code == 200:
        return response.json()
    print(
        f"Failed to fetch models for make ID {make_id}. Status: {response.status_code}"
    )
    return []


async def check_duplicate_entry(year, model_name, make_name):
    """
    Check if an entry for a specific vehicle model, make, and year already exists in the database.
    """
    duplicate_check_query = """
    SELECT COUNT(*) FROM vehicle_emissions 
    WHERE year = :year AND vehicle_model_name = :model_name AND vehicle_make_name = :make_name
    """
    return (
        await database.fetch_val(
            query=duplicate_check_query,
            values={"year": year, "model_name": model_name, "make_name": make_name},
        )
        > 0
    )


async def fetch_emission_estimate(model_id):
    """
    Fetch emission estimate data from the Carbon Interface API for a specific vehicle model ID.
    Stop execution and send a single email notification if API request limit is reached
    (status 401).
    """
    estimate_url = "https://www.carboninterface.com/api/v1/estimates"
    estimate_payload = {
        "type": "vehicle",
        "distance_unit": "km",
        "distance_value": 100,
        "vehicle_model_id": model_id,
    }
    response = requests.post(
        estimate_url, headers=HEADERS, json=estimate_payload, timeout=10
    )
    if response.status_code == 201:
        return response.json()["data"]["attributes"]
    if response.status_code == 401:
        print("API request limit reached. Stopping execution.")
        send_notification(
            subject="API Request Limit Reached",
            body="Your account has hit its monthly API request limit. "
            "Please upgrade to make more requests.",
        )
        raise SystemExit("Stopping execution due to API request limit.")
    print(
        f"Failed to fetch emission estimate. Status: {response.status_code}, "
        f"Message: {response.text}"
    )
    return None


async def insert_vehicle_emission_record(
    model_id, make_name, model_name, year, estimate_data
):
    """
    Insert a new record into the 'vehicle_emissions' table with the computed emissions data.
    """
    insert_query = """INSERT INTO vehicle_emissions (id, vehicle_model_id, vehicle_make_name,
    vehicle_model_name, year, distance_value, distance_unit, carbon_emission_g) VALUES (:id, 
    :model_id, :make_name, :model_name, :year, :distance_value, :distance_unit, 
    :carbon_emission_g)"""
    values = {
        "id": str(uuid.uuid4()),
        "model_id": model_id,
        "make_name": make_name,
        "model_name": model_name,
        "year": year,
        "distance_value": estimate_data["distance_value"],
        "distance_unit": estimate_data["distance_unit"],
        "carbon_emission_g": estimate_data["carbon_g"],
    }
    await database.execute(query=insert_query, values=values)


if __name__ == "__main__":
    import asyncio

    asyncio.run(fetch_and_store_vehicle_emissions())
