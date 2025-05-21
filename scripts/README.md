# Observability Agent Test Data Generation Tools

This directory contains tools to help you test the Observability Agent System by publishing sample data to NATS JetStream. These tools simulate various types of data that might occur in a production environment.

## Data Generation Scripts

The following Node.js scripts are available for generating test data for the UI:

- `generate_all_data.js` - All-in-one script that runs multiple data generators simultaneously
- `publish_metrics.js` - Generates and publishes metrics data
- `publish_logs.js` - Generates and publishes log data
- `publish_deployments.js` - Generates and publishes deployment data
- `publish_agent_status.js` - Generates and publishes agent status updates
- `publish_traces.js` - Generates and publishes distributed tracing data
- `publish_rootcauses.js` - Generates and publishes root cause analysis data
- `publish_notifications.js` - Generates and publishes notification data
- `publish_postmortems.js` - Generates and publishes postmortem data
- `publish_runbooks.js` - Generates and publishes runbook data
- `publish_alerts.js` - Generates and publishes alert data

See the [Node.js Data Generation Scripts](#nodejs-data-generation-scripts) section below for more details.

## Alert Publisher Tool

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

## Node.js Data Generation Scripts

These scripts provide a comprehensive way to generate test data for all components of the Observability Agent UI.

### Prerequisites

- Node.js (v14 or later)
- NATS server with JetStream enabled (for publishing to NATS)
- Access to the NATS server from your local machine

### Testing Without NATS

If you don't have a NATS server available, you can use the test data generator to verify that the data generation functions work correctly:

```bash
node test_data_generator.js --component=metrics --count=2
```

Options:
- `--component=<name>`: Component to test (default: all)
- `--count=<number>`: Number of items to generate (default: 3)
- `--services=<list>`: Comma-separated list of services

This will generate sample data and output it to the console without requiring a NATS server.

### Common Usage

All scripts support the following common options:

- `--nats-url=<url>`: NATS server URL (default: `nats://localhost:4222`)
- `--count=<number>`: Number of data items to generate
- `--interval=<ms>`: Interval between publications in milliseconds
- `--continuous`: Run continuously instead of stopping after `count` items
- `--services=<list>`: Comma-separated list of services to generate data for

### All-in-One Generator

The `generate_all_data.js` script runs multiple data generators simultaneously:

```bash
node generate_all_data.js --nats-url=nats://localhost:4222 --duration=300 --components=metrics,logs,alerts
```

Options:
- `--duration=<seconds>`: How long to run in seconds (default: 300)
- `--components=<list>`: Comma-separated list of components to generate data for (default: all)
  - Available components: metrics, logs, deployments, agents, traces, rootcauses, notifications, postmortems, runbooks, alerts

### Individual Data Generators

#### Agent Status Data

```bash
node publish_agent_status.js --nats-url=nats://localhost:4222 --continuous
```

Publishes agent status updates to the `AGENTS` stream.

#### Metrics Data

```bash
node publish_metrics.js --nats-url=nats://localhost:4222 --count=20 --continuous
```

Publishes metrics data to the `METRICS` stream.

#### Logs Data

```bash
node publish_logs.js --nats-url=nats://localhost:4222 --count=50 --continuous
```

Publishes log entries to the `LOGS` stream.

#### Deployment Data

```bash
node publish_deployments.js --nats-url=nats://localhost:4222 --count=10
```

Publishes deployment events to the `DEPLOYMENTS` stream.

#### Tracing Data

```bash
node publish_traces.js --nats-url=nats://localhost:4222 --count=15
```

Publishes distributed tracing data to the `TRACES` stream.

#### Root Cause Analysis Data

```bash
node publish_rootcauses.js --nats-url=nats://localhost:4222 --count=8
```

Publishes root cause analysis results to the `ROOTCAUSES` stream.

#### Notification Data

```bash
node publish_notifications.js --nats-url=nats://localhost:4222 --count=12
```

Publishes notification events to the `NOTIFICATIONS` stream.

#### Postmortem Data

```bash
node publish_postmortems.js --nats-url=nats://localhost:4222 --count=5
```

Publishes postmortem documents to the `POSTMORTEMS` stream.

#### Runbook Data

```bash
node publish_runbooks.js --nats-url=nats://localhost:4222 --count=8
```

Publishes runbooks to the `RUNBOOKS` stream.

#### Alert Data

```bash
node publish_alerts.js --nats-url=nats://localhost:4222 --count=15 --active-ratio=0.3
```

Publishes alerts to the `ALERTS` stream.

Options:
- `--active-ratio=<float>`: Ratio of active to resolved alerts (default: 0.3)

### Using with Kubernetes

If your NATS server is running in Kubernetes, you can use port forwarding to access it:

```bash
# Forward the NATS port to your local machine
kubectl port-forward service/nats 4222:4222 -n your-namespace

# In another terminal, run the data generator
node generate_all_data.js --nats-url=nats://localhost:4222
```

### Examples

#### Generate a continuous stream of metrics and logs

```bash
node generate_all_data.js --components=metrics,logs --continuous
```

#### Generate a fixed number of alerts

```bash
node publish_alerts.js --count=20 --active-ratio=0.5
```

#### Generate data for a specific service

```bash
node publish_metrics.js --services=payment-service --count=50
```

#### Generate all types of data for 10 minutes

```bash
node generate_all_data.js --duration=600
```