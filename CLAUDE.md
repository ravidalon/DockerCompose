# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Docker Compose microservices demo project with three Python Flask backend services and a Vue.js frontend:
- `echo`: Simple echo service that returns JSON data sent to it
- `database`: Graph database API service with full Neo4j integration for nodes, relationships, and queries
- `fileshare`: File storage service with graph-based tracking of uploads, downloads, and edits
- `frontend`: Vue 3 + Vite SPA for user-friendly file management interface

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

The frontend is a Vue 3 SPA:
```
frontend/
├── Dockerfile       # Multi-stage build: Node.js build + nginx serve
├── nginx.conf       # nginx config with SPA routing and API proxying
├── package.json     # Vue 3 and Vite dependencies
├── vite.config.js   # Vite configuration
├── index.html       # Entry HTML
└── src/
    ├── main.js          # App entry point
    ├── App.vue          # Root component
    ├── style.css        # Global styles
    └── components/
        ├── LoginView.vue    # User login/registration
        └── FileManager.vue  # File upload/download UI
```

### Dependency Management
- **Backend**: Uses `uv` for Python dependency management
  - Root `pyproject.toml` defines workspace with all services as path dependencies
  - Each service has its own `pyproject.toml` with service-specific dependencies
    - echo: Flask
    - database: Flask, neo4j driver
    - fileshare: Flask, requests (for calling database service)
  - Services share the same Python environment for local development
- **Frontend**: Uses npm for JavaScript dependency management
  - Vue 3 for reactive UI components
  - Vite for fast development and optimized production builds

### Docker Setup
- **Backend services** run Flask on port 5000 internally
- **Frontend** runs nginx on port 80 internally, built with multi-stage Docker build
- **Traefik** reverse proxy routes external traffic:
  - `/` → frontend (Vue SPA - lowest priority)
  - `/echo/*` → echo service (public)
  - `/fileshare/*` → fileshare service (public, proxied by frontend nginx and Traefik)
  - database service: internal only (no external access)
- Traefik dashboard available at `http://localhost:8080`
- Volume types demonstrated:
  - **Bind mounts** (code hot-reloading): `./services/{name}/{name}:/app/{name}`
  - **Named volumes** (persistent data): `neo4j_data`, `neo4j_logs`, `fileshare_uploads`
- Backend services use Python 3.11-slim base image with `uv` package manager
- Frontend uses Node.js 20 for build, nginx:alpine for serving
- Service dependencies: frontend depends on fileshare, fileshare depends on database, database depends on neo4j

## Development Commands

### Environment Configuration

The project uses environment files to configure services:

- **`default.env`**: Default configuration values (committed to repo)
- **`example.env`**: Template showing all available variables (committed to repo)
- **`.env`**: Optional local overrides (not committed, takes precedence)

To use custom configuration:
```bash
# Copy example and customize
cp example.env .env
# Edit .env with your values
```

Available environment variables:
- `NEO4J_USER`, `NEO4J_PASSWORD`: Neo4j credentials
- `NEO4J_HTTP_PORT`, `NEO4J_BOLT_PORT`: Neo4j port mappings
- `FLASK_ENV`: Flask environment mode
- `TRAEFIK_HTTP_PORT`, `TRAEFIK_DASHBOARD_PORT`: Traefik port mappings
- `TRAEFIK_LOG_LEVEL`: Traefik logging verbosity
- `UPLOAD_DIR`: File upload directory path
- `COMPOSE_PROJECT_NAME`: Docker Compose project name

### Docker Compose Profiles

Services are organized into profiles for different use cases:

- **`dev`** (default): Full stack including frontend
  - Includes: traefik, echo, database, fileshare, frontend, neo4j
  - Use for: Local development with web UI

- **`backend-only`**: Backend services without frontend
  - Includes: traefik, echo, database, fileshare, neo4j
  - Use for: API testing, backend development

- **`test`**: Backend services with integration test runner
  - Includes: traefik, echo, database, fileshare, neo4j, tests
  - Use for: Running integration tests in Docker

### Local Development
```bash
# Backend: Install dependencies for all services
uv sync

# Run a specific backend service locally (from service directory)
cd services/echo
python -m echo.app

cd services/database
python -m database.app

cd services/fileshare
python -m fileshare.app

# Frontend: Install dependencies and run dev server
cd frontend
npm install
npm run dev  # Runs on http://localhost:5173
```

### Docker Operations
```bash
# Build and start all services (uses 'dev' profile by default)
docker compose --env-file default.env --profile dev up --build

# Start with backend only (no frontend)
docker compose --env-file default.env --profile backend-only up --build

# Use custom environment file
docker compose --env-file .env --profile dev up --build

# Start services in detached mode
docker compose --env-file default.env --profile dev up -d

# Stop all services
docker compose down

# View logs for all services
docker compose logs -f

# View logs for specific service
docker compose logs -f echo
docker compose logs -f database
docker compose logs -f fileshare
docker compose logs -f frontend

# Rebuild a specific service
docker compose --env-file default.env --profile dev up --build fileshare
docker compose --env-file default.env --profile dev up --build frontend
```

### Running Tests

The project includes integration tests that verify the fileshare service correctly updates the Neo4j database.

**Test Coverage:**
- Person creation in database
- File upload (creates File node and UPLOADED relationship)
- File download (creates DOWNLOADED relationship)
- File edit (creates EDITED relationship)
- Batch file upload (creates UPLOADED_WITH relationships)

**Run tests using Docker Compose:**
```bash
# Run tests with the test profile
docker compose --env-file default.env --profile test up --build tests

# Run tests and exit (recommended for CI)
docker compose --env-file default.env --profile test up --build --exit-code-from tests tests

# Clean up after tests
docker compose --profile test down
```

**Run tests locally:**
```bash
# Install test dependencies
cd tests
uv sync

# Run tests
uv run pytest -v

# Run specific test
uv run pytest test_integration.py::test_person_creation_in_database -v

# Go back to root
cd ..
```

**Test Service Details:**
- Uses pytest for test framework
- Makes HTTP requests to fileshare API
- Queries Neo4j directly to verify database state
- Automatically cleans up test data after each test
- Runs in isolated Docker container with access to all backend services

## Service Details

### Frontend (Port 80 via Traefik)
A Vue 3 single-page application providing a user-friendly interface for file management.

**Features:**
- Simple name-based authentication (no actual auth, creates/fetches person from database)
- File upload with visual feedback
- File download via dropdown selection
- File list display with size formatting
- File deletion with confirmation
- Responsive design with modern UI

**Tech Stack:**
- Vue 3 Composition API with `<script setup>`
- Vite for development and build
- nginx for production serving
- API requests proxied to fileshare service

**User Flow:**
1. Enter name (and optionally email) on login screen
2. System checks if person exists, creates if not
3. Main interface shows:
   - User info with logout button
   - Upload section with file picker
   - Download section with dropdown of user's files
   - List of all user's files with delete buttons

### Echo Service
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

### Frontend Web UI
The easiest way to test the application is through the web interface:

```bash
# Start all services
docker compose up --build

# Access the frontend in your browser
open http://localhost

# Or on specific port if configured differently
# open http://localhost:4200
```

The web UI provides:
- Name-based login (no password required)
- Visual file upload with drag-and-drop
- Dropdown list of your files for download
- File management (view, download, delete)

### API Testing
All backend services are accessed through Traefik on port 80 with path-based routing:

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
