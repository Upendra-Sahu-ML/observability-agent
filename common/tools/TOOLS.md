# Observability Agent System Tools Documentation

This documentation describes the tools available in the `common/tools` directory and their integration with the Observability Agent System.

## Directory Structure
```
common/tools/
├── __init__.py
├── TOOLS.md                # This documentation
├── argocd_tools.py         # ArgoCD integration tools
├── base.py                 # Base classes and utilities
├── deployment_tools.py     # Deployment monitoring tools
├── git_tools.py            # Git repository tools
├── knowledge_tools.py      # Knowledge base and incident management tools
├── kube_tools.py           # Kubernetes integration tools
├── log_tools.py            # Log analysis tools
├── metric_tools.py         # Metric analysis tools
├── notification_tools.py   # Multi-channel notification tools
├── prometheus_tools.py     # Prometheus query utilities (used by metric_tools)
├── root_cause_tools.py     # Root cause analysis tools
├── runbook_tools.py        # Runbook management tools
└── tempo_tools.py          # Distributed tracing tools
```

## Core Tools Overview

### Root Cause Analysis Tools

#### 1. `root_cause_tools.py`
- **Purpose**: Analyze system components to identify the root cause of incidents
- **Key Functions**:
  - `correlation_analysis`: Analyzes correlations between system components and events
  - `dependency_analysis`: Analyzes service dependencies and their impact on the system
- **Usage in Agents**: Root Cause Agent
- **Example**:
  ```python
  from common.tools.root_cause_tools import correlation_analysis, dependency_analysis
  
  # Analyze correlations
  correlation_results = correlation_analysis(
      events=[...],
      time_window="1h",
      correlation_threshold=0.7
  )
  
  # Analyze dependencies
  dependency_results = dependency_analysis(
      services=["service-a", "service-b"],
      include_transitive=True
  )
  ```

### Notification Tools

#### 2. `notification_tools.py`
- **Purpose**: Send notifications through various channels
- **Key Classes**:
  - `NotificationTools`: Contains tools for Slack, PagerDuty, and Webex notifications
- **Key Methods**:
  - `send_slack_message`: Send notifications to Slack channels
  - `create_pagerduty_incident`: Create incidents in PagerDuty
  - `send_webex_message`: Send messages to Webex Teams
  - `send_multi_channel_notification`: Send to multiple channels at once
- **Usage in Agents**: Notification Agent
- **Example**:
  ```python
  from common.tools.notification_tools import NotificationTools
  
  notification_tools = NotificationTools()
  
  # Send a Slack message
  notification_tools.send_slack_message(
      message="Critical system alert!",
      channel="#incidents"
  )
  
  # Create a PagerDuty incident
  notification_tools.create_pagerduty_incident(
      title="Database failure",
      description="Primary database is not responding",
      severity="critical"
  )
  ```

### Knowledge Management Tools

#### 3. `knowledge_tools.py`
- **Purpose**: Manage knowledge base, postmortems, and runbooks
- **Key Classes**:
  - `KnowledgeBaseTool`: Manages incident data in vector database
  - `PostmortemTemplateTool`: Handles postmortem template operations
  - `PostmortemGeneratorTool`: Generates comprehensive postmortem documents
  - `RunbookUpdateTool`: Manages runbook updates
- **Key Methods**:
  - `store_incident`: Store incident data in knowledge base
  - `retrieve_incident`: Retrieve incident data by ID
  - `search_incidents`: Search for similar incidents
  - `get_template`: Get a postmortem template
  - `fill_template`: Fill a template with incident data
  - `generate_postmortem`: Generate a complete postmortem document
  - `update_runbook`: Update existing runbook
  - `create_runbook`: Create a new runbook
- **Usage in Agents**: Postmortem Agent, Runbook Agent
- **Example**:
  ```python
  from common.tools.knowledge_tools import PostmortemGeneratorTool
  
  generator = PostmortemGeneratorTool()
  
  # Generate a postmortem
  postmortem = generator.generate_postmortem(
      incident_data={"alert_id": "alert-123", "service": "api", "severity": "high"},
      root_cause="Database connection pool exhaustion",
      impact="API latency increased by 300%",
      resolution="Increased connection pool size and implemented circuit breaker"
  )
  ```

### Metric Analysis Tools

