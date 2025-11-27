"""File management endpoints."""

import logging
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, send_file
from ..config import UPLOAD_DIR
from ..db_client import call_database
from ..person_utils import (
    get_person_by_name,
    file_exists_for_person,
    get_file_by_person_and_filename
)
from ..validation import sanitize_filename, validate_file_upload, validate_content_type

logger = logging.getLogger(__name__)
bp = Blueprint("files", __name__, url_prefix="/files")


def validate_person(person_name: str) -> tuple[dict | None, tuple[dict, int] | None]:
    """Validate that a person exists.

    Args:
        person_name: The person's name

    Returns:
        Tuple of (person_node, error_response). If person exists, returns (node, None).
        If person doesn't exist, returns (None, error_response).
    """
    person_node = get_person_by_name(person_name)
    if not person_node:
        return None, (jsonify({"error": f"Person '{person_name}' not found"}), 404)
    return person_node, None


def validate_person_and_file(person_name: str, filename: str) -> tuple[tuple[dict, dict] | None, tuple[dict, int] | None]:
    """Validate that both a person and their file exist.

    Args:
        person_name: The person's name
        filename: The file's name

    Returns:
        Tuple of ((person_node, file_node), error_response). If both exist, returns ((person, file), None).
        If either doesn't exist, returns (None, error_response).
    """
    # First validate person
    person_node, error = validate_person(person_name)
    if error:
        return None, error

    # Then validate file
    file_node = get_file_by_person_and_filename(person_name, filename)
    if not file_node:
        return None, (jsonify({"error": f"File '{filename}' not found for person '{person_name}'"}), 404)

    return (person_node, file_node), None


