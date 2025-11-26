"""Pytest configuration and fixtures for integration tests."""

import os
import pytest
import requests
from neo4j import GraphDatabase


@pytest.fixture(scope="session")
def fileshare_url():
    """Base URL for fileshare service."""
    return os.getenv("FILESHARE_URL", "http://fileshare:5000")


@pytest.fixture(scope="session")
def database_url():
    """Base URL for database service."""
    return os.getenv("DATABASE_URL", "http://database:5000")


@pytest.fixture(scope="session")
def neo4j_driver():
    """Neo4j driver for direct database queries."""
    uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    yield driver
    driver.close()


@pytest.fixture(scope="function")
def cleanup_test_data(neo4j_driver):
    """Clean up test data after each test."""
    yield

    # Delete all test-related nodes and relationships
    with neo4j_driver.session() as session:
        session.run(
            "MATCH (p:Person) WHERE p.name STARTS WITH 'TestUser' "
            "OPTIONAL MATCH (p)-[r]-() DELETE r, p"
        )
        session.run(
            "MATCH (f:File) WHERE f.filename STARTS WITH 'test_' "
            "OPTIONAL MATCH (f)-[r]-() DELETE r, f"
        )


@pytest.fixture(scope="function")
def test_person(fileshare_url, cleanup_test_data):
    """Create a test person for use in tests."""
    person_name = "TestUser1"
    response = requests.post(
        f"{fileshare_url}/persons",
        json={"name": person_name, "email": f"{person_name.lower()}@test.com"}
    )
    assert response.status_code in [200, 201], f"Failed to create test person: {response.text}"
    return person_name
