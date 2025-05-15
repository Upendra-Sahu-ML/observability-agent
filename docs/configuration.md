# Configuration Guide

This document provides detailed information about configuring the observability system components.

## Environment Variables

### Common Configuration

The following environment variables are used across all agents:

```bash
# NATS Configuration
NATS_SERVER=nats://nats:4222

# OpenAI Configuration
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4
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

# File System Configuration
POSTMORTEM_TEMPLATE_DIR=/app/templates
RUNBOOK_DIR=/app/runbooks
```

### Metric Agent

```bash
# Prometheus Configuration
PROMETHEUS_URL=http://prometheus:9090
```

### Log Agent

```bash
# Elasticsearch Configuration
ELASTICSEARCH_URL=http://elasticsearch:9200
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
  nats_server: "nats://nats:4222"
  slack_default_channel: "#incidents"
  pagerduty_service_id: "your-service-id"
  webex_default_room_id: "your-room-id"
  qdrant_url: "http://qdrant:6333"
  prometheus_url: "http://prometheus:9090"
  elasticsearch_url: "http://elasticsearch:9200"
```

### Secrets

Create a Secret for sensitive configuration:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: observability-secrets
  namespace: observability
type: Opaque
data:
  openai_api_key: <base64-encoded-key>
  slack_bot_token: <base64-encoded-token>
  pagerduty_api_token: <base64-encoded-token>
  webex_access_token: <base64-encoded-token>
```

## NATS Configuration

### JetStream Configuration

Configure NATS JetStream for persistent messaging:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: nats-js-config
  namespace: observability
data:
  nats.conf: |
    jetstream {
      store_dir: /data
      max_mem: 1G
      max_file: 10G
    }
    
    # Streams Configuration
    jetstream {
      # ALERTS Stream
      streams {
        name: ALERTS
        subjects: ["alert_stream"]
        retention: limits
        max_age: 24h
      }
      
      # AGENT_TASKS Stream
      streams {
        name: AGENT_TASKS
        subjects: [
          "metric_agent", 
          "log_agent", 
          "deployment_agent", 
          "tracing_agent", 
          "root_cause_agent", 
          "notification_agent", 
          "postmortem_agent", 
          "runbook_agent"
        ]
        retention: limits
        max_msgs: 10000
      }
      
      # RESPONSES Stream
      streams {
        name: RESPONSES
        subjects: ["orchestrator_response"]
        retention: limits
        max_msgs: 10000
      }
      
      # NOTIFICATIONS Stream
      streams {
        name: NOTIFICATIONS
        subjects: ["notification_requests"]
        retention: limits
        max_msgs: 10000
      }
    }
```

### Durable Consumers

Each agent uses durable consumers to ensure message delivery:

```yaml
# Example consumer creation in Python
consumer_config = ConsumerConfig(
    durable_name="metric_agent",
    deliver_policy=DeliverPolicy.ALL,
    ack_policy="explicit",
    max_deliver=5,  # Retry up to 5 times
    ack_wait=60,    # Wait 60 seconds for acknowledgment
)

await js.subscribe(
    "metric_agent",
    cb=message_handler,
    queue="metric_processors",
    config=consumer_config
)
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

### Orchestrator
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "200m"
```

### Specialized Agents
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "200m"
```

### NATS Server
```yaml
resources:
  requests:
    memory: "128Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "200m"
```

## Storage

### NATS JetStream Storage

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: nats-js-pvc
  namespace: observability
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

### Postmortem Agent Storage

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

## Security Configuration

### NATS Authentication

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: nats-auth
  namespace: observability
type: Opaque
data:
  nats-auth.conf: |
    accounts {
      observability {
        users = [
          {user: agent, password: $AGENT_PASSWORD}
        ]
        exports [
          {stream: alert_stream}
          {stream: agent_tasks}
          {stream: orchestrator_response}
        ]
      }
    }
```