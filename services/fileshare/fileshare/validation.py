from pathlib import Path

from flask import jsonify


def sanitize_filename(filename: str) -> tuple[str | None, tuple[dict, int] | None]:
    """Sanitize filename to prevent path traversal attacks"""
    if not filename or filename.strip() == "":
        return None, (jsonify({"error": "Filename cannot be empty"}), 400)

    # Prevent path traversal by extracting only the filename
    safe_filename = Path(filename).name

    if safe_filename != filename:
        return None, (jsonify({"error": "Filename contains invalid path components"}), 400)

    if safe_filename.startswith('.'):
        return None, (jsonify({"error": "Hidden files are not allowed"}), 400)

    # Neo4j has a max property size, keep filenames reasonable
    if len(safe_filename) > 255:
        return None, (jsonify({"error": "Filename is too long (max 255 characters)"}), 400)

    return safe_filename, None


def validate_file_upload(file, max_size_mb: int = 100) -> tuple[bool, tuple[dict, int] | None]:
    if not file or file.filename == "":
        return False, (jsonify({"error": "No file selected"}), 400)

    safe_filename, error = sanitize_filename(file.filename)
    if error:
        return False, error

    if hasattr(file, 'content_length') and file.content_length:
        max_size_bytes = max_size_mb * 1024 * 1024
        if file.content_length > max_size_bytes:
            return False, (jsonify({"error": f"File size exceeds {max_size_mb}MB limit"}), 400)

    return True, None


ALLOWED_CONTENT_TYPES = {
    'text/plain',
    'text/csv',
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
    'application/zip',
    'application/x-tar',
    'application/gzip',
    'application/json',
    'application/xml',
    'text/html',
    'text/css',
    'text/javascript',
    'application/javascript',
}


def validate_content_type(content_type: str | None) -> tuple[bool, tuple[dict, int] | None]:
    if not content_type:
        return True, None

    base_type = content_type.split(';')[0].strip().lower()

    if base_type not in ALLOWED_CONTENT_TYPES:
        return False, (jsonify({
            "error": f"File type '{base_type}' is not allowed",
            "allowed_types": sorted(list(ALLOWED_CONTENT_TYPES))
        }), 400)

    return True, None
