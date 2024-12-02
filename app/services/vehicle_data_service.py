"""
Vehicle Data Service for CarbonCity Insights

This module provides functions to fetch vehicle data from the Carbon Interface API,
compute carbon emissions for specific trips, and store the results in PostgreSQL,
ensuring no duplicate entries.
"""

import logging
import os
import smtplib
import uuid
from email.message import EmailMessage

import requests
from asyncpg.exceptions import PostgresError
from databases import Database
from dotenv import load_dotenv
from requests.exceptions import RequestException

# Load environment variables
load_dotenv()
CARBON_INTERFACE_API_KEY = os.getenv("CARBON_INTERFACE_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL")  # Email for notifications
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  # SMTP password for email notifications

# Configure log directory
log_dir = os.path.abspath(os.path.join(__file__, "../../../log"))
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Configure logger
log_path = os.path.join(log_dir, "services.log")
services_logger = logging.getLogger("services_logger")
services_logger.setLevel(logging.INFO)

# File and console handlers for services_logger
file_handler = logging.FileHandler(log_path)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
console_handler = logging.StreamHandler()

# Adding handlers to services_logger
services_logger.addHandler(file_handler)
services_logger.addHandler(console_handler)

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
    services_logger.info("Sending notification email.")
    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = NOTIFICATION_EMAIL
    msg["To"] = NOTIFICATION_EMAIL

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(NOTIFICATION_EMAIL, EMAIL_PASSWORD)
            smtp.send_message(msg)
        services_logger.info("Notification email sent successfully.")
    except smtplib.SMTPAuthenticationError as e:
        services_logger.error("Authentication failed: %s", e)
    except smtplib.SMTPException as e:
        services_logger.error("SMTP error occurred: %s", e)
    except ConnectionRefusedError as e:
        services_logger.error("Connection refused: %s", e)


async def fetch_vehicle_makes():
    """
    Fetch all vehicle makes from the Carbon Interface API.

    :returns: list of dict: A list containing vehicle make data, each with 'id' and 'name'.
    """
    services_logger.info("Fetching vehicle makes from Carbon Interface API...")
    url = "https://www.carboninterface.com/api/v1/vehicle_makes"
    try:
        response = requests.get(url, headers=HEADERS, timeout=60)
        if response.status_code == 200:
            services_logger.info("Successfully fetched vehicle makes.")
            return response.json()
        services_logger.error(
            "Failed to fetch vehicle makes. Status: %s, Message: %s",
            response.status_code,
            response.text,
        )
    except RequestException as e:
        services_logger.error("Request to fetch vehicle makes failed: %s", e)
    return []


async def process_vehicle_model(model, make_name):
    """
    Process a single vehicle model by checking for duplicates, fetching emission estimates,
    and inserting records if not duplicated.
    """
    model_id = model["data"]["id"]
    model_name = model["data"]["attributes"]["name"]
    year = model["data"]["attributes"].get("year")

    if await check_duplicate_entry(year, model_name, make_name):
        services_logger.info(
            "Duplicate model skipped: %s (%s) for make: %s", model_name, year, make_name
        )
        return

    estimate_data = await fetch_emission_estimate(model_id)
    if estimate_data:
        await insert_vehicle_emission_record(
            model_id, make_name, model_name, year, estimate_data
        )
        services_logger.info(
            "Inserted emission estimate for model: %s (%s) for make: %s",
            model_name,
            year,
            make_name,
        )
    else:
        services_logger.warning(
            "Failed to fetch emission estimate for model %s.", model_name
        )


async def fetch_and_store_vehicle_emissions():
    """
    Fetch vehicle models, compute emissions estimates, and store them in the PostgreSQL database.
    Ensures no duplicate entries based on 'year', 'vehicle_model_name', and 'vehicle_make_name'.
    """
    services_logger.info("Connecting to the database.")
    await database.connect()
    try:
        vehicle_makes = await fetch_vehicle_makes()
        for vehicle_make in vehicle_makes:
            make_id = vehicle_make["data"]["id"]
            make_name = vehicle_make["data"]["attributes"]["name"]
            services_logger.info("Fetching models for make: %s", make_name)

            vehicle_models = await fetch_vehicle_models(make_id)
            for model in vehicle_models:
                await process_vehicle_model(model, make_name)
    except RequestException as e:
        services_logger.error("Network error while fetching data: %s", e)
    except PostgresError as e:
        services_logger.error("Database operation failed: %s", e)
    except KeyError as e:
        services_logger.error("Data format error, missing key: %s", e)
    services_logger.info("Disconnecting from the database.")
    await database.disconnect()
    services_logger.info("All vehicle models have been processed.")


