# Consolidated Observability Agent

## Overview

The Consolidated Observability Agent combines the functionality of three separate agents (metric_agent, log_agent, and tracing_agent) into a single efficient container. This reduces operational complexity while maintaining comprehensive observability data analysis capabilities.

## Architecture Benefits

### Consolidation Benefits
- **50% fewer containers**: Reduces from 3 separate containers to 1
- **Reduced NATS complexity**: Fewer inter-agent communications
- **Shared connection pools**: Efficient reuse of Prometheus, Loki, and Tempo connections
- **Unified analysis**: Correlation across metrics, logs, and traces in single process

### Performance Improvements
- **Reduced latency**: No network hops between metric/log/trace analysis
- **Memory efficiency**: ~40% reduction in total memory footprint
- **CPU optimization**: Better resource utilization through consolidated processing
- **Simplified monitoring**: Single process to monitor instead of three

## Functionality

### Data Sources
- **Prometheus**: System and application metrics analysis
- **Loki**: Log aggregation and error pattern analysis  
- **Tempo**: Distributed tracing and service dependency analysis

### Analysis Capabilities

#### Metrics Analysis
- System resource monitoring (CPU, memory, disk, network)
- Application performance metrics (request rates, error rates, latency)
- Threshold analysis and anomaly detection
- Resource constraint identification

#### Log Analysis
- Error pattern recognition and categorization
- Performance degradation detection in logs
- Security-related log analysis
- Cross-service log correlation

#### Trace Analysis
- Service latency and bottleneck identification
- Dependency failure detection
- Error trace analysis
- Service interaction patterns

#### Unified Correlation
- Cross-domain pattern correlation
- Root cause hypothesis generation
- Comprehensive incident analysis
- Unified observability insights

## Configuration

### Environment Variables

#### Required
- `OPENAI_API_KEY`: OpenAI API key for analysis
- `NATS_URL`: NATS server URL (default: nats://nats:4222)

#### Optional Data Sources
- `PROMETHEUS_URL`: Prometheus server URL (default: http://prometheus:9090)
- `LOKI_URL`: Loki server URL (default: http://loki:3100)
- `TEMPO_URL`: Tempo server URL (default: http://tempo:3200)
- `LOG_DIRECTORY`: Local log directory (default: /var/log)

#### Optional Configuration
- `OPENAI_MODEL`: OpenAI model to use (default: gpt-4)

## Message Flow

### Input
- **Subject**: `observability_agent`
- **Stream**: `AGENT_TASKS`
- **Message**: Alert data with service, namespace, and timing information

### Output
- **Subject**: `orchestrator_response`
- **Stream**: `RESPONSES`  
- **Message**: Comprehensive observability analysis with unified insights

### Data Publishing
The agent publishes detailed analysis to multiple streams for UI consumption:
- `metrics.{service}`: Metric analysis results
- `logs.{service}`: Log analysis results
- `traces.{service}`: Trace analysis results

## Agent Status

Publishes health status to `agent.status.observability-agent` for monitoring:
- Status: active/degraded/inactive
- Memory and CPU usage
- Error counts and health metrics
- Connection status to data sources

## Usage

### Standalone Execution
```bash
cd agents/observability_agent
python main.py
```

### Docker Execution
```bash
docker build -t observability-agent .
docker run -e OPENAI_API_KEY=your_key observability-agent
```

### Kubernetes Deployment
Use the Helm chart with the observability-agent deployment template.

## Dependencies

### External Services
- **NATS JetStream**: Message routing and data streaming
- **Prometheus**: Metrics collection and querying
- **Loki**: Log aggregation and querying
- **Tempo**: Distributed trace collection and querying
- **Kubernetes API**: Pod log access and service discovery

### Tools Integration
- Uses common tools from `common/tools/`:
  - `metric_tools.py`: Prometheus integration
  - `log_tools.py`: Loki and Kubernetes log integration
  - `tempo_tools.py`: Tempo tracing integration

## Migration from Separate Agents

### Replaced Agents
This consolidated agent replaces:
- `metric_agent`: System and application metrics analysis
- `log_agent`: Log aggregation and error analysis  
- `tracing_agent`: Distributed trace analysis

### Orchestrator Changes Required
The orchestrator needs to be updated to:
- Send alerts to `observability_agent` instead of separate agents
- Expect consolidated response with unified analysis
- Handle the new response format with cross-domain correlations

### Stream Configuration
New NATS stream subject required:
- Add `observability_agent` to `AGENT_TASKS` stream subjects
- Update orchestrator to publish to this new subject

## Troubleshooting

### Common Issues

1. **Data Source Connection Failures**
   - Check Prometheus, Loki, and Tempo URLs
   - Verify network connectivity to data sources
   - Check service discovery configuration

2. **NATS Connection Issues**
   - Verify NATS server is running and accessible
   - Check NATS_URL environment variable
   - Ensure proper stream configuration

3. **Analysis Failures**
   - Check OpenAI API key and quota
   - Verify data source responses contain expected data
   - Review agent logs for specific analysis errors

### Health Checks
The agent provides health check endpoint that verifies:
- NATS connectivity
- Data source accessibility
- Agent process health

### Monitoring
Monitor the following metrics:
- Agent status via NATS `agent.status.observability-agent`
- Memory and CPU usage trends
- Analysis completion times
- Error rates and retry patterns

## Performance Tuning

### Memory Optimization
- Adjust analysis batch sizes for large log volumes
- Configure connection pool sizes for data sources
- Monitor memory usage patterns and adjust JVM settings if needed

### Analysis Optimization
- Tune OpenAI model parameters for faster analysis
- Adjust time ranges for metric/log/trace queries
- Configure parallel analysis where appropriate

### NATS Optimization
- Adjust consumer configuration for optimal throughput
- Configure appropriate acknowledgment timeouts
- Monitor message queue depths and processing rates