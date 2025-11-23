"""Utility routes (health, stats)"""
from flask import Blueprint, jsonify
from werkzeug.wrappers.response import Response as WerkzeugResponse
from neo4j.exceptions import Neo4jError
from database.db import get_db


utils_bp = Blueprint('utils', __name__)


@utils_bp.route('/health', methods=['GET'])
def health() -> tuple[WerkzeugResponse, int]:
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200


@utils_bp.route('/stats', methods=['GET'])
def get_stats() -> tuple[WerkzeugResponse, int]:
    """Get database statistics"""
    try:
        driver = get_db()
        with driver.session() as session:
            # Get node count
            node_count_result = session.run("MATCH (n) RETURN count(n) as count")
            node_count = node_count_result.single()["count"]

            # Get relationship count
            rel_count_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = rel_count_result.single()["count"]

            # Get all labels
            labels_result = session.run("CALL db.labels()")
            labels = [record["label"] for record in labels_result]

            # Get all relationship types
            rel_types_result = session.run("CALL db.relationshipTypes()")
            rel_types = [record["relationshipType"] for record in rel_types_result]

            return jsonify({
                "stats": {
                    "node_count": node_count,
                    "relationship_count": rel_count,
                    "labels": labels,
                    "relationship_types": rel_types
                }
            }), 200
    except Neo4jError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500
