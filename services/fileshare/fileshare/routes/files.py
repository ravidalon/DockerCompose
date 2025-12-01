import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Blueprint, request, jsonify, send_file
from werkzeug.datastructures import FileStorage
from werkzeug.wrappers.response import Response as WerkzeugResponse

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


def get_current_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_person(person_name: str) -> tuple[dict | None, tuple[WerkzeugResponse, int] | None]:
    person_node = get_person_by_name(person_name)
    if not person_node:
        return None, (jsonify({"error": f"Person '{person_name}' not found"}), 404)
    return person_node, None


def validate_person_and_file(
    person_name: str,
    filename: str
) -> tuple[tuple[dict, dict] | None, tuple[WerkzeugResponse, int] | None]:
    person_node, error = validate_person(person_name)
    if error:
        return None, error

    file_node = get_file_by_person_and_filename(person_name, filename)
    if not file_node:
        return None, (jsonify({"error": f"File '{filename}' not found for person '{person_name}'"}), 404)

    return (person_node, file_node), None


def create_relationship(from_node_id: str, to_node_id: str, rel_type: str) -> None:
    logger.debug(f"Creating {rel_type} relationship: {from_node_id} -> {to_node_id}")

    rel_data = {
        "from_node": from_node_id,
        "to_node": to_node_id,
        "type": rel_type,
        "properties": {
            "timestamp": get_current_timestamp()
        }
    }

    try:
        result = call_database("POST", "relationships", rel_data)
        logger.debug(f"Relationship created successfully: {result}")
    except RuntimeError as e:
        logger.error(f"Failed to create {rel_type} relationship: {e}")
        raise


def create_file_node(file: FileStorage, safe_filename: str) -> dict:
    file_path = UPLOAD_DIR / safe_filename

    file_data = {
        "labels": ["File"],
        "properties": {
            "filename": safe_filename,
            "size": file_path.stat().st_size,
            "content_type": file.content_type or "application/octet-stream",
            "created_at": get_current_timestamp(),
            "updated_at": get_current_timestamp(),
            "deleted": False
        }
    }

    return call_database("POST", "nodes", file_data)


