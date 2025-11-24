"""File share service with Neo4j graph database integration."""

from flask import Flask, jsonify
from .config import UPLOAD_DIR
from .routes import persons, files

app = Flask(__name__)

# Ensure upload directory exists
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Register blueprints
app.register_blueprint(persons.bp)
app.register_blueprint(files.bp)


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "fileshare"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
