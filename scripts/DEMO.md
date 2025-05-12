# Observability Agent System Demo Guide

## Prerequisites

1. **System Requirements**
   - Kubernetes cluster running
   - Helm installed
   - Python 3.10+
   - Redis server
   - Qdrant server

2. **Pre-demo Setup**
   ```bash
   # 1. Deploy the system
   helm install observability-agent ./helm/observability-agent

   # 2. Verify deployment
   kubectl get pods

   # 3. Install alert publisher
   pip install redis
   chmod +x scripts/alert_publisher.py
   ```

## Demo Structure (60 minutes)

### 1. System Overview (5 minutes)

#### Architecture
- **Orchestrator**: Central coordinator for alert distribution and response aggregation
- **Specialized Agents**: 
  - Metric Agent: CPU, Memory, Latency analysis
  - Log Agent: Error pattern detection
  - Deployment Agent: Deployment status monitoring
  - Notification Agent: Multi-channel alerting
  - Postmortem Agent: Incident documentation
- **Knowledge Base (Qdrant)**: Vector storage for incidents and pattern recognition
- **Message Bus (Redis)**: Pub/sub communication and state synchronization

#### Data Flow
1. Alert Ingestion → Orchestrator
2. Orchestrator → Specialized Agents
3. Agents → Analysis & Actions
4. Results → Knowledge Base
5. Notifications → External Systems

### 2. Live Demonstration (20 minutes)

#### A. Basic Alert Flow (5 minutes)
```bash
# Terminal 1: Watch orchestrator
kubectl logs -f deployment/observability-agent-orchestrator

# Terminal 2: Watch Redis
redis-cli
> SUBSCRIBE alerts

# Terminal 3: Generate alert
./scripts/alert_publisher.py --alert-type cpu --count 1
```

**What to Explain:**
- Alert format and structure
- Orchestrator's role in distribution
- Agent selection logic
- Response aggregation

#### B. Knowledge Base Integration (5 minutes)
```bash
# View stored incidents
curl http://localhost:6333/collections/incidents/points

# Search similar incidents
curl -X POST http://localhost:6333/collections/incidents/points/search \
  -H "Content-Type: application/json" \
  -d '{"vector": [0.1, 0.2, 0.3], "limit": 5}'
```

**What to Explain:**
- Vector storage concept
- Similarity search mechanism
- Historical correlation
- Pattern recognition

#### C. Notification System (5 minutes)
```bash
# Watch notification flow
kubectl logs -f deployment/observability-agent-notification-agent
kubectl logs -f deployment/observability-agent-postmortem-agent
```

**What to Explain:**
- Multi-channel alerting
- Priority handling
- Postmortem generation
- Action item tracking

#### D. Complex Scenario (5 minutes)
```bash
# Simulate complex incident
./scripts/alert_publisher.py --alert-type cpu --count 1
./scripts/alert_publisher.py --alert-type error_rate --count 1
./scripts/alert_publisher.py --alert-type latency --count 1
```

**What to Explain:**
- Correlated analysis
- Impact assessment
- Resolution tracking
- System scalability

### 3. Technical Deep Dive (15 minutes)

#### A. Agent Architecture
- **Metric Agent**
  - Time series analysis
  - Threshold detection
  - Anomaly detection

- **Log Agent**
  - Pattern matching
  - Error correlation
  - Context analysis

- **Deployment Agent**
  - Status monitoring
  - Rollback detection
  - Health checks

#### B. Knowledge Base Design
- Vector storage and embedding
- Similarity calculation
- Metadata management
- Version control

#### C. System Scalability
```bash
# Load test
./scripts/alert_publisher.py --count 10 --interval 2

# Monitor resources
kubectl top pods
```

### 4. Integration & Customization (10 minutes)

#### A. External Systems
- Prometheus metrics
- Grafana dashboards
- Slack/PagerDuty/Webex integration

#### B. Custom Extensions
- New alert types
- Custom agents
- Extended notifications

### 5. Q&A Session (10 minutes)

#### Technical Questions
- Architecture design
- Performance metrics
- Scalability
- Fault tolerance

#### Business Value
- ROI calculation
- Maintenance requirements
- Training needs

## Troubleshooting Guide

### Common Issues

1. **Alert Not Received**
   ```bash
   # Check Redis connection
   redis-cli ping
   
   # Verify channel
   redis-cli
   > SUBSCRIBE alerts
   ```

2. **Agent Not Responding**
   ```bash
   # Check agent status
   kubectl get pods
   
   # View agent logs
   kubectl logs -f deployment/observability-agent-{agent-name}
   ```

3. **Knowledge Base Issues**
   ```bash
   # Check Qdrant status
   curl http://localhost:6333/health
   
   # Verify collection
   curl http://localhost:6333/collections/incidents
   ```

## Demo Tips

### Before the Demo
1. Test all commands
2. Prepare backup commands
3. Create screenshots of expected outputs
4. Set up monitoring dashboards

### During the Demo
1. Explain each step clearly
2. Show both success and error handling
3. Maintain steady pace
4. Have backup plans ready

### After the Demo
1. Share documentation
2. Provide test environment access
3. Collect feedback
4. Schedule follow-up meetings 