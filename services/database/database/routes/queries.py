"""Query operation routes (Cypher execution, path finding, node relationships)"""
import logging
from typing import Any

from flask import Blueprint, request, jsonify
from neo4j.exceptions import Neo4jError
from werkzeug.wrappers.response import Response as WerkzeugResponse

from database.db import get_db, node_to_dict, relationship_to_dict
from database.validation import validate_identifier, validate_identifiers

logger = logging.getLogger(__name__)
queries_bp = Blueprint('queries', __name__)


@queries_bp.route('/nodes/<node_id>/relationships', methods=['GET'])
def get_node_relationships(node_id: str) -> tuple[WerkzeugResponse, int]:
    """Get all relationships for a specific node

    Query params:
    - direction: "incoming", "outgoing", or "all" (default: "all")
    - type: filter by relationship type (optional)
    """
    direction: str = request.args.get('direction', 'all')
    rel_type: str | None = request.args.get('type')

    # Validate relationship type if provided
    if rel_type:
        is_valid, error = validate_identifier(rel_type, "relationship type")
        if not is_valid:
            return jsonify({"error": error}), 400

    try:
        driver = get_db()
        with driver.session() as session:
            # Build query based on direction and type
            if direction == "incoming":
                pattern = "<-[r]-()"
            elif direction == "outgoing":
                pattern = "-[r]->()"
            else:  # all
                pattern = "-[r]-()"

            if rel_type:
                pattern = pattern.replace("[r]", f"[r:{rel_type}]")

            query = f"""
            MATCH (n){pattern}
            WHERE elementId(n) = $node_id
            RETURN r
            """
            result = session.run(query, node_id=node_id)
            relationships = [relationship_to_dict(record["r"]) for record in result]

            return jsonify({"relationships": relationships, "count": len(relationships)}), 200
    except Neo4jError as e:
        logger.error(f"Neo4j error getting node relationships: {str(e)}", exc_info=True)
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Unexpected error getting node relationships: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@queries_bp.route('/query/cypher', methods=['POST'])
def execute_cypher() -> tuple[WerkzeugResponse, int]:
    """Execute a custom Cypher query

    Expected JSON body:
    {
        "query": "MATCH (n:Person) WHERE n.age > $age RETURN n",
        "parameters": {
            "age": 25
        }
    }
    """
    data: dict[str, Any] | None = request.get_json()

    if not data or 'query' not in data:
        return jsonify({"error": "No query provided"}), 400

    query: str = data['query']
    parameters: dict[str, Any] = data.get('parameters', {})

    try:
        driver = get_db()
        with driver.session() as session:
            result = session.run(query, **parameters)
            records = []

            for record in result:
                record_dict: dict[str, Any] = {}
                for key in record.keys():
                    value = record[key]
                    # Convert Neo4j types to dicts
                    if hasattr(value, 'labels'):  # Node
                        record_dict[key] = node_to_dict(value)
                    elif hasattr(value, 'type') and hasattr(value, 'start_node'):  # Relationship
                        record_dict[key] = relationship_to_dict(value)
                    else:
                        record_dict[key] = value
                records.append(record_dict)

            return jsonify({"results": records, "count": len(records)}), 200
    except Neo4jError as e:
        logger.error(f"Neo4j error executing Cypher query: {str(e)}", exc_info=True)
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Unexpected error executing Cypher query: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@queries_bp.route('/query/path', methods=['POST'])
def find_path() -> tuple[WerkzeugResponse, int]:
    """Find path between two nodes

    Expected JSON body:
    {
        "from_node": "node_id_1",
        "to_node": "node_id_2",
        "max_depth": 5,
        "relationship_types": ["KNOWS", "WORKS_WITH"]
    }
    """
    data: dict[str, Any] | None = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    from_node: str | None = data.get("from_node")
    to_node: str | None = data.get("to_node")
    max_depth: int = data.get("max_depth", 5)
    rel_types: list[str] | None = data.get("relationship_types")

    if not from_node or not to_node:
        return jsonify({"error": "from_node and to_node are required"}), 400

    # Validate max_depth to prevent resource exhaustion
    if not isinstance(max_depth, int) or max_depth < 1 or max_depth > 15:
        return jsonify({"error": "max_depth must be an integer between 1 and 15"}), 400

    # Validate relationship types if provided
    if rel_types:
        is_valid, error = validate_identifiers(rel_types, "relationship type")
        if not is_valid:
            return jsonify({"error": error}), 400

    try:
        driver = get_db()
        with driver.session() as session:
            # Build relationship type filter (safe after validation)
            rel_filter = ""
            if rel_types:
                rel_filter = ":" + "|".join(rel_types)

            query = f"""
            MATCH path = shortestPath(
                (a)-[{rel_filter}*..{max_depth}]-(b)
            )
            WHERE elementId(a) = $from_node AND elementId(b) = $to_node
            RETURN path
            """
            result = session.run(query, from_node=from_node, to_node=to_node)
            record = result.single()

            if record:
                path = record["path"]
                nodes = [node_to_dict(node) for node in path.nodes]
                relationships = [relationship_to_dict(rel) for rel in path.relationships]

                return jsonify({
                    "path": {
                        "nodes": nodes,
                        "relationships": relationships,
                        "length": len(relationships)
                    }
                }), 200

            return jsonify({"error": "No path found between the nodes"}), 404
    except Neo4jError as e:
        logger.error(f"Neo4j error finding path: {str(e)}", exc_info=True)
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Unexpected error finding path: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
