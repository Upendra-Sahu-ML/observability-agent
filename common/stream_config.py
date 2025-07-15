"""
NATS Stream Configuration
Centralized configuration for all NATS streams used by the observability agent.
This ensures consistency across all components.
"""

# Stream configurations matching Helm NATS ConfigMap
STREAM_CONFIGS = {
    "ALERTS": {
        "name": "ALERTS",
        "subjects": ["alerts", "alerts.>"],
        "description": "Alert data from external monitoring systems"
    },
    "AGENT_TASKS": {
        "name": "AGENT_TASKS", 
        "subjects": [
            "observability_agent",  # Consolidated agent for metrics, logs, and traces
            "infrastructure_agent",  # Consolidated agent for deployment and runbooks
            "communication_agent",  # Consolidated agent for notifications and postmortems
            "root_cause_agent",
            # Legacy fallback subjects for backward compatibility (if needed)
            "metric_agent", "log_agent", "deployment_agent", "tracing_agent",
            "notification_agent", "postmortem_agent", "runbook_agent",
            "agent.tasks.>"
        ],
        "description": "Task distribution from orchestrator to agents"
    },
    "AGENTS": {
        "name": "AGENTS",
        "subjects": ["agent.status.>"],
        "description": "Agent status and health updates"
    },
    "RESPONSES": {
        "name": "RESPONSES",
        "subjects": ["orchestrator_response", "responses.>"],
        "description": "Agent responses back to orchestrator"
    },
    "ALERT_DATA": {
        "name": "ALERT_DATA",
        "subjects": ["alert_data_request", "alert_data_response.*", "alert.data.>"],
        "description": "Alert data requests and responses"
    },
    "ROOT_CAUSE": {
        "name": "ROOT_CAUSE",
        "subjects": ["root_cause_analysis", "root_cause_result", "rootcause.>"],
        "description": "Root cause analysis data"
    },
    "NOTIFICATIONS": {
        "name": "NOTIFICATIONS",
        "subjects": ["notification_requests", "notifications.>"],
        "description": "Notification requests and status"
    },
    "METRICS": {
        "name": "METRICS",
        "subjects": ["metrics", "metrics.>"],
        "description": "Performance metrics data"
    },
    "LOGS": {
        "name": "LOGS",
        "subjects": ["logs", "logs.>"],
        "description": "Application logs"
    },
    "DEPLOYMENTS": {
        "name": "DEPLOYMENTS",
        "subjects": ["deployments", "deployments.>"],
        "description": "Deployment events and status"
    },
    "TRACES": {
        "name": "TRACES",
        "subjects": ["traces", "traces.>"],
        "description": "Distributed tracing data"
    },
    "POSTMORTEMS": {
        "name": "POSTMORTEMS",
        "subjects": ["postmortems", "postmortems.>"],
        "description": "Incident postmortem reports"
    },
    "RUNBOOKS": {
        "name": "RUNBOOKS",
        "subjects": ["runbooks", "runbooks.>", "runbook.definition.>"],
        "description": "Operational runbooks"
    },
    "RUNBOOK_EXECUTIONS": {
        "name": "RUNBOOK_EXECUTIONS",
        "subjects": ["runbook.execute", "runbook.status.>", "runbook.execution.>"],
        "description": "Runbook execution results"
    },
    "NOTEBOOKS": {
        "name": "NOTEBOOKS",
        "subjects": ["notebooks", "notebooks.>"],
        "description": "Notebook data for analysis"
    }
}

# Subject patterns for publishing (maps to stream subjects)
PUBLISH_SUBJECTS = {
    # Agent task distribution
    "observability_agent": "observability_agent",  # Consolidated agent
    "infrastructure_agent": "infrastructure_agent",  # Consolidated agent
    "communication_agent": "communication_agent",  # Consolidated agent
    "metric_agent": "metric_agent",
    "log_agent": "log_agent", 
    "deployment_agent": "deployment_agent",
    "tracing_agent": "tracing_agent",
    "root_cause_agent": "root_cause_agent",
    "notification_agent": "notification_agent",
    "postmortem_agent": "postmortem_agent",
    "runbook_agent": "runbook_agent",
    
    # Agent responses
    "orchestrator_response": "orchestrator_response",
    
    # Alert data
    "alerts": "alerts",
    "alert_data_request": "alert_data_request",
    "alert_data_response": "alert_data_response",  # Use with ID suffix
    
    # Root cause analysis
    "root_cause_analysis": "root_cause_analysis",
    "root_cause_result": "root_cause_result",
    "rootcause": "rootcause",  # Use with service suffix
    
    # Data streams
    "metrics": "metrics",  # Use with service suffix
    "logs": "logs",  # Use with service suffix
    "deployments": "deployments",  # Use with service suffix
    "traces": "traces",  # Use with service suffix
    "postmortems": "postmortems",  # Use with ID suffix
    "runbooks": "runbooks",  # Use with ID suffix
    "runbook_definition": "runbook.definition",  # Use with ID suffix
    "runbook_execute": "runbook.execute",
    "runbook_status": "runbook.status",  # Use with ID suffix
    "runbook_execution": "runbook.execution",  # Use with ID suffix
    "notifications": "notifications",  # Use with ID suffix
    "notification_requests": "notification_requests",
    "notebooks": "notebooks",  # Use with ID suffix
    
    # Agent status
    "agent_status": "agent.status"  # Use with agent_id suffix
}

# Consumer patterns for subscribing (maps to stream subjects)
SUBSCRIBE_SUBJECTS = {
    # For UI backend consumption
    "metrics_all": "metrics.>",
    "logs_all": "logs.>",
    "deployments_all": "deployments.>",
    "traces_all": "traces.>",
    "postmortems_all": "postmortems.>",
    "runbooks_all": "runbook.definition.>",
    "runbook_executions_all": "runbook.execution.>",
    "notifications_all": "notifications.>",
    "alerts_all": "alerts.>",
    "agent_status_all": "agent.status.>",
    "rootcause_all": "rootcause.>",
    "notebooks_all": "notebooks.>",
    
    # For agent consumption
    "observability_agent_tasks": "observability_agent",  # Consolidated agent
    "infrastructure_agent_tasks": "infrastructure_agent",  # Consolidated agent
    "communication_agent_tasks": "communication_agent",  # Consolidated agent
    "metric_agent_tasks": "metric_agent",
    "log_agent_tasks": "log_agent",
    "deployment_agent_tasks": "deployment_agent",
    "tracing_agent_tasks": "tracing_agent",
    "root_cause_agent_tasks": "root_cause_agent",
    "notification_agent_tasks": "notification_agent",
    "postmortem_agent_tasks": "postmortem_agent",
    "runbook_agent_tasks": "runbook_agent",
    
    # For orchestrator consumption
    "orchestrator_responses": "orchestrator_response",
    "root_cause_results": "root_cause_result",
    "alert_data_requests": "alert_data_request",
    "alerts": "alerts"
}

def get_stream_config(stream_name):
    """Get configuration for a specific stream"""
    return STREAM_CONFIGS.get(stream_name)

def get_all_stream_configs():
    """Get all stream configurations"""
    return STREAM_CONFIGS

def get_publish_subject(subject_key):
    """Get subject pattern for publishing"""
    return PUBLISH_SUBJECTS.get(subject_key)

def get_subscribe_subject(subject_key):
    """Get subject pattern for subscribing"""
    return SUBSCRIBE_SUBJECTS.get(subject_key)

def get_stream_for_subject(subject):
    """Find which stream contains a given subject"""
    for stream_name, config in STREAM_CONFIGS.items():
        if subject in config["subjects"]:
            return stream_name
    return None