"""
Azure Monitor Tools for Observability Agent
Provides integration with Azure Monitor, Application Insights, and Log Analytics
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from crewai.tools import tool
import time

logger = logging.getLogger(__name__)

class AzureMonitorTools:
    """Tools for interacting with Azure Monitor services"""
    
    def __init__(self, 
                 subscription_id: str = None,
                 resource_group: str = None,
                 workspace_id: str = None,
                 app_insights_id: str = None):
        self.subscription_id = subscription_id or os.environ.get("AZURE_SUBSCRIPTION_ID")
        self.resource_group = resource_group or os.environ.get("AZURE_RESOURCE_GROUP")
        self.workspace_id = workspace_id or os.environ.get("AZURE_LOG_ANALYTICS_WORKSPACE_ID")
        self.app_insights_id = app_insights_id or os.environ.get("AZURE_APPLICATION_INSIGHTS_ID")
        
        # Check if we have required components
        self.has_workspace = bool(self.workspace_id)
        self.has_app_insights = bool(self.app_insights_id)
        
        if not self.has_workspace:
            logger.warning("Azure Log Analytics workspace not configured. Some features will be limited.")
        
        if not self.has_app_insights:
            logger.info("Application Insights not configured (optional). Will use Log Analytics for container logs and Kubernetes metrics.")
        
        # Azure authentication
        self.access_token = self._get_access_token()
        
        # Base URLs for Azure Monitor APIs
        self.monitor_base_url = "https://management.azure.com"
        if self.has_workspace:
            self.logs_base_url = f"https://api.loganalytics.io/v1/workspaces/{self.workspace_id}"
        if self.has_app_insights:
            self.app_insights_base_url = f"https://api.applicationinsights.io/v1/apps/{self.app_insights_id}"
    
    def _get_access_token(self) -> str:
        """Get Azure access token using Azure CLI or managed identity"""
        try:
            # Try to get token from Azure CLI
            import subprocess
            result = subprocess.run([
                "az", "account", "get-access-token", 
                "--resource", "https://management.azure.com/",
                "--query", "accessToken", 
                "--output", "tsv"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.warning("Azure CLI token failed, trying managed identity")
                return self._get_managed_identity_token()
                
        except Exception as e:
            logger.error(f"Failed to get Azure access token: {e}")
            return ""
    
    def _get_managed_identity_token(self) -> str:
        """Get access token using Azure managed identity"""
        try:
            # Azure Instance Metadata Service endpoint
            url = "http://169.254.169.254/metadata/identity/oauth2/token"
            params = {
                "api-version": "2018-02-01",
                "resource": "https://management.azure.com/"
            }
            headers = {"Metadata": "true"}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json().get("access_token", "")
            else:
                logger.error(f"Managed identity token failed: {response.status_code}")
                return ""
                
        except Exception as e:
            logger.error(f"Failed to get managed identity token: {e}")
            return ""
    
    def _make_request(self, url: str, params: Dict = None) -> Optional[Dict]:
        """Make authenticated request to Azure Monitor API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                # Token expired, try to refresh
                self.access_token = self._get_access_token()
                headers["Authorization"] = f"Bearer {self.access_token}"
                response = requests.get(url, headers=headers, params=params, timeout=30)
                if response.status_code == 200:
                    return response.json()
            
            logger.error(f"Azure Monitor API error: {response.status_code} - {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Azure Monitor request failed: {e}")
            return None
    
    @tool
    def get_petclinic_jvm_metrics(self, time_range: str = "PT1H") -> str:
        """
        Get JVM metrics for PetClinic application from Azure Monitor.
        Uses Application Insights if available, otherwise falls back to container logs analysis.
        """
        try:
            if self.has_app_insights:
                # Use Application Insights for JVM metrics (requires code instrumentation)
                query = f"""
                customMetrics
                | where timestamp >= ago({time_range})
                | where name in ("jvm.memory.used", "jvm.memory.max", "jvm.gc.pause", 
                               "jvm.threads.live", "jvm.classes.loaded", "process.cpu.usage")
                | where customDimensions.application == "petclinic"
                | summarize 
                    avg_value = avg(todouble(value)) by name, bin(timestamp, 5m)
                | order by timestamp desc
                | take 100
                """
                
                url = f"{self.app_insights_base_url}/query"
                params = {"query": query}
                
                result = self._make_request(url, params)
                if result and "tables" in result:
                    return f"Application Insights JVM metrics: {result['tables'][0]['rows']}"
            
            # Fallback to Log Analytics for container resource metrics
            if self.has_workspace:
                query = f"""
                Perf
                | where TimeGenerated >= ago({time_range})
                | where ObjectName == "K8SContainer"
                | where InstanceName contains "petclinic"
                | where CounterName in ("cpuUsageNanoCores", "memoryWorkingSetBytes")
                | summarize 
                    avg_cpu = avg(CounterValue) by bin(TimeGenerated, 5m)
                | order by TimeGenerated desc
                | take 20
                """
                
                url = f"{self.logs_base_url}/query"
                params = {"query": query}
                
                result = self._make_request(url, params)
                if result and "tables" in result:
                    return f"Container metrics from Log Analytics: {result['tables'][0]['rows']}"
            
            return "JVM metrics not available. Application Insights not configured and no container metrics found. Consider enabling Application Insights for detailed JVM metrics."
                
        except Exception as e:
            logger.error(f"Failed to get JVM metrics: {e}")
            return f"Error retrieving JVM metrics: {e}"
    
    @tool
    def get_postgresql_metrics(self, time_range: str = "PT1H") -> str:
        """
        Get PostgreSQL database metrics from Azure Monitor.
        Uses Application Insights if available, otherwise falls back to container logs.
        """
        try:
            if self.has_app_insights:
                # Use Application Insights for detailed PostgreSQL metrics
                query = f"""
                customMetrics
                | where timestamp >= ago({time_range})
                | where name in ("postgresql.connections.active", "postgresql.connections.max", 
                               "postgresql.database.size", "postgresql.locks", 
                               "postgresql.slow_queries", "postgresql.commits", "postgresql.rollbacks")
                | where customDimensions.database == "petclinic"
                | summarize 
                    avg_value = avg(todouble(value)),
                    max_value = max(todouble(value))
                    by name, bin(timestamp, 5m)
                | order by timestamp desc
                | take 100
                """
                
                url = f"{self.app_insights_base_url}/query"
                params = {"query": query}
                
                result = self._make_request(url, params)
                if result and "tables" in result:
                    return f"PostgreSQL metrics from Application Insights: {result['tables'][0]['rows']}"
            
            # Fallback to Log Analytics for container metrics
            if self.has_workspace:
                query = f"""
                ContainerLog
                | where TimeGenerated >= ago({time_range})
                | where ContainerName contains "postgresql"
                | where LogEntry contains "connections" or LogEntry contains "database"
                | summarize count() by bin(TimeGenerated, 5m)
                | order by TimeGenerated desc
                | take 20
                """
                
                url = f"{self.logs_base_url}/query"
                params = {"query": query}
                
                result = self._make_request(url, params)
                if result and "tables" in result:
                    return f"PostgreSQL container logs analysis: {result['tables'][0]['rows']}"
            
            return "PostgreSQL metrics not available. Consider enabling Application Insights for detailed database metrics or check Log Analytics workspace configuration."
                
        except Exception as e:
            logger.error(f"Failed to get PostgreSQL metrics: {e}")
            return f"Error retrieving PostgreSQL metrics: {e}"
    
    @tool
    def get_petclinic_application_logs(self, time_range: str = "PT1H", severity: str = "Error") -> str:
        """
        Get application logs for PetClinic from Azure Log Analytics.
        Focuses on Spring Boot application logs and error patterns.
        """
        try:
            # KQL query for application logs
            query = f"""
            ContainerLog
            | where TimeGenerated >= ago({time_range})
            | where ContainerName contains "petclinic"
            | where LogEntry contains "{severity}" or LogLevel == "{severity}"
            | extend ParsedLog = parse_json(LogEntry)
            | project 
                TimeGenerated,
                ContainerName,
                LogLevel = coalesce(ParsedLog.level, LogLevel),
                Message = coalesce(ParsedLog.message, LogEntry),
                Logger = ParsedLog.logger,
                Thread = ParsedLog.thread,
                Exception = ParsedLog.exception
            | order by TimeGenerated desc
            | take 50
            """
            
            url = f"{self.logs_base_url}/query"
            params = {"query": query}
            
            result = self._make_request(url, params)
            if result and "tables" in result:
                logs = result["tables"][0]["rows"]
                
                log_data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "application": "petclinic",
                    "query_range": time_range,
                    "log_count": len(logs),
                    "logs": []
                }
                
                for row in logs:
                    log_entry = {
                        "timestamp": row[0],
                        "container": row[1],
                        "level": row[2],
                        "message": row[3],
                        "logger": row[4] if len(row) > 4 else None,
                        "thread": row[5] if len(row) > 5 else None,
                        "exception": row[6] if len(row) > 6 else None
                    }
                    log_data["logs"].append(log_entry)
                
                return f"PetClinic Application Logs: {json.dumps(log_data, indent=2)}"
            else:
                return f"No {severity} logs found for PetClinic application"
                
        except Exception as e:
            logger.error(f"Failed to get application logs: {e}")
            return f"Error retrieving application logs: {e}"
    
    @tool
    def get_petclinic_performance_metrics(self, time_range: str = "PT1H") -> str:
        """
        Get performance metrics for PetClinic application including response times,
        request rates, and error rates. Uses Application Insights if available.
        """
        try:
            if self.has_app_insights:
                # Use Application Insights for detailed performance metrics
                query = f"""
                requests
                | where timestamp >= ago({time_range})
                | where cloud_RoleName == "petclinic"
                | summarize 
                    request_count = count(),
                    avg_duration = avg(duration),
                    p95_duration = percentile(duration, 95),
                    error_rate = countif(success == false) * 100.0 / count(),
                    unique_users = dcount(user_Id)
                    by bin(timestamp, 5m), name
                | order by timestamp desc
                | take 100
                """
                
                url = f"{self.app_insights_base_url}/query"
                params = {"query": query}
                
                result = self._make_request(url, params)
                if result and "tables" in result:
                    return f"Performance metrics from Application Insights: {result['tables'][0]['rows']}"
            
            # Fallback to basic container metrics if Application Insights not available
            if self.has_workspace:
                query = f"""
                ContainerLog
                | where TimeGenerated >= ago({time_range})
                | where ContainerName contains "petclinic"
                | where LogEntry contains "response" or LogEntry contains "request"
                | summarize log_count = count() by bin(TimeGenerated, 5m)
                | order by TimeGenerated desc
                | take 20
                """
                
                url = f"{self.logs_base_url}/query"
                params = {"query": query}
                
                result = self._make_request(url, params)
                if result and "tables" in result:
                    return f"Basic performance data from container logs: {result['tables'][0]['rows']}"
            
            return "Performance metrics not available. Application Insights not configured. Consider enabling Application Insights for detailed request/response metrics."
                
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return f"Error retrieving performance metrics: {e}"
    
    @tool
    def check_aks_cluster_health(self) -> str:
        """
        Check AKS cluster health including node status, pod health, and resource utilization.
        """
        try:
            # Get cluster information
            cluster_url = f"{self.monitor_base_url}/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group}/providers/Microsoft.ContainerService/managedClusters"
            
            result = self._make_request(cluster_url)
            if result and "value" in result:
                clusters = result["value"]
                
                health_data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "cluster_count": len(clusters),
                    "clusters": []
                }
                
                for cluster in clusters:
                    cluster_info = {
                        "name": cluster.get("name"),
                        "location": cluster.get("location"),
                        "status": cluster.get("properties", {}).get("provisioningState"),
                        "kubernetes_version": cluster.get("properties", {}).get("kubernetesVersion"),
                        "node_count": len(cluster.get("properties", {}).get("agentPoolProfiles", [])),
                        "fqdn": cluster.get("properties", {}).get("fqdn")
                    }
                    health_data["clusters"].append(cluster_info)
                
                return f"AKS Cluster Health: {json.dumps(health_data, indent=2)}"
            else:
                return "No AKS clusters found or access denied"
                
        except Exception as e:
            logger.error(f"Failed to get AKS cluster health: {e}")
            return f"Error retrieving AKS cluster health: {e}"
    
    @tool
    def analyze_petclinic_errors(self, time_range: str = "PT1H") -> str:
        """
        Analyze error patterns in PetClinic application to identify common issues
        and suggest potential causes and solutions.
        """
        try:
            # KQL query for error analysis
            query = f"""
            union
            (exceptions | where timestamp >= ago({time_range}) | where cloud_RoleName == "petclinic"),
            (traces | where timestamp >= ago({time_range}) | where cloud_RoleName == "petclinic" and severityLevel >= 3)
            | extend ErrorType = coalesce(type, "Unknown")
            | extend ErrorMessage = coalesce(outerMessage, message)
            | summarize 
                error_count = count(),
                sample_message = any(ErrorMessage),
                first_occurrence = min(timestamp),
                last_occurrence = max(timestamp)
                by ErrorType
            | order by error_count desc
            | take 20
            """
            
            url = f"{self.app_insights_base_url}/query"
            params = {"query": query}
            
            result = self._make_request(url, params)
            if result and "tables" in result:
                errors = result["tables"][0]["rows"]
                
                error_analysis = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "application": "petclinic",
                    "analysis_period": time_range,
                    "total_error_types": len(errors),
                    "error_patterns": [],
                    "recommendations": []
                }
                
                for row in errors:
                    error_type = row[0]
                    error_count = row[1]
                    sample_message = row[2]
                    first_seen = row[3]
                    last_seen = row[4]
                    
                    pattern = {
                        "error_type": error_type,
                        "count": error_count,
                        "sample_message": sample_message,
                        "first_occurrence": first_seen,
                        "last_occurrence": last_seen,
                        "potential_cause": self._analyze_error_cause(error_type, sample_message)
                    }
                    error_analysis["error_patterns"].append(pattern)
                
                # Generate recommendations based on error patterns
                error_analysis["recommendations"] = self._generate_error_recommendations(errors)
                
                return f"PetClinic Error Analysis: {json.dumps(error_analysis, indent=2)}"
            else:
                return "No errors found for PetClinic application"
                
        except Exception as e:
            logger.error(f"Failed to analyze errors: {e}")
            return f"Error analyzing PetClinic errors: {e}"
    
    def _analyze_error_cause(self, error_type: str, message: str) -> str:
        """Analyze error type and message to suggest potential causes"""
        error_type_lower = error_type.lower()
        message_lower = message.lower() if message else ""
        
        if "sql" in error_type_lower or "database" in message_lower:
            return "Database connectivity or query issue"
        elif "memory" in message_lower or "outofmemory" in message_lower:
            return "Memory pressure or memory leak"
        elif "timeout" in message_lower or "connection" in error_type_lower:
            return "Network connectivity or service timeout"
        elif "null" in message_lower or "nullpointer" in error_type_lower:
            return "Application logic error or missing data validation"
        elif "security" in message_lower or "authentication" in message_lower:
            return "Security or authentication issue"
        else:
            return "Application logic or configuration issue"
    
    def _generate_error_recommendations(self, errors: List) -> List[str]:
        """Generate recommendations based on error patterns"""
        recommendations = []
        
        for error in errors[:5]:  # Top 5 errors
            error_type = error[0].lower()
            count = error[1]
            
            if count > 10:
                if "sql" in error_type or "database" in error_type:
                    recommendations.append("Check PostgreSQL connection pool settings and database performance")
                elif "memory" in error_type:
                    recommendations.append("Review JVM heap settings and check for memory leaks")
                elif "timeout" in error_type:
                    recommendations.append("Investigate network latency and service dependencies")
                else:
                    recommendations.append(f"Investigate high frequency {error_type} errors ({count} occurrences)")
        
        if not recommendations:
            recommendations.append("Monitor application for recurring error patterns")
        
        return recommendations