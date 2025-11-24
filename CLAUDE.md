# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Docker Compose microservices demo project with three Python Flask services:
- `echo`: Simple echo service that returns JSON data sent to it
- `database`: Graph database API service with full Neo4j integration for nodes, relationships, and queries
- `fileshare`: File storage service with graph-based tracking of uploads, downloads, and edits

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

The fileshare service has a similar modular structure:
```
services/fileshare/fileshare/
├── app.py           # Application factory and entry point
├── config.py        # Configuration (upload dir, database URL)
├── db_client.py     # Database service HTTP client
└── routes/
    ├── __init__.py
    ├── persons.py   # Person management and queries
    └── files.py     # File operations (upload, download, edit, delete)
```

### Dependency Management
- Uses `uv` for Python dependency management
- Root `pyproject.toml` defines workspace with all services as path dependencies
- Each service has its own `pyproject.toml` with service-specific dependencies
  - echo: Flask
  - database: Flask, neo4j driver
  - fileshare: Flask, requests (for calling database service)
- Services share the same Python environment for local development

### Docker Setup
- Each service runs Flask on port 5000 internally
- Mapped to host ports: echo (8080), database (8081), fileshare (8082)
- Volume types demonstrated:
  - **Bind mounts** (code hot-reloading): `./services/{name}/{name}:/app/{name}`
  - **Named volumes** (persistent data): `neo4j_data`, `neo4j_logs`, `fileshare_uploads`
- All services use Python 3.11-slim base image with `uv` package manager
- Service dependencies: fileshare depends on database, database depends on neo4j

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

cd services/fileshare
python -m fileshare.app
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
docker compose logs -f fileshare

# Rebuild a specific service
docker compose up --build fileshare
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

### File Share Service (Port 8082)
Demonstrates persistent volumes and service-to-service communication. Stores files in a named volume and tracks all file interactions in the graph database.

**Graph Schema:**
- Nodes: `Person` (name, email), `File` (filename, size, content_type, deleted)
- Relationships: `UPLOADED`, `DOWNLOADED`, `EDITED` (Person -> File), `UPLOADED_WITH` (File <-> File)

**Person Operations:**
- `POST /persons`: Create person (name must be unique)
- `GET /persons/<person_name>`: Get person by name
- `GET /persons`: List all persons
- `GET /persons/<person_name>/files`: Get files uploaded by person

**File Operations:**
- `POST /files/upload`: Upload single file (requires person name, filename must be unique per person)
- `POST /files/upload/batch`: Upload multiple files, creates UPLOADED_WITH relationships
- `GET /files`: List all files
- `GET /files/<person>/<filename>/download`: Download file and track download
- `PUT /files/<person>/<filename>`: Edit/replace file content
- `DELETE /files/<person>/<filename>`: Soft delete (marks as deleted, removes physical file)

**Query Operations:**
- `GET /files/<person>/<filename>/history`: Get all interactions with file
- `GET /files/<person>/<filename>/batch-related`: Get files uploaded in same batch

**Health:**
- `GET /health`: Health check

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

# Test fileshare service
# Create a person
curl -X POST http://localhost:8082/persons \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "alice@example.com"}'

# Try to create duplicate person (will fail with 409)
curl -X POST http://localhost:8082/persons \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "different@example.com"}'

# Upload a file
echo "Hello World" > test.txt
curl -X POST http://localhost:8082/files/upload \
  -F "file=@test.txt" \
  -F "person=Alice"

# Try to upload duplicate file (will fail with 409)
curl -X POST http://localhost:8082/files/upload \
  -F "file=@test.txt" \
  -F "person=Alice"

# Upload batch of files
echo "File 1" > file1.txt
echo "File 2" > file2.txt
curl -X POST http://localhost:8082/files/upload/batch \
  -F "files=@file1.txt" \
  -F "files=@file2.txt" \
  -F "person=Alice"

# Download a file
curl http://localhost:8082/files/Alice/test.txt/download -o downloaded.txt

# Edit a file
echo "Updated content" > updated.txt
curl -X PUT http://localhost:8082/files/Alice/test.txt \
  -F "file=@updated.txt"

# Get file history
curl http://localhost:8082/files/Alice/test.txt/history

# Get files uploaded in same batch
curl http://localhost:8082/files/Alice/file1.txt/batch-related

# Get files uploaded by person
curl http://localhost:8082/persons/Alice/files

# Delete a file
curl -X DELETE http://localhost:8082/files/Alice/test.txt

# Try operations with non-existent person (will fail with 404)
curl -X POST http://localhost:8082/files/upload \
  -F "file=@test.txt" \
  -F "person=Bob"
```

## Key Implementation Notes

- **Database service**: Full Neo4j integration with proper validation and error handling
- **File share service**: Demonstrates both persistent volumes (for uploads) and service-to-service HTTP communication (calls database service)
- All services use Flask's development mode with debug=True
- Type hints are used throughout (Python 3.11+ style with `|` union syntax)
- Volume mounts enable code changes without rebuilding containers
- Modular architecture: database and fileshare services use separate route modules for better organization
- Soft delete pattern: fileshare marks files as deleted in database but removes physical files
