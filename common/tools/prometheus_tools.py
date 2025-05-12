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