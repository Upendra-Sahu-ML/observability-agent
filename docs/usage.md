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

## Alert Flow

1. When an alert is triggered, it is sent to the notification agent
2. The notification agent distributes the alert to configured channels (Slack, PagerDuty, Webex)
3. The postmortem agent creates an incident record and begins documentation
4. Specialized agents (Deployment, Log, Root Cause) analyze the incident
5. The runbook agent suggests and executes relevant runbooks
6. The postmortem agent updates documentation with findings and resolutions

## Notification Channels

### Slack

The notification agent sends alerts to Slack channels with the following format:

```
🚨 *Alert: [Alert Name]*
Severity: [Severity Level]
Description: [Alert Description]
Timestamp: [Alert Time]
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

## Postmortem Process

1. **Incident Creation**
   - Automatic creation when alert is received
   - Initial documentation with alert details

2. **Investigation**
   - Root cause analysis
   - Timeline construction
   - Impact assessment

3. **Resolution**
   - Action items tracking
   - Resolution documentation
   - Lessons learned

4. **Knowledge Base Update**
   - Runbook updates
   - Pattern recognition
   - Similar incident linking

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

### System Health

The system exposes metrics for monitoring:
- Alert processing rate
- Notification delivery success
- Postmortem completion time
- Runbook execution success

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

3. **Runbook Execution Problems**
   - Validate runbook format
   - Check execution permissions
   - Review error logs

### Debugging

Enable debug logging by setting:
```bash
LOG_LEVEL=DEBUG
```

View detailed logs:
```bash
kubectl logs -n observability deployment/[agent-name] -f
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
   - Log rotation
   - Database maintenance

## API Reference

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