# Usage Guide

This document provides instructions for using the observability system components.

## System Overview

The observability system consists of several specialized agents that work together to provide comprehensive monitoring, alerting, and incident management capabilities:

1. **Notification Agent**: Handles alert distribution across multiple channels
2. **Postmortem Agent**: Manages incident documentation and knowledge base
3. **Deployment Agent**: Monitors deployment health and rollbacks
4. **Log Agent**: Analyzes logs for patterns and anomalies
5. **Root Cause Agent**: Identifies incident root causes
6. **Runbook Agent**: Manages and executes runbooks
7. **Metric Agent**: Monitors system metrics and thresholds
8. **Tracing Agent**: Analyzes distributed traces for performance issues

## Alert Flow

1. An alert is received by the Orchestrator via NATS "alert_stream" subject
2. The Orchestrator distributes tasks to relevant specialized agents via NATS
3. Specialized agents (Metric, Log, Deployment, Tracing) analyze the incident
4. Agents publish their analyses back to the Orchestrator via "orchestrator_response" 
5. The Root Cause Agent correlates analyses to determine the most likely cause
6. The Notification Agent distributes alerts to configured channels
7. The Runbook Agent suggests and executes relevant runbooks
8. The Postmortem Agent creates and updates incident documentation

## Notification Channels

### Slack

The notification agent sends alerts to Slack channels with the following format:

```
🚨 *Alert: [Alert Name]*
Severity: [Severity Level]
Description: [Alert Description]
Timestamp: [Alert Time]
Service: [Service Name]
Root Cause: [Root Cause] (if available)
```

### PagerDuty

PagerDuty incidents are created with:
- Title: Alert name
- Description: Detailed alert information
- Severity: Based on alert level
- Service: Configured service ID

### Webex

Webex notifications include:
- Alert title and description
- Severity level
- Timestamp
- Direct link to incident details

## Correlation Analysis

The Root Cause Agent can correlate multiple alerts occurring within a time window to identify common underlying issues:

1. Multiple alerts are processed by the Orchestrator
2. The Root Cause Agent uses the `correlation_analysis` tool to analyze temporal relationships
3. Alerts with high correlation are grouped into a single incident
4. The notification includes information about all correlated alerts
5. The postmortem documents the relationship between the alerts

Example of using correlation analysis:

```python
from common.tools.root_cause_tools import correlation_analysis

# Analyze multiple alerts
results = correlation_analysis(
    events=[alert1, alert2, alert3],
    time_window="15m",
    correlation_threshold=0.7
)

# Results contain correlation information
correlated_components = results["correlations"]
```

## Postmortem Process

1. **Incident Creation**
   - Automatic creation when alert is received
   - Initial documentation with alert details

2. **Investigation**
   - Root cause analysis is incorporated
   - Timeline construction from agent analyses
   - Impact assessment

3. **Resolution**
   - Action items tracking
   - Resolution documentation
   - Lessons learned

4. **Knowledge Base Update**
   - Runbook updates from the Runbook Agent
   - Pattern recognition for future incidents
   - Similar incident linking through vector database

## Runbook Management

### Creating Runbooks

1. Create a new markdown file in the runbooks directory
2. Follow the template structure:
   ```markdown
   # [Service Name] Runbook

   ## Overview
   [Service description]

   ## Common Issues
   [List of common issues]

   ## Resolution Steps
   [Step-by-step resolution procedures]

   ## Recent Incidents
   [Auto-updated by the system]
   ```

### Updating Runbooks

Runbooks are automatically updated by the postmortem agent when:
- New incidents occur
- Resolution steps are documented
- Lessons learned are identified

## Health Monitoring

### Agent Health

Monitor agent health through Kubernetes:

```bash
# Check agent status
kubectl get pods -n observability

# View agent logs
kubectl logs -n observability deployment/notification-agent
kubectl logs -n observability deployment/postmortem-agent
```

### NATS Health

Monitor NATS and JetStream status:

```bash
# Check NATS server
kubectl exec -it nats-0 -n observability -- nats server info

# Check NATS streams
kubectl exec -it nats-0 -n observability -- nats stream ls

# Check NATS consumers
kubectl exec -it nats-0 -n observability -- nats consumer ls AGENT_TASKS
```

### System Health

The system exposes metrics for monitoring:
- Alert processing rate
- Notification delivery success
- Postmortem completion time
- Runbook execution success
- NATS message throughput

## Troubleshooting

### Common Issues

1. **Notification Failures**
   - Check API token validity
   - Verify channel/room configurations
   - Review rate limits

2. **Postmortem Generation Issues**
   - Verify template format
   - Check storage permissions
   - Review vector database connectivity

3. **NATS Connectivity Issues**
   - Verify NATS server is running
   - Check NATS stream configurations
   - Review consumer acknowledgments

4. **Agent Processing Problems**
   - Check agent logs for errors
   - Verify message acknowledgments
   - Review CrewAI tool outputs

### Debugging

Enable debug logging by setting:
```bash
LOG_LEVEL=DEBUG
```

View detailed logs:
```bash
kubectl logs -n observability deployment/[agent-name] -f
```

Check NATS message flow:
```bash
# Create monitoring subject
kubectl exec -it nats-0 -n observability -- nats sub ">"
```

## Best Practices

1. **Alert Configuration**
   - Use appropriate severity levels
   - Include detailed descriptions
   - Set up proper routing

2. **Postmortem Documentation**
   - Document all significant incidents
   - Include root cause analysis
   - Track action items

3. **Runbook Maintenance**
   - Keep runbooks up to date
   - Include common scenarios
   - Document resolution steps

4. **System Maintenance**
   - Regular health checks
   - NATS stream management
   - Database maintenance

## API Reference

### Orchestrator API

```python
# Submit alert
POST /api/v1/alert
{
    "alert_id": "string",
    "labels": {
        "alertname": "string",
        "service": "string",
        "severity": "string"
    },
    "annotations": {
        "description": "string"
    },
    "startsAt": "string"
}
```

### Notification Agent

```python
# Send alert
POST /api/v1/notify
{
    "alert_name": "string",
    "severity": "string",
    "description": "string",
    "channels": ["slack", "pagerduty", "webex"]
}
```

### Postmortem Agent

```python
# Create postmortem
POST /api/v1/postmortem
{
    "alert_id": "string",
    "title": "string",
    "description": "string",
    "template": "string"
}

# Update postmortem
PUT /api/v1/postmortem/{id}
{
    "root_cause": "string",
    "resolution": "string",
    "lessons_learned": "string"
}
```

### Runbook Agent

```python
# Execute runbook
POST /api/v1/runbook/execute
{
    "runbook_name": "string",
    "parameters": {}
}

# Update runbook
PUT /api/v1/runbook/{name}
{
    "content": "string"
}
```