def create_relationship(from_node_id: str, to_node_id: str, rel_type: str) -> None:
    """Create a relationship with timestamp.

    Args:
        from_node_id: Source node element ID
        to_node_id: Target node element ID
        rel_type: Relationship type (e.g., "UPLOADED", "DOWNLOADED", "EDITED")
    """
    rel_data = {
        "from_node": from_node_id,
        "to_node": to_node_id,
        "type": rel_type,
        "properties": {
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }
    call_database("POST", "relationships", rel_data)


@bp.route("/upload", methods=["POST"])
def upload_file():
    """Upload a single file."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    if "person" not in request.form:
        return jsonify({"error": "person is required"}), 400

    file = request.files["file"]
    person_name = request.form["person"]

    # Validate file upload (size, empty file, etc.)
    is_valid, error = validate_file_upload(file)
    if not is_valid:
        return error

    # Sanitize filename to prevent path traversal
    safe_filename, error = sanitize_filename(file.filename)
    if error:
        return error

    # Validate content type
    is_valid, error = validate_content_type(file.content_type)
    if not is_valid:
        return error

    # Validate person exists
    person_node, error = validate_person(person_name)
    if error:
        return error

    # Check if file already exists for this person
    if file_exists_for_person(person_name, safe_filename):
        return jsonify({"error": f"File '{safe_filename}' already exists for person '{person_name}'"}), 409

    # Save file with sanitized filename
    file_path = UPLOAD_DIR / safe_filename
    try:
        file.save(file_path)
    except Exception as e:
        return jsonify({"error": f"Failed to save file: {str(e)}"}), 500

    # Create file node
    file_data = {
        "labels": ["File"],
        "properties": {
            "filename": safe_filename,
            "size": file_path.stat().st_size,
            "content_type": file.content_type or "application/octet-stream",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "deleted": False
        }
    }

    file_node = call_database("POST", "nodes", file_data)

    # Create UPLOADED relationship
    create_relationship(person_node["id"], file_node["id"], "UPLOADED")

    return jsonify({
        "file": file_node,
        "message": "File uploaded successfully"
    }), 201


@bp.route("/upload/batch", methods=["POST"])
def upload_batch():
    """Upload multiple files in a batch."""
    if "person" not in request.form:
        return jsonify({"error": "person is required"}), 400

    person_name = request.form["person"]
    files = request.files.getlist("files")

    if not files:
        return jsonify({"error": "No files provided"}), 400

    # Validate person exists
    person_node, error = validate_person(person_name)
    if error:
        return error

    person_element_id = person_node["id"]
    uploaded_files = []
    file_ids = []
    seen_filenames = set()

    # Upload each file
    for file in files:
        # Validate file upload
        is_valid, error = validate_file_upload(file)
        if not is_valid:
            return error

        # Sanitize filename to prevent path traversal
        safe_filename, error = sanitize_filename(file.filename)
        if error:
            return error

        # Validate content type
        is_valid, error = validate_content_type(file.content_type)
        if not is_valid:
            return error

        # Check for duplicate filenames within this batch
        if safe_filename in seen_filenames:
            return jsonify({"error": f"Duplicate filename in batch: '{safe_filename}'"}), 400
        seen_filenames.add(safe_filename)

        # Check if file already exists for this person
        if file_exists_for_person(person_name, safe_filename):
            return jsonify({"error": f"File '{safe_filename}' already exists for person '{person_name}'"}), 409

        # Save file with sanitized filename
        file_path = UPLOAD_DIR / safe_filename
        try:
            file.save(file_path)
        except Exception as e:
            return jsonify({"error": f"Failed to save file '{safe_filename}': {str(e)}"}), 500

        # Create file node
        file_data = {
            "labels": ["File"],
            "properties": {
                "filename": safe_filename,
                "size": file_path.stat().st_size,
                "content_type": file.content_type or "application/octet-stream",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "deleted": False
            }
        }

        file_node = call_database("POST", "nodes", file_data)
        file_id = file_node["id"]
        file_ids.append(file_id)
        uploaded_files.append(file_node)

        # Create UPLOADED relationship
        create_relationship(person_element_id, file_id, "UPLOADED")

    # Create UPLOADED_WITH relationships between files
    for i, file_id_a in enumerate(file_ids):
        for file_id_b in file_ids[i + 1:]:
            # Create bidirectional relationships
            rel_data = {
                "from_node": file_id_a,
                "to_node": file_id_b,
                "type": "UPLOADED_WITH",
                "properties": {}
            }
            call_database("POST", "relationships", rel_data)

            rel_data = {
                "from_node": file_id_b,
                "to_node": file_id_a,
                "type": "UPLOADED_WITH",
                "properties": {}
            }
            call_database("POST", "relationships", rel_data)

    return jsonify({
        "files": uploaded_files,
        "count": len(uploaded_files),
        "message": f"Batch upload successful: {len(uploaded_files)} files"
    }), 201


@bp.route("/<path:file_id>", methods=["GET"])
def get_file(file_id: str):
    """Get file metadata."""
    result = call_database("GET", f"nodes/{file_id}", None)
    return jsonify(result)


@bp.route("", methods=["GET"])
def list_files():
    """List all files."""
    result = call_database("GET", "nodes/label/File", None)
    return jsonify(result)


@bp.route("/<person_name>/<filename>/download", methods=["GET"])
def download_file(person_name: str, filename: str):
    """Download a file and track the download."""
    logger.info(f"Download request: person={person_name}, filename={filename}")

    try:
        # Sanitize filename to prevent path traversal
        logger.debug(f"Sanitizing filename: {filename}")
        safe_filename, error = sanitize_filename(filename)
        if error:
            logger.warning(f"Filename sanitization failed: {filename}")
            return error

        # Validate person and file exist
        logger.debug(f"Validating person and file: {person_name}/{safe_filename}")
        result, error = validate_person_and_file(person_name, safe_filename)
        if error:
            logger.warning(f"Validation failed for {person_name}/{safe_filename}")
            return error

        person_node, file_node = result
        logger.debug(f"Found person_node: {person_node.get('id')}, file_node: {file_node.get('id')}")

        if file_node.get("properties", {}).get("deleted", False):
            logger.warning(f"Attempted to download deleted file: {person_name}/{safe_filename}")
            return jsonify({"error": "File has been deleted"}), 404

        file_path = UPLOAD_DIR / safe_filename
        logger.debug(f"Checking file path: {file_path}")

        if not file_path.exists():
            logger.error(f"File not found on disk: {file_path} (but exists in database)")
            return jsonify({"error": "File not found on disk"}), 404

        # Create DOWNLOADED relationship
        logger.debug(f"Creating DOWNLOADED relationship: {person_node['id']} -> {file_node['id']}")
        create_relationship(person_node["id"], file_node["id"], "DOWNLOADED")

        logger.info(f"Sending file: {safe_filename}")
        return send_file(file_path, as_attachment=True, download_name=safe_filename)

    except Exception as e:
        logger.error(f"Unexpected error in download_file: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error during file download",
            "message": str(e)
        }), 500


@bp.route("/<person_name>/<filename>", methods=["PUT"])
def edit_file(person_name: str, filename: str):
    """Edit/replace a file."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]

    # Validate file upload
    is_valid, error = validate_file_upload(file)
    if not is_valid:
        return error

    # Sanitize filename to prevent path traversal
    safe_filename, error = sanitize_filename(filename)
    if error:
        return error

    # Validate content type
    is_valid, error = validate_content_type(file.content_type)
    if not is_valid:
        return error

    # Validate person and file exist
    result, error = validate_person_and_file(person_name, safe_filename)
    if error:
        return error

    person_node, file_node = result

    if file_node.get("properties", {}).get("deleted", False):
        return jsonify({"error": "Cannot edit deleted file"}), 400

    # Save new file (use original filename)
    file_path = UPLOAD_DIR / safe_filename
    try:
        file.save(file_path)
    except Exception as e:
        return jsonify({"error": f"Failed to save file: {str(e)}"}), 500

    # Update file node
    file_id = file_node["id"]
    update_data = {
        "properties": {
            "size": file_path.stat().st_size,
            "content_type": file.content_type or "application/octet-stream",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    }

    updated_node = call_database("PUT", f"nodes/{file_id}", update_data)

    # Create EDITED relationship
    create_relationship(person_node["id"], file_id, "EDITED")

    return jsonify({
        "file": updated_node,
        "message": "File edited successfully"
    })


@bp.route("/<person_name>/<filename>", methods=["DELETE"])
def delete_file(person_name: str, filename: str):
    """Soft delete a file."""
    # Sanitize filename to prevent path traversal
    safe_filename, error = sanitize_filename(filename)
    if error:
        return error

    # Validate person and file exist
    result, error = validate_person_and_file(person_name, safe_filename)
    if error:
        return error

    person_node, file_node = result

    if file_node.get("properties", {}).get("deleted", False):
        return jsonify({"error": "File already deleted"}), 400

    file_path = UPLOAD_DIR / safe_filename
    file_id = file_node["id"]

    # Delete physical file
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as e:
            return jsonify({"error": f"Failed to delete physical file: {str(e)}"}), 500

    # Update node with deleted flag
    update_data = {
        "properties": {
            "deleted": True,
            "deleted_at": datetime.now(timezone.utc).isoformat()
        }
    }

    updated_node = call_database("PUT", f"nodes/{file_id}", update_data)

    return jsonify({
        "file": updated_node,
        "message": "File deleted successfully"
    })


@bp.route("/<person_name>/<filename>/history", methods=["GET"])
def get_file_history(person_name: str, filename: str):
    """Get all interactions with a file."""
    # Sanitize filename to prevent path traversal
    safe_filename, error = sanitize_filename(filename)
    if error:
        return error

    # Validate person and file exist
    result, error = validate_person_and_file(person_name, safe_filename)
    if error:
        return error

    person_node, file_node = result
    file_id = file_node["id"]

    result = call_database("GET", f"nodes/{file_id}/relationships", None)

    return jsonify({
        "person": person_name,
        "filename": safe_filename,
        "relationships": result.get("relationships", [])
    })


@bp.route("/<person_name>/<filename>/batch-related", methods=["GET"])
def get_batch_related(person_name: str, filename: str):
    """Get files uploaded in the same batch."""
    # Sanitize filename to prevent path traversal
    safe_filename, error = sanitize_filename(filename)
    if error:
        return error

    # Validate person and file exist
    result, error = validate_person_and_file(person_name, safe_filename)
    if error:
        return error

    person_node, file_node = result
    file_id = file_node["id"]

    query_data = {
        "query": """
            MATCH (f1:File)-[:UPLOADED_WITH]-(f2:File)
            WHERE elementId(f1) = $file_id
            RETURN f2
        """,
        "parameters": {
            "file_id": file_id
        }
    }

    result = call_database("POST", "query/cypher", query_data)

    related_files = []
    for record in result.get("results", []):
        if "f2" in record:
            related_files.append(record["f2"])

    return jsonify({
        "person": person_name,
        "filename": safe_filename,
        "related_files": related_files
    })
