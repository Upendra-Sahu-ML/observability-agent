# Configuration Guide

This document provides detailed information about configuring the observability system components.

## Environment Variables

### Common Configuration

The following environment variables are used across all agents:

```bash
# Redis Configuration
REDIS_HOST=redis-service
REDIS_PORT=6379

# OpenAI Configuration
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4-turbo-preview
```

### Notification Agent

```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_DEFAULT_CHANNEL=#incidents

# PagerDuty Configuration
PAGERDUTY_API_TOKEN=your-token
PAGERDUTY_SERVICE_ID=your-service-id

# Webex Configuration
WEBEX_ACCESS_TOKEN=your-token
WEBEX_DEFAULT_ROOM_ID=your-room-id
```

### Postmortem Agent

```bash
# Vector Database Configuration
QDRANT_URL=http://qdrant:6333
WEAVIATE_URL=http://weaviate:8080

# File System Configuration
POSTMORTEM_TEMPLATE_DIR=/app/templates
RUNBOOK_DIR=/app/runbooks
```

## Kubernetes Configuration

### ConfigMaps

Create a ConfigMap for common configuration:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: observability-config
  namespace: observability
data:
  redis_host: "redis-service"
  redis_port: "6379"
  slack_default_channel: "#incidents"
  pagerduty_service_id: "your-service-id"
  webex_default_room_id: "your-room-id"
  qdrant_url: "http://qdrant:6333"
  weaviate_url: "http://weaviate:8080"
```

### Secrets

Create a Secret for sensitive configuration:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: notification-secrets
  namespace: observability
type: Opaque
data:
  slack_bot_token: <base64-encoded-token>
  pagerduty_api_token: <base64-encoded-token>
  webex_access_token: <base64-encoded-token>
```

## Postmortem Templates

Postmortem templates should be stored in the `templates` directory and mounted as a ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: postmortem-templates
  namespace: observability
data:
  default.md: |
    # Incident Postmortem: {{ title }}

    ## Overview
    {{ description }}

    ## Timeline
    {{ timeline }}

    ## Root Cause
    {{ root_cause }}

    ## Impact
    {{ impact }}

    ## Resolution
    {{ resolution }}

    ## Lessons Learned
    {{ lessons_learned }}

    ## Action Items
    {{ action_items }}
```

## Runbooks

Runbooks are stored in a persistent volume and should be initialized with basic templates:

```markdown
# Service Runbook

## Overview
[Service description]

## Common Issues
[List of common issues and their solutions]

## Recent Incidents
[This section will be automatically updated by the postmortem agent]
```

## Health Checks

All agents expose health check endpoints:

- `/health` - Liveness probe
- `/ready` - Readiness probe

Configure these in the Kubernetes deployments:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
```

## Resource Requirements

### Notification Agent
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "200m"
```

### Postmortem Agent
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "200m"
  limits:
    memory: "1Gi"
    cpu: "500m"
```

## Storage

The postmortem agent requires persistent storage for runbooks:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: runbooks-pvc
  namespace: observability
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
``` 