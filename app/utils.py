"""
Utility module for data serialization.

This module provides helper functions for serializing complex data types
into JSON-compatible formats. It is especially useful for handling objects
like UUIDs or Pydantic models, which are not natively serializable by the
standard `json` library.

Functions:
- serialize_data: Recursively converts non-serializable objects into
  JSON-compatible formats.
"""

import os
from datetime import datetime, timedelta
from uuid import UUID

from jose import jwt


def serialize_data(data):
    """
    Recursively converts non-serializable objects (e.g., UUID) into serializable formats.

    :param data: The data to serialize (dict, list, or object).
    :return: A JSON-serializable version of the data.
    """
    if isinstance(data, list):
        return [serialize_data(item) for item in data]
    if isinstance(data, dict):
        return {key: serialize_data(value) for key, value in data.items()}
    if isinstance(data, UUID):  # Convert UUID to string
        return str(data)
    if hasattr(data, "dict"):  # Convert Pydantic models to dict
        return serialize_data(data.dict())
    return data


JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default_secret_key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "30"))


def create_access_token(data: dict):
    """
    Generates a JWT token with a given payload.
    :param data: The data to be included in the token.
    :return: A signed JWT token.
    """
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str):
    """
    Decodes a JWT token to extract data.
    :param token: The JWT token to decode.
    :return: The data contained in the token.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.JWTError:
        return None
