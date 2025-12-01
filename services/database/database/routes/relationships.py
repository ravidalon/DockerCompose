"""Relationship CRUD operation routes"""
import logging
from typing import Any

from flask import Blueprint, request, jsonify
from neo4j.exceptions import Neo4jError
from werkzeug.wrappers.response import Response as WerkzeugResponse

from database.db import get_db, relationship_to_dict
from database.validation import validate_identifier

logger = logging.getLogger(__name__)
relationships_bp = Blueprint('relationships', __name__, url_prefix='/relationships')


@relationships_bp.route('', methods=['POST'])
def create_relationship() -> tuple[WerkzeugResponse, int]:
    """Create a relationship between two nodes

    Expected JSON body:
    {
        "from_node": "node_id_1",
        "to_node": "node_id_2",
        "type": "KNOWS",
        "properties": {
            "since": 2020
        }
    }
    """
    data: dict[str, Any] | None = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    from_node: str | None = data.get("from_node")
    to_node: str | None = data.get("to_node")
    rel_type: str | None = data.get("type")
    properties: dict[str, Any] = data.get("properties", {})

    if not from_node or not to_node or not rel_type:
        return jsonify({"error": "from_node, to_node, and type are required"}), 400

    # Validate relationship type to prevent Cypher injection
    is_valid, error = validate_identifier(rel_type, "relationship type")
    if not is_valid:
        return jsonify({"error": error}), 400

    try:
        driver = get_db()
        with driver.session() as session:
            query = f"""
            MATCH (a) WHERE elementId(a) = $from_node
            MATCH (b) WHERE elementId(b) = $to_node
            CREATE (a)-[r:{rel_type} $properties]->(b)
            RETURN r
            """
            result = session.run(query, from_node=from_node, to_node=to_node, properties=properties)
            record = result.single()

            if record:
                rel = record["r"]
                return jsonify(relationship_to_dict(rel)), 201

            return jsonify({"error": "Failed to create relationship. Nodes may not exist."}), 404
    except Neo4jError as e:
        logger.error(f"Neo4j error creating relationship: {e}", exc_info=True)
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Unexpected error creating relationship: {e}", exc_info=True)
        return jsonify({"error": "Internal server error", "message": str(e)}), 500


@relationships_bp.route('/<relationship_id>', methods=['GET'])
def get_relationship(relationship_id: str) -> tuple[WerkzeugResponse, int]:
    """Get a relationship by ID"""
    try:
        driver = get_db()
        with driver.session() as session:
            query = "MATCH ()-[r]->() WHERE elementId(r) = $relationship_id RETURN r"
            result = session.run(query, relationship_id=relationship_id)
            record = result.single()

            if record:
                rel = record["r"]
                return jsonify(relationship_to_dict(rel)), 200

            return jsonify({"error": "Relationship not found"}), 404
    except Neo4jError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500


@relationships_bp.route('/<relationship_id>', methods=['PUT'])
def update_relationship(relationship_id: str) -> tuple[WerkzeugResponse, int]:
    """Update a relationship's properties

    Expected JSON body:
    {
        "properties": {
            "since": 2021
        }
    }
    """
    data: dict[str, Any] | None = request.get_json()

    if not data or "properties" not in data:
        return jsonify({"error": "No properties provided"}), 400

    properties: dict[str, Any] = data["properties"]

    try:
        driver = get_db()
        with driver.session() as session:
            query = """
            MATCH ()-[r]->() WHERE elementId(r) = $relationship_id
            SET r += $properties
            RETURN r
            """
            result = session.run(query, relationship_id=relationship_id, properties=properties)
            record = result.single()

            if record:
                rel = record["r"]
                return jsonify(relationship_to_dict(rel)), 200

            return jsonify({"error": "Relationship not found"}), 404
    except Neo4jError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500


@relationships_bp.route('/<relationship_id>', methods=['DELETE'])
def delete_relationship(relationship_id: str) -> tuple[WerkzeugResponse, int]:
    """Delete a relationship"""
    try:
        driver = get_db()
        with driver.session() as session:
            query = """
            MATCH ()-[r]->() WHERE elementId(r) = $relationship_id
            DELETE r
            RETURN count(r) as deleted_count
            """
            result = session.run(query, relationship_id=relationship_id)
            record = result.single()

            if record and record["deleted_count"] > 0:
                return jsonify({"message": "Relationship deleted successfully"}), 200

            return jsonify({"error": "Relationship not found"}), 404
    except Neo4jError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500


@relationships_bp.route('/type/<rel_type>', methods=['GET'])
def get_relationships_by_type(rel_type: str) -> tuple[WerkzeugResponse, int]:
    """Get all relationships of a specific type"""
    # Validate relationship type to prevent Cypher injection
    is_valid, error = validate_identifier(rel_type, "relationship type")
    if not is_valid:
        return jsonify({"error": error}), 400

    try:
        driver = get_db()
        with driver.session() as session:
            query = f"MATCH ()-[r:{rel_type}]->() RETURN r"
            result = session.run(query)
            relationships = [relationship_to_dict(record["r"]) for record in result]

            return jsonify({"relationships": relationships, "count": len(relationships)}), 200
    except Neo4jError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500
