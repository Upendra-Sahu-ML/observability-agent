# Metric Agent

The Metric Agent is a specialized component of the Observability Agent system responsible for analyzing metric data from Prometheus to identify patterns, anomalies, and potential issues contributing to incidents.

## Overview

The Metric Agent uses AI-powered analysis to process time series metrics from Prometheus, looking for correlations between metric patterns and system incidents. It's designed to answer questions like: "Is there a CPU spike?", "Are we seeing increased error rates?", or "Is there unusual latency in the system?".

## Functionality

- **Prometheus Integration**: Connects to Prometheus to query and analyze metric data
- **Dynamic Query Construction**: Builds appropriate Prometheus queries based on the incident context
- **Anomaly Detection**: Identifies unusual patterns in metrics during incident timeframes
- **Trend Analysis**: Analyzes metric trends leading up to incidents to identify potential causes
- **Response Publishing**: Sends analysis results back to the Orchestrator

## Key Components

- **PrometheusQueryTool**: Executes instant queries against Prometheus
- **PrometheusRangeQueryTool**: Performs time-range queries to analyze metric patterns over time
- **PrometheusMetricsTool**: Lists and provides metadata for available metrics
- **PrometheusTargetsTool**: Analyzes Prometheus scrape targets to check for monitoring issues

## How It Works

1. The agent listens on the "metric_agent" Redis channel for alerts from the Orchestrator
2. When an alert is received, the agent:
   - Extracts relevant context (service, namespace, timeframe)
   - Constructs appropriate Prometheus queries
   - Retrieves instant metric values and time-range data
   - Uses CrewAI with GPT-4 to analyze the metric data
   - Classifies the type of metric issue observed
   - Sends the analysis back to the Orchestrator via the "orchestrator_response" channel

## Configuration

The Metric Agent can be configured with the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `PROMETHEUS_URL` | URL of the Prometheus server | `http://prometheus:9090` |
| `REDIS_HOST` | Redis host for message communication | `redis` |
| `REDIS_PORT` | Redis port for message communication | `6379` |
| `OPENAI_API_KEY` | OpenAI API key for metric analysis | None (required) |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4` |

## Customization

To modify the metric analysis behavior:

1. Update the query patterns in `_get_metrics_for_alert()` method
2. Enhance the issue detection logic in `_determine_observed_issue()` method
3. Add new metric collection methods for specific analysis needs

## Local Development

```bash
# Run the Metric Agent standalone
cd agents/metric_agent
python main.py
```

## Docker

Build and run the Metric Agent as a Docker container:

```bash
docker build -t metric-agent -f agents/metric_agent/Dockerfile .
docker run -e PROMETHEUS_URL=http://prometheus:9090 -e OPENAI_API_KEY=your_key metric-agent
```

## Integration

The Metric Agent is designed to work as part of the Observability Agent system. It:
- Receives alerts from the Orchestrator
- Publishes analysis results back to the Orchestrator
- Contributes to root cause analysis alongside other specialized agents