from flask import Blueprint, jsonify
from neo4j.exceptions import Neo4jError
from werkzeug.wrappers.response import Response as WerkzeugResponse

from database.db import get_db

utils_bp = Blueprint('utils', __name__)


@utils_bp.route('/health', methods=['GET'])
def health() -> tuple[WerkzeugResponse, int]:
    return jsonify({"status": "healthy"}), 200


@utils_bp.route('/stats', methods=['GET'])
def get_stats() -> tuple[WerkzeugResponse, int]:
    try:
        driver = get_db()
        with driver.session() as session:
            node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
            labels = [record["label"] for record in session.run("CALL db.labels()")]
            rel_types = [record["relationshipType"] for record in session.run("CALL db.relationshipTypes()")]

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
