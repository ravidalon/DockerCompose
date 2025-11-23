import os
from typing import Any
from neo4j import GraphDatabase, Driver
from neo4j.graph import Node, Relationship


class Neo4jConnection:
    """Manages Neo4j database connection"""

    def __init__(self) -> None:
        self._driver: Driver | None = None
        self._uri: str = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self._user: str = os.getenv('NEO4J_USER', 'neo4j')
        self._password: str = os.getenv('NEO4J_PASSWORD', 'password')

    def get_driver(self) -> Driver:
        """Get or create the Neo4j driver instance"""
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self._uri,
                auth=(self._user, self._password)
            )
        return self._driver

    def close(self) -> None:
        """Close the driver connection"""
        if self._driver is not None:
            self._driver.close()
            self._driver = None


# Global connection instance
neo4j_conn: Neo4jConnection = Neo4jConnection()


def get_db() -> Driver:
    """Get the Neo4j driver instance"""
    return neo4j_conn.get_driver()


def close_db() -> None:
    """Close the Neo4j driver connection"""
    neo4j_conn.close()


def node_to_dict(node: Node) -> dict[str, Any]:
    """Convert a Neo4j node to a dictionary"""
    return {
        "id": str(node.element_id),
        "labels": list(node.labels),
        "properties": dict(node)
    }


def relationship_to_dict(relationship: Relationship) -> dict[str, Any]:
    """Convert a Neo4j relationship to a dictionary"""
    return {
        "id": str(relationship.element_id),
        "type": relationship.type,
        "start_node_id": str(relationship.start_node.element_id),
        "end_node_id": str(relationship.end_node.element_id),
        "properties": dict(relationship)
    }
