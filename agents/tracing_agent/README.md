# Tracing Agent

The Tracing Agent is a specialized component of the Observability Agent system dedicated to analyzing distributed tracing data to understand service interactions, identify performance bottlenecks, and pinpoint failures in distributed systems.

## Overview

The Tracing Agent uses AI-powered analysis to process distributed traces from systems like Tempo, Jaeger, or Zipkin. It examines trace data to identify slow services, failed requests, and service dependencies that may be contributing to system incidents.

## Functionality

- **Trace Analysis**: Analyzes distributed trace data to identify service issues
- **Service Performance Profiling**: Establishes performance baselines and detects deviations
- **Bottleneck Detection**: Identifies slow spans and services that contribute to latency
- **Error Path Identification**: Traces the path of failed requests through the system
- **Service Relationship Mapping**: Understands dependencies between services

## Key Components

- **TempoTraceTool**: Retrieves and analyzes individual traces from Tempo
- **TempoServiceTool**: Analyzes service performance and health using Tempo data

## How It Works

1. The agent listens on the "tracing_agent" Redis channel for alerts from the Orchestrator
2. When an alert is received, the agent:
   - Extracts relevant context (service, timeframe)
   - Finds traces related to the incident timeframe
   - Analyzes detailed trace information for slow or failed services
   - Compares current service performance to established baselines
   - Identifies anomalies in service behavior
   - Sends the analysis back to the Orchestrator via the "orchestrator_response" channel
3. Additionally, it continuously monitors configured services to detect performance anomalies

## Configuration

The Tracing Agent can be configured with the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `TEMPO_URL` | URL of the Tempo tracing backend | `http://tempo:3100` |
| `SERVICES_TO_MONITOR` | Comma-separated list of services to monitor | None |
| `REDIS_HOST` | Redis host for message communication | `redis` |
| `REDIS_PORT` | Redis port for message communication | `6379` |
| `OPENAI_API_KEY` | OpenAI API key for trace analysis | None (required) |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4` |

## Customization

To modify the tracing analysis behavior:

1. Update the `find_related_traces()` method to adjust trace search parameters
2. Enhance the `analyze_trace()` method to detect additional trace patterns
3. Modify the service baseline logic in `build_service_baseline()` and `compare_to_baseline()`

## Local Development

```bash
# Run the Tracing Agent standalone
cd agents/tracing_agent
python main.py
```

## Docker

Build and run the Tracing Agent as a Docker container:

```bash
docker build -t tracing-agent -f agents/tracing_agent/Dockerfile .
docker run -e TEMPO_URL=http://tempo:3100 -e OPENAI_API_KEY=your_key tracing-agent
```

## API Endpoints

The Tracing Agent exposes a FastAPI interface with the following endpoints:

- `GET /health`: Health check endpoint
- `POST /traces/search`: Search for traces matching criteria
- `POST /traces/analyze`: Analyze a specific trace by ID
- `POST /services/baseline`: Build performance baseline for a service
- `POST /traces/related-to-alert`: Find traces related to an alert
- `GET /services/monitored`: List services being monitored

## Integration

The Tracing Agent is designed to work as part of the Observability Agent system. It:
- Receives alerts from the Orchestrator
- Publishes tracing analysis results back to the Orchestrator
- Provides insights into service interactions and dependencies
- Works alongside other specialized agents to provide comprehensive incident analysis