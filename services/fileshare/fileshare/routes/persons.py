"""Person management endpoints."""

from datetime import datetime
from flask import Blueprint, request, jsonify
from ..db_client import call_database
from ..person_utils import person_exists, get_person_by_name

bp = Blueprint("persons", __name__, url_prefix="/persons")


@bp.route("", methods=["POST"])
def create_person():
    """Create a new person node."""
    data = request.get_json()

    if not data or "name" not in data:
        return jsonify({"error": "name is required"}), 400

    name = data["name"]

    # Check if person already exists
    if person_exists(name):
        return jsonify({"error": f"Person with name '{name}' already exists"}), 409

    person_data = {
        "labels": ["Person"],
        "properties": {
            "name": name,
            "email": data.get("email", ""),
            "created_at": datetime.utcnow().isoformat()
        }
    }

    result = call_database("POST", "nodes", person_data)
    return jsonify(result), 201


@bp.route("/<person_name>", methods=["GET"])
def get_person(person_name: str):
    """Get person by name."""
    person = get_person_by_name(person_name)

    if not person:
        return jsonify({"error": f"Person '{person_name}' not found"}), 404

    return jsonify(person)


@bp.route("", methods=["GET"])
def list_persons():
    """List all persons."""
    result = call_database("GET", "nodes/label/Person", None)
    return jsonify(result)


@bp.route("/<person_name>/files", methods=["GET"])
def get_person_files(person_name: str):
    """Get all files uploaded by a person."""
    # Check if person exists
    person = get_person_by_name(person_name)
    if not person:
        return jsonify({"error": f"Person '{person_name}' not found"}), 404

    query_data = {
        "query": f"""
            MATCH (p:Person {{name: '{person_name}'}})-[:UPLOADED]->(f:File)
            RETURN f
        """
    }

    result = call_database("POST", "query/cypher", query_data)

    files = []
    for record in result.get("results", []):
        if "f" in record:
            files.append(record["f"])

    return jsonify({"person": person_name, "files": files})
