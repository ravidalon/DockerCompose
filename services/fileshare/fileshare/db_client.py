"""Database service client."""

import logging
import requests
from .config import DATABASE_URL

logger = logging.getLogger(__name__)


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
    logger.debug(f"Database request: {method} {url}")
    if json:
        logger.debug(f"Request payload: {json}")

    try:
        response = requests.request(method, url, json=json, timeout=10)
        logger.debug(f"Database response: {response.status_code}")

        response.raise_for_status()
        result = response.json()
        logger.debug(f"Response data: {result}")
        return result
    except requests.Timeout as e:
        logger.error(f"Database request timeout: {method} {url} - {e}")
        raise RuntimeError(f"Database service timeout: {e}")
    except requests.ConnectionError as e:
        logger.error(f"Database connection error: {method} {url} - {e}")
        raise RuntimeError(f"Database service unreachable: {e}")
    except requests.HTTPError as e:
        logger.error(f"Database HTTP error: {method} {url} - Status {response.status_code} - {e}")
        logger.error(f"Response body: {response.text[:500]}")
        raise RuntimeError(f"Database service HTTP error: {e}")
    except requests.RequestException as e:
        logger.error(f"Database request failed: {method} {url} - {e}")
        raise RuntimeError(f"Database service error: {e}")
