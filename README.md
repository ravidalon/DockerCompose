# Docker Compose Microservices Demo

> A hands-on demonstration project showcasing real-world Docker Compose features through a working microservices application with a Vue.js frontend, Python Flask backends, and Neo4j graph database.

## What Is This?

This repository demonstrates how to build and orchestrate a multi-service application using Docker Compose. It's designed as a learning resource that goes beyond "hello world" examples to show practical patterns you'll use in production.

**The application:** A file-sharing system where users can upload, download, and manage files while tracking all interactions in a graph database.

## Docker Compose Features Demonstrated

This project showcases essential Docker Compose capabilities:

- **Extension Fields & YAML Anchors**: DRY configuration using reusable blocks
- **Profiles**: Multiple deployment scenarios (dev, backend-only, test)
- **Health Checks & Smart Dependencies**: Eliminate startup race conditions with `condition: service_healthy`
- **Network Isolation**: Three-layer security architecture (frontend/backend/database)
- **Volume Types**: Both bind mounts (hot-reload) and named volumes (persistent data)
- **Reverse Proxy**: Traefik for path-based routing and automatic service discovery
- **Environment Management**: Multiple env files with override capabilities
- **Service Communication**: HTTP calls between services, internal vs public endpoints

## Quick Start

### Prerequisites

- Docker and Docker Compose
- No other dependencies needed for Docker mode!

### Run the Application

```bash
# Start all services with web UI
docker compose up --build

# Access the application
open http://localhost

# View Traefik dashboard
open http://localhost:8080
```

That's it! The frontend will be available at `http://localhost` where you can:
- Create a user account (just enter a name)
- Upload and download files
- See your file history
- Delete files

### Other Modes

```bash
# Backend only (no frontend)
docker compose --profile backend-only up --build

# Run integration tests
docker compose --profile test up --build --exit-code-from tests tests

# Stop everything
docker compose down
```

## What Can You Do With It?

### 1. Use the Web Interface

The easiest way to explore the application:

1. Open `http://localhost`
2. Enter your name (e.g., "Alice")
3. Upload some files
4. Download, view, and delete files
5. Log in as a different user to see separate file spaces

### 2. Test the APIs

All services are accessible through Traefik at `http://localhost`:

```bash
# Calculator service - simple demo endpoint
curl -X POST http://localhost/calc/calculate \
  -H "Content-Type: application/json" \
  -d '{"expression": "2 + 2"}'

# Create a user
curl -X POST http://localhost/fileshare/persons \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "alice@example.com"}'

# Upload a file
echo "Hello World" > test.txt
curl -X POST http://localhost/fileshare/files/upload \
  -F "file=@test.txt" \
  -F "person=Alice"

# Upload multiple files (creates relationships between them)
echo "File 1" > file1.txt
echo "File 2" > file2.txt
curl -X POST http://localhost/fileshare/files/upload/batch \
  -F "files=@file1.txt" \
  -F "files=@file2.txt" \
  -F "person=Alice"

# Download a file (tracked in database)
curl http://localhost/fileshare/files/Alice/test.txt/download -o downloaded.txt

# Get file interaction history
curl http://localhost/fileshare/files/Alice/test.txt/history

# Get files uploaded together in a batch
curl http://localhost/fileshare/files/Alice/file1.txt/batch-related
```

### 3. Explore the Traefik Dashboard

Visit `http://localhost:8080` to see:
- Registered routes and services
- Health status of all services
- Real-time request metrics

### 4. Watch Hot-Reload in Action

```bash
# Start services
docker compose up

# Edit any Python file in services/*/
# Watch the service automatically reload

# Edit frontend/src/App.vue
# Watch the browser auto-refresh
```

### 5. Experiment with Profiles

```bash
# Run only backend services
docker compose --profile backend-only up

# Run integration tests
docker compose --profile test up --build --exit-code-from tests tests

# Combine with custom environment
docker compose --env-file .env --profile dev up
```

## Project Structure

```
.
├── services/
│   ├── calc/              # Simple calculator service (demo endpoint)
│   ├── database/          # Neo4j API with full CRUD operations
│   └── fileshare/         # File storage with graph tracking
├── frontend/              # Vue 3 + Vite SPA
├── tests/                 # Integration tests
├── docker-compose.yml     # Base configuration
├── default.env            # Default environment variables
└── example.env            # Template for customization
```

### Service Architecture

```
                    Traefik Reverse Proxy
                           |
        +------------------+------------------+
        |                  |                  |
    Frontend           Calc API          Fileshare API
     (Vue 3)          (Flask)             (Flask)
        |                                     |
        |                              Database API
        |                               (Flask)
        |                                     |
        +---------------Neo4j-----------------+
```

**Network Isolation:**
- Frontend network: Public-facing services (traefik, calc, fileshare, frontend)
- Backend network: Internal APIs (fileshare, database)
- Database network: Most isolated (database, neo4j only)

This means:
- Neo4j is never directly accessible from public services
- Database API is only callable by fileshare service
- Compromised frontend can't reach the database layer

## Architecture Highlights

### Routing with Traefik

All external traffic goes through Traefik on port 80:
- `/` → Frontend (Vue SPA)
- `/calc/*` → Calculator service
- `/fileshare/*` → Fileshare service
- Database service: Internal only (not exposed)

### Health Checks Prevent Race Conditions

Every service has a health check, and dependencies use `condition: service_healthy`:

```yaml
services:
  neo4j:
    healthcheck:
      test: ["CMD", "wget", "--spider", "http://localhost:7474"]

  database:
    depends_on:
      neo4j:
        condition: service_healthy  # Wait for Neo4j to be ready
```

This eliminates connection errors and startup timing issues.

### Graph Database Tracking

The fileshare service tracks all file interactions in Neo4j:

- **Nodes**: `Person`, `File`
- **Relationships**: `UPLOADED`, `DOWNLOADED`, `EDITED`, `UPLOADED_WITH`

This lets you query:
- "Who has accessed this file?"
- "What files were uploaded together?"
- "Show me a user's complete file history"

## Learn More

Want to dive deeper? Check out these resources:

- **[CLAUDE.md](CLAUDE.md)**: Complete technical documentation
  - Detailed API documentation
  - Development workflows
  - Troubleshooting guide
  - Implementation details

- **Docker Compose files**: Read the comments in:
  - `docker-compose.yml`: Extension fields, profiles, networks
  - `default.env`: Environment configuration

- **Service code**: Each service is simple and well-commented:
  - `services/database/database/routes/`: Modular route organization
  - `services/fileshare/fileshare/routes/`: Service-to-service calls
  - `frontend/nginx.conf`: SPA routing and API proxying

## Local Development (Optional)

If you want to develop without Docker:

```bash
# Backend services
uv sync
cd services/fileshare
python -m fileshare.app

# Frontend
cd frontend
npm install
npm run dev  # Runs on http://localhost:5173
```

## Common Issues

**Services return 404?**
- Check Traefik dashboard at `http://localhost:8080`
- Verify services are up: `docker compose ps`

**Gateway timeout (504)?**
- Services may still be starting (health checks take 10-20s)
- Check logs: `docker compose logs -f [service_name]`

**Port conflicts?**
- Copy `example.env` to `.env` and change ports
- Or stop services using ports 80/8080

**Changes not reflected?**
- Code changes should hot-reload automatically via bind mounts
- If not, restart: `docker compose restart [service_name]`

## Contributing

This is a demonstration project. Feel free to:
- Fork it and experiment
- Use it as a template for your own projects
- Submit issues or improvements

## License

MIT - Use this code however you like!
