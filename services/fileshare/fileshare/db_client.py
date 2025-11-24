"""Database service client."""

import requests
from .config import DATABASE_URL


def call_database(method: str, endpoint: str, json: dict | None = None) -> dict:
    """Make a request to the database service.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        endpoint: API endpoint path (without leading slash)
        json: Optional JSON payload

    Returns:
        Response JSON as dictionary

    Raises:
        RuntimeError: If database service request fails
    """
    url = f"{DATABASE_URL}/{endpoint}"
    try:
        response = requests.request(method, url, json=json, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Database service error: {e}")
