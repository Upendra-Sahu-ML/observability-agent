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

## 🚀 Quick Start Guide

### Prerequisites
- Docker and Docker Compose (or Podman)
- Kubernetes cluster (optional, for advanced deployment)
- OpenAI API key
- Python 3.8+ (for testing scripts)

### 1. Basic Setup (Docker Compose)
```bash
# Clone the repository
git clone <repository-url>
cd observability-agent

# Set your OpenAI API key
export OPENAI_API_KEY=your_openai_api_key

# Start all services
make run
# or: docker-compose up -d

# Check if services are running
docker-compose ps
```

### 2. Test with Dummy Data (No External Dependencies)
```bash
# Install Python dependencies for testing
cd scripts
pip install -r requirements.txt

# Run full test suite (generates data + tests everything)
./run_tests.sh full

# Or run step by step
./run_tests.sh setup      # Setup NATS streams
./run_tests.sh generate   # Generate test data
./run_tests.sh test       # Run system tests
```

### 3. Access the UI
```bash
# Frontend (React UI)
open http://localhost:3000

# Backend API
curl http://localhost:5000/api/health

# NATS Management UI (optional)
open http://localhost:8222
```

### 4. Advanced Kubernetes Deployment
```bash
# Deploy in basic mode (minimal resources)
cd scripts
./deploy-tiered.sh --mode=basic --api-key=$OPENAI_API_KEY

# Deploy in standard mode (full observability)
./deploy-tiered.sh --mode=standard --api-key=$OPENAI_API_KEY

# Check deployment status
kubectl get pods -n observability
```

## 🎯 Demo Use Cases & Scenarios

### Use Case 1: PetClinic High Memory Usage
**Scenario**: Spring Boot PetClinic experiencing JVM memory pressure  
**Demo Flow**:
1. **Generate Alert**: `./simulate_petclinic_alerts.py --scenario=memory_pressure`
2. **Monitor UI**: Watch JVM memory alert appear in Dashboard
3. **Azure Monitor Analysis**: Observability agent analyzes JVM heap metrics
4. **Runbook Suggestion**: Infrastructure agent suggests JVM tuning runbook
5. **Execution**: View automated JVM optimization steps
6. **Resolution**: See memory usage normalized

**UI Components**: Dashboard → Alerts → JVM Metrics → Runbooks → Status
**Azure Monitor**: JVM heap usage, GC pause times, thread counts

### Use Case 2: PostgreSQL Database Connection Issues
**Scenario**: PetClinic cannot connect to PostgreSQL database  
**Demo Flow**:
1. **Trigger**: `./simulate_petclinic_alerts.py --scenario=database_outage`
2. **Impact Analysis**: Multi-agent analysis of database connectivity
3. **Root Cause**: Identify connection pool or database issues
4. **Rollback**: Automated database restart or connection pool reset
5. **Notification**: Teams alerts sent for critical database issue
6. **Postmortem**: Automated incident documentation

**UI Components**: Database → Connectivity → Runbooks → Communications
**Azure Monitor**: Database connection metrics, query performance

### Use Case 3: PetClinic Slow Response Times
**Scenario**: Users experiencing slow page loads in PetClinic web interface  
**Demo Flow**:
1. **Pattern Recognition**: Azure Monitor detects response time degradation
2. **Correlation**: Observability agent correlates slow database queries with response times
3. **Analysis**: Identifies PostgreSQL performance bottlenecks
4. **Proactive Action**: Suggests database optimization and JVM tuning
5. **Monitoring**: Continuous tracking of response times and database performance
6. **Learning**: System learns from resolution patterns

**UI Components**: Performance → Database → JVM → Runbooks
**Azure Monitor**: HTTP request duration, database query times, JVM metrics

### Use Case 4: AKS Node Resource Pressure
**Scenario**: Kubernetes nodes experiencing high CPU/memory usage affecting PetClinic  
**Demo Flow**:
1. **Error Detection**: Azure Monitor detects node resource pressure
2. **Impact Analysis**: Identify affected pods and services (PetClinic, PostgreSQL)
3. **Dependency Analysis**: Check cluster autoscaling and resource quotas
4. **Escalation**: Automatic Teams notification for infrastructure team
5. **Recovery**: Node scaling or pod rescheduling runbook
6. **Validation**: Cluster health and application performance confirmation

**UI Components**: Infrastructure → Cluster → Scaling → Runbooks
**Azure Monitor**: AKS node metrics, pod resource usage, cluster events

## 🖥️ UI Demo Guide

