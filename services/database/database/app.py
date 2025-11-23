import re
from typing import Any
from flask import Flask, request, jsonify
from werkzeug.wrappers.response import Response as WerkzeugResponse
from neo4j.exceptions import Neo4jError
from database.db import get_db, node_to_dict, relationship_to_dict, close_db

app = Flask(__name__)

# Input validation regex for Neo4j identifiers (labels, relationship types)
IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

def validate_identifier(value: str, name: str = "identifier") -> tuple[bool, str | None]:
    """Validate Neo4j identifier (label or relationship type) to prevent injection"""
    if not value:
        return False, f"{name} cannot be empty"
    if not IDENTIFIER_PATTERN.match(value):
        return False, f"{name} must contain only alphanumeric characters and underscores, and start with a letter"
    if len(value) > 65535:  # Neo4j max identifier length
        return False, f"{name} is too long (max 65535 characters)"
    return True, None

def validate_identifiers(values: list[str], name: str = "identifiers") -> tuple[bool, str | None]:
    """Validate multiple Neo4j identifiers"""
    for value in values:
        is_valid, error = validate_identifier(value, name)
        if not is_valid:
            return False, error
    return True, None

@app.teardown_appcontext
def teardown_db(exception: Exception | None = None) -> None:
    """Close database connection on application context teardown"""
    close_db()

# ============================================================================
# NODE OPERATIONS
# ============================================================================

@app.route('/nodes', methods=['POST'])
def create_node() -> tuple[WerkzeugResponse, int]:
    """Create a new node with labels and properties

    Expected JSON body:
    {
        "labels": ["Person", "Employee"],
        "properties": {
            "name": "John",
            "age": 30
        }
    }
    """
    data: dict[str, Any] | None = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    labels: list[str] = data.get("labels", [])
    properties: dict[str, Any] = data.get("properties", {})

    if not labels:
        return jsonify({"error": "At least one label is required"}), 400

    # Validate labels to prevent Cypher injection
    is_valid, error = validate_identifiers(labels, "label")
    if not is_valid:
        return jsonify({"error": error}), 400

    try:
        driver = get_db()
        with driver.session() as session:
            # Build Cypher query dynamically (safe after validation)
            labels_str = ':'.join(labels)
            query = f"CREATE (n:{labels_str} $properties) RETURN n"
            result = session.run(query, properties=properties)
            record = result.single()

            if record:
                node = record["n"]
                return jsonify(node_to_dict(node)), 201

            return jsonify({"error": "Failed to create node"}), 500
    except Neo4jError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/nodes/<node_id>', methods=['GET'])
def get_node(node_id: str) -> tuple[WerkzeugResponse, int]:
    """Get a node by ID"""
    try:
        driver = get_db()
        with driver.session() as session:
            query = "MATCH (n) WHERE elementId(n) = $node_id RETURN n"
            result = session.run(query, node_id=node_id)
            record = result.single()

            if record:
                node = record["n"]
                return jsonify(node_to_dict(node)), 200

            return jsonify({"error": "Node not found"}), 404
    except Neo4jError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/nodes/<node_id>', methods=['PUT'])
def update_node(node_id: str) -> tuple[WerkzeugResponse, int]:
    """Update a node's properties

    Expected JSON body:
    {
        "properties": {
            "name": "Jane",
            "age": 31
        }
    }
    """
    data: dict[str, Any] | None = request.get_json()

    if not data or "properties" not in data:
        return jsonify({"error": "No properties provided"}), 400

    properties: dict[str, Any] = data["properties"]

    try:
        driver = get_db()
        with driver.session() as session:
            query = """
            MATCH (n) WHERE elementId(n) = $node_id
            SET n += $properties
            RETURN n
            """
            result = session.run(query, node_id=node_id, properties=properties)
            record = result.single()

            if record:
                node = record["n"]
                return jsonify(node_to_dict(node)), 200

            return jsonify({"error": "Node not found"}), 404
    except Neo4jError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/nodes/<node_id>', methods=['DELETE'])
def delete_node(node_id: str) -> tuple[WerkzeugResponse, int]:
    """Delete a node"""
    try:
        driver = get_db()
        with driver.session() as session:
            query = """
            MATCH (n) WHERE elementId(n) = $node_id
            DETACH DELETE n
            RETURN count(n) as deleted_count
            """
            result = session.run(query, node_id=node_id)
            record = result.single()

            if record and record["deleted_count"] > 0:
                return jsonify({"message": "Node deleted successfully"}), 200

            return jsonify({"error": "Node not found"}), 404
    except Neo4jError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/nodes/label/<label>', methods=['GET'])
def get_nodes_by_label(label: str) -> tuple[WerkzeugResponse, int]:
    """Get all nodes with a specific label"""
    # Validate label to prevent Cypher injection
    is_valid, error = validate_identifier(label, "label")
    if not is_valid:
        return jsonify({"error": error}), 400

    try:
        driver = get_db()
        with driver.session() as session:
            query = f"MATCH (n:{label}) RETURN n"
            result = session.run(query)
            nodes = [node_to_dict(record["n"]) for record in result]

            return jsonify({"nodes": nodes, "count": len(nodes)}), 200
    except Neo4jError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

