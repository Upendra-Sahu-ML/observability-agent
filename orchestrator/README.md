# Orchestrator Agent

The Orchestrator Agent is the central component of the Observability Agent system. It coordinates the activities of specialized agents to provide comprehensive incident analysis and response.

## Overview

The Orchestrator Agent:
- Receives and processes alerts from monitoring systems
- Coordinates responses from specialized agents
- Enriches alerts with additional context
- Manages the incident response workflow
- Maintains the knowledge base of incidents

## Architecture

### Components

1. **Alert Processing**
   - Receives alerts via Redis pub/sub
   - Validates and normalizes alert data
   - Enriches alerts with metadata

2. **Agent Coordination**
   - Distributes alerts to relevant specialized agents
   - Collects and aggregates agent responses
   - Manages response timeouts and retries

3. **Knowledge Base Integration**
   - Stores incident data in Qdrant vector database
   - Retrieves similar past incidents
   - Updates runbooks and postmortems

4. **Response Management**
   - Coordinates notification delivery
   - Triggers automated remediation
   - Maintains incident state

### Agent Types

The orchestrator coordinates with the following specialized agents:

- **Metric Agent**: Analyzes time-series metrics
- **Log Agent**: Processes and analyzes log data
- **Deployment Agent**: Manages deployment-related issues
- **Tracing Agent**: Analyzes distributed traces
- **Root Cause Agent**: Identifies incident root causes
- **Runbook Agent**: Manages and executes runbooks
- **Notification Agent**: Handles alert notifications
- **Postmortem Agent**: Generates incident documentation

## Configuration

### Environment Variables

```yaml
# Core Configuration
OPENAI_API_KEY: "your-api-key"
OPENAI_MODEL: "gpt-4"
REDIS_HOST: "localhost"
REDIS_PORT: "6379"

# Agent Enablement
ENABLE_METRIC_AGENT: "true"
ENABLE_LOG_AGENT: "true"
ENABLE_DEPLOYMENT_AGENT: "true"
ENABLE_TRACING_AGENT: "true"
ENABLE_ROOT_CAUSE_AGENT: "true"
ENABLE_RUNBOOK_AGENT: "true"
ENABLE_NOTIFICATION_AGENT: "true"
ENABLE_POSTMORTEM_AGENT: "true"

# Knowledge Base
QDRANT_URL: "http://qdrant:6333"
POSTMORTEM_TEMPLATE_DIR: "/app/templates"
RUNBOOK_DIR: "/app/runbooks"

# Timeouts
RESPONSE_TIMEOUT_SECONDS: "300"
```

### Helm Configuration

The orchestrator can be configured through Helm values:

```yaml
orchestrator:
  replicas: 1
  image:
    repository: observability-agent/orchestrator
    tag: latest
  resources:
    requests:
      memory: "256Mi"
      cpu: "100m"
    limits:
      memory: "512Mi"
      cpu: "200m"
```

## Knowledge Base Integration

The orchestrator uses Qdrant for vector storage and similarity search:

1. **Vector Storage**
   - Stores incident data with embeddings
   - Enables semantic search for similar incidents
   - Maintains historical context

2. **Data Structure**
   ```json
   {
     "alert_id": "string",
     "title": "string",
     "description": "string",
     "root_cause": "string",
     "resolution": "string",
     "timestamp": "string",
     "metadata": {}
   }
   ```

3. **Search Capabilities**
   - Semantic similarity search
   - Metadata filtering
   - Time-based queries

## Alert Processing Flow

1. **Alert Reception**
   - Receive alert via Redis
   - Validate alert format
   - Extract key information

2. **Agent Selection**
   - Determine relevant agents
   - Check agent availability
   - Prepare agent requests

3. **Response Collection**
   - Send requests to agents
   - Monitor response timeouts
   - Aggregate responses

4. **Knowledge Integration**
   - Store incident data
   - Update runbooks
   - Generate postmortems

5. **Notification Dispatch**
   - Trigger notifications
   - Update incident status
   - Log actions taken

## Development

### Prerequisites

- Python 3.10+
- Redis
- Qdrant
- OpenAI API key

### Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment:
   ```bash
   export OPENAI_API_KEY="your-api-key"
   export REDIS_HOST="localhost"
   export QDRANT_URL="http://localhost:6333"
   ```

3. Run the orchestrator:
   ```bash
   python main.py
   ```

### Docker Deployment

1. Build the image:
   ```bash
   docker build -t observability-agent/orchestrator:latest .
   ```

2. Run the container:
   ```bash
   docker run -d \
     -e OPENAI_API_KEY="your-api-key" \
     -e REDIS_HOST="redis" \
     -e QDRANT_URL="http://qdrant:6333" \
     observability-agent/orchestrator:latest
   ```

### Kubernetes Deployment

1. Install using Helm:
   ```bash
   helm install observability-agent ./helm/observability-agent
   ```

2. Configure values:
   ```bash
   helm upgrade observability-agent ./helm/observability-agent \
     --set orchestrator.resources.limits.memory=1Gi \
     --set qdrant.persistence.size=20Gi
   ```

## Monitoring

The orchestrator exposes metrics for:
- Alert processing rate
- Agent response times
- Error rates
- Knowledge base operations

## Troubleshooting

Common issues and solutions:

1. **Agent Timeouts**
   - Check agent availability
   - Verify network connectivity
   - Adjust timeout settings

2. **Knowledge Base Errors**
   - Verify Qdrant connection
   - Check storage capacity
   - Validate data format

3. **Redis Connection Issues**
   - Check Redis service
   - Verify credentials
   - Test network connectivity

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.