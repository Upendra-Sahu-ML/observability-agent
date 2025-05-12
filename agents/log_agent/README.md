# Log Agent

The Log Agent is a specialized component of the Observability Agent system dedicated to analyzing log data from multiple sources to detect patterns, errors, and anomalies that may contribute to system incidents.

## Overview

The Log Agent uses AI-powered analysis to process logs from various sources, including Loki, Kubernetes pods, and system log files. It's designed to identify critical error messages, recurring patterns, and unusual behaviors in application and system logs that may indicate the root cause of incidents.

## Functionality

- **Multi-Source Log Collection**: Gathers logs from Loki, Kubernetes pods, and filesystem
- **Contextual Analysis**: Analyzes log data in the context of specific alerts and timeframes
- **Pattern Recognition**: Identifies recurring patterns and anomalies in log data
- **Error Classification**: Categorizes different types of issues found in logs (e.g., OOM, crash loops)
- **Response Publishing**: Sends detailed log analysis back to the Orchestrator

## Key Components

- **LokiQueryTool**: Executes queries against Loki to retrieve application logs
- **PodLogTool**: Fetches logs directly from Kubernetes pods
- **FileLogTool**: Reads log files from the local filesystem

## How It Works

1. The agent listens on the "log_agent" Redis channel for alerts from the Orchestrator
2. When an alert is received, the agent:
   - Extracts context like service name, namespace, and timeframe
   - Queries logs from multiple sources for the relevant timeframe
   - Uses CrewAI with GPT-4 to analyze the log content
   - Identifies common error patterns and critical messages
   - Classifies the specific type of log issue observed
   - Sends the analysis back to the Orchestrator via the "orchestrator_response" channel

## Configuration

The Log Agent can be configured with the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `LOKI_URL` | URL of the Loki server | `http://loki:3100` |
| `LOG_DIRECTORY` | Directory to search for log files | `/var/log` |
| `REDIS_HOST` | Redis host for message communication | `redis` |
| `REDIS_PORT` | Redis port for message communication | `6379` |
| `OPENAI_API_KEY` | OpenAI API key for log analysis | None (required) |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4` |

## Customization

To modify the log analysis behavior:

1. Update the `_get_logs_for_alert()` method to collect logs from additional sources
2. Enhance the `_determine_observed_issue()` method to detect more specific log patterns
3. Modify the log analysis prompt in `analyze_logs()` to focus on specific patterns

## Local Development

```bash
# Run the Log Agent standalone
cd agents/log_agent
python main.py
```

## Docker

Build and run the Log Agent as a Docker container:

```bash
docker build -t log-agent -f agents/log_agent/Dockerfile .
docker run -e LOKI_URL=http://loki:3100 -e OPENAI_API_KEY=your_key log-agent
```

## Integration

The Log Agent is designed to work as part of the Observability Agent system. It:
- Receives alerts from the Orchestrator
- Publishes log analysis results back to the Orchestrator
- Helps determine the root cause by identifying error patterns in logs
- Works alongside other specialized agents to provide comprehensive incident analysis