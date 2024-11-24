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

from uuid import UUID


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
