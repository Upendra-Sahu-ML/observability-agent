# Observability Agent

A **simplified, database-free** distributed observability system that uses AI agents to analyze and respond to system events. Built for maximum efficiency with minimal operational overhead.

## 🏗️ Consolidated Architecture

The system uses a **streamlined 4-agent architecture** instead of traditional 8+ separate services:

### **Core Agents (4 containers)**
- 🔍 **Observability Agent**: Unified metrics, logs, and tracing analysis
- 🏗️ **Infrastructure Agent**: Deployment monitoring and runbook automation  
- 💬 **Communication Agent**: Notifications and postmortem generation
- 🧠 **Root Cause Agent**: Multi-agent incident analysis

### **UI Layer (2 containers)**
- 📱 **UI Frontend**: React-based web interface
- 🚀 **Unified Backend**: Consolidated API server (replaces 3 separate backends + database)

### **Infrastructure (1 service)**
- 📨 **NATS JetStream**: Messaging, task distribution, and persistence

### **Optional Integrations**
- 📊 **Prometheus**: Metrics analysis (can work without)
- 📝 **Loki**: Log analysis (can work without)
- 🔍 **Tempo**: Trace analysis (can work without)
- 🚀 **ArgoCD**: Deployment management (can work without)

## ✨ Key Benefits

- 🎯 **Zero Database Dependencies**: No MongoDB, Redis, Qdrant, or external databases required
- 📉 **70% Resource Reduction**: Optimized memory and CPU usage (from 3.5Gi to 1Gi total)
- 🔄 **Simplified Operations**: 6 containers instead of 15+ (removed Qdrant + Redis)
- ⚡ **Single Dependency**: Only NATS required for messaging and persistence
- 🛡️ **Minimal Attack Surface**: Fewer services to secure and monitor

## 🚀 Quick Start

### Using Docker Compose (Recommended)
```bash
# Clone and start the system
git clone <repository-url>
cd observability-agent

# Set your OpenAI API key
export OPENAI_API_KEY=your_openai_api_key

# Start all services
make run
# or: docker-compose up -d

# Access the UI
open http://localhost:8080
```

### Using Kubernetes
```bash
# Deploy with Helm
helm install observability-agent ./helm/observability-agent \
  --set openai.apiKey=your_openai_api_key \
  --set observabilityAgent.prometheus.url=http://prometheus:9090 \
  --set observabilityAgent.loki.url=http://loki:3100
```

## 📊 Architecture Details

### **Observability Agent** (Consolidated)
**Replaces**: Metric Agent + Log Agent + Tracing Agent
- **Memory**: 512Mi-1Gi (was 768Mi across 3 agents)
- **Features**: Unified data collection from Prometheus, Loki, and Tempo
- **Analysis**: Performance metrics, error logs, and distributed tracing correlation

### **Infrastructure Agent** (Consolidated) 
**Replaces**: Deployment Agent + Runbook Agent
- **Memory**: 512Mi-1Gi (was 512Mi across 2 agents)
- **Features**: Kubernetes integration, ArgoCD monitoring, automated runbooks
- **Analysis**: Deployment correlation, infrastructure health, automated remediation

### **Communication Agent** (Consolidated)
**Replaces**: Notification Agent + Postmortem Agent
- **Memory**: 512Mi-1Gi (was 384Mi across 2 agents)
- **Features**: Multi-channel notifications, automated postmortem generation
- **Channels**: Slack, WebEx, PagerDuty with severity-based routing

### **Unified Backend** (Database-Free)
**Replaces**: UI Backend + K8s Command Backend + MongoDB + Qdrant + Redis
- **Memory**: 300Mi (was 1.5Gi+ across 5 services + databases)
- **Features**: 
  - Observability data API from NATS streams
  - Natural language to kubectl translation
  - Notebook management with NATS persistence
  - Knowledge base via NATS (replaces Qdrant)
  - Zero database setup or maintenance

## 🔧 Development

### Building Components
```bash
# Build all containers
make build

# Build individual components
make observability-agent
make infrastructure-agent
make communication-agent
make unified-backend
make ui

# Deploy locally
make deploy
```

