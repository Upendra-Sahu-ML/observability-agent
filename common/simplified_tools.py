"""
Simplified Tool Manager - Consolidates 50+ tools into 15 essential ones

This module provides a simplified interface to the most essential tools needed
for runbook execution while maintaining fallback capabilities.
"""

import logging
from typing import Dict, Any, List, Optional
from crewai.tools import tool

logger = logging.getLogger(__name__)

class SimplifiedToolManager:
    """
    Manages essential tools for runbook execution with intelligent fallbacks.
    Reduces complexity from 50+ tools to 15 core tools.
    """
    
    def __init__(self, observability_manager=None, deployment_tools=None, 
                 notification_tools=None, runbook_tools=None):
        self.observability_manager = observability_manager
        self.deployment_tools = deployment_tools
        self.notification_tools = notification_tools
        self.runbook_tools = runbook_tools
    
    # === OBSERVABILITY TOOLS (5 essential) ===
    
    @tool
    def get_service_metrics(self, service: str, namespace: str = "default") -> str:
        """
        Get essential metrics for a service with intelligent fallbacks.
        Returns CPU, memory, request rates, and error rates.
        """
        try:
            if self.observability_manager:
                metrics = self.observability_manager.get_metrics_or_fallback(service, namespace)
                return f"Metrics for {service}: {metrics}"
            else:
                return f"Observability manager not available. Use kubectl top pods -n {namespace}"
        except Exception as e:
            logger.error(f"Failed to get metrics for {service}: {e}")
            return f"Failed to get metrics. Try: kubectl top pods -n {namespace} -l app={service}"
    
    @tool
    def get_service_logs(self, service: str, namespace: str = "default", lines: int = 100) -> str:
        """
        Get recent logs for a service with intelligent fallbacks.
        Returns error patterns and performance issues.
        """
        try:
            if self.observability_manager:
                logs = self.observability_manager.get_logs_or_fallback(service, namespace, lines)
                return f"Logs for {service}: {logs}"
            else:
                return f"Observability manager not available. Use kubectl logs -n {namespace} -l app={service}"
        except Exception as e:
            logger.error(f"Failed to get logs for {service}: {e}")
            return f"Failed to get logs. Try: kubectl logs -n {namespace} -l app={service} --tail={lines}"
    
    @tool
    def get_service_health(self, service: str, namespace: str = "default") -> str:
        """
        Get overall service health including pod status, metrics, and recent errors.
        One-stop health check for runbook decision making.
        """
        try:
            if self.observability_manager:
                context = self.observability_manager.get_comprehensive_incident_context({
                    'labels': {'service': service, 'namespace': namespace}
                })
                return f"Health check for {service}: {context['incident_classification']}"
            else:
                return f"Health check not available. Use kubectl get pods -n {namespace} -l app={service}"
        except Exception as e:
            logger.error(f"Failed to get health for {service}: {e}")
            return f"Failed health check. Try: kubectl describe pods -n {namespace} -l app={service}"
    
    @tool
    def analyze_error_patterns(self, service: str, namespace: str = "default") -> str:
        """
        Analyze error patterns in logs to guide runbook selection.
        Returns error types, frequency, and suggested runbook categories.
        """
        try:
            if self.observability_manager:
                logs = self.observability_manager.get_logs_or_fallback(service, namespace, 200)
                error_analysis = {
                    "error_count": logs.get("error_count", 0),
                    "error_types": logs.get("recent_errors", [])[:5],
                    "suggested_runbooks": []
                }
                
                # Simple error pattern matching for runbook suggestions
                errors_text = str(logs.get("recent_errors", [])).lower()
                if "outofmemory" in errors_text or "memory" in errors_text:
                    error_analysis["suggested_runbooks"].append("memory_scaling")
                if "timeout" in errors_text or "connection" in errors_text:
                    error_analysis["suggested_runbooks"].append("connection_troubleshooting")
                if "database" in errors_text:
                    error_analysis["suggested_runbooks"].append("database_connection")
                
                return f"Error analysis for {service}: {error_analysis}"
            else:
                return f"Error analysis not available for {service}"
        except Exception as e:
            logger.error(f"Failed error analysis for {service}: {e}")
            return f"Error analysis failed for {service}: {e}"
    
    @tool
    def check_resource_usage(self, service: str, namespace: str = "default") -> str:
        """
        Check resource usage to determine if scaling runbooks are needed.
        Returns CPU/memory usage with scaling recommendations.
        """
        try:
            if self.observability_manager:
                metrics = self.observability_manager.get_metrics_or_fallback(service, namespace)
                recommendations = []
                
                cpu_usage = metrics.get("cpu_usage", 0)
                memory_usage = metrics.get("memory_usage", 0)
                
                if cpu_usage > 80:
                    recommendations.append("cpu_scaling_needed")
                if memory_usage > 85:
                    recommendations.append("memory_scaling_needed")
                if cpu_usage < 20 and memory_usage < 30:
                    recommendations.append("scale_down_possible")
                
                return f"Resource check for {service}: CPU={cpu_usage}%, Memory={memory_usage}%, Recommendations={recommendations}"
            else:
                return f"Resource check not available for {service}"
        except Exception as e:
            return f"Resource check failed for {service}: {e}"
    
    # === KUBERNETES TOOLS (5 essential) ===
    
    @tool
    def restart_service(self, service: str, namespace: str = "default") -> str:
        """
        Restart a service by rolling out the deployment.
        Common runbook action for resolving service issues.
        """
        try:
            if self.deployment_tools:
                result = self.deployment_tools.restart_deployment(service, namespace)
                return f"Restarted {service} in {namespace}: {result}"
            else:
                return f"Use: kubectl rollout restart deployment/{service} -n {namespace}"
        except Exception as e:
            return f"Failed to restart {service}: {e}"
    
    @tool
    def scale_service(self, service: str, replicas: int, namespace: str = "default") -> str:
        """
        Scale a service to the specified number of replicas.
        Common runbook action for performance issues.
        """
        try:
            if self.deployment_tools:
                result = self.deployment_tools.scale_deployment(service, replicas, namespace)
                return f"Scaled {service} to {replicas} replicas in {namespace}: {result}"
            else:
                return f"Use: kubectl scale deployment/{service} --replicas={replicas} -n {namespace}"
        except Exception as e:
            return f"Failed to scale {service}: {e}"
    
    @tool
    def get_pod_status(self, service: str, namespace: str = "default") -> str:
        """
        Get detailed pod status for troubleshooting.
        Essential for understanding deployment issues.
        """
        try:
            if self.deployment_tools:
                result = self.deployment_tools.get_pod_status(service, namespace)
                return f"Pod status for {service}: {result}"
            else:
                return f"Use: kubectl get pods -n {namespace} -l app={service} -o wide"
        except Exception as e:
            return f"Failed to get pod status for {service}: {e}"
    
    @tool
    def check_deployment_status(self, service: str, namespace: str = "default") -> str:
        """
        Check deployment rollout status and health.
        Critical for deployment-related runbooks.
        """
        try:
            if self.deployment_tools:
                result = self.deployment_tools.check_deployment_status(service, namespace)
                return f"Deployment status for {service}: {result}"
            else:
                return f"Use: kubectl rollout status deployment/{service} -n {namespace}"
        except Exception as e:
            return f"Failed to check deployment status for {service}: {e}"
    
    @tool
    def get_service_events(self, service: str, namespace: str = "default") -> str:
        """
        Get recent Kubernetes events for a service.
        Helpful for understanding what went wrong.
        """
        try:
            if self.deployment_tools:
                result = self.deployment_tools.get_service_events(service, namespace)
                return f"Events for {service}: {result}"
            else:
                return f"Use: kubectl get events -n {namespace} --field-selector involvedObject.name={service}"
        except Exception as e:
            return f"Failed to get events for {service}: {e}"
    
    # === RUNBOOK TOOLS (3 essential) ===
    
    @tool
    def search_runbooks(self, incident_type: str, service: str = "") -> str:
        """
        Search for relevant runbooks based on incident type and service.
        Core functionality for intelligent runbook selection.
        """
        try:
            if self.runbook_tools:
                results = self.runbook_tools.search_runbooks(incident_type, service)
                return f"Runbooks for {incident_type}: {results}"
            else:
                # Fallback to basic runbook suggestions
                basic_runbooks = {
                    "high_cpu": ["cpu_scaling", "performance_tuning"],
                    "high_memory": ["memory_scaling", "memory_leak_investigation"],
                    "errors": ["error_investigation", "log_analysis"],
                    "connection": ["connection_troubleshooting", "network_issues"],
                    "deployment": ["deployment_rollback", "deployment_fix"]
                }
                suggestions = basic_runbooks.get(incident_type.lower(), ["general_troubleshooting"])
                return f"Suggested runbooks for {incident_type}: {suggestions}"
        except Exception as e:
            return f"Failed to search runbooks for {incident_type}: {e}"
    
    @tool
    def execute_runbook_step(self, step_description: str, service: str, namespace: str = "default") -> str:
        """
        Execute a specific runbook step safely.
        Core runbook execution functionality.
        """
        try:
            if self.runbook_tools:
                result = self.runbook_tools.execute_step(step_description, service, namespace)
                return f"Executed step '{step_description}': {result}"
            else:
                return f"Manual execution required: {step_description} for {service} in {namespace}"
        except Exception as e:
            return f"Failed to execute step '{step_description}': {e}"
    
    @tool
    def validate_runbook_success(self, validation_criteria: str, service: str, namespace: str = "default") -> str:
        """
        Validate that a runbook execution was successful.
        Essential for automated runbook workflows.
        """
        try:
            # Basic validation using observability data
            health_check = self.get_service_health(service, namespace)
            metrics_check = self.get_service_metrics(service, namespace)
            
            return f"Validation for {service}: Health={health_check}, Metrics={metrics_check}"
        except Exception as e:
            return f"Failed to validate runbook success for {service}: {e}"
    
    # === NOTIFICATION TOOLS (2 essential) ===
    
    @tool
    def send_notification(self, message: str, severity: str = "medium", channels: List[str] = None) -> str:
        """
        Send notifications about runbook execution.
        Essential for keeping teams informed of automated actions.
        """
        try:
            if self.notification_tools:
                result = self.notification_tools.send_notification(message, severity, channels)
                return f"Notification sent: {result}"
            else:
                return f"Would send notification: {message} (severity: {severity})"
        except Exception as e:
            return f"Failed to send notification: {e}"
    
    @tool
    def create_incident_summary(self, incident_data: Dict[str, Any]) -> str:
        """
        Create a summary of the incident and actions taken.
        Essential for postmortem and learning.
        """
        try:
            summary = {
                "incident_id": incident_data.get("alert_id", "unknown"),
                "service": incident_data.get("labels", {}).get("service", "unknown"),
                "actions_taken": incident_data.get("actions_taken", []),
                "resolution_status": incident_data.get("resolution_status", "in_progress"),
                "timestamp": incident_data.get("timestamp", "unknown")
            }
            return f"Incident summary: {summary}"
        except Exception as e:
            return f"Failed to create incident summary: {e}"

    def get_essential_tools_list(self) -> List[str]:
        """
        Get list of all essential tools for agent configuration.
        Returns the 15 core tools that agents should have access to.
        """
        return [
            # Observability tools (5)
            "get_service_metrics",
            "get_service_logs", 
            "get_service_health",
            "analyze_error_patterns",
            "check_resource_usage",
            # Kubernetes tools (5)
            "restart_service",
            "scale_service",
            "get_pod_status",
            "check_deployment_status",
            "get_service_events",
            # Runbook tools (3)
            "search_runbooks",
            "execute_runbook_step", 
            "validate_runbook_success",
            # Notification tools (2)
            "send_notification",
            "create_incident_summary"
        ]

    def get_tools_for_agent(self, agent_type: str) -> List:
        """
        Get the appropriate subset of tools for different agent types.
        Reduces tool complexity per agent while maintaining functionality.
        """
        if agent_type == "observability":
            return [
                self.get_service_metrics,
                self.get_service_logs,
                self.get_service_health,
                self.analyze_error_patterns,
                self.check_resource_usage
            ]
        elif agent_type == "infrastructure":
            return [
                self.restart_service,
                self.scale_service,
                self.get_pod_status,
                self.check_deployment_status,
                self.get_service_events,
                self.search_runbooks,
                self.execute_runbook_step,
                self.validate_runbook_success
            ]
        elif agent_type == "communication":
            return [
                self.send_notification,
                self.create_incident_summary,
                self.get_service_health  # For status updates
            ]
        else:
            # Return all tools for unified agents
            return [
                self.get_service_metrics,
                self.get_service_logs,
                self.get_service_health,
                self.analyze_error_patterns,
                self.check_resource_usage,
                self.restart_service,
                self.scale_service,
                self.get_pod_status,
                self.check_deployment_status,
                self.get_service_events,
                self.search_runbooks,
                self.execute_runbook_step,
                self.validate_runbook_success,
                self.send_notification,
                self.create_incident_summary
            ]