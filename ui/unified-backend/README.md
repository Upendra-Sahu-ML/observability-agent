# Unified UI Backend

This is the **simplified, database-free** backend service for the Observability Agent UI that consolidates three previously separate services into one lightweight container:

1. **UI Backend** - Observability data API from NATS streams
2. **K8s Command Backend** - Kubernetes command execution and management  
3. **Notebook Management** - Pure NATS persistence (no database required)

## Features

### Observability Data API
- **Metrics**: Real-time performance metrics from consolidated observability agent
- **Logs**: Application logs with filtering and search capabilities  
- **Deployments**: Deployment events and status from infrastructure agent
- **Traces**: Distributed tracing data
- **Alerts**: Active and historical alert management
- **Agent Status**: Health monitoring of all consolidated agents
- **Root Cause Analysis**: Results from multi-agent analysis
- **Notifications**: Alert notification status and history
- **Postmortems**: Incident postmortem documents
- **Runbooks**: Operational runbook definitions and executions

### Kubernetes Integration
- **Natural Language Translation**: Convert natural language to kubectl commands using OpenAI
- **Safe Command Execution**: Execute kubectl commands with security restrictions
- **Command History**: Track command execution results
- **Error Handling**: Comprehensive error reporting and timeout management

### Notebook Management
- **NATS Persistence**: Stores notebooks in NATS streams instead of MongoDB
- **CRUD Operations**: Full create, read, update, delete functionality
- **Cell Management**: Support for command and result cells
- **Auto-save**: Automatic persistence to NATS on updates

## Database-Free Architecture

**🎯 Zero External Dependencies**: This backend requires **no database setup** - everything persists in NATS streams that are already part of your observability infrastructure.

**Benefits of Database-Free Design:**
- ✅ **No Database Administration**: No MongoDB setup, maintenance, or backups
- ✅ **No Migration Scripts**: No schema changes or data migration concerns  
- ✅ **Simplified Deployment**: Just deploy the container - no database initialization
- ✅ **Reduced Attack Surface**: Fewer components to secure and monitor
- ✅ **Better Reliability**: One less service that can fail
- ✅ **Cost Savings**: No database licensing or hosting costs

**How It Works:**
- **Notebooks**: Stored as JSON in NATS `NOTEBOOKS` stream
- **Command History**: Persisted in NATS streams with TTL
- **Cache Data**: In-memory with NATS backing for durability
- **All Operations**: Pure NATS messaging - no SQL or document queries

## Architecture Benefits

### Resource Optimization
- **Memory**: Reduced from 768Mi (3 services + MongoDB) to 300Mi (1 service)
- **CPU**: Consolidated processing reduces overhead by ~60%
- **Network**: Eliminates inter-service and database calls
- **Storage**: **Zero database dependencies** - pure NATS persistence
- **Deployment**: Single container replaces 4 separate deployments

### Operational Simplification
- **Single Service**: One backend instead of three separate deployments
- **Shared Connections**: Single NATS connection pool for all operations
- **Unified Monitoring**: Single service to monitor and troubleshoot
- **Simpler Scaling**: Scale one service instead of managing multiple

### Development Efficiency
- **Unified API**: All endpoints under single service
- **Shared Utilities**: Common NATS helpers and data processing
- **Consistent Patterns**: Unified error handling and logging
- **Easier Testing**: Single service integration tests

## API Endpoints

### Observability Data
```
GET /api/agents           - Agent status and health
GET /api/metrics          - Performance metrics data
GET /api/logs             - Application logs
GET /api/deployment       - Deployment events
GET /api/rootcause        - Root cause analysis
GET /api/tracing          - Distributed traces
GET /api/notification     - Notification events
GET /api/postmortem       - Postmortem documents
GET /api/runbook          - Runbook definitions
GET /api/alerts/history   - Historical alerts
GET /api/alerts/active    - Active alerts
```

### Kubernetes Commands
```
POST /api/k8s/translate   - Convert natural language to kubectl
POST /api/k8s/execute     - Execute kubectl commands safely
```

### Notebook Management
```
GET    /api/notebooks     - List all notebooks
POST   /api/notebooks     - Create new notebook
GET    /api/notebooks/:id - Get specific notebook
PUT    /api/notebooks/:id - Update notebook
DELETE /api/notebooks/:id - Delete notebook
```

### Runbook Execution
```
POST /api/runbook/:id/execute       - Execute runbook
GET  /api/runbook/execution/:execId - Get execution status
```

## Environment Variables

```bash
# NATS Configuration
NATS_URL=nats://nats:4222

# OpenAI Configuration (for K8s command translation)
OPENAI_API_KEY=your_openai_api_key

# Server Configuration
PORT=5000

# Cache Configuration
CACHE_TTL=300000  # 5 minutes in milliseconds
```

## Usage

### Development
```bash
cd ui/unified-backend
npm install
npm run dev
```

### Production
```bash
docker build -t observability-agent-unified-backend .
docker run -p 5000:5000 \
  -e NATS_URL=nats://nats:4222 \
  -e OPENAI_API_KEY=your_key \
  observability-agent-unified-backend
```

### Kubernetes Deployment
The unified backend replaces three separate deployments:
- `ui-backend` deployment
- `k8s-command-backend` deployment  
- `mongodb` deployment

See Helm chart configuration for deployment details.

## Migration Notes

### From Separate Services
1. **Data Compatibility**: All API endpoints maintain backward compatibility
2. **Zero Database Migration**: Notebooks stored in NATS streams (no database setup required)
3. **Service Discovery**: Frontend needs single backend URL instead of multiple
4. **Resource Allocation**: Dramatically reduced resource requirements
5. **Simplified Deployment**: No database initialization or migration scripts needed

### Frontend Changes Required
Update frontend API configuration to point to single unified backend:
```javascript
// Before
const UI_BACKEND_URL = 'http://ui-backend:5000';
const K8S_BACKEND_URL = 'http://k8s-command-backend:5002';

// After  
const UNIFIED_BACKEND_URL = 'http://unified-backend:5000';
```

## Monitoring

### Health Checks
- HTTP endpoint: `GET /api/agents` (returns 200 if healthy)
- Docker healthcheck: Built-in curl-based health monitoring
- NATS connectivity: Automatic reconnection and error handling

### Metrics
- Memory usage: Monitor for optimal cache performance
- Response times: Track API endpoint performance  
- NATS message throughput: Monitor stream consumption rates
- Error rates: Track failed requests and command executions

## Security

### K8s Command Execution
- **Restricted Commands**: Only kubectl commands allowed
- **Timeout Protection**: 30-second timeout on command execution
- **Output Limits**: 1MB maximum output buffer
- **User Context**: Runs with service account permissions only

### NATS Security
- **Connection Security**: Uses service account authentication
- **Stream Isolation**: Separate streams for different data types
- **ACK Requirements**: Explicit message acknowledgment for reliability

## Performance

### Caching Strategy
- **In-Memory Cache**: 5-minute TTL for observability data
- **NATS Persistence**: Notebooks stored in NATS streams
- **Connection Pooling**: Shared NATS connection across all operations

### Optimization Features
- **Lazy Loading**: Fetch data only when requested
- **Batch Processing**: Process multiple NATS messages efficiently
- **Stream Filtering**: Server-side filtering reduces network overhead
- **Compression**: JSON response compression for large datasets