### Dashboard Overview
- **Real-time Alerts**: Live alert feed with severity indicators
- **System Health**: Overall system status and metrics
- **Agent Status**: Health of all 4 agents
- **Recent Activity**: Timeline of recent incidents and resolutions

### Key UI Features for Demo:
1. **Interactive Alerts**: Click to drill down into incident details
2. **Metrics Visualization**: Real-time graphs and charts
3. **Log Search**: Query and filter logs across services
4. **Runbook Execution**: Step-by-step runbook progress
5. **Root Cause Analysis**: Visual correlation of findings
6. **Notification History**: Track all sent notifications

### Demo Data Generation:
```bash
# Generate realistic PetClinic demo scenario
./generate_test_data.py --type=all --count=20

# Generate specific incident types for PetClinic
./generate_test_data.py --type=alerts --count=5      # PetClinic, PostgreSQL, AKS alerts
./generate_test_data.py --type=metrics --count=100   # JVM, database, infrastructure metrics
./generate_test_data.py --type=logs --count=200      # Spring Boot, PostgreSQL logs

# Simulate realistic PetClinic incidents
./simulate_petclinic_alerts.py --scenario=memory_pressure    # JVM memory issues
./simulate_petclinic_alerts.py --scenario=database_outage    # DB connectivity issues
./simulate_petclinic_alerts.py --scenario=high_load         # Performance degradation
./simulate_petclinic_alerts.py --continuous=30              # 30 minutes of realistic alerts
```

## 🔧 Testing & Validation

### Automated Testing
```bash
# Run comprehensive system tests
./run_tests.sh full

# Test specific components
./test_system.py --test=observability  # Test fallback strategies
./test_system.py --test=tools          # Test simplified tools
./test_system.py --test=agents         # Test 4-agent architecture
```

### Manual Testing Scenarios
```bash
# Test 1: Basic Alert Processing
./generate_test_data.py --type=alerts --count=1
# Check UI for alert appearance and processing

# Test 2: Agent Response
./run_tests.sh generate --type=metrics --count=10
# Verify agents process and respond to data

# Test 3: Fallback Functionality
# Stop external services (Prometheus, Loki)
# Verify system continues with kubectl fallbacks
```

### Performance Testing
```bash
# Load test with high volume
./generate_test_data.py --type=all --count=500

# Memory usage check
docker stats

# Response time validation
curl -w "%{time_total}" http://localhost:5000/api/health
```

## ⚙️ Configuration Options

### Environment Variables
```bash
# Core Configuration
export OPENAI_API_KEY="your-api-key"              # Required for AI agents
export NATS_URL="nats://localhost:4222"           # NATS server URL
export DEPLOYMENT_MODE="basic"                    # basic|standard|advanced

# Azure Monitor Integration
export AZURE_SUBSCRIPTION_ID="your-subscription-id"         # Azure subscription
export AZURE_RESOURCE_GROUP="petclinic-rg"                 # Resource group for PetClinic
export AZURE_LOG_ANALYTICS_WORKSPACE_ID="workspace-id"      # Log Analytics workspace
# export AZURE_APPLICATION_INSIGHTS_ID="app-insights-id"   # Application Insights (OPTIONAL - requires code instrumentation)

## Azure Monitor Components

### Log Analytics Workspace (Required)
- **Container logs**: Spring Boot application logs, PostgreSQL logs  
- **AKS metrics**: Node performance, pod resource usage, cluster events
- **No code changes needed**: Works with any containerized application

### Application Insights (Optional)
- **Detailed JVM metrics**: Heap usage, GC pause times, thread counts
- **Request/response metrics**: HTTP response times, error rates, request counts  
- **Requires code instrumentation**: Must add Application Insights SDK to PetClinic
- **Fallback available**: System works without Application Insights

# AKS Cluster Configuration
export AKS_CLUSTER_NAME="aks-petclinic-cluster"           # AKS cluster name
export AKS_RESOURCE_GROUP="petclinic-rg"                  # AKS resource group
export KUBECONFIG="/path/to/kubeconfig"                   # Kubernetes config for AKS

# Agent Configuration
export ENABLE_OBSERVABILITY_AGENT="true"          # Unified observability with Azure Monitor
export ENABLE_INFRASTRUCTURE_AGENT="true"         # AKS deployment + runbooks
export ENABLE_COMMUNICATION_AGENT="true"          # Teams/Slack notifications + postmortems
export ENABLE_ROOT_CAUSE_AGENT="true"            # Root cause analysis

# PetClinic Application Configuration
export PETCLINIC_NAMESPACE="default"              # Kubernetes namespace for PetClinic
export POSTGRESQL_SERVICE="postgresql"            # PostgreSQL service name
```

