import atexit
import logging
import sys

from flask import Flask, jsonify

from database.db import close_db
from database.routes import nodes_bp, relationships_bp, queries_bp, utils_bp

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)

    app.register_blueprint(nodes_bp)
    app.register_blueprint(relationships_bp)
    app.register_blueprint(queries_bp)
    app.register_blueprint(utils_bp)

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        logger.error(f"Unhandled exception: {error}", exc_info=True)
        return jsonify({"error": "Internal server error", "type": type(error).__name__}), 500

    return app


app = create_app()
atexit.register(close_db)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
