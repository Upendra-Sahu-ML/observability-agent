"""
Log tools for querying and analyzing log data from various sources
"""
import os
import json
import requests
import subprocess
from datetime import datetime, timedelta
from urllib.parse import urljoin
from common.tools.base import AgentTool

class LokiQueryTool(AgentTool):
    """Tool for querying logs from Loki"""
    
    def __init__(self, loki_url="http://loki:3100"):
        self.base_url = loki_url
        self.api_path = "/loki/api/v1/"
    
    @property
    def name(self):
        return "loki_query"
    
    @property
    def description(self):
        return "Query logs from Loki using LogQL"
    
    def execute(self, query, start=None, end=None, limit=100, direction="backward"):
        """
        Execute a LogQL query against Loki
        
        Args:
            query (str): The LogQL query to execute
            start (str, optional): Start time for the query (RFC3339 or Unix timestamp)
            end (str, optional): End time for the query (RFC3339 or Unix timestamp)
            limit (int, optional): Maximum number of log entries to return
            direction (str, optional): Query direction, either "forward" or "backward"
            
        Returns:
            dict: Query results containing log streams
        """
        endpoint = urljoin(self.base_url, f"{self.api_path}query_range")
        
        # Set default time range if not provided
        if not start:
            start = datetime.now() - timedelta(hours=1)
            start = start.isoformat() + "Z"
        if not end:
            end = datetime.now().isoformat() + "Z"
            
        params = {
            "query": query,
            "start": start,
            "end": end,
            "limit": limit,
            "direction": direction
        }
            
        response = requests.get(endpoint, params=params)
        
        if response.status_code == 200:
            return response.json()["data"]
        else:
            raise Exception(f"Loki query failed with status {response.status_code}: {response.text}")

class PodLogTool(AgentTool):
    """Tool for retrieving Kubernetes pod logs using kubectl"""
    
    @property
    def name(self):
        return "pod_logs"
    
    @property
    def description(self):
        return "Retrieve logs from Kubernetes pods using kubectl"
    
    def execute(self, namespace, pod_name=None, container=None, selector=None, tail=100, previous=False, since=None):
        """
        Retrieve logs from Kubernetes pods
        
        Args:
            namespace (str): Kubernetes namespace
            pod_name (str, optional): Specific pod name to get logs from
            container (str, optional): Specific container name if pod has multiple containers
            selector (str, optional): Label selector to filter pods (e.g., "app=nginx")
            tail (int, optional): Number of lines to retrieve from the end of logs
            previous (bool, optional): Get logs from previous container instance if it exists
            since (str, optional): Only return logs newer than this time (e.g., "1h", "15m")
            
        Returns:
            dict: Pod logs organized by pod name
        """
        cmd = ["kubectl", "logs"]
        
        if pod_name:
            cmd.append(pod_name)
        elif selector:
            cmd.extend(["-l", selector])
        else:
            raise ValueError("Either pod_name or selector must be provided")
            
        cmd.extend(["-n", namespace])
        
        if container:
            cmd.extend(["-c", container])
            
        if tail:
            cmd.extend(["--tail", str(tail)])
            
        if previous:
            cmd.append("-p")
            
        if since:
            cmd.extend(["--since", since])
            
        try:
            log_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
            
            if pod_name:
                return {pod_name: log_output}
            else:
                # For selector-based logs, we need to parse and organize by pod
                # This is simplified and might need enhancement based on actual output format
                return {"logs": log_output}
                
        except subprocess.CalledProcessError as e:
            return {"error": str(e), "output": e.output}

class FileLogTool(AgentTool):
    """Tool for retrieving and analyzing logs from local files"""
    
    @property
    def name(self):
        return "file_logs"
    
    @property
    def description(self):
        return "Retrieve and analyze logs from local files"
    
    def execute(self, file_path, pattern=None, max_lines=1000, tail=None):
        """
        Retrieve and optionally filter logs from local files
        
        Args:
            file_path (str): Path to the log file
            pattern (str, optional): Grep pattern to filter log lines
            max_lines (int, optional): Maximum number of lines to process
            tail (int, optional): Get only the last N lines of the file
            
        Returns:
            dict: Filtered log contents or error message
        """
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}
            
        cmd = []
        
        if tail:
            # Use tail command to get last N lines
            cmd = ["tail", f"-{tail}", file_path]
        else:
            # Use head to limit maximum lines
            cmd = ["head", f"-{max_lines}", file_path]
            
        try:
            # Get file content with optional line limit
            log_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
            
            # Apply pattern filtering if specified
            if pattern:
                filtered_lines = []
                for line in log_output.splitlines():
                    if pattern in line:
                        filtered_lines.append(line)
                return {"filtered_lines": filtered_lines, "count": len(filtered_lines)}
            else:
                return {"content": log_output, "lines": log_output.count('\n') + 1}
                
        except subprocess.CalledProcessError as e:
            return {"error": str(e), "output": e.output}