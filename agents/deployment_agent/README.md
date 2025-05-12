# Deployment Agent

The Deployment Agent is a specialized component of the Observability Agent system focused on analyzing deployment configurations, code changes, and infrastructure state to identify deployment-related issues that may be causing system incidents.

## Overview

The Deployment Agent uses AI-powered analysis to correlate deployment activities with system incidents. It examines Git commits, Kubernetes deployment configurations, and ArgoCD state to determine if recent changes or misconfigurations might be responsible for system problems.

## Functionality

- **Git Change Analysis**: Examines recent code changes in Git repositories
- **Kubernetes Inspection**: Analyzes Kubernetes deployment configurations and state
- **ArgoCD Integration**: Checks ArgoCD application state and deployment history
- **Change Correlation**: Correlates deployment changes with incident timing
- **Response Publishing**: Sends deployment analysis back to the Orchestrator

## Key Components

- **GitChangeTool**: Retrieves and analyzes recent Git commits and code diffs
- **KubeDeploymentTool**: Examines Kubernetes deployment configurations and status
- **ArgoCDTool**: Checks ArgoCD application state and deployment history

## How It Works

1. The agent listens on the "deployment_agent" Redis channel for alerts from the Orchestrator
2. When an alert is received, the agent:
   - Extracts relevant context (service, namespace, timeframe)
   - Checks recent Git repository changes
   - Analyzes Kubernetes deployment configurations
   - Examines ArgoCD deployment history if available
   - Uses CrewAI with GPT-4 to analyze the deployment data
   - Classifies the type of deployment issue observed
   - Sends the analysis back to the Orchestrator via the "orchestrator_response" channel

## Configuration

The Deployment Agent can be configured with the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `GIT_REPO_PATH` | Path to the Git repository | `/app/repo` |
| `ARGOCD_SERVER` | URL of the ArgoCD server | `https://argocd-server.argocd:443` |
| `ARGOCD_TOKEN` | ArgoCD API token for authentication | None |
| `REDIS_HOST` | Redis host for message communication | `redis` |
| `REDIS_PORT` | Redis port for message communication | `6379` |
| `OPENAI_API_KEY` | OpenAI API key for deployment analysis | None (required) |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4` |

## Customization

To modify the deployment analysis behavior:

1. Update the `_get_deployment_data()` method to collect additional deployment information
2. Enhance the `_determine_observed_issue()` method to detect more specific deployment patterns
3. Add support for additional deployment tools or CI/CD systems

## Local Development

```bash
# Run the Deployment Agent standalone
cd agents/deployment_agent
python main.py
```

## Docker

Build and run the Deployment Agent as a Docker container:

```bash
docker build -t deployment-agent -f agents/deployment_agent/Dockerfile .
docker run -e GIT_REPO_PATH=/app/repo -e OPENAI_API_KEY=your_key deployment-agent
```

## Integration

The Deployment Agent is designed to work as part of the Observability Agent system. It:
- Receives alerts from the Orchestrator
- Publishes deployment analysis results back to the Orchestrator
- Identifies deployment-related causes of incidents
- Works alongside other specialized agents to provide comprehensive incident analysis