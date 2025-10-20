# Riff CLI Infrastructure

This directory contains Docker and deployment infrastructure for the riff-cli project.

## Components

### Qdrant Vector Database

Qdrant is used for semantic search of Claude conversation sessions.

**Directory Structure:**
```
infrastructure/
├── docker-compose.yml          # Service orchestration
└── qdrant/
    ├── config.yaml            # Qdrant configuration
    └── storage/               # Data persistence (auto-created)
```

## Quick Start

### Start Services

```bash
# From infrastructure/ directory
docker-compose up -d

# Or from project root with Taskfile
task docker:up
```

### Stop Services

```bash
# From infrastructure/ directory
docker-compose down

# Or from project root
task docker:down
```

### Check Status

```bash
# View logs
docker-compose logs -f qdrant

# Check health
curl http://localhost:6333/healthz
```

## Ports

- **6333**: Qdrant HTTP API (used by riff search)
- **6334**: Qdrant gRPC API

See `~/docs/federation/PORT_REGISTRY.md` for complete port allocations.

## Data Persistence

Qdrant data is persisted in `./qdrant/storage/` directory. This directory is:
- Created automatically on first run
- Mounted as a volume in the container
- **Should be backed up regularly**

## Configuration

Edit `qdrant/config.yaml` to customize:
- Performance settings
- Indexing thresholds
- Logging levels
- Cluster configuration

## Troubleshooting

### Service won't start

```bash
# Check if port is already in use
lsof -i :6333

# View detailed logs
docker-compose logs qdrant
```

### Reset data

```bash
# WARNING: This deletes all indexed sessions
docker-compose down
rm -rf qdrant/storage
docker-compose up -d
```

### Check collection status

```bash
curl http://localhost:6333/collections/claude_sessions
```

## Integration

The riff search functionality connects to Qdrant at `http://localhost:6333` by default. You can override this with:

```bash
riff search --qdrant-url http://other-host:6333 "query"
```

## Development

For local development without Docker:

```bash
# Install Qdrant locally (macOS)
brew install qdrant

# Run locally
qdrant --config-path infrastructure/qdrant/config.yaml
```

## Production Deployment

For production deployment to edge devices or remote servers, see:
- `~/docs/infrastructure/eternal-agents/QUICK_REFERENCE.md`
- `~/docs/federation/PORT_REGISTRY.md`
