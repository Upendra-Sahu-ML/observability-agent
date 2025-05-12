# Observability Agent

An AI-powered observability system that uses specialized agents to analyze metrics, logs, traces, and deployment data to determine the root cause of incidents and automatically generate runbooks for resolution.

## Architecture

The system consists of the following components, each running in its own container:

1. **Orchestrator**: Coordinates the analysis across specialized agents
2. **Metric Agent**: Analyzes metric data from Prometheus
3. **Log Agent**: Analyzes log data from Loki and Kubernetes pods
4. **Tracing Agent**: Analyzes distributed tracing data from Tempo
5. **Deployment Agent**: Checks deployment configurations, Git repositories, and ArgoCD state
6. **Root Cause Agent**: Synthesizes findings from specialized agents to determine the root cause
7. **Runbook Agent**: Automatically generates remediation steps based on the identified root cause
8. **Notification Agent**: Manages and sends notifications across various channels (Slack, PagerDuty, Webex)
9. **Postmortem Agent**: Automatically generates and maintains postmortem documentation for incidents
10. **Redis**: Message broker for inter-agent communication

## Prerequisites

- Docker and Docker Compose (for local development)
- Kubernetes cluster (for deployment)
- Helm 3
- Access to a Docker registry
- OpenAI API key
- Prometheus instance (for metric data)
- Loki instance (for log data)
- Tempo instance (for tracing data)
- Git repository access (for deployment data)

## Local Development

### Setup Environment

Create a `.env` file with your OpenAI API key:

```sh
OPENAI_API_KEY=your_openai_api_key
```

### Running Locally with Docker Compose

```sh
# Run all components
docker-compose up --build

# Test the system with a sample alert
docker exec -it observability-agent_redis_1 redis-cli
> PUBLISH alerts '{"id":"test1","labels":{"service":"myapp","namespace":"default"},"startsAt":"2023-01-01T00:00:00Z"}'
```

## Building and Pushing Docker Images

We provide a Makefile to simplify the build and deployment process:

```sh
# Build all Docker images
make build

# Push images to a registry
make push REGISTRY=your-registry.com

# Build individual components
make orchestrator
make metric-agent
make log-agent
make deployment-agent
make root-cause-agent
make runbook-agent
make tracing-agent
```

## Kubernetes Deployment with Helm

### Installation

```sh
# Deploy with default settings
helm install observability-agent ./helm/observability-agent \
  --namespace observability --create-namespace \
  --set openai.apiKey=your_openai_api_key

# Deploy with custom settings
helm install observability-agent ./helm/observability-agent \
  --namespace observability --create-namespace \
  --set openai.apiKey=your_openai_api_key \
  --set global.imageRegistry=your-registry.com/ \
  --set metricAgent.prometheus.url=http://your-prometheus:9090 \
  --set logAgent.loki.url=http://your-loki:3100 \
  --set tracingAgent.tempo.url=http://your-tempo:3100
```

### Configuration

The Helm chart can be configured with the following values:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `openai.apiKey` | OpenAI API key | `""` |
| `openai.model` | OpenAI model to use | `"gpt-4"` |
| `redis.enabled` | Whether to deploy Redis | `true` |
| `redis.external.enabled` | Use external Redis | `false` |
| `redis.external.host` | External Redis host | `"redis"` |
| `redis.external.port` | External Redis port | `6379` |
| `metricAgent.prometheus.url` | Prometheus URL | `"http://prometheus-server.monitoring:9090"` |
| `logAgent.loki.url` | Loki URL | `"http://loki-gateway.monitoring:3100"` |
| `tracingAgent.tempo.url` | Tempo URL | `"http://tempo:3100"` |
| `deploymentAgent.gitRepoPath` | Git repository path | `"/app/repo"` |
| `deploymentAgent.argocdServer` | ArgoCD server URL | `"https://argocd-server.argocd:443"` |

For a complete list of configuration options, see the `values.yaml` file in the Helm chart.

## Testing the System

Once deployed, you can test the system by sending an alert to the orchestrator:

```sh
# Port-forward to Redis
kubectl port-forward svc/observability-agent-redis 6379:6379 -n observability

# Send a test alert
redis-cli -h localhost -p 6379 publish alerts '{"id":"test1","labels":{"service":"myapp","namespace":"default"},"startsAt":"2023-01-01T00:00:00Z"}'
```

## Agent Workflows

### Incident Analysis

When an alert is received, the system follows this workflow:

1. **Orchestrator** receives the alert and distributes tasks to specialized agents
2. **Metric Agent** analyzes relevant metrics for the service in alert
3. **Log Agent** gathers and analyzes logs from the affected components
4. **Tracing Agent** identifies related traces and analyzes request flow
5. **Deployment Agent** checks for recent deployments and configuration changes
6. **Root Cause Agent** aggregates findings and determines the most likely root cause
7. **Runbook Agent** generates remediation steps based on the identified root cause
8. **Notification Agent** sends alerts and updates to configured channels
9. **Postmortem Agent** documents the incident and its resolution
10. **Orchestrator** compiles the final report with root cause and remediation steps

### Customizing and Extending

#### Adding New Tools

To add new tools for specialized agents:

1. Create a new tool class in the appropriate file under `common/tools/`
2. Ensure the tool extends the `AgentTool` base class
3. Implement the required methods
4. Import and initialize the tool in the appropriate agent

#### Modifying Agent Behavior

To change how agents analyze data:

1. Edit the appropriate agent file (e.g., `agents/log_agent/agent.py`)
2. Modify the tools used or analysis process
3. Rebuild and redeploy the component

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

[MIT License](LICENSE)
