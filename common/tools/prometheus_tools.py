"""
Prometheus tools for querying metrics data
"""
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urljoin
from common.tools.base import AgentTool

class PrometheusQueryTool(AgentTool):
    """Tool for executing PromQL queries against Prometheus"""
    
    def __init__(self, prometheus_url="http://prometheus:9090"):
        self.base_url = prometheus_url
        self.api_path = "/api/v1/"
    
    @property
    def name(self):
        return "prometheus_query"
    
    @property
    def description(self):
        return "Execute a PromQL instant query against Prometheus"
    
    def execute(self, query, time=None):
        """
        Execute a PromQL instant query
        
        Args:
            query (str): The PromQL query to execute
            time (str, optional): RFC3339 or Unix timestamp for query evaluation time
            
        Returns:
            dict: Query results
        """
        endpoint = urljoin(self.base_url, f"{self.api_path}query")
        params = {"query": query}
        
        if time:
            params["time"] = time
            
        response = requests.get(endpoint, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Query failed with status {response.status_code}: {response.text}")

    def get_service_health(self, service, namespace):
        """
        Get service health metrics
        
        Args:
            service (str): Service name
            namespace (str): Kubernetes namespace
            
        Returns:
            dict: Service health metrics
        """
        metrics = {}
        
        # Get request rate
        rate_query = f'sum(rate(http_requests_total{{service="{service}",namespace="{namespace}"}}[5m]))'
        rate_result = self.execute(rate_query)
        metrics["request_rate"] = rate_result.get("data", {}).get("result", [{}])[0].get("value", [None, 0])[1]
        
        # Get error rate
        error_query = f'sum(rate(http_requests_total{{service="{service}",namespace="{namespace}",status=~"5.."}}[5m]))'
        error_result = self.execute(error_query)
        metrics["error_rate"] = error_result.get("data", {}).get("result", [{}])[0].get("value", [None, 0])[1]
        
        # Get latency
        latency_query = f'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{service="{service}",namespace="{namespace}"}}[5m])) by (le))'
        latency_result = self.execute(latency_query)
        metrics["p95_latency"] = latency_result.get("data", {}).get("result", [{}])[0].get("value", [None, 0])[1]
        
        # Calculate error rate percentage
        if metrics["request_rate"] > 0:
            metrics["error_rate_percent"] = (metrics["error_rate"] / metrics["request_rate"]) * 100
        else:
            metrics["error_rate_percent"] = 0
            
        return metrics

    def get_resource_usage(self, pod, namespace):
        """
        Get pod resource usage metrics
        
        Args:
            pod (str): Pod name
            namespace (str): Kubernetes namespace
            
        Returns:
            dict: Resource usage metrics
        """
        metrics = {}
        
        # Get CPU usage
        cpu_query = f'sum(rate(container_cpu_usage_seconds_total{{pod="{pod}",namespace="{namespace}"}}[5m]))'
        cpu_result = self.execute(cpu_query)
        metrics["cpu_usage"] = cpu_result.get("data", {}).get("result", [{}])[0].get("value", [None, 0])[1]
        
        # Get memory usage
        memory_query = f'container_memory_usage_bytes{{pod="{pod}",namespace="{namespace}"}}'
        memory_result = self.execute(memory_query)
        metrics["memory_usage"] = memory_result.get("data", {}).get("result", [{}])[0].get("value", [None, 0])[1]
        
        # Get memory limit
        memory_limit_query = f'container_spec_memory_limit_bytes{{pod="{pod}",namespace="{namespace}"}}'
        memory_limit_result = self.execute(memory_limit_query)
        memory_limit = memory_limit_result.get("data", {}).get("result", [{}])[0].get("value", [None, 0])[1]
        
        # Calculate memory usage percentage
        if memory_limit > 0:
            metrics["memory_usage_percent"] = (metrics["memory_usage"] / memory_limit) * 100
        else:
            metrics["memory_usage_percent"] = 0
            
        return metrics

    def get_service_dependencies(self, service, namespace):
        """
        Get service dependency metrics
        
        Args:
            service (str): Service name
            namespace (str): Kubernetes namespace
            
        Returns:
            dict: Service dependency metrics
        """
        metrics = {}
        
        # Get upstream service calls
        upstream_query = f'sum(rate(http_client_requests_total{{service="{service}",namespace="{namespace}"}}[5m])) by (upstream_service)'
        upstream_result = self.execute(upstream_query)
        
        upstream_calls = {}
        for result in upstream_result.get("data", {}).get("result", []):
            service_name = result.get("metric", {}).get("upstream_service", "unknown")
            rate = result.get("value", [None, 0])[1]
            upstream_calls[service_name] = rate
            
        metrics["upstream_calls"] = upstream_calls
        
        # Get downstream service calls
        downstream_query = f'sum(rate(http_server_requests_total{{service="{service}",namespace="{namespace}"}}[5m])) by (downstream_service)'
        downstream_result = self.execute(downstream_query)
        
        downstream_calls = {}
        for result in downstream_result.get("data", {}).get("result", []):
            service_name = result.get("metric", {}).get("downstream_service", "unknown")
            rate = result.get("value", [None, 0])[1]
            downstream_calls[service_name] = rate
            
        metrics["downstream_calls"] = downstream_calls
        
        return metrics

class PrometheusRangeQueryTool(AgentTool):
    """Tool for executing PromQL range queries against Prometheus"""
    
    def __init__(self, prometheus_url="http://prometheus:9090"):
        self.base_url = prometheus_url
        self.api_path = "/api/v1/"
    
    @property
    def name(self):
        return "prometheus_range_query"
    
    @property
    def description(self):
        return "Execute a PromQL range query with start time, end time, and step interval"
    
    def execute(self, query, start, end, step):
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
        endpoint = urljoin(self.base_url, f"{self.api_path}query_range")
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
            raise Exception(f"Range query failed with status {response.status_code}: {response.text}")
            
class PrometheusMetricsTool(AgentTool):
    """Tool for listing available metrics in Prometheus"""
    
    def __init__(self, prometheus_url="http://prometheus:9090"):
        self.base_url = prometheus_url
        self.api_path = "/api/v1/"
    
    @property
    def name(self):
        return "prometheus_list_metrics"
    
    @property
    def description(self):
        return "List all available metrics in Prometheus"
    
    def execute(self):
        """
        List all metric names available in Prometheus
        
        Returns:
            list: List of metric names
        """
        endpoint = urljoin(self.base_url, f"{self.api_path}label/__name__/values")
            
        response = requests.get(endpoint)
        
        if response.status_code == 200:
            return response.json()["data"]
        else:
            raise Exception(f"Failed to list metrics with status {response.status_code}: {response.text}")

class PrometheusTargetsTool(AgentTool):
    """Tool for getting information about Prometheus scrape targets"""
    
    def __init__(self, prometheus_url="http://prometheus:9090"):
        self.base_url = prometheus_url
        self.api_path = "/api/v1/"
    
    @property
    def name(self):
        return "prometheus_targets"
    
    @property
    def description(self):
        return "Get information about all scrape targets"
    
    def execute(self):
        """
        Get all scrape targets and their state
        
        Returns:
            dict: Information about active and dropped targets
        """
        endpoint = urljoin(self.base_url, f"{self.api_path}targets")
            
        response = requests.get(endpoint)
        
        if response.status_code == 200:
            return response.json()["data"]
        else:
            raise Exception(f"Failed to get targets with status {response.status_code}: {response.text}")