### Testing Data Generation
```bash
cd scripts
npm install

# Generate test data for all components
node generate_all_data.js --duration=300

# Generate specific data types
node publish_core_data.js --component=metrics --count=50
```

### Running Tests
```bash
# Agent tests
pytest tests/

# UI tests  
cd ui && npm test

# Integration tests
cd scripts && node test_nats.js
```

## 🛠️ Configuration

### Environment Variables
```bash
# Core Configuration
OPENAI_API_KEY=sk-...                    # Required for AI analysis
OPENAI_MODEL=gpt-4o-mini                # AI model to use
NATS_URL=nats://nats:4222               # NATS connection

# Observability Sources
PROMETHEUS_URL=http://prometheus:9090    # Metrics source
LOKI_URL=http://loki:3100               # Logs source  
TEMPO_URL=http://tempo:3200             # Tracing source

# Notification Channels (optional)
SLACK_BOT_TOKEN=xoxb-...                # Slack integration
WEBEX_BOT_TOKEN=...                     # WebEx integration
PAGERDUTY_INTEGRATION_KEY=...           # PagerDuty integration
```

### Agent Enablement
```yaml
# Helm values.yaml
agents:
  enabled:
    observability: true     # Consolidated agent
    infrastructure: true    # Consolidated agent  
    communication: true     # Consolidated agent
    rootCause: true        # Individual agent
    
    # Legacy agents (disabled by default)
    metric: false
    log: false
    tracing: false
    deployment: false
    runbook: false
    notification: false
    postmortem: false
```

## 🔌 API Endpoints

### Unified Backend (Port 5000)
```bash
# Observability Data
GET /api/metrics          # Performance metrics
GET /api/logs             # Application logs  
GET /api/agents           # Agent health status
GET /api/deployment       # Deployment events
GET /api/rootcause        # Root cause analysis
GET /api/tracing          # Distributed traces
GET /api/alerts/active    # Active alerts
GET /api/alerts/history   # Alert history

# Kubernetes Commands
POST /api/k8s/translate   # Natural language → kubectl
POST /api/k8s/execute     # Execute kubectl commands

# Notebooks (Database-Free)
GET    /api/notebooks     # List notebooks
POST   /api/notebooks     # Create notebook
GET    /api/notebooks/:id # Get notebook
PUT    /api/notebooks/:id # Update notebook
DELETE /api/notebooks/:id # Delete notebook
```

## 📋 NATS Stream Architecture

All data flows through NATS JetStream streams:

```
ALERTS          → Alert data from monitoring systems
AGENT_TASKS     → Task distribution to consolidated agents  
AGENTS          → Agent health and status updates
RESPONSES       → Agent analysis results
ROOT_CAUSE      → Root cause analysis data
METRICS         → Performance metrics from observability agent
LOGS            → Log data from observability agent
DEPLOYMENTS     → Deployment events from infrastructure agent
TRACES          → Tracing data from observability agent
NOTIFICATIONS   → Notification events from communication agent
POSTMORTEMS     → Postmortem documents from communication agent
NOTEBOOKS       → Notebook data (replaces database)
```

## 🔄 Migration from Legacy Architecture

If upgrading from a multi-agent setup:

1. **Agents**: Legacy individual agents automatically fallback if consolidated agents are disabled
2. **Data**: All API endpoints maintain backward compatibility
3. **UI**: Frontend automatically adapts to unified backend
4. **Database**: Notebooks automatically migrate from MongoDB to NATS streams
5. **Configuration**: Gradual migration supported with agent enable/disable flags

## 📚 Documentation

- [CLAUDE.md](CLAUDE.md) - Development commands and architecture details
- [Unified Backend](ui/unified-backend/README.md) - Database-free backend architecture
- [Scripts](scripts/README.md) - Data generation and testing tools
- [Helm Chart](helm/observability-agent/README.md) - Kubernetes deployment guide

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Test your changes (`make test`)
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

**🎯 Production-Ready**: This observability agent is designed for production use with minimal operational overhead, zero database dependencies, and maximum resource efficiency.