#### 4. `metric_tools.py` and `prometheus_tools.py`
- **Purpose**: Query and analyze system metrics
- **Key Classes**:
  - `PrometheusQueryTool`: High-level interface for Prometheus queries
  - `MetricAnalysisTool`: Analyze metric data to identify trends and anomalies
  - `PrometheusTools`: Low-level Prometheus API client (used by PrometheusQueryTool)
- **Key Methods**:
  - `query_metrics`: Execute a PromQL query
  - `get_cpu_metrics`: Get CPU utilization metrics
  - `get_memory_metrics`: Get memory usage metrics
  - `get_error_rate`: Get error rate metrics
  - `get_service_health`: Get overall service health metrics
  - `analyze_trend`: Analyze metric trends
  - `analyze_anomalies`: Detect anomalies in metrics
  - `analyze_threshold`: Analyze metrics against thresholds
- **Usage in Agents**: Metric Agent
- **Example**:
  ```python
  from common.tools.metric_tools import PrometheusQueryTool, MetricAnalysisTool
  
  query_tool = PrometheusQueryTool()
  analysis_tool = MetricAnalysisTool()
  
  # Query CPU metrics
  cpu_metrics = query_tool.get_cpu_metrics(
      service="payment-service",
      duration="1h"
  )
  
  # Analyze for anomalies
  anomalies = analysis_tool.analyze_anomalies(metrics=cpu_metrics)
  ```

### Log Analysis Tools

#### 5. `log_tools.py`
- **Purpose**: Analyze logs to identify patterns and anomalies
- **Key Classes/Functions**: Various log analysis tools
- **Usage in Agents**: Log Agent
- **Example**:
  ```python
  from common.tools.log_tools import ElasticsearchLogTool
  
  log_tool = ElasticsearchLogTool()
  
  # Search logs
  logs = log_tool.search_logs(
      query="error",
      service="authentication-service",
      time_range="30m"
  )
  
  # Analyze log patterns
  patterns = log_tool.analyze_patterns(logs)
  ```

### Deployment Analysis Tools

#### 6. `deployment_tools.py`, `argocd_tools.py`, `kube_tools.py`
- **Purpose**: Monitor and analyze deployments
- **Key Functionality**: 
  - Kubernetes resource monitoring
  - ArgoCD deployment tracking
  - Deployment health analysis
- **Usage in Agents**: Deployment Agent
- **Example**:
  ```python
  from common.tools.kube_tools import KubernetesAPITool
  
  kube_tool = KubernetesAPITool()
  
  # Get deployment status
  deployment = kube_tool.get_deployment(
      name="web-frontend",
      namespace="production"
  )
  
  # Check recent changes
  changes = kube_tool.get_recent_changes(
      namespace="production",
      time_window="1h"
  )
  ```

### Tracing Analysis Tools

#### 7. `tempo_tools.py`
- **Purpose**: Analyze distributed traces
- **Key Functionality**: Tempo/Jaeger trace analysis
- **Usage in Agents**: Tracing Agent
- **Example**:
  ```python
  from common.tools.tempo_tools import TempoTracingTool
  
  tracing_tool = TempoTracingTool()
  
  # Search traces
  traces = tracing_tool.search_traces(
      service="payment-service",
      operation="processPayment",
      time_range="15m"
  )
  
  # Analyze latency
  latency_analysis = tracing_tool.analyze_latency(traces)
  ```

## Tool Integration with CrewAI

All tools in the Observability Agent System use the CrewAI tool decorator pattern, which allows them to be directly used by CrewAI agents:

```python
from crewai import Agent
from crewai.tools import tool
from common.tools.notification_tools import NotificationTools

# Initialize tools
notification_tools = NotificationTools()

# Create an agent that uses the tools
agent = Agent(
    role="Notification Manager",
    goal="Send appropriate notifications for incidents",
    tools=[
        notification_tools.send_slack_message,
        notification_tools.create_pagerduty_incident,
        notification_tools.send_webex_message,
        notification_tools.send_multi_channel_notification
    ]
)
```

## Communication with NATS

The tools themselves don't directly communicate with NATS. Instead, the agents use NATS for inter-agent communication while leveraging the tools for specific tasks. This separation of concerns allows tools to be focused on their specific functionality while the messaging infrastructure is handled at the agent level.

## Future Tool Enhancements

Upcoming tool improvements include:
- Enhanced correlation analysis with ML capabilities
- Extended metric anomaly detection algorithms
- Automated runbook generation based on incidents
- Integration with more notification channels
- Advanced log analysis with NLP techniques