### Deployment Modes
1. **Basic Mode**: Minimal resources, kubectl fallbacks (~1Gi memory)
2. **Standard Mode**: Full observability integration (~3Gi memory)
3. **Advanced Mode**: All features enabled (~5Gi memory)

### Helm Configuration
```bash
# Basic deployment
helm install observability-agent ./helm/observability-agent \
  --set openai.apiKey="$OPENAI_API_KEY" \
  --set deployment.mode="basic"

# Standard deployment with observability
helm install observability-agent ./helm/observability-agent \
  --set openai.apiKey="$OPENAI_API_KEY" \
  --set deployment.mode="standard" \
  --set observability.prometheus.enabled=true \
  --set observability.loki.enabled=true
```

## 🚨 Troubleshooting

### Common Issues & Solutions

#### 1. NATS Connection Failed
```bash
# Check NATS is running
docker-compose ps nats
kubectl get pods -n observability -l app=nats

# Test NATS connectivity
./nats_utils.py health --nats-url=nats://localhost:4222

# Restart NATS
docker-compose restart nats
```

#### 2. Agents Not Responding
```bash
# Check agent logs
docker-compose logs observability-agent
kubectl logs -n observability -l app=observability-agent

# Verify agent configuration
./test_system.py --test=agents

# Check OpenAI API key
echo $OPENAI_API_KEY
```

#### 3. UI Not Loading
```bash
# Check UI services
docker-compose ps ui unified-backend

# Test backend API
curl http://localhost:5000/api/health

# Check frontend
curl http://localhost:3000

# Restart UI services
docker-compose restart ui unified-backend
```

#### 4. External Dependencies Missing
```bash
# System works without external deps - uses kubectl fallbacks
# Verify kubectl access
kubectl get pods
kubectl get deployments

# Test fallback functionality
./test_system.py --test=observability
```

#### 5. Memory Issues
```bash
# Switch to basic mode
export DEPLOYMENT_MODE="basic"
./deploy-tiered.sh --mode=basic --api-key=$OPENAI_API_KEY

# Monitor resource usage
docker stats
kubectl top pods -n observability
```

### Logs & Debugging
```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs observability-agent
docker-compose logs nats

# In Kubernetes
kubectl logs -n observability -l app=observability-agent -f
kubectl logs -n observability -l app=nats -f
```

## 📊 Monitoring & Metrics

### Health Checks
```bash
# System health
./run_tests.sh health

# Individual components
curl http://localhost:5000/api/health          # Backend
curl http://localhost:3000                     # Frontend
./nats_utils.py health                         # NATS
```

### Performance Metrics
```bash
# Resource usage
docker stats

# Response times
curl -w "%{time_total}" http://localhost:5000/api/alerts

# NATS stream info
./nats_utils.py info --stream=ALERTS
```

## 📚 Documentation Structure

### Core Documentation
- **README.md** (this file) - Main usage guide and demo scenarios
- **CLAUDE.md** - Development commands and architecture overview
- **scripts/README.md** - Testing and data generation scripts

### Detailed Documentation
- **docs/ARCHITECTURE.md** - Technical architecture details
- **docs/configuration.md** - Advanced configuration options
- **docs/usage.md** - Detailed usage instructions

### Agent Documentation
- **agents/*/README.md** - Individual agent documentation
- **orchestrator/README.md** - Orchestrator details
- **ui/*/README.md** - UI component documentation

## 🤝 Contributing

### Development Setup
```bash
# Start development environment
make run

# Run tests
cd scripts
./run_tests.sh full

# Check code quality
make lint
make typecheck
```

### Adding New Features
1. Update agent code in `agents/*/`
2. Add tests in `scripts/test_system.py`
3. Update documentation
4. Test with `./run_tests.sh full`

## 📝 License

[Add your license information here]

---

## 🎯 Quick Demo Commands

```bash
# 1. Start the system
make run

# 2. Generate demo data
cd scripts && ./run_tests.sh full

# 3. Open UI and explore
open http://localhost:3000

# 4. Generate specific scenarios
./generate_test_data.py --type=alerts --count=5
./generate_test_data.py --type=metrics --count=100

# 5. Test system health
./run_tests.sh health
```

The system is now ready for demonstration with realistic data and comprehensive testing capabilities!
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