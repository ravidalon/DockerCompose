# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Docker Compose microservices demo with three Python Flask backends and a Vue.js frontend:
- **calc**: Simple calculator service
- **database**: Neo4j graph database API (nodes, relationships, queries)
- **fileshare**: File storage with graph-based tracking
- **frontend**: Vue 3 + Vite SPA for file management

## Quick Start

```bash
# Start all services (web UI at http://localhost)
docker compose up --build

# Backend only (no frontend)
docker compose --profile backend-only up --build

# Run integration tests
docker compose --profile test up --build --exit-code-from tests tests

# View Traefik dashboard
open http://localhost:8080
```

## Architecture Overview

### Services
- **Backend**: Python 3.11 + Flask + uv package manager
- **Frontend**: Vue 3 + Vite, served by nginx
- **Database**: Neo4j graph database (internal only)
- **Routing**: Traefik reverse proxy with path-based routing

### Routing & Network Isolation
```
Traefik (public entry point)
├── / → frontend (Vue SPA)
├── /calc/* → calc service
└── /fileshare/* → fileshare service
    └── (internal) → database service
        └── (internal) → neo4j
```

Three-layer network security:
- **Frontend network**: Public-facing (traefik, calc, fileshare, frontend)
- **Backend network**: Internal APIs (fileshare, database)
- **Database network**: Most isolated (database, neo4j)

## Docker Compose Features Demonstrated

### 1. Extension Fields & YAML Anchors
Reusable configuration blocks reduce duplication:
- `x-flask-service`: Common Flask config (health checks, restart policy)
- `x-common-profiles`: Shared profile definitions

### 2. Multiple Compose Files
- `docker-compose.yml`: Base configuration
- `docker-compose.override.yml`: Local dev (auto-loaded, hot-reload enabled)
- `docker-compose.ci.yml`: CI/CD (explicit, production-like)

### 3. Profiles
- `dev`: Full stack with frontend (default)
- `backend-only`: APIs without UI
- `test`: Backend + integration tests

### 4. Health Checks & Smart Dependencies
All services use health checks with `condition: service_healthy` to eliminate startup race conditions.

### 5. Network Isolation
Three-layer network architecture prevents direct access between layers (e.g., frontend cannot reach Neo4j).

### 6. Volume Types
- **Bind mounts**: Hot-reloading for development
- **Named volumes**: Persistent data (neo4j_data, fileshare_uploads)

## Common Commands

### Docker Compose
```bash
# Start all services (dev mode with hot-reload)
docker compose up --build

# Backend only
docker compose --profile backend-only up --build

# Detached mode
docker compose up -d

# Stop services
docker compose down

# View logs
docker compose logs -f [service_name]

# Run tests
docker compose --profile test up --build --exit-code-from tests tests
```

### Local Development
```bash
# Backend: Install dependencies
uv sync

# Run specific service
cd services/fileshare
python -m fileshare.app

# Frontend: Install and run
cd frontend
npm install
npm run dev  # http://localhost:5173
```

### Environment Configuration
- `default.env`: Default values (committed)
- `.env`: Local overrides (not committed)
- Copy `example.env` to `.env` for customization

## Service APIs

### Calculator Service
Simple demonstration service:
- `POST /calculate`: Evaluates mathematical expressions (supports +, -, *, /, **, sqrt, sin, cos, tan, pi, e, etc.)
- `GET /health`: Health check

### Database Service (Internal Only)
Neo4j graph database API:
- Node CRUD: `POST /nodes`, `GET /nodes/<id>`, `PUT /nodes/<id>`, `DELETE /nodes/<id>`
- Relationship CRUD: `POST /relationships`, `GET /relationships/<id>`, etc.
- Queries: `POST /query/cypher`, `POST /query/path`
- Utility: `GET /health`, `GET /stats`

### Fileshare Service
File storage with graph tracking (demonstrates volumes + service-to-service communication):

**Graph Schema:**
- Nodes: `Person`, `File`
- Relationships: `UPLOADED`, `DOWNLOADED`, `EDITED`, `UPLOADED_WITH`

**Key Endpoints:**
- Persons: `POST /persons`, `GET /persons/<name>`, `GET /persons/<name>/files`
- Files: `POST /files/upload`, `POST /files/upload/batch`, `GET /files/<person>/<filename>/download`
- Queries: `GET /files/<person>/<filename>/history`, `GET /files/<person>/<filename>/batch-related`

### Frontend
Vue 3 SPA with:
- Name-based login (creates/fetches person from database)
- File upload/download interface
- File list with delete functionality

## Testing the Demo

### Web UI (Easiest)
```bash
docker compose up --build
open http://localhost
```

### API Testing
```bash
# Calculator service
curl -X POST http://localhost/calc/calculate \
  -H "Content-Type: application/json" \
  -d '{"expression": "2 + 2"}'

# Fileshare: Create person
curl -X POST http://localhost/fileshare/persons \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "alice@example.com"}'

# Upload file
echo "Hello World" > test.txt
curl -X POST http://localhost/fileshare/files/upload \
  -F "file=@test.txt" \
  -F "person=Alice"

# Upload batch (creates UPLOADED_WITH relationships)
echo "File 1" > file1.txt
echo "File 2" > file2.txt
curl -X POST http://localhost/fileshare/files/upload/batch \
  -F "files=@file1.txt" \
  -F "files=@file2.txt" \
  -F "person=Alice"

# Download file (tracks DOWNLOADED relationship)
curl http://localhost/fileshare/files/Alice/test.txt/download -o downloaded.txt

# Get file history
curl http://localhost/fileshare/files/Alice/test.txt/history

# View Traefik dashboard
open http://localhost:8080
```

### Integration Tests
Tests verify fileshare correctly updates Neo4j:
```bash
docker compose --profile test up --build --exit-code-from tests tests
```

## Troubleshooting

### 404 Errors
- Check Traefik dashboard: http://localhost:8080
- Verify containers: `docker compose ps`
- Check logs: `docker compose logs traefik`

### 504 Gateway Timeout
- Services starting up (wait 10-20s for health checks)
- Check status: `docker compose ps`
- View logs: `docker compose logs -f <service>`

### Port Conflicts
```bash
lsof -i :80
lsof -i :8080
# Modify ports in .env or docker-compose.yml
```

### Code Changes Not Reflected
- Hot-reload requires bind mounts (auto-enabled in dev mode)
- Restart if needed: `docker compose restart <service>`

## Project Structure

```
.
├── services/
│   ├── calc/            # Simple calculator service
│   ├── database/        # Neo4j API (modular: routes/, db.py, validation.py)
│   └── fileshare/       # File storage (modular: routes/, db_client.py, config.py)
├── frontend/            # Vue 3 + Vite SPA
├── tests/               # Integration tests (pytest)
├── docker-compose.yml           # Base configuration
├── docker-compose.override.yml  # Dev overrides (hot-reload)
├── docker-compose.ci.yml        # CI configuration
├── default.env          # Default environment variables
└── example.env          # Environment template
```

## Key Implementation Details

- **Traefik**: Path-based routing with automatic service discovery
- **Health checks**: `condition: service_healthy` eliminates race conditions
- **Network isolation**: Three layers (frontend/backend/database)
- **Volumes**: Bind mounts (dev hot-reload) + named volumes (persistent data)
- **Security**: Parameterized queries, input validation, network isolation
- **Dependencies**: uv (Python), npm (frontend)
- **Restart policy**: `unless-stopped` for resilience
