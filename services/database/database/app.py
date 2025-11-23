"""Flask application entry point for Neo4j graph database API"""
from flask import Flask
from database.db import close_db
from database.routes import nodes_bp, relationships_bp, queries_bp, utils_bp


def create_app() -> Flask:
    """Application factory pattern"""
    app = Flask(__name__)

    # Register blueprints
    app.register_blueprint(nodes_bp)
    app.register_blueprint(relationships_bp)
    app.register_blueprint(queries_bp)
    app.register_blueprint(utils_bp)

    # Register teardown handler
    @app.teardown_appcontext
    def teardown_db(exception: Exception | None = None) -> None:
        """Close database connection on application context teardown"""
        close_db()

    return app


# Create application instance
app = create_app()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
