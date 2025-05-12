# Alert Publisher Tool

This tool helps you test the Observability Agent System by publishing sample alerts to Redis. It simulates various types of alerts that might occur in a production environment.

## Prerequisites

1. Python 3.10+
2. Redis server running
3. Observability Agent System deployed

## Installation

1. Install the required Python package:
   ```bash
   pip install redis
   ```

2. Make the script executable:
   ```bash
   chmod +x alert_publisher.py
   ```

## Usage

### Basic Usage

Publish a single random alert:
```bash
./alert_publisher.py
```

### Command Line Options

```bash
./alert_publisher.py [options]

Options:
  --redis-host HOST     Redis host (default: localhost)
  --redis-port PORT     Redis port (default: 6379)
  --alert-type TYPE     Type of alert to publish
  --interval SECONDS    Interval between alerts (default: 5)
  --count NUMBER        Number of alerts to publish (default: 1)
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

1. Publish 5 CPU alerts with 10-second intervals:
   ```bash
   ./alert_publisher.py --alert-type cpu --count 5 --interval 10
   ```

2. Publish random alerts continuously:
   ```bash
   ./alert_publisher.py --count 0 --interval 30
   ```

3. Publish to a remote Redis instance:
   ```bash
   ./alert_publisher.py --redis-host redis.example.com --redis-port 6379
   ```

## Expected System Behavior

When you publish alerts, you should observe the following in the Observability Agent System:

1. **Orchestrator**
   - Receives the alert from Redis
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

3. **Check Redis Messages**
   ```bash
   redis-cli
   > SUBSCRIBE alerts
   ```

4. **Check Qdrant Data**
   ```bash
   curl http://localhost:6333/collections/incidents/points
   ```

## Troubleshooting

1. **Alert Not Received**
   - Verify Redis connection
   - Check Redis pub/sub channel
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