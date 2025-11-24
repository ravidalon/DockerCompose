"""Utility functions for person and file management."""

from .db_client import call_database


def get_person_by_name(name: str) -> dict | None:
    """Get a person node by name.

    Args:
        name: The person's name

    Returns:
        Person node dict if found, None otherwise
    """
    query_data = {
        "query": f"""
            MATCH (p:Person {{name: '{name}'}})
            RETURN p
            LIMIT 1
        """
    }

    result = call_database("POST", "query/cypher", query_data)

    if result.get("results") and len(result["results"]) > 0:
        record = result["results"][0]
        if "p" in record:
            return record["p"]

    return None


def person_exists(name: str) -> bool:
    """Check if a person with the given name exists.

    Args:
        name: The person's name

    Returns:
        True if person exists, False otherwise
    """
    return get_person_by_name(name) is not None


def get_file_by_person_and_filename(person_name: str, filename: str) -> dict | None:
    """Get a file node uploaded by a specific person.

    Args:
        person_name: The person's name
        filename: The file's name

    Returns:
        File node dict if found, None otherwise
    """
    query_data = {
        "query": f"""
            MATCH (p:Person {{name: '{person_name}'}})-[:UPLOADED]->(f:File {{filename: '{filename}'}})
            RETURN f
            LIMIT 1
        """
    }

    result = call_database("POST", "query/cypher", query_data)

    if result.get("results") and len(result["results"]) > 0:
        record = result["results"][0]
        if "f" in record:
            return record["f"]

    return None


def file_exists_for_person(person_name: str, filename: str) -> bool:
    """Check if a file with the given name exists for a person.

    Args:
        person_name: The person's name
        filename: The file's name

    Returns:
        True if file exists for this person, False otherwise
    """
    return get_file_by_person_and_filename(person_name, filename) is not None
