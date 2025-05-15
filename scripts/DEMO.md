# Observability Agent System Demo Guide

## Prerequisites

1. **System Requirements**
   - Kubernetes cluster running
   - Helm installed
   - Python 3.9+
   - NATS with JetStream enabled
   - Qdrant server

2. **Pre-demo Setup**
   ```bash
   # 1. Deploy the observability-agent system
   helm install observability-agent ./helm/observability-agent

   # 2. Verify deployment
   kubectl get pods

   # 3. Build and deploy the alert publisher
   make alert-publisher REGISTRY=your-registry
   docker push your-registry/alert-publisher:latest
   sed -i 's|\${REGISTRY}|your-registry|g' scripts/alert-publisher-k8s.yaml
   kubectl apply -f scripts/alert-publisher-k8s.yaml
   ```

## Demo Structure (60 minutes)

### 1. System Overview (5 minutes)

#### Architecture
- **Orchestrator**: Central coordinator for alert distribution and response aggregation
- **Specialized Agents**: 
  - Metric Agent: CPU, Memory, Latency analysis
  - Log Agent: Error pattern detection
  - Deployment Agent: Deployment status monitoring
  - Tracing Agent: Distributed trace analysis
  - Notification Agent: Multi-channel alerting
  - Postmortem Agent: Incident documentation
- **Knowledge Base (Qdrant)**: Vector storage for incidents and pattern recognition
- **Message Bus (NATS JetStream)**: Pub/sub communication and state synchronization

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

# Terminal 2: Watch NATS streams
kubectl exec -it deployment/observability-agent-nats -- nats stream info ALERTS

# Terminal 3: Generate alert
# Option 1: Use the deployed container
kubectl logs -f pod/alert-publisher-once

# Option 2: Run a one-time job
kubectl run alert-publisher-job --image=your-registry/alert-publisher:latest --restart=Never -- --alert-type cpu --count 1
```

**What to Explain:**
- Alert format and structure
- Orchestrator's role in distribution
- Agent selection logic
- Response aggregation

#### B. Knowledge Base Integration (5 minutes)
```bash
# View stored incidents
curl http://observability-agent-qdrant:6333/collections/incidents/points

# Search similar incidents
curl -X POST http://observability-agent-qdrant:6333/collections/incidents/points/search \
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
# Simulate complex incident with multiple alert types
kubectl run complex-scenario --image=your-registry/alert-publisher:latest --restart=Never -- --alert-type cpu --count 1
kubectl run latency-alert --image=your-registry/alert-publisher:latest --restart=Never -- --alert-type latency --count 1
kubectl run error-alert --image=your-registry/alert-publisher:latest --restart=Never -- --alert-type error_rate --count 1
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

- **Tracing Agent**
  - Distributed trace analysis
  - Service dependency mapping
  - Performance bottleneck identification

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
# Load test with continuous alerts
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: load-test-publisher
spec:
  replicas: 3
  selector:
    matchLabels:
      app: load-test-publisher
  template:
    metadata:
      labels:
        app: load-test-publisher
    spec:
      containers:
      - name: alert-publisher
        image: your-registry/alert-publisher:latest
        args:
        - "--alert-type"
        - "random"
        - "--count"
        - "10"
        - "--interval"
        - "2"
EOF

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
   # Check NATS connection
   kubectl exec -it deployment/observability-agent-nats -- nats server info
   
   # Verify ALERTS stream existence
   kubectl exec -it deployment/observability-agent-nats -- nats stream info ALERTS
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
   curl http://observability-agent-qdrant:6333/health
   
   # Verify collection
   curl http://observability-agent-qdrant:6333/collections/incidents
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