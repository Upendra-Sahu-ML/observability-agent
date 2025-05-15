"""
Prometheus tools for querying metrics data
"""
import requests
import json
import os
from datetime import datetime, timedelta
from urllib.parse import urljoin

class PrometheusTools:
    """Collection of tools for working with Prometheus metrics"""
    
    def __init__(self, prometheus_url=None):
        self.prometheus_url = prometheus_url or os.environ.get('PROMETHEUS_URL', "http://prometheus:9090")
        self.api_path = "/api/v1/"
    
    def query(self, query, time=None):
        """
        Execute a PromQL instant query
        
        Args:
            query (str): The PromQL query to execute
            time (str, optional): RFC3339 or Unix timestamp for query evaluation time
            
        Returns:
            dict: Query results
        """
        endpoint = urljoin(self.prometheus_url, f"{self.api_path}query")
        params = {"query": query}
        
        if time:
            params["time"] = time
            
        response = requests.get(endpoint, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "status": "error",
                "error": f"Query failed with status {response.status_code}: {response.text}"
            }
    
    def range_query(self, query, start, end, step):
        """
        Execute a PromQL range query
        
        Args:
            query (str): The PromQL query to execute
            start (str): Start timestamp (RFC3339 or Unix timestamp)
            end (str): End timestamp (RFC3339 or Unix timestamp)
            step (str): Query resolution step width (e.g. "30s", "5m")
            
        Returns:
            dict: Range query results
        """
        endpoint = urljoin(self.prometheus_url, f"{self.api_path}query_range")
        params = {
            "query": query,
            "start": start,
            "end": end,
            "step": step
        }
            
        response = requests.get(endpoint, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "status": "error",
                "error": f"Range query failed with status {response.status_code}: {response.text}"
            }
    
    def get_service_health(self, service):
        """
        Get service health metrics
        
        Args:
            service (str): Service name
            
        Returns:
            dict: Service health metrics
        """
        query = f'up{{service="{service}"}}'
        result = self.query(query)
        
        response = {
            "status": result.get("status", "error")
        }
        
        if result.get("status") == "success":
            data = result.get("data", {}).get("result", [])
            if data and float(data[0].get("value", [0, "0"])[1]) > 0:
                response["health"] = "healthy"
            else:
                response["health"] = "unhealthy"
        else:
            response["error"] = result.get("error", "Unknown error")
            
        return response
    
    def get_resource_usage(self, service, resource):
        """
        Get service resource usage metrics
        
        Args:
            service (str): Service name
            resource (str): Resource type (cpu, memory)
            
        Returns:
            dict: Resource usage metrics
        """
        if resource == "cpu":
            query = f'sum(rate(container_cpu_usage_seconds_total{{service="{service}"}}[5m]))'
        elif resource == "memory":
            query = f'sum(container_memory_usage_bytes{{service="{service}"}}) / 1024 / 1024'
        else:
            return {"status": "error", "error": f"Unsupported resource type: {resource}"}
            
        result = self.query(query)
        
        response = {
            "status": result.get("status", "error")
        }
        
        if result.get("status") == "success":
            data = result.get("data", {}).get("result", [])
            if data:
                response["usage"] = float(data[0].get("value", [0, "0"])[1])
            else:
                response["usage"] = 0
        else:
            response["error"] = result.get("error", "Unknown error")
            
        return response
    
    def get_service_dependencies(self, service):
        """
        Get service dependency metrics
        
        Args:
            service (str): Service name
            
        Returns:
            dict: Service dependency metrics
        """
        query = f'count by (destination_service) (service_calls{{source_service="{service}"}})'
        result = self.query(query)
        
        response = {
            "status": result.get("status", "error")
        }
        
        if result.get("status") == "success":
            data = result.get("data", {}).get("result", [])
            dependencies = []
            
            for item in data:
                dependencies.append({
                    "service": item.get("metric", {}).get("destination_service", "unknown"),
                    "calls": float(item.get("value", [0, "0"])[1])
                })
                
            response["dependencies"] = dependencies
        else:
            response["error"] = result.get("error", "Unknown error")
            
        return response
    
    def list_metrics(self):
        """
        List all metric names available in Prometheus
        
        Returns:
            dict: List of metric names
        """
        endpoint = urljoin(self.prometheus_url, f"{self.api_path}label/__name__/values")
            
        response = requests.get(endpoint)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "status": "success",
                "metrics": data.get("data", [])
            }
        else:
            return {
                "status": "error",
                "error": f"Failed to list metrics with status {response.status_code}: {response.text}"
            }
    
    def get_metric_metadata(self, metric):
        """
        Get metadata for a specific metric
        
        Args:
            metric (str): The metric name
            
        Returns:
            dict: Metric metadata
        """
        endpoint = urljoin(self.prometheus_url, f"{self.api_path}metadata")
        params = {}
        
        if metric:
            params["metric"] = metric
            
        response = requests.get(endpoint, params=params)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "status": "success",
                "metadata": data.get("data", {})
            }
        else:
            return {
                "status": "error",
                "error": f"Failed to get metadata with status {response.status_code}: {response.text}"
            }
    
    def list_targets(self, state=None):
        """
        Get all scrape targets and their state
        
        Args:
            state (str, optional): Filter targets by state (active, dropped, any)
            
        Returns:
            dict: Information about targets
        """
        endpoint = urljoin(self.prometheus_url, f"{self.api_path}targets")
        params = {}
        
        if state and state != "any":
            params["state"] = state
            
        response = requests.get(endpoint, params=params)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "status": "success",
                "targets": data.get("data", {})
            }
        else:
            return {
                "status": "error",
                "error": f"Failed to get targets with status {response.status_code}: {response.text}"
            }
    
    def get_target_health(self, job):
        """
        Get health status for targets of a specific job
        
        Args:
            job (str): The job name
            
        Returns:
            dict: Target health information
        """
        targets_result = self.list_targets()
        
        if targets_result.get("status") != "success":
            return targets_result
        
        active_targets = targets_result.get("targets", {}).get("activeTargets", [])
        job_targets = [t for t in active_targets if t.get("labels", {}).get("job") == job]
        
        healthy = sum(1 for t in job_targets if t.get("health") == "up")
        total = len(job_targets)
        
        return {
            "status": "success",
            "job": job,
            "healthy_targets": healthy,
            "total_targets": total,
            "health_percentage": (healthy / total * 100) if total > 0 else 0
        }