@bp.route("/upload", methods=["POST"])
def upload_file() -> tuple[WerkzeugResponse, int]:
    """Upload file and create UPLOADED relationship"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    if "person" not in request.form:
        return jsonify({"error": "person is required"}), 400

    file = request.files["file"]
    person_name = request.form["person"]

    is_valid, error = validate_file_upload(file)
    if not is_valid:
        return error

    safe_filename, error = sanitize_filename(file.filename)
    if error:
        return error

    is_valid, error = validate_content_type(file.content_type)
    if not is_valid:
        return error

    person_node, error = validate_person(person_name)
    if error:
        return error

    if file_exists_for_person(person_name, safe_filename):
        return jsonify({"error": f"File '{safe_filename}' already exists for person '{person_name}'"}), 409

    file_path = UPLOAD_DIR / safe_filename
    try:
        file.save(file_path)
    except Exception as e:
        return jsonify({"error": f"Failed to save file: {str(e)}"}), 500

    file_node = create_file_node(file, safe_filename)
    create_relationship(person_node["id"], file_node["id"], "UPLOADED")

    return jsonify({
        "file": file_node,
        "message": "File uploaded successfully"
    }), 201


def process_single_batch_file(
    file: FileStorage,
    person_name: str,
    seen_filenames: set[str]
) -> tuple[dict | None, tuple[WerkzeugResponse, int] | None]:
    is_valid, error = validate_file_upload(file)
    if not is_valid:
        return None, error

    safe_filename, error = sanitize_filename(file.filename)
    if error:
        return None, error

    is_valid, error = validate_content_type(file.content_type)
    if not is_valid:
        return None, error

    if safe_filename in seen_filenames:
        return None, (jsonify({"error": f"Duplicate filename in batch: '{safe_filename}'"}), 400)

    if file_exists_for_person(person_name, safe_filename):
        return None, (jsonify({"error": f"File '{safe_filename}' already exists for person '{person_name}'"}), 409)

    file_path = UPLOAD_DIR / safe_filename
    try:
        file.save(file_path)
    except Exception as e:
        return None, (jsonify({"error": f"Failed to save file '{safe_filename}': {str(e)}"}), 500)

    file_node = create_file_node(file, safe_filename)
    return file_node, None


def create_batch_relationships(file_ids: list[str]) -> None:
    """Create bidirectional UPLOADED_WITH relationships between all files"""
    for i, file_id_a in enumerate(file_ids):
        for file_id_b in file_ids[i + 1:]:
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


@bp.route("/upload/batch", methods=["POST"])
def upload_batch() -> tuple[WerkzeugResponse, int]:
    """Upload multiple files and create UPLOADED_WITH relationships"""
    if "person" not in request.form:
        return jsonify({"error": "person is required"}), 400

    person_name = request.form["person"]
    files = request.files.getlist("files")

    if not files:
        return jsonify({"error": "No files provided"}), 400

    person_node, error = validate_person(person_name)
    if error:
        return error

    person_element_id = person_node["id"]
    uploaded_files: list[dict] = []
    file_ids: list[str] = []
    seen_filenames: set[str] = set()

    for file in files:
        file_node, error = process_single_batch_file(file, person_name, seen_filenames)
        if error:
            return error

        safe_filename = file_node["properties"]["filename"]
        seen_filenames.add(safe_filename)

        file_id = file_node["id"]
        file_ids.append(file_id)
        uploaded_files.append(file_node)

        create_relationship(person_element_id, file_id, "UPLOADED")

    create_batch_relationships(file_ids)

    return jsonify({
        "files": uploaded_files,
        "count": len(uploaded_files),
        "message": f"Batch upload successful: {len(uploaded_files)} files"
    }), 201


@bp.route("/<path:file_id>", methods=["GET"])
def get_file(file_id: str) -> tuple[WerkzeugResponse, int]:
    """Get file by ID"""
    result = call_database("GET", f"nodes/{file_id}", None)
    return jsonify(result)


@bp.route("", methods=["GET"])
def list_files() -> tuple[WerkzeugResponse, int]:
    """List all files"""
    result = call_database("GET", "nodes/label/File", None)
    return jsonify(result)


@bp.route("/<person_name>/<filename>/download", methods=["GET"])
def download_file(person_name: str, filename: str) -> tuple[WerkzeugResponse, int]:
    """Download file and create DOWNLOADED relationship"""
    logger.info(f"Download request: person={person_name}, filename={filename}")

    try:
        safe_filename, error = sanitize_filename(filename)
        if error:
            logger.warning(f"Filename sanitization failed: {filename}")
            return error

        result, error = validate_person_and_file(person_name, safe_filename)
        if error:
            logger.warning(f"Validation failed for {person_name}/{safe_filename}")
            return error

        person_node, file_node = result

        if not person_node.get("id"):
            logger.error(f"Person node missing ID field: {person_node}")
            return jsonify({"error": "Invalid person data from database"}), 500

        if not file_node.get("id"):
            logger.error(f"File node missing ID field: {file_node}")
            return jsonify({"error": "Invalid file data from database"}), 500

        if file_node.get("properties", {}).get("deleted", False):
            logger.warning(f"Attempted to download deleted file: {person_name}/{safe_filename}")
            return jsonify({"error": "File has been deleted"}), 404

        file_path = UPLOAD_DIR / safe_filename

        if not file_path.exists():
            logger.error(f"File not found on disk: {file_path} (but exists in database)")
            return jsonify({"error": "File not found on disk"}), 404

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
def edit_file(person_name: str, filename: str) -> tuple[WerkzeugResponse, int]:
    """Edit file and create EDITED relationship"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]

    is_valid, error = validate_file_upload(file)
    if not is_valid:
        return error

    safe_filename, error = sanitize_filename(filename)
    if error:
        return error

    is_valid, error = validate_content_type(file.content_type)
    if not is_valid:
        return error

    result, error = validate_person_and_file(person_name, safe_filename)
    if error:
        return error

    person_node, file_node = result

    if file_node.get("properties", {}).get("deleted", False):
        return jsonify({"error": "Cannot edit deleted file"}), 400

    file_path = UPLOAD_DIR / safe_filename
    try:
        file.save(file_path)
    except Exception as e:
        return jsonify({"error": f"Failed to save file: {str(e)}"}), 500

    file_id = file_node["id"]
    update_data = {
        "properties": {
            "size": file_path.stat().st_size,
            "content_type": file.content_type or "application/octet-stream",
            "updated_at": get_current_timestamp()
        }
    }

    updated_node = call_database("PUT", f"nodes/{file_id}", update_data)
    create_relationship(person_node["id"], file_id, "EDITED")

    return jsonify({
        "file": updated_node,
        "message": "File edited successfully"
    })


@bp.route("/<person_name>/<filename>", methods=["DELETE"])
def delete_file(person_name: str, filename: str) -> tuple[WerkzeugResponse, int]:
    """Soft delete file (marks deleted in DB, removes physical file)"""
    safe_filename, error = sanitize_filename(filename)
    if error:
        return error

    result, error = validate_person_and_file(person_name, safe_filename)
    if error:
        return error

    person_node, file_node = result

    if file_node.get("properties", {}).get("deleted", False):
        return jsonify({"error": "File already deleted"}), 400

    file_path = UPLOAD_DIR / safe_filename
    file_id = file_node["id"]

    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as e:
            return jsonify({"error": f"Failed to delete physical file: {str(e)}"}), 500

    update_data = {
        "properties": {
            "deleted": True,
            "deleted_at": get_current_timestamp()
        }
    }

    updated_node = call_database("PUT", f"nodes/{file_id}", update_data)

    return jsonify({
        "file": updated_node,
        "message": "File deleted successfully"
    })


@bp.route("/<person_name>/<filename>/history", methods=["GET"])
def get_file_history(person_name: str, filename: str) -> tuple[WerkzeugResponse, int]:
    """Get all file interactions (relationships)"""
    safe_filename, error = sanitize_filename(filename)
    if error:
        return error

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
def get_batch_related(person_name: str, filename: str) -> tuple[WerkzeugResponse, int]:
    """Get files uploaded in same batch"""
    safe_filename, error = sanitize_filename(filename)
    if error:
        return error

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

    related_files: list[dict] = []
    for record in result.get("results", []):
        if "f2" in record:
            related_files.append(record["f2"])

    return jsonify({
        "person": person_name,
        "filename": safe_filename,
        "related_files": related_files
    })