async def fetch_vehicle_models(make_id):
    """
    Fetch all vehicle models for a given make ID from the Carbon Interface API.
    """
    services_logger.info("Fetching vehicle models for make ID: %s", make_id)
    models_url = (
        f"https://www.carboninterface.com/api/v1/vehicle_makes/{make_id}/vehicle_models"
    )
    try:
        response = requests.get(models_url, headers=HEADERS, timeout=60)
        if response.status_code == 200:
            services_logger.info(
                "Successfully fetched vehicle models for make ID: %s", make_id
            )
            return response.json()
        services_logger.error(
            "Failed to fetch models for make ID %s. Status: %s",
            make_id,
            response.status_code,
        )
    except RequestException as e:
        services_logger.error("Request to fetch vehicle models failed: %s", e)
    return []


async def check_duplicate_entry(year, model_name, make_name):
    """
    Check if an entry for a specific vehicle model, make, and year already exists in the database.
    """
    services_logger.debug(
        "Checking for duplicate entry for model: %s, make: %s, year: %s",
        model_name,
        make_name,
        year,
    )
    duplicate_check_query = """
    SELECT COUNT(*) FROM vehicle_emissions 
    WHERE year = :year AND vehicle_model_name = :model_name AND vehicle_make_name = :make_name
    """
    try:
        is_duplicate = (
            await database.fetch_val(
                query=duplicate_check_query,
                values={"year": year, "model_name": model_name, "make_name": make_name},
            )
            > 0
        )
        if is_duplicate:
            services_logger.info(
                "Duplicate entry found for model: %s (%s) - make: %s",
                model_name,
                year,
                make_name,
            )
        return is_duplicate
    except PostgresError as e:
        services_logger.error("Database error during duplicate check: %s", e)
    return False


async def fetch_emission_estimate(model_id):
    """
    Fetch emission estimate data from the Carbon Interface API for a specific vehicle model ID.
    Stop execution and send a single email notification if API request limit is reached
    (status 401).
    """
    services_logger.info("Fetching emission estimate for model ID: %s", model_id)
    estimate_url = "https://www.carboninterface.com/api/v1/estimates"
    estimate_payload = {
        "type": "vehicle",
        "distance_unit": "km",
        "distance_value": 100,
        "vehicle_model_id": model_id,
    }
    try:
        response = requests.post(
            estimate_url, headers=HEADERS, json=estimate_payload, timeout=10
        )
        if response.status_code == 201:
            services_logger.info(
                "Successfully fetched emission estimate for model ID: %s", model_id
            )
            return response.json()["data"]["attributes"]
        if response.status_code == 401:
            send_notification(
                subject="API Request Limit Reached",
                body="Your account has hit its monthly API request limit. "
                "Please upgrade to make more requests.",
            )
            services_logger.error("API request limit reached. Execution stopped.")
            raise SystemExit("Stopping execution due to API request limit.")
        services_logger.error(
            "Failed to fetch emission estimate. Status: %s, Message: %s",
            response.status_code,
            response.text,
        )
    except RequestException as e:
        services_logger.error("Request to fetch emission estimate failed: %s", e)
    return None


async def insert_vehicle_emission_record(
    model_id, make_name, model_name, year, estimate_data
):
    """
    Insert a new record into the 'vehicle_emissions' table with the computed émissions data.
    """
    services_logger.info(
        "Inserting record for model: %s (%s) - make: %s", model_name, year, make_name
    )
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
    try:
        await database.execute(query=insert_query, values=values)
        services_logger.info("Record inserted successfully.")
    except PostgresError as e:
        services_logger.error("Failed to insert record: %s", e)


if __name__ == "__main__":
    import asyncio

    asyncio.run(fetch_and_store_vehicle_emissions())
