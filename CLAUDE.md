# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Docker Compose microservices demo project with two Python Flask services:
- `echo`: Simple echo service that returns JSON data sent to it
- `database`: Graph database API service with full Neo4j integration for nodes, relationships, and queries

## Architecture

### Service Structure
Each service follows this pattern:
```
services/{service_name}/
├── Dockerfile
├── pyproject.toml
├── uv.lock
├── {service_name}/
│   ├── __init__.py
│   └── app.py
```

The database service has additional modular structure:
```
services/database/database/
├── app.py           # Application factory and entry point
├── db.py            # Neo4j database connection management
├── validation.py    # Input validation to prevent injection attacks
└── routes/
    ├── __init__.py
    ├── nodes.py         # Node CRUD operations
    ├── relationships.py # Relationship CRUD operations
    ├── queries.py       # Cypher queries and path finding
    └── utils.py         # Health check and statistics
```

### Dependency Management
- Uses `uv` for Python dependency management
- Root `pyproject.toml` defines workspace with both services as path dependencies
- Each service has its own `pyproject.toml` with Flask dependency
- Services share the same Python environment for local development

### Docker Setup
- Each service runs Flask on port 5000 internally
- Mapped to host ports: echo (8080), database (8081)
- Volume mounts allow hot-reloading during development: `./services/{name}/{name}:/app/{name}`
- All services use Python 3.11-slim base image with `uv` package manager

## Development Commands

### Local Development
```bash
# Install dependencies for all services
uv sync

# Run a specific service locally (from service directory)
cd services/echo
python -m echo.app

cd services/database
python -m database.app
```

### Docker Operations
```bash
# Build and start all services
docker compose up --build

# Start services in detached mode
docker compose up -d

# Stop all services
docker compose down

# View logs for all services
docker compose logs -f

# View logs for specific service
docker compose logs -f echo
docker compose logs -f database

# Rebuild a specific service
docker compose up --build echo
```

## Service Details

### Echo Service (Port 8080)
- `POST /echo`: Returns the JSON body sent to it
- `GET /health`: Health check endpoint

### Database Service (Port 8081)
Fully implemented Neo4j graph database API with the following endpoints:

**Node Operations:**
- `POST /nodes`: Create node with labels and properties
- `GET /nodes/<node_id>`: Retrieve node by ID
- `PUT /nodes/<node_id>`: Update node properties
- `DELETE /nodes/<node_id>`: Delete node
- `GET /nodes/label/<label>`: Get nodes by label

**Relationship Operations:**
- `POST /relationships`: Create relationship between nodes
- `GET /relationships/<relationship_id>`: Get relationship by ID
- `PUT /relationships/<relationship_id>`: Update relationship properties
- `DELETE /relationships/<relationship_id>`: Delete relationship
- `GET /relationships/type/<rel_type>`: Get relationships by type
- `GET /nodes/<node_id>/relationships`: Get relationships for a node (with direction/type filters)

**Query Operations:**
- `POST /query/cypher`: Execute Cypher query
- `POST /query/path`: Find path between nodes

**Utility:**
- `GET /health`: Health check
- `GET /stats`: Database statistics

## Testing Services

```bash
# Test echo service
curl -X POST http://localhost:8080/echo \
  -H "Content-Type: application/json" \
  -d '{"message": "hello"}'

# Test database service health
curl http://localhost:8081/health

# Create a node
curl -X POST http://localhost:8081/nodes \
  -H "Content-Type: application/json" \
  -d '{"labels": ["Person"], "properties": {"name": "John"}}'
```

## Key Implementation Notes

- Database service has full Neo4j integration with proper validation and error handling
- Both services use Flask's development mode with debug=True
- Type hints are used throughout (Python 3.11+ style with `|` union syntax)
- Volume mounts enable code changes without rebuilding containers
- Database service uses modular architecture with separate route modules for nodes, relationships, queries, and utilities
