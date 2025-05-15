"""
Metric tools for analyzing and querying metrics data
"""
import requests
import json
import os
from datetime import datetime, timedelta
from urllib.parse import urljoin
from crewai.tools import tool
from common.tools.prometheus_tools import PrometheusTools

class PrometheusQueryTool:
    """Tool for querying Prometheus metrics"""
    
    def __init__(self, prometheus_url=None):
        self.prometheus_url = prometheus_url or os.environ.get('PROMETHEUS_URL', "http://prometheus:9090")
        self.prometheus_tools = PrometheusTools(prometheus_url=self.prometheus_url)
    
    @tool("Query metrics from Prometheus using PromQL")
    def query_metrics(self, query=None, start=None, end=None, step=None):
        """
        Execute a Prometheus query
        
        Args:
            query (str): The PromQL query to execute
            start (str, optional): Start time for range query (e.g., "-30m")
            end (str, optional): End time for range query (default: now)
            step (str, optional): Step size for range queries (e.g., "15s")
            
        Returns:
            dict: Query results
        """
        if not query:
            return {
                "status": "error",
                "error": "Query parameter is required"
            }
            
        # Handle relative time specifications like "-30m"
        if start and start.startswith("-"):
            try:
                minutes = int(start[1:-1]) if start.endswith("m") else int(start[1:])
                start_time = datetime.now() - timedelta(minutes=minutes)
                start = start_time.timestamp()
            except (ValueError, IndexError):
                return {
                    "status": "error",
                    "error": f"Invalid start time format: {start}"
                }
                
        # If end is not specified, use current time
        if not end:
            end = datetime.now().timestamp()
            
        # If we have both start and end, perform a range query
        if start and end and step:
            return self.prometheus_tools.range_query(query, start, end, step)
        else:
            # Otherwise, perform an instant query
            return self.prometheus_tools.query(query)
            
    @tool("Query CPU utilization metrics")
    def get_cpu_metrics(self, service, namespace=None, duration="30m", step="15s"):
        """
        Get CPU utilization metrics for a service
        
        Args:
            service (str): The service name
            namespace (str, optional): The Kubernetes namespace
            duration (str, optional): Duration to look back (e.g., "30m")
            step (str, optional): Step size for range query
            
        Returns:
            dict: CPU metrics for the service
        """
        queries = []
        
        if namespace:
            queries.append(f'sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}",pod=~"{service}-.*"}}[5m]))')
        else:
            queries.append(f'sum(rate(container_cpu_usage_seconds_total{{pod=~"{service}-.*"}}[5m]))')
            
        results = {}
        for i, query in enumerate(queries):
            results[f"query_{i}"] = self.query_metrics(
                query=query,
                start=f"-{duration}", 
                end=None,
                step=step
            )
            
        return results
    
    @tool("Query memory usage metrics")
    def get_memory_metrics(self, service, namespace=None, duration="30m", step="15s"):
        """
        Get memory usage metrics for a service
        
        Args:
            service (str): The service name
            namespace (str, optional): The Kubernetes namespace
            duration (str, optional): Duration to look back (e.g., "30m")
            step (str, optional): Step size for range query
            
        Returns:
            dict: Memory metrics for the service
        """
        queries = []
        
        if namespace:
            queries.append(f'sum(container_memory_usage_bytes{{namespace="{namespace}",pod=~"{service}-.*"}})')
        else:
            queries.append(f'sum(container_memory_usage_bytes{{pod=~"{service}-.*"}})')
            
        results = {}
        for i, query in enumerate(queries):
            results[f"query_{i}"] = self.query_metrics(
                query=query,
                start=f"-{duration}", 
                end=None,
                step=step
            )
            
        return results
        
    @tool("Query error rate metrics")
    def get_error_rate(self, service, namespace=None, duration="30m", step="15s"):
        """
        Get error rate metrics for a service
        
        Args:
            service (str): The service name
            namespace (str, optional): The Kubernetes namespace
            duration (str, optional): Duration to look back (e.g., "30m")
            step (str, optional): Step size for range query
            
        Returns:
            dict: Error rate metrics for the service
        """
        queries = []
        
        if namespace:
            queries.append(f'sum(rate(http_requests_total{{namespace="{namespace}",service="{service}",status=~"5.*"}}[5m])) / sum(rate(http_requests_total{{namespace="{namespace}",service="{service}"}}[5m]))')
        else:
            queries.append(f'sum(rate(http_requests_total{{service="{service}",status=~"5.*"}}[5m])) / sum(rate(http_requests_total{{service="{service}"}}[5m]))')
            
        results = {}
        for i, query in enumerate(queries):
            results[f"query_{i}"] = self.query_metrics(
                query=query,
                start=f"-{duration}", 
                end=None,
                step=step
            )
            
        return results

    @tool("Get service health metrics")
    def get_service_health(self, service, namespace=None, duration="30m", step="15s"):
        """
        Get overall health metrics for a service
        
        Args:
            service (str): The service name
            namespace (str, optional): The Kubernetes namespace
            duration (str, optional): Duration to look back (e.g., "30m")
            step (str, optional): Step size for range query
            
        Returns:
            dict: Health metrics including CPU, memory, and error rates
        """
        cpu_metrics = self.get_cpu_metrics(service, namespace, duration, step)
        memory_metrics = self.get_memory_metrics(service, namespace, duration, step)
        error_metrics = self.get_error_rate(service, namespace, duration, step)
        
        return {
            "service": service,
            "namespace": namespace,
            "cpu": cpu_metrics,
            "memory": memory_metrics,
            "error_rate": error_metrics
        }

