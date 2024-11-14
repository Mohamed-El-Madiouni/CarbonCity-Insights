"""
Database configuration for CarbonCity Insights.

This module initializes the connection to the PostgreSQL database
using environment variables. It provides a `database` object that
can be imported and used throughout the project for database operations.
"""

import os

from databases import Database
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the database connection
DATABASE_URL = os.getenv("DATABASE_URL")
database = Database(DATABASE_URL, min_size=1, max_size=20)
