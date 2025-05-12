import os

# Core configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

# Agent-specific configuration
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
LOKI_URL = os.getenv("LOKI_URL", "http://localhost:3100")
TEMPO_URL = os.getenv("TEMPO_URL", "http://localhost:3100")

# Knowledge base configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
POSTMORTEM_TEMPLATE_DIR = os.getenv("POSTMORTEM_TEMPLATE_DIR", "/app/templates")
RUNBOOK_DIR = os.getenv("RUNBOOK_DIR", "/app/runbooks")

# Deployment agent configuration
ARGOCD_SERVER = os.getenv("ARGOCD_SERVER")
ARGOCD_TOKEN = os.getenv("ARGOCD_TOKEN")
GIT_REPO_PATH = os.getenv("GIT_REPO_PATH")

# Orchestrator configuration
RESPONSE_TIMEOUT_SECONDS = os.getenv("RESPONSE_TIMEOUT_SECONDS", "300")

# Agent enable/disable configuration
# Default: all agents are enabled
ENABLED_AGENTS = {
    "metric": os.getenv("ENABLE_METRIC_AGENT", "true").lower() == "true",
    "log": os.getenv("ENABLE_LOG_AGENT", "true").lower() == "true", 
    "deployment": os.getenv("ENABLE_DEPLOYMENT_AGENT", "true").lower() == "true",
    "tracing": os.getenv("ENABLE_TRACING_AGENT", "true").lower() == "true",
    "root_cause": os.getenv("ENABLE_ROOT_CAUSE_AGENT", "true").lower() == "true",
    "runbook": os.getenv("ENABLE_RUNBOOK_AGENT", "true").lower() == "true",
    "notification": os.getenv("ENABLE_NOTIFICATION_AGENT", "true").lower() == "true",
    "postmortem": os.getenv("ENABLE_POSTMORTEM_AGENT", "true").lower() == "true"
}

def is_agent_enabled(agent_type):
    """Check if a specific agent type is enabled"""
    return ENABLED_AGENTS.get(agent_type, True)  # Default to enabled if not specified
