"""Routes package initialization"""
from database.routes.nodes import nodes_bp
from database.routes.relationships import relationships_bp
from database.routes.queries import queries_bp
from database.routes.utils import utils_bp


__all__ = ['nodes_bp', 'relationships_bp', 'queries_bp', 'utils_bp']
