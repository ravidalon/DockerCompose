# Docker Compose Microservices Demo

A simple demonstration of microservices architecture using Docker Compose with two Python Flask services.

## Services

### Echo Service (Port 8080)
A simple echo service that returns JSON data sent to it.

**Endpoints:**
- `POST /echo`: Returns the JSON body sent to it
- `GET /health`: Health check endpoint

### Database Service (Port 8081)
Graph database API service with Neo4j-style operations for nodes, relationships, and queries.

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
- `GET /nodes/<node_id>/relationships`: Get relationships for a node

**Query Operations:**
- `POST /query/cypher`: Execute Cypher query
- `POST /query/path`: Find path between nodes

**Utility:**
- `GET /health`: Health check
- `GET /stats`: Database statistics

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)
- `uv` package manager (for dependency management)

### Running with Docker Compose

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

### Local Development

```bash
# Install dependencies for all services
uv sync

# Run a specific service locally
cd services/echo
python -m echo.app

# Or run the database service
cd services/database
python -m database.app
```

## Testing

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

## Architecture

See [CLAUDE.md](CLAUDE.md) for detailed architecture and development guidance.
