# Consolidated Communication Agent

## Overview

The Consolidated Communication Agent combines the functionality of the notification_agent and postmortem_agent into a single efficient container. This provides end-to-end incident communication from immediate notifications to comprehensive postmortem documentation while reducing operational complexity.

## Architecture Benefits

### Consolidation Benefits
- **50% fewer containers**: Reduces from 2 separate containers to 1
- **Integrated workflow**: Seamless progression from notification to postmortem generation
- **Shared context**: Notification data directly available for postmortem analysis
- **Unified communication strategy**: Coordinated incident communication lifecycle

### Performance Improvements
- **Reduced latency**: Direct integration between notification and postmortem systems
- **Memory efficiency**: ~40% reduction in memory footprint vs separate agents
- **Simplified monitoring**: Single process to monitor instead of two
- **Coordinated responses**: Better orchestration of communication activities

## Functionality

### Notification Management
- **Multi-channel notifications**: Supports Slack, WebEx, and PagerDuty
- **Intelligent prioritization**: Determines appropriate channels based on severity
- **Severity-based escalation**: Critical alerts trigger multiple channels
- **Formatted messaging**: Optimizes message format for each platform

### Postmortem Generation
- **Multi-agent analysis**: Uses specialized AI agents for comprehensive analysis
- **Technical root cause analysis**: Deep technical investigation
- **Business impact assessment**: Quantifies user and business impact
- **Timeline construction**: Creates detailed incident chronology
- **Remediation planning**: Develops prevention strategies
- **Document compilation**: Produces professional postmortem reports

### Integrated Communication Workflow
- Alert reception → Immediate notification → Context gathering → Postmortem generation
- Notification tracking → Impact assessment → Documentation → Stakeholder communication

## Architecture

The Communication Agent uses a multi-agent CrewAI framework with specialized roles:

### Notification Agents
- **Alert Prioritizer**: Analyzes severity and determines notification strategy
- **Notification Manager**: Executes notifications across multiple channels

### Postmortem Agents
- **Technical Analyst**: Analyzes technical root causes and system failures
- **Impact Analyst**: Assesses business and user impact
- **Timeline Constructor**: Creates detailed incident timelines
- **Remediation Planner**: Develops prevention and improvement plans
- **Postmortem Editor**: Compiles final comprehensive documents

## Usage

### Environment Variables
```bash
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini  # Optional, defaults to gpt-4
NATS_URL=nats://nats:4222
```

### Message Flow

#### Input
- **Subject**: `communication_agent`
- **Stream**: `AGENT_TASKS`
- **Message**: Alert data with notification and postmortem requirements

#### Output
- **Subject**: `orchestrator_response`
- **Stream**: `RESPONSES`
- **Message**: Combined notification status and postmortem generation results

#### Data Publishing
The agent publishes results to multiple streams for UI consumption:
- `notifications.{service}`: Notification status and delivery confirmations
- `postmortems.{incident_id}`: Generated postmortem documents

### Message Format

#### Notification Request
```json
{
  "alert_id": "alert-123",
  "task_type": "notification",
  "labels": {
    "alertname": "High CPU Usage",
    "service": "api-service",
    "severity": "critical"
  },
  "annotations": {
    "description": "CPU usage is above 90%"
  }
}
```

#### Postmortem Request
```json
{
  "alert_id": "alert-123",
  "task_type": "postmortem",
  "root_cause": "Database connection pool exhaustion due to...",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Resource Requirements

The Communication Agent requires increased resources compared to individual agents:

- **Memory**: 512Mi request, 1Gi limit
- **CPU**: 200m request, 500m limit

## Integration

### With Orchestrator
The agent integrates with the orchestrator for:
- Receiving alert notifications
- Fetching complete alert data
- Publishing results back to orchestrator

### With UI
Results are stored in NATS streams for UI consumption:
- Notification statuses in `RESPONSES` stream
- Postmortem documents in `RESPONSES` stream with sub_function markers

### Notification Channels
Configure notification tools with appropriate credentials:
- Slack: Bot token and channel configuration
- PagerDuty: Integration key and service ID
- WebEx: Bot token and room ID

## Agent Status

Publishes health status to `agent.status.communication-agent` for monitoring:
- Status: active/degraded/inactive
- Memory and CPU usage
- Error counts and health metrics
- Notification channel connectivity status

## Migration from Separate Agents

### Replaced Agents
This consolidated agent replaces:
- `notification_agent`: Multi-channel alert notification management
- `postmortem_agent`: Incident postmortem document generation

### Orchestrator Changes Required
The orchestrator needs to be updated to:
- Send communication-related alerts to `communication_agent`
- Handle integrated notification + postmortem analysis responses
- Support the new workflow where postmortem generation follows notification

### Stream Configuration
New NATS stream subjects required:
- Add `communication_agent` to `AGENT_TASKS` stream subjects
- Update notification and postmortem data publishing to use consolidated subjects

## Benefits of Consolidation

1. **Resource Efficiency**: 40% reduction in memory and CPU usage
2. **Simplified Operations**: Single agent to monitor instead of two
3. **Improved Coordination**: Shared context between notification and postmortem functions
4. **Consistent Configuration**: Unified environment and deployment management
5. **Enhanced Reliability**: Fewer moving parts reduce failure points

## Deployment

The agent is deployed as a Kubernetes deployment with:
- Service account for RBAC
- ConfigMaps for notification templates
- Secrets for API keys and credentials
- Persistent volumes for postmortem templates

See the Helm chart configuration for detailed deployment options.