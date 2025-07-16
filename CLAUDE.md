# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Core Development
- `make build` - Build all container images (consolidated architecture)
- `make run` - Run the entire system with docker-compose
- `docker-compose up -d` - Start all services in detached mode
- `docker-compose down` - Stop all services
- `pytest tests/` - Run Python tests
- `make help` - Show all available Makefile targets

### Frontend Development
- `cd ui && npm start` - Start React development server
- `cd ui && npm run build` - Build React app for production
- `cd ui && npm test` - Run frontend tests
- `cd ui/unified-backend && npm start` - Start unified backend server

### Data Generation and Testing (Python-based)
- `cd scripts && pip install -r requirements.txt` - Install Python dependencies
- `./run_tests.sh full` - Run complete test suite with data generation
- `./generate_test_data.py --type=all --count=100` - Generate all test data
- `./generate_test_data.py --type=alerts --count=10` - Generate specific data
- `./nats_utils.py setup` - Initialize NATS streams
- `./test_system.py --test=all` - Test system functionality

### Container Management (Consolidated)
- `make orchestrator` - Build orchestrator image
- `make observability-agent` - Build consolidated observability agent
- `make infrastructure-agent` - Build consolidated infrastructure agent  
- `make communication-agent` - Build consolidated communication agent
- `make root-cause-agent` - Build root cause agent
- `make unified-backend` - Build unified backend (replaces 3 services + database)
- `make ui` - Build UI image (requires `npm run build` first)
- `make clean` - Remove all container images

## Architecture Overview

### Core Components
This is a **simplified, database-free** distributed observability system using consolidated AI agents for incident response:

1. **Orchestrator** (`orchestrator/agent.py`) - Central coordinator that receives alerts and distributes them to consolidated agents
2. **Consolidated Agents** (`agents/*/`) - Four streamlined agents handle all observability aspects:
   - **Observability Agent**: Unified metrics, logs, and tracing analysis (replaces 3 agents)
   - **Infrastructure Agent**: Deployment monitoring and runbook automation (replaces 2 agents)
   - **Communication Agent**: Notifications and postmortem generation (replaces 2 agents)
   - **Root Cause Agent**: Multi-agent analysis for root cause determination (unchanged)
3. **Unified Backend** (`ui/unified-backend/`) - Single API server replacing 3 services + database

### Communication Architecture
- **NATS JetStream** - Message broker for agent communication AND persistence
- **Subjects**: Each consolidated agent subscribes to specific subjects (e.g., `observability_agent`, `infrastructure_agent`)
- **Streams**: Data stored in JetStream streams for UI consumption AND notebook persistence
- **Zero Databases**: No MongoDB, Redis, or external databases required

### UI Architecture (Simplified)
- **React Frontend** (`ui/src/`) - Web interface with Material-UI
- **Unified Backend** (`ui/unified-backend/`) - Single Node.js server providing:
  - Observability data API from NATS streams
  - Natural language to Kubernetes commands
  - Notebook management with NATS persistence
  - Zero database setup or maintenance

### Tools and Common Utilities
- **Common Tools** (`common/tools/`) - Shared utilities for Kubernetes, Prometheus, Git, ArgoCD integration
- **Configuration** (`common/config.py`) - Centralized configuration management
- **CrewAI Framework** - Used for multi-agent orchestration within consolidated agents

## Key Implementation Details

### Consolidated Agent Pattern
1. **Observability Agent** processes metrics, logs, and tracing data using 6 specialized sub-agents
2. **Infrastructure Agent** handles deployments and runbooks using 5 specialized sub-agents
3. **Communication Agent** manages notifications and postmortems using 7 specialized sub-agents
4. Each consolidated agent uses CrewAI for internal task coordination
5. Results published to unified response subjects for orchestrator consumption

### Environment Configuration
- All agents require `OPENAI_API_KEY` and `NATS_URL`
- Kubernetes agents need `KUBECONFIG` mounted
- Agent enable/disable via Helm values (consolidated agents preferred)
- Default OpenAI model is `gpt-4o-mini` for cost efficiency

### Development Workflow
1. Use `make run` for full system testing (6 containers total)
2. Individual consolidated agents can be developed and tested independently
3. Use scripts in `scripts/` directory to generate test data
4. UI development requires only unified backend server
5. Kubernetes integration requires proper RBAC configuration
6. **No database setup required** - pure NATS persistence

## Important Notes

### Container Runtime
- Makefile automatically detects podman/docker and uses appropriate commands
- Uses `podman-compose` if podman is available, otherwise `docker-compose`

### Kubernetes Dependencies
- Infrastructure Agent requires Kubernetes access for deployment monitoring
- RBAC permissions needed for reading deployments, pods, events
- ArgoCD integration available for deployment history

### Data Streams (Database-Free)
- NATS JetStream stores **all** operational data including notebooks
- Stream subjects follow pattern: `{datatype}.{service}` (e.g., `metrics.api-service`)
- UI backend retrieves data from these streams for visualization
- **Notebooks stream**: `notebooks.{id}` replaces MongoDB entirely

### Resource Optimization
- **Memory**: ~60% reduction from individual agent architecture
- **CPU**: ~50% reduction through consolidated processing
- **Storage**: 100% elimination of database dependencies
- **Containers**: 50% reduction (12+ → 6 containers)

### Testing Strategy
- Python tests in `tests/` directory using pytest
- Frontend tests using React Testing Library
- Integration tests via scripts that publish to NATS
- Full system testing with docker-compose (simplified 6-container stack)
- **No database setup** required for testing

### Migration Notes
- Legacy individual agents remain available as fallback
- Orchestrator supports both consolidated and individual agent subjects
- Gradual migration supported via agent enable/disable flags
- All API endpoints maintain backward compatibility
- **Database migration**: Notebooks automatically move from MongoDB to NATS streams

## Performance Characteristics

### Consolidated Agents
- **Observability Agent**: 512Mi-1Gi memory, 200-500m CPU
- **Infrastructure Agent**: 512Mi-1Gi memory, 200-500m CPU  
- **Communication Agent**: 512Mi-1Gi memory, 200-500m CPU
- **Root Cause Agent**: 256-512Mi memory, 100-200m CPU

### Unified Backend
- **Memory**: 300Mi (vs 768Mi+ for separate services + database)
- **CPU**: 150m (vs 600m+ for separate services + database)
- **Connections**: Single NATS connection pool for all operations
- **Latency**: Reduced inter-service communication overhead

## Production Deployment

### Helm Configuration
```yaml
agents:
  enabled:
    observability: true    # Consolidated (recommended)
    infrastructure: true   # Consolidated (recommended)  
    communication: true    # Consolidated (recommended)
    rootCause: true       # Individual agent
    
    # Legacy agents (fallback, disabled by default)
    metric: false
    log: false
    tracing: false
    deployment: false
    runbook: false
    notification: false
    postmortem: false
```

### Resource Requirements
- **Total Memory**: ~1.5Gi (vs ~2.5Gi for individual agents)
- **Total CPU**: ~600m (vs ~1200m for individual agents)  
- **Storage**: NATS persistence only (no database PVCs)
- **Network**: Simplified service mesh (6 vs 12+ services)