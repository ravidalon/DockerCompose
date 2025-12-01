import logging
import sys
import traceback

from typing import Any

from flask import Flask, jsonify, request
from werkzeug.wrappers.response import Response as WerkzeugResponse

from .config import UPLOAD_DIR
from .routes import persons, files

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app.register_blueprint(persons.bp)
app.register_blueprint(files.bp)


@app.route("/health", methods=["GET"])
def health() -> tuple[WerkzeugResponse, int]:
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "fileshare"})


@app.errorhandler(500)
def internal_error(error: Any) -> tuple[WerkzeugResponse, int]:
    logger.error(f"Internal Server Error: {error}")
    logger.error(f"Request: {request.method} {request.url}")
    logger.error(f"Request data: {request.get_data(as_text=True)[:500]}")
    logger.error(f"Traceback: {traceback.format_exc()}")

    return jsonify({
        "error": "Internal server error",
        "message": str(error),
        "path": request.path
    }), 500


@app.errorhandler(Exception)
def handle_exception(error: Exception) -> tuple[WerkzeugResponse, int]:
    logger.error(f"Unhandled exception: {error}")
    logger.error(f"Request: {request.method} {request.url}")
    logger.error(f"Traceback: {traceback.format_exc()}")

    return jsonify({
        "error": "Internal server error",
        "message": str(error),
        "type": type(error).__name__
    }), 500


if __name__ == "__main__":
    logger.info("Starting fileshare service on port 5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