# ============================================================================
# RELATIONSHIP/EDGE OPERATIONS
# ============================================================================

@app.route('/relationships', methods=['POST'])
def create_relationship() -> tuple[WerkzeugResponse, int]:
    """Create a relationship between two nodes

    Expected JSON body:
    {
        "from_node": "node_id_1",
        "to_node": "node_id_2",
        "type": "KNOWS",
        "properties": {
            "since": 2020
        }
    }
    """
    data: dict[str, Any] | None = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    from_node: str | None = data.get("from_node")
    to_node: str | None = data.get("to_node")
    rel_type: str | None = data.get("type")
    properties: dict[str, Any] = data.get("properties", {})

    if not from_node or not to_node or not rel_type:
        return jsonify({"error": "from_node, to_node, and type are required"}), 400

    # Validate relationship type to prevent Cypher injection
    is_valid, error = validate_identifier(rel_type, "relationship type")
    if not is_valid:
        return jsonify({"error": error}), 400

    try:
        driver = get_db()
        with driver.session() as session:
            query = f"""
            MATCH (a) WHERE elementId(a) = $from_node
            MATCH (b) WHERE elementId(b) = $to_node
            CREATE (a)-[r:{rel_type} $properties]->(b)
            RETURN r
            """
            result = session.run(query, from_node=from_node, to_node=to_node, properties=properties)
            record = result.single()

            if record:
                rel = record["r"]
                return jsonify(relationship_to_dict(rel)), 201

            return jsonify({"error": "Failed to create relationship. Nodes may not exist."}), 404
    except Neo4jError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/relationships/<relationship_id>', methods=['GET'])
def get_relationship(relationship_id: str) -> tuple[WerkzeugResponse, int]:
    """Get a relationship by ID"""
    try:
        driver = get_db()
        with driver.session() as session:
            query = "MATCH ()-[r]->() WHERE elementId(r) = $relationship_id RETURN r"
            result = session.run(query, relationship_id=relationship_id)
            record = result.single()

            if record:
                rel = record["r"]
                return jsonify(relationship_to_dict(rel)), 200

            return jsonify({"error": "Relationship not found"}), 404
    except Neo4jError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/relationships/<relationship_id>', methods=['PUT'])
def update_relationship(relationship_id: str) -> tuple[WerkzeugResponse, int]:
    """Update a relationship's properties

    Expected JSON body:
    {
        "properties": {
            "since": 2021
        }
    }
    """
    data: dict[str, Any] | None = request.get_json()

    if not data or "properties" not in data:
        return jsonify({"error": "No properties provided"}), 400

    properties: dict[str, Any] = data["properties"]

    try:
        driver = get_db()
        with driver.session() as session:
            query = """
            MATCH ()-[r]->() WHERE elementId(r) = $relationship_id
            SET r += $properties
            RETURN r
            """
            result = session.run(query, relationship_id=relationship_id, properties=properties)
            record = result.single()

            if record:
                rel = record["r"]
                return jsonify(relationship_to_dict(rel)), 200

            return jsonify({"error": "Relationship not found"}), 404
    except Neo4jError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/relationships/<relationship_id>', methods=['DELETE'])
def delete_relationship(relationship_id: str) -> tuple[WerkzeugResponse, int]:
    """Delete a relationship"""
    try:
        driver = get_db()
        with driver.session() as session:
            query = """
            MATCH ()-[r]->() WHERE elementId(r) = $relationship_id
            DELETE r
            RETURN count(r) as deleted_count
            """
            result = session.run(query, relationship_id=relationship_id)
            record = result.single()

            if record and record["deleted_count"] > 0:
                return jsonify({"message": "Relationship deleted successfully"}), 200

            return jsonify({"error": "Relationship not found"}), 404
    except Neo4jError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/relationships/type/<rel_type>', methods=['GET'])
def get_relationships_by_type(rel_type: str) -> tuple[WerkzeugResponse, int]:
    """Get all relationships of a specific type"""
    # Validate relationship type to prevent Cypher injection
    is_valid, error = validate_identifier(rel_type, "relationship type")
    if not is_valid:
        return jsonify({"error": error}), 400

    try:
        driver = get_db()
        with driver.session() as session:
            query = f"MATCH ()-[r:{rel_type}]->() RETURN r"
            result = session.run(query)
            relationships = [relationship_to_dict(record["r"]) for record in result]

            return jsonify({"relationships": relationships, "count": len(relationships)}), 200
    except Neo4jError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/nodes/<node_id>/relationships', methods=['GET'])
