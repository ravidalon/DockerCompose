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
- **Traefik** reverse proxy routes external traffic:
  - `/echo/*` → echo service (public)
  - `/fileshare/*` → fileshare service (public)
  - database service: internal only (no external access)
- Traefik dashboard available at `http://localhost:8080`
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

All services are accessed through Traefik on port 80 with path-based routing:

```bash
# Test echo service (accessible via Traefik)
curl -X POST http://localhost/echo/echo \
  -H "Content-Type: application/json" \
  -d '{"message": "hello"}'

# Echo health check
curl http://localhost/echo/health

# Database service (internal only - not accessible via Traefik)
# Returns 404: curl http://localhost/database/health

# Test fileshare service (accessible via Traefik)
# Create a person
curl -X POST http://localhost/fileshare/persons \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "alice@example.com"}'

# Try to create duplicate person (will fail with 409)
curl -X POST http://localhost/fileshare/persons \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "different@example.com"}'

# Upload a file
echo "Hello World" > test.txt
curl -X POST http://localhost/fileshare/files/upload \
  -F "file=@test.txt" \
  -F "person=Alice"

# Try to upload duplicate file (will fail with 409)
curl -X POST http://localhost/fileshare/files/upload \
  -F "file=@test.txt" \
  -F "person=Alice"

# Upload batch of files
echo "File 1" > file1.txt
echo "File 2" > file2.txt
curl -X POST http://localhost/fileshare/files/upload/batch \
  -F "files=@file1.txt" \
  -F "files=@file2.txt" \
  -F "person=Alice"

# Download a file
curl http://localhost/fileshare/files/Alice/test.txt/download -o downloaded.txt

# Edit a file
echo "Updated content" > updated.txt
curl -X PUT http://localhost/fileshare/files/Alice/test.txt \
  -F "file=@updated.txt"

# Get file history
curl http://localhost/fileshare/files/Alice/test.txt/history

# Get files uploaded in same batch
curl http://localhost/fileshare/files/Alice/file1.txt/batch-related

# Get files uploaded by person
curl http://localhost/fileshare/persons/Alice/files

# Delete a file
curl -X DELETE http://localhost/fileshare/files/Alice/test.txt

# Try operations with non-existent person (will fail with 404)
curl -X POST http://localhost/fileshare/files/upload \
  -F "file=@test.txt" \
  -F "person=Bob"

# Access Traefik dashboard
open http://localhost:8080
```

## Troubleshooting

### Services return 404
- **Check Traefik dashboard**: Visit http://localhost:8080 to see registered routes and service health
- **Verify containers are running**: `docker compose ps` should show all services as "Up"
- **Check Traefik logs**: `docker compose logs traefik` for routing errors
- **Verify service labels**: Ensure Traefik labels are correctly set in docker-compose.yml

### Gateway Timeout (504) errors
- Services may still be starting up - wait 10-20 seconds
- Check if backend service is healthy: `docker compose ps`
- Check service logs: `docker compose logs -f <service_name>`
- Verify service is listening on the correct port (5000)

### Port conflicts
If port 80 or 8080 is already in use:
```bash
# Check what's using the ports
lsof -i :80
lsof -i :8080

# Stop conflicting services or change ports in docker-compose.yml
```

### Changes not reflected
- **Code changes**: Should hot-reload automatically via bind mounts
- **Docker Compose changes**: Restart services with `docker compose up -d`
- **Traefik routing changes**: Traefik picks up label changes automatically

### Database connection issues
- Ensure Neo4j is fully started before other services
- Check Neo4j logs: `docker compose logs neo4j`
- Verify database service can reach Neo4j: `docker compose exec database curl http://neo4j:7474`

## Key Implementation Notes

- **Traefik reverse proxy**: Path-based routing with automatic service discovery via Docker labels
  - Public services (echo, fileshare) accessible via `/echo/*` and `/fileshare/*`
  - Internal services (database, neo4j) not exposed externally
  - Dashboard available at port 8080 for monitoring and debugging
- **Database service**: Full Neo4j integration with proper validation and error handling
- **File share service**: Demonstrates both persistent volumes (for uploads) and service-to-service HTTP communication (calls database service)
- **Security**: Fileshare service uses parameterized queries to prevent Cypher injection, filename sanitization to prevent path traversal, and file type/size validation
- All services use Flask's development mode with debug=True
- Type hints are used throughout (Python 3.11+ style with `|` union syntax)
- Volume mounts enable code changes without rebuilding containers
- Modular architecture: database and fileshare services use separate route modules for better organization
- Soft delete pattern: fileshare marks files as deleted in database but removes physical files
