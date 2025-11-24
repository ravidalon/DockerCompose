"""Input validation and sanitization utilities."""

from pathlib import Path
from flask import jsonify


def sanitize_filename(filename: str) -> tuple[str | None, tuple[dict, int] | None]:
    """Sanitize and validate a filename.

    Args:
        filename: The filename to sanitize

    Returns:
        Tuple of (sanitized_filename, error_response). If valid, returns (filename, None).
        If invalid, returns (None, error_response).
    """
    if not filename or filename.strip() == "":
        return None, (jsonify({"error": "Filename cannot be empty"}), 400)

    # Use Path().name to strip any directory components (prevents path traversal)
    safe_filename = Path(filename).name

    # Check if the filename was modified (indicates attempted path traversal)
    if safe_filename != filename:
        return None, (jsonify({"error": "Filename contains invalid path components"}), 400)

    # Reject hidden files (starting with .)
    if safe_filename.startswith('.'):
        return None, (jsonify({"error": "Hidden files are not allowed"}), 400)

    # Reject filenames that are too long
    if len(safe_filename) > 255:
        return None, (jsonify({"error": "Filename is too long (max 255 characters)"}), 400)

    return safe_filename, None


def validate_file_upload(file, max_size_mb: int = 100) -> tuple[bool, tuple[dict, int] | None]:
    """Validate an uploaded file.

    Args:
        file: The uploaded file object
        max_size_mb: Maximum file size in megabytes

    Returns:
        Tuple of (is_valid, error_response). If valid, returns (True, None).
        If invalid, returns (False, error_response).
    """
    if not file or file.filename == "":
        return False, (jsonify({"error": "No file selected"}), 400)

    # Validate filename
    safe_filename, error = sanitize_filename(file.filename)
    if error:
        return False, error

    # Check file size if possible (not all WSGI servers provide content_length)
    if hasattr(file, 'content_length') and file.content_length:
        max_size_bytes = max_size_mb * 1024 * 1024
        if file.content_length > max_size_bytes:
            return False, (jsonify({"error": f"File size exceeds {max_size_mb}MB limit"}), 400)

    return True, None


# Allowed MIME types - can be configured based on requirements
ALLOWED_CONTENT_TYPES = {
    # Documents
    'text/plain',
    'text/csv',
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',

    # Images
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',

    # Archives
    'application/zip',
    'application/x-tar',
    'application/gzip',

    # Code and config
    'application/json',
    'application/xml',
    'text/html',
    'text/css',
    'text/javascript',
    'application/javascript',
}


def validate_content_type(content_type: str | None) -> tuple[bool, tuple[dict, int] | None]:
    """Validate file content type.

    Args:
        content_type: The MIME type of the file

    Returns:
        Tuple of (is_valid, error_response). If valid, returns (True, None).
        If invalid, returns (False, error_response).
    """
    if not content_type:
        # Default to octet-stream if not provided
        return True, None

    # Extract base content type (remove parameters like charset)
    base_type = content_type.split(';')[0].strip().lower()

    if base_type not in ALLOWED_CONTENT_TYPES:
        return False, (jsonify({
            "error": f"File type '{base_type}' is not allowed",
            "allowed_types": sorted(list(ALLOWED_CONTENT_TYPES))
        }), 400)

    return True, None