def get_node_relationships(node_id: str) -> tuple[WerkzeugResponse, int]:
    """Get all relationships for a specific node

    Query params:
    - direction: "incoming", "outgoing", or "all" (default: "all")
    - type: filter by relationship type (optional)
    """
    direction: str = request.args.get('direction', 'all')
    rel_type: str | None = request.args.get('type')

    # Validate relationship type if provided
    if rel_type:
        is_valid, error = validate_identifier(rel_type, "relationship type")
        if not is_valid:
            return jsonify({"error": error}), 400

    try:
        driver = get_db()
        with driver.session() as session:
            # Build query based on direction and type
            if direction == "incoming":
                pattern = "<-[r]-()"
            elif direction == "outgoing":
                pattern = "-[r]->()"
            else:  # all
                pattern = "-[r]-()"

            if rel_type:
                pattern = pattern.replace("[r]", f"[r:{rel_type}]")

            query = f"""
            MATCH (n){pattern}
            WHERE elementId(n) = $node_id
            RETURN r
            """
            result = session.run(query, node_id=node_id)
            relationships = [relationship_to_dict(record["r"]) for record in result]

            return jsonify({"relationships": relationships, "count": len(relationships)}), 200
    except Neo4jError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

# ============================================================================
# QUERY OPERATIONS
# ============================================================================

@app.route('/query/cypher', methods=['POST'])
def execute_cypher() -> tuple[WerkzeugResponse, int]:
    """Execute a custom Cypher query

    Expected JSON body:
    {
        "query": "MATCH (n:Person) WHERE n.age > $age RETURN n",
        "parameters": {
            "age": 25
        }
    }
    """
    data: dict[str, Any] | None = request.get_json()

    if not data or 'query' not in data:
        return jsonify({"error": "No query provided"}), 400

    query: str = data['query']
    parameters: dict[str, Any] = data.get('parameters', {})

    try:
        driver = get_db()
        with driver.session() as session:
            result = session.run(query, **parameters)
            records = []

            for record in result:
                record_dict: dict[str, Any] = {}
                for key in record.keys():
                    value = record[key]
                    # Convert Neo4j types to dicts
                    if hasattr(value, 'labels'):  # Node
                        record_dict[key] = node_to_dict(value)
                    elif hasattr(value, 'type') and hasattr(value, 'start_node'):  # Relationship
                        record_dict[key] = relationship_to_dict(value)
                    else:
                        record_dict[key] = value
                records.append(record_dict)

            return jsonify({"results": records, "count": len(records)}), 200
    except Neo4jError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/query/path', methods=['POST'])
def find_path() -> tuple[WerkzeugResponse, int]:
    """Find path between two nodes

    Expected JSON body:
    {
        "from_node": "node_id_1",
        "to_node": "node_id_2",
        "max_depth": 5,
        "relationship_types": ["KNOWS", "WORKS_WITH"]
    }
    """
    data: dict[str, Any] | None = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    from_node: str | None = data.get("from_node")
    to_node: str | None = data.get("to_node")
    max_depth: int = data.get("max_depth", 5)
    rel_types: list[str] | None = data.get("relationship_types")

    if not from_node or not to_node:
        return jsonify({"error": "from_node and to_node are required"}), 400

    # Validate max_depth to prevent resource exhaustion
    if not isinstance(max_depth, int) or max_depth < 1 or max_depth > 15:
        return jsonify({"error": "max_depth must be an integer between 1 and 15"}), 400

    # Validate relationship types if provided
    if rel_types:
        is_valid, error = validate_identifiers(rel_types, "relationship type")
        if not is_valid:
            return jsonify({"error": error}), 400

    try:
        driver = get_db()
        with driver.session() as session:
            # Build relationship type filter (safe after validation)
            rel_filter = ""
            if rel_types:
                rel_filter = ":" + "|".join(rel_types)

            query = f"""
            MATCH path = shortestPath(
                (a)-[{rel_filter}*..{max_depth}]-(b)
            )
            WHERE elementId(a) = $from_node AND elementId(b) = $to_node
            RETURN path
            """
            result = session.run(query, from_node=from_node, to_node=to_node)
            record = result.single()

            if record:
                path = record["path"]
                nodes = [node_to_dict(node) for node in path.nodes]
                relationships = [relationship_to_dict(rel) for rel in path.relationships]

                return jsonify({
                    "path": {
                        "nodes": nodes,
                        "relationships": relationships,
                        "length": len(relationships)
                    }
                }), 200

            return jsonify({"error": "No path found between the nodes"}), 404
    except Neo4jError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

# ============================================================================
# UTILITY OPERATIONS
# ============================================================================

@app.route('/health', methods=['GET'])
def health() -> tuple[WerkzeugResponse, int]:
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

@app.route('/stats', methods=['GET'])
def get_stats() -> tuple[WerkzeugResponse, int]:
    """Get database statistics"""
    try:
        driver = get_db()
        with driver.session() as session:
            # Get node count
            node_count_result = session.run("MATCH (n) RETURN count(n) as count")
            node_count = node_count_result.single()["count"]

            # Get relationship count
            rel_count_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = rel_count_result.single()["count"]

            # Get all labels
            labels_result = session.run("CALL db.labels()")
            labels = [record["label"] for record in labels_result]

            # Get all relationship types
            rel_types_result = session.run("CALL db.relationshipTypes()")
            rel_types = [record["relationshipType"] for record in rel_types_result]

            return jsonify({
                "stats": {
                    "node_count": node_count,
                    "relationship_count": rel_count,
                    "labels": labels,
                    "relationship_types": rel_types
                }
            }), 200
    except Neo4jError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
