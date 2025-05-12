import redis
import json
import os
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from common.tools.prometheus_tools import (
    PrometheusQueryTool,
    PrometheusRangeQueryTool,
    PrometheusMetricsTool,
    PrometheusTargetsTool
)

load_dotenv()

class MetricAgent:
    def __init__(self, prometheus_url="http://prometheus:9090"):
        self.redis_client = redis.Redis(host='redis', port=6379)
        # Initialize OpenAI model
        self.llm = ChatOpenAI(model="gpt-4")
        
        # Initialize Prometheus tools
        self.prom_query_tool = PrometheusQueryTool(prometheus_url=prometheus_url)
        self.prom_range_query_tool = PrometheusRangeQueryTool(prometheus_url=prometheus_url)
        self.prom_metrics_tool = PrometheusMetricsTool(prometheus_url=prometheus_url)
        self.prom_targets_tool = PrometheusTargetsTool(prometheus_url=prometheus_url)
        
        # Create a crewAI agent for metric analysis
        self.metric_analyzer = Agent(
            role="Metric Data Analyst",
            goal="Analyze metric data to identify anomalies and patterns",
            backstory="You are an expert at analyzing metrics and detecting abnormal patterns that might indicate system issues.",
            verbose=True,
            llm=self.llm,
            tools=[
                self.prom_query_tool.execute,
                self.prom_range_query_tool.execute,
                self.prom_metrics_tool.execute,
                self.prom_targets_tool.execute
            ]
        )

    def _get_metrics_for_alert(self, alert_data):
        """Collect relevant metrics for the alert by intelligently analyzing the alert context"""
        metrics_data = {}
        
        try:
            # Extract basic alert information
            alert_name = alert_data.get('labels', {}).get('alertname', '').lower()
            service = alert_data.get('labels', {}).get('service')
            namespace = alert_data.get('labels', {}).get('namespace', 'default')
            pod = alert_data.get('labels', {}).get('pod', '')
            alert_summary = alert_data.get('annotations', {}).get('summary', '').lower()
            alert_description = alert_data.get('annotations', {}).get('description', '').lower()
            
            # Get time range from alert or use a default
            end_time = alert_data.get('startsAt', None)
            # Look at data from 30 minutes before the alert
            start_time = None
            if end_time:
                from datetime import datetime, timedelta
                try:
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    start_time = (end_dt - timedelta(minutes=30)).isoformat() + 'Z'
                except:
                    pass
            
            # First, let's discover what metrics are available in Prometheus
            available_metrics = self.prom_metrics_tool.execute()
            
            # Define metric categories based on common alert types
            metric_categories = {
                'cpu': ['cpu', 'processor', 'load'],
                'memory': ['memory', 'heap', 'ram', 'oom'],
                'disk': ['disk', 'storage', 'filesystem', 'volume'],
                'network': ['network', 'connection', 'http', 'request', 'latency'],
                'error': ['error', 'exception', 'fail', '5xx', 'status'],
                'jvm': ['jvm', 'gc', 'garbage', 'java']
            }
            
            # Determine which categories apply to this alert
            alert_categories = []
            combined_text = f"{alert_name} {alert_summary} {alert_description}"
            
            for category, keywords in metric_categories.items():
                if any(keyword in combined_text for keyword in keywords):
                    alert_categories.append(category)
            
            # If no categories match, include all by default
            if not alert_categories:
                alert_categories = list(metric_categories.keys())
            
            print(f"[MetricAgent] Alert matches these metric categories: {alert_categories}")
            
            # Build dynamic queries based on alert information and categories
            queries = {}
            
            # Add CPU metrics if relevant
            if 'cpu' in alert_categories:
                if pod:
                    queries['pod_cpu'] = f'sum(rate(container_cpu_usage_seconds_total{{pod=~"{pod}"}}[5m]))'
                elif service:
                    queries['service_cpu'] = f'sum(rate(container_cpu_usage_seconds_total{{service="{service}"}}[5m]))'
                else:
                    queries['overall_cpu'] = 'sum(rate(container_cpu_usage_seconds_total[5m])) by (pod)'
                
                # Add node CPU if available
                if any('node_cpu' in metric for metric in available_metrics.get('data', [])):
                    queries['node_cpu'] = 'avg by (instance) (irate(node_cpu_seconds_total{mode!="idle"}[5m]))'
            
            # Add memory metrics if relevant
            if 'memory' in alert_categories:
                if pod:
                    queries['pod_memory'] = f'container_memory_usage_bytes{{pod=~"{pod}"}}'
                elif service:
                    queries['service_memory'] = f'sum(container_memory_usage_bytes{{service="{service}"}}) by (container)'
                else:
                    queries['overall_memory'] = 'sum(container_memory_usage_bytes) by (pod)'
                
                # Add node memory if available
                if any('node_memory' in metric for metric in available_metrics.get('data', [])):
                    queries['node_memory'] = 'node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes'
            
            # Add disk metrics if relevant
            if 'disk' in alert_categories:
                if any('node_filesystem' in metric for metric in available_metrics.get('data', [])):
                    queries['filesystem_usage'] = 'node_filesystem_size_bytes{mountpoint="/"} - node_filesystem_free_bytes{mountpoint="/"}'
                
                if any('kubelet_volume' in metric for metric in available_metrics.get('data', [])):
                    queries['volume_usage'] = 'kubelet_volume_stats_used_bytes / kubelet_volume_stats_capacity_bytes'
            
            # Add network and error metrics if relevant
            if 'network' in alert_categories or 'error' in alert_categories:
                # Build service-specific filters
                service_filter = f'service="{service}"' if service else ''
                
                if 'network' in alert_categories:
                    if any('http_request_duration' in metric for metric in available_metrics.get('data', [])):
                        latency_query = f'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{{service_filter}}}[5m])) by (le))'
                        queries['latency_p95'] = latency_query
                
                if 'error' in alert_categories:
                    if any('http_requests_total' in metric for metric in available_metrics.get('data', [])):
                        error_filter = f'{service_filter + "," if service_filter else ""}status=~"5.."'
                        error_query = f'sum(rate(http_requests_total{{{error_filter}}}[5m]))'
                        queries['error_rate'] = error_query
            
            # Add JVM metrics if relevant
            if 'jvm' in alert_categories:
                if any('jvm_memory' in metric for metric in available_metrics.get('data', [])):
                    queries['jvm_heap'] = f'sum(jvm_memory_used_bytes{{area="heap"{f", service=\"{service}\"" if service else ""}}})'
                
                if any('jvm_gc' in metric for metric in available_metrics.get('data', [])):
                    queries['jvm_gc'] = f'rate(jvm_gc_collection_seconds_sum{{{f"service=\"{service}\"" if service else ""}}}[5m])'
            
            # If we couldn't find relevant metrics or none of our conditions matched,
            # fall back to basic metrics that should be available in most systems
            if not queries:
                print("[MetricAgent] No specific metrics matched alert context, using fallback metrics")
                
                # Add default fallback metrics
                queries['cpu_usage'] = 'sum(rate(container_cpu_usage_seconds_total[5m])) by (pod)'
                queries['memory_usage'] = 'container_memory_usage_bytes{pod=~".*"}'
                
                if service:
                    queries['service_error_rate'] = f'sum(rate(http_requests_total{{service="{service}",status=~"5.."}}[5m]))'
                    queries['service_latency'] = f'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{service="{service}"}}[5m])) by (le))'
                else:
                    queries['error_rate'] = 'sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)'
                    queries['latency'] = 'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service))'
            
            # Execute the queries and store results
            for metric_name, query in queries.items():
                print(f"[MetricAgent] Querying {metric_name}: {query}")
                metrics_data[metric_name] = self.prom_query_tool.execute(query)
                
                # Get range queries for trends if start and end time are available
                if start_time and end_time:
                    metrics_data[f"{metric_name}_trend"] = self.prom_range_query_tool.execute(
                        query, start_time, end_time, "1m"
                    )
            
            # Check targets health
            metrics_data['targets'] = self.prom_targets_tool.execute()
            
        except Exception as e:
            metrics_data['error'] = str(e)
            print(f"[MetricAgent] Error collecting metrics: {str(e)}")
            
        return metrics_data

    def analyze_metrics(self, alert_data):
        """Analyze metrics using crewAI"""
        # First collect relevant metrics data
        metrics_data = self._get_metrics_for_alert(alert_data)
        
        # Determine if there's a specific metric issue from the alert
        alert_name = alert_data.get('labels', {}).get('alertname', '')
        alert_summary = alert_data.get('annotations', {}).get('summary', '')
        
        # Create task for metric analysis
        analysis_task = Task(
            description=f"""
            Analyze the following metric data to identify anomalies:
            {json.dumps(metrics_data)}
            
            Alert Information:
            Name: {alert_name}
            Summary: {alert_summary}
            Labels: {json.dumps(alert_data.get('labels', {}))}
            
            Focus your analysis on metrics related to this alert.
            """,
            agent=self.metric_analyzer,
            expected_output="A detailed analysis of metrics and identification of potential anomalies"
        )
        
        # Create a crew with the metric analyzer agent
        crew = Crew(
            agents=[self.metric_analyzer],
            tasks=[analysis_task],
            verbose=True
        )
        
        # Execute the crew to analyze the metrics
        result = crew.kickoff()
        return result, metrics_data

    def listen(self):
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe("metric_agent")
        print("[MetricAgent] Listening for messages...")
        
        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        alert = json.loads(message['data'])
                        print(f"[MetricAgent] Processing alert: {alert}")
                        
                        # Use crewAI to analyze the metrics
                        analysis_result, metrics_data = self.analyze_metrics(alert)
                        
                        # Determine what type of metric issue was observed based on the alert and metrics
                        observed_issue = self._determine_observed_issue(alert, metrics_data)
                        
                        # Prepare result for the orchestrator
                        result = {
                            "agent": "metric", 
                            "observed": observed_issue,
                            "analysis": str(analysis_result),
                            "alert_id": alert.get("alert_id", "unknown")
                        }
                        
                        print(f"[MetricAgent] Sending analysis for alert ID: {result['alert_id']}")
                        self.redis_client.publish("orchestrator_response", json.dumps(result))
                    except Exception as e:
                        print(f"[MetricAgent] Error processing message: {str(e)}")
        except redis.RedisError as e:
            print(f"[MetricAgent] Redis connection error: {str(e)}")
            # Try to reconnect
            self.redis_client = redis.Redis(host='redis', port=6379)
            self.listen()  # Recursive call to restart listening
            
    def _determine_observed_issue(self, alert, metrics_data):
        """Determine the type of metric issue observed based on alert and metrics data"""
        # Default observation
        observed_issue = "unknown_metric_issue"
        
        # Check alert name first
        alert_name = alert.get('labels', {}).get('alertname', '').lower()
        if 'cpu' in alert_name:
            observed_issue = "cpu_usage_high"
        elif 'memory' in alert_name:
            observed_issue = "memory_usage_high"
        elif 'latency' in alert_name or 'slow' in alert_name:
            observed_issue = "high_latency"
        elif 'error' in alert_name or '5xx' in alert_name:
            observed_issue = "error_rate_spike"
            
        # Check metrics data for additional clues
        if 'error' not in metrics_data:
            # Check if error rate data shows a spike
            error_rate_data = metrics_data.get('error_rate', {})
            if error_rate_data and error_rate_data.get('data', {}).get('result'):
                for result in error_rate_data.get('data', {}).get('result', []):
                    if result.get('value') and float(result.get('value', [0, 0])[1]) > 0:
                        observed_issue = "error_rate_spike"
                        break
                        
            # Check if latency is high
            latency_data = metrics_data.get('latency', {})
            if latency_data and latency_data.get('data', {}).get('result'):
                for result in latency_data.get('data', {}).get('result', []):
                    if result.get('value') and float(result.get('value', [0, 0])[1]) > 1:  # >1s latency
                        observed_issue = "high_latency"
                        break
        
        return observed_issue