class MetricAnalysisTool:
    """Tool for analyzing metric data"""
    
    @tool("Analyze metric data to identify trends")
    def analyze_trend(self, metrics=None):
        """
        Analyze trend in metric data
        
        Args:
            metrics (dict): Dictionary containing metric data
            
        Returns:
            dict: Trend analysis results
        """
        if not metrics:
            return {
                "status": "error",
                "error": "Metrics data is required for trend analysis"
            }
            
        # Extract metric data
        data = self._extract_metric_data(metrics)
            
        # Initialize results
        results = {
            "status": "success",
            "analyzed_at": datetime.now().isoformat(),
            "analysis_type": "trend",
            "findings": self._analyze_trend(data)
        }
            
        return results
    
    @tool("Analyze metric data to identify anomalies")
    def analyze_anomalies(self, metrics=None):
        """
        Detect anomalies in metric data
        
        Args:
            metrics (dict): Dictionary containing metric data
            
        Returns:
            dict: Anomaly detection results
        """
        if not metrics:
            return {
                "status": "error",
                "error": "Metrics data is required for anomaly detection"
            }
            
        # Extract metric data
        data = self._extract_metric_data(metrics)
            
        # Initialize results
        results = {
            "status": "success",
            "analyzed_at": datetime.now().isoformat(),
            "analysis_type": "anomaly",
            "findings": self._analyze_anomalies(data)
        }
            
        return results
    
    @tool("Analyze metric data against thresholds")
    def analyze_threshold(self, metrics=None, threshold=None):
        """
        Analyze metric data against a threshold
        
        Args:
            metrics (dict): Dictionary containing metric data
            threshold (float): Threshold value for analysis
            
        Returns:
            dict: Threshold analysis results
        """
        if not metrics or threshold is None:
            return {
                "status": "error",
                "error": "Both metrics data and threshold are required for threshold analysis"
            }
            
        # Extract metric data
        data = self._extract_metric_data(metrics)
            
        # Initialize results
        results = {
            "status": "success",
            "analyzed_at": datetime.now().isoformat(),
            "analysis_type": "threshold",
            "threshold": threshold,
            "findings": self._analyze_threshold(data, threshold)
        }
            
        return results
    
    @tool("Perform general analysis on metric data")
    def analyze_metrics(self, metrics=None, analysis_type=None, threshold=None):
        """
        Analyze metric data
        
        Args:
            metrics (dict): Dictionary containing metric data
            analysis_type (str, optional): Type of analysis to perform (trend, anomaly, threshold)
            threshold (float, optional): Threshold value for threshold analysis
            
        Returns:
            dict: Analysis results
        """
        if not metrics:
            return {
                "status": "error",
                "error": "Metrics data is required for analysis"
            }
            
        # Extract metric data
        data = self._extract_metric_data(metrics)
            
        # Initialize results
        results = {
            "status": "success",
            "analyzed_at": datetime.now().isoformat(),
            "analysis_type": analysis_type or "general",
            "findings": []
        }
        
        # Perform analysis based on type
        if analysis_type == "trend":
            results["findings"] = self._analyze_trend(data)
        elif analysis_type == "anomaly":
            results["findings"] = self._analyze_anomalies(data)
        elif analysis_type == "threshold" and threshold is not None:
            results["findings"] = self._analyze_threshold(data, threshold)
        else:
            # Default to general analysis
            results["findings"] = self._analyze_general(data)
            
        return results
    
    def _extract_metric_data(self, metrics):
        """Extract and format metric data from Prometheus response"""
        data = []
        if metrics.get("status") == "success":
            result_data = metrics.get("data", {}).get("result", [])
            
            for series in result_data:
                metric_name = series.get("metric", {}).get("__name__", "unknown")
                
                # For instant queries
                if "value" in series:
                    timestamp, value = series["value"]
                    try:
                        data.append({
                            "metric": metric_name,
                            "timestamp": timestamp,
                            "value": float(value)
                        })
                    except (ValueError, TypeError):
                        # Skip non-numeric values
                        continue
                
                # For range queries
                elif "values" in series:
                    for timestamp, value in series["values"]:
                        try:
                            data.append({
                                "metric": metric_name,
                                "timestamp": timestamp,
                                "value": float(value)
                            })
                        except (ValueError, TypeError):
                            # Skip non-numeric values
                            continue
        return data
    
    def _analyze_trend(self, data):
        """Analyze trend in metric data"""
        if not data:
            return [{"type": "info", "message": "No data available for trend analysis"}]
            
        findings = []
        
        # Group by metric
        metrics = {}
        for item in data:
            metric = item["metric"]
            if metric not in metrics:
                metrics[metric] = []
            metrics[metric].append(item)
            
        # Analyze each metric
        for metric, values in metrics.items():
            # Sort by timestamp
            values.sort(key=lambda x: x["timestamp"])
            
            if len(values) < 2:
                findings.append({
                    "type": "info",
                    "metric": metric,
                    "message": "Not enough data points for trend analysis"
                })
                continue
                
            # Calculate simple linear regression
            start_value = values[0]["value"]
            end_value = values[-1]["value"]
            change = end_value - start_value
            
            if change > 0:
                findings.append({
                    "type": "trend",
                    "metric": metric,
                    "message": f"Increasing trend detected",
                    "change": change,
                    "percentage": (change / start_value * 100) if start_value != 0 else float('inf')
                })
            elif change < 0:
                findings.append({
                    "type": "trend",
                    "metric": metric,
                    "message": f"Decreasing trend detected",
                    "change": change,
                    "percentage": (change / start_value * 100) if start_value != 0 else float('-inf')
                })
            else:
                findings.append({
                    "type": "trend",
                    "metric": metric,
                    "message": "No significant trend detected",
                    "change": 0,
                    "percentage": 0
                })
                
        return findings
    
    def _analyze_anomalies(self, data):
        """Simple anomaly detection in metric data"""
        if not data:
            return [{"type": "info", "message": "No data available for anomaly detection"}]
            
        findings = []
        
        # Group by metric
        metrics = {}
        for item in data:
            metric = item["metric"]
            if metric not in metrics:
                metrics[metric] = []
            metrics[metric].append(item)
            
        # Analyze each metric
        for metric, values in metrics.items():
            if len(values) < 3:
                findings.append({
                    "type": "info",
                    "metric": metric,
                    "message": "Not enough data points for anomaly detection"
                })
                continue
                
            # Calculate mean and standard deviation
            data_values = [item["value"] for item in values]
            mean = sum(data_values) / len(data_values)
            variance = sum((x - mean) ** 2 for x in data_values) / len(data_values)
            std_dev = variance ** 0.5
            
            # Identify anomalies (values more than 2 standard deviations from mean)
            anomalies = []
            for item in values:
                if abs(item["value"] - mean) > 2 * std_dev:
                    anomalies.append({
                        "timestamp": item["timestamp"],
                        "value": item["value"],
                        "deviation": (item["value"] - mean) / std_dev
                    })
                    
            if anomalies:
                findings.append({
                    "type": "anomaly",
                    "metric": metric,
                    "message": f"Found {len(anomalies)} anomalies",
                    "mean": mean,
                    "std_dev": std_dev,
                    "anomalies": anomalies
                })
            else:
                findings.append({
                    "type": "info",
                    "metric": metric,
                    "message": "No anomalies detected",
                    "mean": mean,
                    "std_dev": std_dev
                })
                
        return findings
    
    def _analyze_threshold(self, data, threshold):
        """Analyze metric data against a threshold"""
        if not data:
            return [{"type": "info", "message": "No data available for threshold analysis"}]
            
        findings = []
        
        # Group by metric
        metrics = {}
        for item in data:
            metric = item["metric"]
            if metric not in metrics:
                metrics[metric] = []
            metrics[metric].append(item)
            
        # Analyze each metric
        for metric, values in metrics.items():
            # Count values above threshold
            above_threshold = [item for item in values if item["value"] > threshold]
            
            if above_threshold:
                findings.append({
                    "type": "threshold",
                    "metric": metric,
                    "message": f"{len(above_threshold)} of {len(values)} values exceed threshold of {threshold}",
                    "threshold": threshold,
                    "count": len(above_threshold),
                    "percentage": len(above_threshold) / len(values) * 100
                })
            else:
                findings.append({
                    "type": "info",
                    "metric": metric,
                    "message": f"No values exceed threshold of {threshold}",
                    "threshold": threshold
                })
                
        return findings
    
    def _analyze_general(self, data):
        """General analysis of metric data"""
        if not data:
            return [{"type": "info", "message": "No data available for analysis"}]
            
        findings = []
        
        # Group by metric
        metrics = {}
        for item in data:
            metric = item["metric"]
            if metric not in metrics:
                metrics[metric] = []
            metrics[metric].append(item)
            
        # Analyze each metric
        for metric, values in metrics.items():
            if not values:
                continue
                
            # Calculate basic statistics
            data_values = [item["value"] for item in values]
            mean = sum(data_values) / len(data_values)
            min_value = min(data_values)
            max_value = max(data_values)
            
            findings.append({
                "type": "statistics",
                "metric": metric,
                "count": len(values),
                "min": min_value,
                "max": max_value,
                "mean": mean,
                "range": max_value - min_value
            })
            
            # Check for zero values
            zero_values = [item for item in values if item["value"] == 0]
            if zero_values:
                findings.append({
                    "type": "warning",
                    "metric": metric,
                    "message": f"Found {len(zero_values)} zero values out of {len(values)} total values",
                    "count": len(zero_values),
                    "percentage": len(zero_values) / len(values) * 100
                })
                
        return findings