# Alert Publisher Tool

This tool helps you test the Observability Agent System by publishing sample alerts to NATS JetStream. It simulates various types of alerts that might occur in a production environment.

## Overview

The Alert Publisher can be run in two ways:
1. As a Python script directly on your local machine
2. As a containerized application in a Kubernetes environment

## Prerequisites

### For Local Execution
1. Python 3.9+
2. NATS server with JetStream enabled
3. Observability Agent System deployed

### For Kubernetes Deployment
1. Kubernetes cluster with the Observability Agent deployed
2. Container registry to store the alert publisher image

## Installation

### Local Installation

1. Install the required Python packages:
   ```bash
   pip install -r requirements-alert-publisher.txt
   ```

2. Make the script executable:
   ```bash
   chmod +x alert_publisher.py
   ```

### Container Image Build

1. Build the Docker image:
   ```bash
   # Using the Makefile
   make alert-publisher REGISTRY=your-registry

   # Or directly with Docker
   docker build -t your-registry/alert-publisher:latest -f Dockerfile.alert-publisher .
   ```

2. Push the image to your registry:
   ```bash
   docker push your-registry/alert-publisher:latest
   ```

## Usage

### Running Locally

```bash
./alert_publisher.py [options]

Options:
  --nats-server URL     NATS server URL (default: nats://nats:4222)
  --alert-type TYPE     Type of alert to publish
  --interval SECONDS    Interval between alerts (default: 5)
  --count NUMBER        Number of alerts to publish (default: 1)
```

### Running in Kubernetes

1. Update the registry reference in the Kubernetes manifest:
   ```bash
   sed -i 's|\${REGISTRY}|your-registry|g' alert-publisher-k8s.yaml
   ```

2. Deploy as a one-time job:
   ```bash
   kubectl apply -f alert-publisher-k8s.yaml
   ```

3. For continuous alert generation, use the deployment:
   ```bash
   # The deployment will continuously generate alerts at the configured interval
   kubectl get pods -l app=alert-publisher  # Check if it's running
   ```

4. To customize alert generation, edit the manifest or use kubectl:
   ```bash
   kubectl set env deployment/alert-publisher ALERT_TYPE=cpu ALERT_COUNT=10 INTERVAL=30
   ```

### Alert Types

The tool supports the following alert types:

1. **CPU Usage** (`--alert-type cpu`)
   - Simulates high CPU usage alerts
   - Values: 80-100%
   - Threshold: 80%

2. **Memory Usage** (`--alert-type memory`)
   - Simulates high memory usage alerts
   - Values: 85-100%
   - Threshold: 85%

3. **Latency** (`--alert-type latency`)
   - Simulates high latency alerts
   - Values: 1.5-3.0s
   - Threshold: 1s

4. **Error Rate** (`--alert-type error_rate`)
   - Simulates high error rate alerts
   - Values: 5-20%
   - Threshold: 5%

5. **Deployment** (`--alert-type deployment`)
   - Simulates deployment failure alerts
   - Values: "failed" or "stuck"

6. **Random** (`--alert-type random`)
   - Randomly selects one of the above types

### Examples

1. Publish 5 CPU alerts with 10-second intervals locally:
   ```bash
   ./alert_publisher.py --alert-type cpu --count 5 --interval 10 --nats-server nats://localhost:4222
   ```

2. Run a one-time job in Kubernetes:
   ```bash
   kubectl run alert-publisher-job --image=your-registry/alert-publisher:latest --restart=Never -- --alert-type cpu --count 5 --interval 10
   ```

## Expected System Behavior

When you publish alerts, you should observe the following in the Observability Agent System:

1. **Orchestrator**
   - Receives the alert from NATS JetStream
   - Logs the alert reception
   - Distributes to relevant agents

2. **Specialized Agents**
   - Metric Agent: Processes CPU, memory, and latency alerts
   - Log Agent: Analyzes error rate alerts
   - Deployment Agent: Handles deployment alerts
   - Other agents: Contribute based on alert type

3. **Knowledge Base**
   - Stores alert data in Qdrant
   - Updates with analysis results
   - Maintains incident history

4. **Notifications**
   - Notification Agent receives alerts
   - Sends to configured channels
   - Logs notification status

## Monitoring the System

1. **Check Orchestrator Logs**
   ```bash
   kubectl logs -f deployment/observability-agent-orchestrator
   ```

2. **Check Agent Logs**
   ```bash
   kubectl logs -f deployment/observability-agent-metric-agent
   kubectl logs -f deployment/observability-agent-log-agent
   # etc.
   ```

3. **Check NATS Streams**
   ```bash
   # Using the NATS CLI
   nats stream info ALERTS
   
   # Or from another pod with the NATS client
   kubectl exec -it observability-agent-nats-0 -- nats stream info ALERTS
   ```

## Troubleshooting

1. **Alert Not Received**
   - Verify NATS connection
   - Check NATS stream existence
   - Verify orchestrator is running

2. **No Agent Response**
   - Check agent logs
   - Verify agent configuration
   - Check agent health status

3. **Knowledge Base Issues**
   - Verify Qdrant connection
   - Check storage capacity
   - Validate data format

## Best Practices

1. **Testing Different Scenarios**
   - Test each alert type
   - Test multiple alerts in sequence
   - Test high-volume scenarios

2. **Monitoring System Response**
   - Watch agent response times
   - Monitor resource usage
   - Check notification delivery

3. **Data Validation**
   - Verify alert format
   - Check data persistence
   - Validate analysis results