# Observability Tools Documentation

This document provides comprehensive documentation for the observability tools available in the system.

## Table of Contents
1. [Log Tools](#log-tools)
2. [Prometheus Tools](#prometheus-tools)
3. [Tempo Tools](#tempo-tools)

## Log Tools

### LokiQueryTool

The `LokiQueryTool` provides advanced log querying and analysis capabilities using LogQL.

#### Basic Query
```python
tool = LokiQueryTool()
results = tool.execute(
    query='{namespace="default", service="myapp"} |~ "error"',
    start="2024-03-20T00:00:00Z",
    end="2024-03-20T01:00:00Z",
    limit=100
)
```

#### Error Pattern Analysis
```python
patterns = tool.get_error_patterns(
    namespace="default",
    service="myapp",
    start="2024-03-20T00:00:00Z",
    end="2024-03-20T01:00:00Z"
)
```
Returns a dictionary of error patterns and their frequencies, categorized by error type.

#### Service Latency Analysis
```python
latency = tool.get_service_latency(
    namespace="default",
    service="myapp",
    start="2024-03-20T00:00:00Z",
    end="2024-03-20T01:00:00Z"
)
```
Returns latency statistics including:
- Count of requests
- Minimum latency
- Maximum latency
- Average latency
- 95th percentile
- 99th percentile

#### Service Error Analysis
```python
errors = tool.get_service_errors(
    namespace="default",
    service="myapp",
    start="2024-03-20T00:00:00Z",
    end="2024-03-20T01:00:00Z"
)
```
Returns comprehensive error statistics including:
- Total request count
- Error count
- Error rate
- Error patterns

## Prometheus Tools

### PrometheusQueryTool

The `PrometheusQueryTool` provides advanced metric querying and analysis capabilities using PromQL.

#### Basic Query
```python
tool = PrometheusQueryTool()
results = tool.execute(
    query='rate(http_requests_total[5m])',
    time="2024-03-20T00:00:00Z"
)
```

#### Service Health Analysis
```python
health = tool.get_service_health(
    service="myapp",
    namespace="default"
)
```
Returns service health metrics including:
- Request rate
- Error rate
- Error rate percentage
- P95 latency

#### Resource Usage Analysis
```python
usage = tool.get_resource_usage(
    pod="myapp-pod",
    namespace="default"
)
```
Returns resource usage metrics including:
- CPU usage
- Memory usage
- Memory usage percentage
- Memory limits

#### Service Dependency Analysis
```python
dependencies = tool.get_service_dependencies(
    service="myapp",
    namespace="default"
)
```
Returns service dependency metrics including:
- Upstream service calls
- Downstream service calls
- Call rates
- Error rates

## Tempo Tools

### TempoTraceTool

The `TempoTraceTool` provides advanced distributed tracing analysis capabilities.

#### Basic Trace Query
```python
tool = TempoTraceTool()
traces = tool.execute(
    service="myapp",
    operation="GET /api/users",
    start="2024-03-20T00:00:00Z",
    end="2024-03-20T01:00:00Z",
    limit=100
)
```

#### Trace Detail Analysis
```python
trace_details = tool.get_trace_by_id("trace-id-123")
```
Returns detailed trace information including:
- Span count
- Services involved
- Operations performed
- Duration
- Span tree structure
- Potential issues

#### Service Latency Analysis
```python
latency = tool.get_service_latency_analysis(
    service="myapp",
    start="2024-03-20T00:00:00Z",
    end="2024-03-20T01:00:00Z"
)
```
Returns comprehensive latency analysis including:
- Overall statistics
- Operation-specific statistics
- Error counts and rates
- P95 and P99 latencies

#### Service Dependency Analysis
```python
dependencies = tool.get_service_dependencies(
    service="myapp",
    start="2024-03-20T00:00:00Z",
    end="2024-03-20T01:00:00Z"
)
```
Returns service dependency analysis including:
- Upstream dependencies
- Downstream dependencies
- Call counts
- Error rates
- Average latencies

#### Error Analysis
```python
errors = tool.get_error_analysis(
    service="myapp",
    start="2024-03-20T00:00:00Z",
    end="2024-03-20T01:00:00Z"
)
```
Returns comprehensive error analysis including:
- Total traces
- Error traces
- Error operations
- Error causes
- Error services
- Error rates

### TempoServiceTool

The `TempoServiceTool` provides high-level service performance analysis.

#### Service Performance Analysis
```python
tool = TempoServiceTool()
performance = tool.execute(
    service="myapp",
    start="2024-03-20T00:00:00Z",
    end="2024-03-20T01:00:00Z"
)
```
Returns service performance analysis including:
- Trace count
- Operation statistics
- Error count
- Duration statistics
- Performance issues
- Slow operations

## Best Practices

1. **Time Ranges**
   - Always specify appropriate time ranges for queries
   - Use ISO 8601 format for timestamps
   - Consider timezone implications

2. **Query Limits**
   - Set reasonable limits to avoid overwhelming the system
   - Default limits are provided but can be adjusted based on needs

3. **Error Handling**
   - Always handle potential errors in tool responses
   - Check for error fields in response dictionaries
   - Implement appropriate retry logic for transient failures

4. **Performance Considerations**
   - Cache frequently used queries
   - Use appropriate time ranges to limit data volume
   - Consider using range queries for historical analysis

5. **Integration**
   - Tools can be used together for comprehensive analysis
   - Correlate logs, metrics, and traces for better insights
   - Use error patterns to identify root causes

## Examples

### Comprehensive Service Analysis
```python
# Initialize tools
loki = LokiQueryTool()
prometheus = PrometheusQueryTool()
tempo = TempoTraceTool()

# Get service health
health = prometheus.get_service_health("myapp", "default")

# Get error patterns
errors = loki.get_error_patterns("default", "myapp")

# Get trace analysis
traces = tempo.get_service_latency_analysis("myapp")

# Correlate findings
analysis = {
    "health": health,
    "errors": errors,
    "traces": traces
}
```

### Error Investigation
```python
# Get error details from logs
error_patterns = loki.get_error_patterns("default", "myapp")

# Get related traces
error_traces = tempo.get_error_analysis("myapp")

# Get service metrics
service_health = prometheus.get_service_health("myapp", "default")

# Correlate error information
error_analysis = {
    "patterns": error_patterns,
    "traces": error_traces,
    "health": service_health
}
``` 