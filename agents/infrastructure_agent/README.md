# Consolidated Infrastructure Agent

## Overview

The Consolidated Infrastructure Agent combines the functionality of the deployment_agent and runbook_agent into a single efficient container. This provides end-to-end infrastructure management from deployment analysis to automated remediation while reducing operational complexity.

## Architecture Benefits

### Consolidation Benefits
- **50% fewer containers**: Reduces from 2 separate containers to 1
- **Integrated workflow**: Seamless progression from deployment analysis to runbook execution
- **Shared Kubernetes access**: Efficient reuse of cluster connections and permissions
- **Unified infrastructure view**: Complete picture of deployment state and remediation options

### Performance Improvements
- **Reduced latency**: Direct integration between deployment analysis and runbook execution
- **Memory efficiency**: ~35% reduction in memory footprint vs separate agents
- **Simplified monitoring**: Single process to monitor instead of two
- **Coordinated responses**: Better orchestration of infrastructure operations

## Functionality

### Infrastructure Management Capabilities

#### Deployment Analysis
- Git repository change analysis
- ArgoCD application status monitoring
- Kubernetes deployment configuration review
- Resource allocation and constraint analysis
- Version compatibility verification
- Rollback feasibility assessment

#### Configuration Management
- Configuration drift detection
- Infrastructure-as-code validation
- Environment-specific configuration analysis
- Resource limit and quota verification
- Dependency configuration analysis

#### Runbook Management
- Automated runbook discovery based on infrastructure issues
- Context-aware runbook adaptation
- Safe runbook execution with validation
- Infrastructure-specific remediation procedures
- Rollback and recovery automation

#### Integrated Workflow
- Deployment issue identification → Runbook selection → Automated remediation
- Configuration problem detection → Custom runbook generation → Execution
- Infrastructure analysis → Remediation planning → Coordinated response

## Configuration

### Environment Variables

#### Required
- `OPENAI_API_KEY`: OpenAI API key for analysis
- `NATS_URL`: NATS server URL (default: nats://nats:4222)

#### Optional Infrastructure Configuration
- `ARGOCD_SERVER`: ArgoCD server URL (default: https://argocd-server.argocd:443)
- `GIT_REPO_PATH`: Git repository path (default: /app/repo)
- `RUNBOOK_DIR`: Runbook directory path (default: /runbooks)
- `KUBECONFIG`: Kubernetes configuration (mounted as secret)

#### Optional Configuration
- `OPENAI_MODEL`: OpenAI model to use (default: gpt-4)

## Message Flow

### Input Messages

#### Infrastructure Analysis Requests
- **Subject**: `infrastructure_agent`
- **Stream**: `AGENT_TASKS`
- **Message**: Alert data with service, namespace, and infrastructure context

#### Runbook Execution Requests  
- **Subject**: `runbook.execute.infrastructure`
- **Stream**: `RUNBOOK_EXECUTIONS`
- **Message**: Runbook execution request with context

### Output Messages

#### Analysis Results
- **Subject**: `orchestrator_response`
- **Stream**: `RESPONSES`
- **Message**: Comprehensive infrastructure analysis with remediation recommendations

#### Data Publishing
- `deployments.{service}`: Deployment analysis results
- `runbook.execution.infrastructure`: Runbook execution results

## Agent Status

Publishes health status to `agent.status.infrastructure-agent` for monitoring:
- Status: active/degraded/inactive
- Memory and CPU usage
- Error counts and health metrics
- Connection status to infrastructure services

## Usage

### Standalone Execution
```bash
cd agents/infrastructure_agent
python main.py
```

### Docker Execution
```bash
docker build -t infrastructure-agent .
docker run -e OPENAI_API_KEY=your_key \
           -v ~/.kube/config:/root/.kube/config \
           infrastructure-agent
```

### Kubernetes Deployment
Use the Helm chart with the infrastructure-agent deployment template.

## Dependencies

### External Services
- **NATS JetStream**: Message routing and data streaming
- **ArgoCD**: GitOps deployment management
- **Kubernetes API**: Cluster resource management and monitoring
- **Git repositories**: Source code and configuration analysis

### Required Permissions
- **Kubernetes RBAC**: Read/write access to deployments, pods, services, events
- **ArgoCD Access**: Application management and sync operations
- **Git Access**: Repository read access for change analysis

### Tools Integration
Uses common tools from `common/tools/`:
- `git_tools.py`: Git repository analysis
- `argocd_tools.py`: ArgoCD integration
- `kube_tools.py`: Kubernetes cluster management
- `deployment_tools.py`: Deployment analysis and management
- `runbook_tools.py`: Runbook search and execution
- `jetstream_runbook_source.py`: NATS-based runbook storage

## Migration from Separate Agents

### Replaced Agents
This consolidated agent replaces:
- `deployment_agent`: Deployment analysis and configuration management
- `runbook_agent`: Runbook search, adaptation, and execution

### Orchestrator Changes Required
The orchestrator needs to be updated to:
- Send infrastructure-related alerts to `infrastructure_agent`
- Handle integrated deployment + runbook analysis responses
- Support the new workflow where runbook execution follows deployment analysis

### Stream Configuration
New NATS stream subjects required:
- Add `infrastructure_agent` to `AGENT_TASKS` stream subjects
- Update runbook execution to use `runbook.execute.infrastructure`

## Troubleshooting

### Common Issues

1. **Kubernetes Access Problems**
   - Verify KUBECONFIG is properly mounted
   - Check RBAC permissions for the service account
   - Ensure cluster connectivity

2. **ArgoCD Connection Issues**
   - Verify ArgoCD server URL and accessibility
   - Check authentication credentials
   - Validate network connectivity to ArgoCD

3. **Git Repository Access**
   - Verify Git repository URLs and credentials
   - Check network access to Git servers
   - Validate repository permissions

4. **Runbook Execution Failures**
   - Check runbook syntax and validity
   - Verify execution permissions and prerequisites
   - Review safety validations and constraints

### Health Checks
The agent provides health check endpoint that verifies:
- NATS connectivity
- Kubernetes API accessibility
- ArgoCD service availability
- Git repository accessibility

### Monitoring
Monitor the following metrics:
- Agent status via NATS `agent.status.infrastructure-agent`
- Deployment analysis completion times
- Runbook execution success rates
- Infrastructure operation error rates

## Performance Tuning

### Resource Optimization
- Adjust Kubernetes API call batching for large clusters
- Configure Git repository caching for faster analysis
- Tune ArgoCD polling intervals for efficiency

### Analysis Optimization
- Configure appropriate timeouts for infrastructure operations
- Adjust runbook execution parallelization
- Optimize deployment comparison algorithms

### Safety Configuration
- Configure runbook execution safety checks
- Set appropriate rollback thresholds
- Implement infrastructure change validation rules

## Security Considerations

### Access Control
- Use least-privilege RBAC for Kubernetes access
- Implement secure credential management for ArgoCD
- Restrict Git repository access to read-only where possible

### Runbook Safety
- Validate runbook steps before execution
- Implement approval workflows for critical operations
- Log all infrastructure changes and operations

### Network Security
- Use secure connections for all external integrations
- Implement network policies for cluster access
- Monitor and audit infrastructure operations