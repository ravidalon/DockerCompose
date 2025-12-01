"""Node CRUD operation routes"""
from typing import Any

from flask import Blueprint, request, jsonify
from neo4j.exceptions import Neo4jError
from werkzeug.wrappers.response import Response as WerkzeugResponse

from database.db import get_db, node_to_dict
from database.validation import validate_identifier, validate_identifiers


nodes_bp = Blueprint('nodes', __name__, url_prefix='/nodes')


@nodes_bp.route('', methods=['POST'])
def create_node() -> tuple[WerkzeugResponse, int]:
    """Create a new node with labels and properties

    Expected JSON body:
    {
        "labels": ["Person", "Employee"],
        "properties": {
            "name": "John",
            "age": 30
        }
    }
    """
    data: dict[str, Any] | None = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    labels: list[str] = data.get("labels", [])
    properties: dict[str, Any] = data.get("properties", {})

    if not labels:
        return jsonify({"error": "At least one label is required"}), 400

    # Validate labels to prevent Cypher injection
    is_valid, error = validate_identifiers(labels, "label")
    if not is_valid:
        return jsonify({"error": error}), 400

    try:
        driver = get_db()
        with driver.session() as session:
            # Build Cypher query dynamically (safe after validation)
            labels_str = ':'.join(labels)
            query = f"CREATE (n:{labels_str} $properties) RETURN n"
            result = session.run(query, properties=properties)
            record = result.single()

            if record:
                node = record["n"]
                return jsonify(node_to_dict(node)), 201

            return jsonify({"error": "Failed to create node"}), 500
    except Neo4jError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500


@nodes_bp.route('/<node_id>', methods=['GET'])
def get_node(node_id: str) -> tuple[WerkzeugResponse, int]:
    """Get a node by ID"""
    try:
        driver = get_db()
        with driver.session() as session:
            query = "MATCH (n) WHERE elementId(n) = $node_id RETURN n"
            result = session.run(query, node_id=node_id)
            record = result.single()

            if record:
                node = record["n"]
                return jsonify(node_to_dict(node)), 200

            return jsonify({"error": "Node not found"}), 404
    except Neo4jError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500


@nodes_bp.route('/<node_id>', methods=['PUT'])
def update_node(node_id: str) -> tuple[WerkzeugResponse, int]:
    """Update a node's properties

    Expected JSON body:
    {
        "properties": {
            "name": "Jane",
            "age": 31
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
            MATCH (n) WHERE elementId(n) = $node_id
            SET n += $properties
            RETURN n
            """
            result = session.run(query, node_id=node_id, properties=properties)
            record = result.single()

            if record:
                node = record["n"]
                return jsonify(node_to_dict(node)), 200

            return jsonify({"error": "Node not found"}), 404
    except Neo4jError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500


@nodes_bp.route('/<node_id>', methods=['DELETE'])
def delete_node(node_id: str) -> tuple[WerkzeugResponse, int]:
    """Delete a node"""
    try:
        driver = get_db()
        with driver.session() as session:
            query = """
            MATCH (n) WHERE elementId(n) = $node_id
            DETACH DELETE n
            RETURN count(n) as deleted_count
            """
            result = session.run(query, node_id=node_id)
            record = result.single()

            if record and record["deleted_count"] > 0:
                return jsonify({"message": "Node deleted successfully"}), 200

            return jsonify({"error": "Node not found"}), 404
    except Neo4jError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500


@nodes_bp.route('/label/<label>', methods=['GET'])
def get_nodes_by_label(label: str) -> tuple[WerkzeugResponse, int]:
    """Get all nodes with a specific label"""
    # Validate label to prevent Cypher injection
    is_valid, error = validate_identifier(label, "label")
    if not is_valid:
        return jsonify({"error": error}), 400

    try:
        driver = get_db()
        with driver.session() as session:
            query = f"MATCH (n:{label}) RETURN n"
            result = session.run(query)
            nodes = [node_to_dict(record["n"]) for record in result]

            return jsonify({"nodes": nodes, "count": len(nodes)}), 200
    except Neo4jError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500
