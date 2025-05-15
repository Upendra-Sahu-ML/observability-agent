import os
import json
import logging
import asyncio
import nats
from nats.js.api import ConsumerConfig, DeliverPolicy
from datetime import datetime
from crewai import Agent, Task, Crew
from crewai.llm import LLM
from crewai.tools import tool
from crewai import process
from dotenv import load_dotenv
from common.tools.metric_tools import (
    PrometheusQueryTool,
    MetricAnalysisTool
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class MetricAgent:
    def __init__(self, prometheus_url="http://prometheus:9090", nats_server="nats://nats:4222"):
        # NATS connection parameters
        self.nats_server = nats_server
        self.nats_client = None
        self.js = None  # JetStream context
        
        # Prometheus configuration
        self.prometheus_url = prometheus_url
        
        # OpenAI API key from environment
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY environment variable not set")
        
        # Initialize OpenAI model
        self.llm = LLM(model=os.environ.get("OPENAI_MODEL", "gpt-4"))
        
        # Initialize metric tools
        self.prometheus_tool = PrometheusQueryTool(prometheus_url=self.prometheus_url)
        self.metric_analysis_tool = MetricAnalysisTool()
        
        # Create specialized agents for different aspects of metric analysis
        self.system_metrics_analyst = Agent(
            role="System Metrics Analyst",
            goal="Analyze system-level metrics to identify resource constraints and bottlenecks",
            backstory="You specialize in analyzing CPU, memory, disk, and network metrics. You can quickly identify resource exhaustion and saturation points in infrastructure.",
            verbose=True,
            llm=self.llm,
            tools=[
                self.prometheus_tool.query_metrics,
                self.prometheus_tool.get_cpu_metrics,
                self.prometheus_tool.get_memory_metrics,
                self.metric_analysis_tool.analyze_threshold
            ]
        )
        
        self.application_metrics_analyst = Agent(
            role="Application Metrics Analyst",
            goal="Analyze application-specific metrics to identify service issues",
            backstory="You focus on application metrics like request rates, error rates, and latency. You can pinpoint service degradation and application-level issues.",
            verbose=True,
            llm=self.llm,
            tools=[
                self.prometheus_tool.query_metrics,
                self.prometheus_tool.get_error_rate,
                self.prometheus_tool.get_service_health,
                self.metric_analysis_tool.analyze_metrics
            ]
        )
        
        self.trend_analyst = Agent(
            role="Metric Trend Analyst",
            goal="Analyze metric trends and patterns over time",
            backstory="You excel at spotting gradual changes, seasonality, and long-term patterns in metrics that might indicate developing problems.",
            verbose=True,
            llm=self.llm,
            tools=[
                self.prometheus_tool.query_metrics,
                self.metric_analysis_tool.analyze_trend
            ]
        )
        
        self.anomaly_detector = Agent(
            role="Metric Anomaly Detector",
            goal="Detect unusual patterns and outliers in metrics",
            backstory="You specialize in identifying abnormal metric behavior, sudden spikes, drops, and statistical outliers that could indicate incidents.",
            verbose=True,
            llm=self.llm,
            tools=[
                self.prometheus_tool.query_metrics,
                self.metric_analysis_tool.analyze_anomalies
            ]
        )
        
        # Keep the original metric analyzer for backward compatibility
        self.metric_analyzer = Agent(
            role="Metric Analyzer",
            goal="Analyze metric data to identify patterns and anomalies",
            backstory="You are an expert at analyzing system metrics and identifying patterns that could indicate system issues.",
            verbose=True,
            llm=self.llm,
            tools=[
                # Prometheus query tools
                self.prometheus_tool.query_metrics,
                self.prometheus_tool.get_cpu_metrics,
                self.prometheus_tool.get_memory_metrics,
                self.prometheus_tool.get_error_rate,
                self.prometheus_tool.get_service_health,
                
                # Metric analysis tools
                self.metric_analysis_tool.analyze_trend,
                self.metric_analysis_tool.analyze_anomalies,
                self.metric_analysis_tool.analyze_threshold,
                self.metric_analysis_tool.analyze_metrics
            ]
        )
    
    async def connect(self):
        """Connect to NATS server and set up JetStream"""
        try:
            # Connect to NATS server
            self.nats_client = await nats.connect(self.nats_server)
            logger.info(f"Connected to NATS server at {self.nats_server}")
            
            # Create JetStream context
            self.js = self.nats_client.jetstream()
            
            # Check if streams exist, don't try to create them if they do
            try:
                # Look up streams first
                streams = []
                try:
                    streams = await self.js.streams_info()
                except Exception as e:
                    logger.warning(f"Failed to get streams info: {str(e)}")

                # Get stream names
                stream_names = [stream.config.name for stream in streams]
                
                # Only create AGENT_TASKS stream if it doesn't already exist
                if "AGENT_TASKS" not in stream_names:
                    await self.js.add_stream(
                        name="AGENT_TASKS", 
                        subjects=["metric_agent"]
                    )
                    logger.info("Created AGENT_TASKS stream")
                else:
                    logger.info("AGENT_TASKS stream already exists")
                
                # Only create RESPONSES stream if it doesn't already exist
                if "RESPONSES" not in stream_names:
                    await self.js.add_stream(
                        name="RESPONSES", 
                        subjects=["orchestrator_response"]
                    )
                    logger.info("Created RESPONSES stream")
                else:
                    logger.info("RESPONSES stream already exists")
                
            except nats.errors.Error as e:
                # Print error but don't raise - we can still work with existing streams
                logger.warning(f"Stream setup error: {str(e)}")
        
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {str(e)}")
            raise
    
    def _determine_observed_issue(self, alert, metrics_data):
        """Determine the type of metric issue observed based on the alert and metrics"""
        alert_name = alert.get("labels", {}).get("alertname", "").lower()
        
        if "cpu" in alert_name:
            return "CPU utilization issue"
        elif "memory" in alert_name:
            return "Memory consumption issue"
        elif "disk" in alert_name:
            return "Disk space issue"
        elif "latency" in alert_name or "response" in alert_name:
            return "Response time degradation"
        elif "error" in alert_name or "failure" in alert_name:
            return "Error rate increase"
        elif "saturation" in alert_name:
            return "System saturation"
        else:
            return "Unspecified metric anomaly"
    
    def _get_time_range(self, alert):
        """Get appropriate time range for metric queries based on alert"""
        # Default to 30 minutes before alert
        minutes_before = 30
        
        # If we have the alert start time, use that
        start_time = alert.get("startsAt")
        if start_time:
            # Convert to proper format for Prometheus
            # This is a simplification - in production code you would want to handle
            # proper time conversion from ISO format to Prometheus format
            return f"-{minutes_before}m"
        
        # Default fallback
        return f"-{minutes_before}m"
    
    def _create_specialized_metrics_tasks(self, alert):
        """Create specialized metrics analysis tasks for each analyst"""
        alert_id = alert.get("alert_id", "unknown")
        alert_name = alert.get("labels", {}).get("alertname", "Unknown Alert")
        service = alert.get("labels", {}).get("service", "")
        namespace = alert.get("labels", {}).get("namespace", "default")
        instance = alert.get("labels", {}).get("instance", "")
        
        # Time range to analyze
        time_range = self._get_time_range(alert)
        
        # Base context information that all analyzers will use
        base_context = f"""
        Alert: {alert_name} (ID: {alert_id})
        Service: {service}
        Namespace: {namespace}
        Instance: {instance}
        Time range to analyze: {time_range} to now
        """
        
        # Determine which metrics to query based on alert name
        system_metrics = []
        application_metrics = []
        
        # System metrics to analyze
        if "cpu" in alert_name.lower() or "memory" in alert_name.lower() or "disk" in alert_name.lower():
            system_metrics.extend([
                f'cpu_usage_total{{service="{service}"}}',
                f'memory_usage{{service="{service}"}}',
                f'memory_limit{{service="{service}"}}',
                f'disk_usage{{service="{service}"}}',
                f'node_load{{instance="{instance}"}}'
            ])
        else:
            system_metrics.extend([
                f'up{{service="{service}"}}',
                f'cpu_usage_total{{service="{service}"}}',
                f'memory_usage{{service="{service}"}}'
            ])
        
        # Application metrics to analyze
        if "latency" in alert_name.lower() or "response" in alert_name.lower() or "error" in alert_name.lower():
            application_metrics.extend([
                f'http_request_duration_seconds{{service="{service}"}}',
                f'http_requests_total{{service="{service}"}}',
                f'http_errors_total{{service="{service}"}}',
                f'request_latency{{service="{service}"}}'
            ])
        else:
            application_metrics.extend([
                f'http_requests_total{{service="{service}"}}',
                f'http_errors_total{{service="{service}"}}'
            ])
        
        # System metrics analysis task
        system_task = Task(
            description=base_context + f"""
            Focus on analyzing system-level metrics:
            
            Use these Prometheus queries to gather data:
            {', '.join(system_metrics)}
            
            Specifically look for:
            1. Resource exhaustion (CPU, memory, disk)
            2. System saturation points
            3. Infrastructure-level bottlenecks
            4. Hardware or OS-level constraints
            
            Provide a detailed analysis of system metrics, focusing on resource utilization and constraints.
            """,
            agent=self.system_metrics_analyst,
            expected_output="A detailed analysis of system-level metrics"
        )
        
        # Application metrics analysis task
        application_task = Task(
            description=base_context + f"""
            Focus on analyzing application-level metrics:
            
            Use these Prometheus queries to gather data:
            {', '.join(application_metrics)}
            
            Specifically look for:
            1. Error rates and patterns
            2. Latency increases or anomalies
            3. Request rate changes
            4. Service health indicators
            
            Provide a detailed analysis of application metrics, focusing on service behavior and health.
            """,
            agent=self.application_metrics_analyst,
            expected_output="A detailed analysis of application-level metrics"
        )
        
        # Trend analysis task
        trend_task = Task(
            description=base_context + """
            Focus on analyzing metric trends over time:
            
            Specifically look for:
            1. Gradual increases or decreases
            2. Cyclical patterns or seasonality
            3. Long-term trends that may indicate developing issues
            4. Changes in patterns compared to normal baseline
            
            Provide a detailed analysis of metric trends, focusing on how metrics have changed over time.
            """,
            agent=self.trend_analyst,
            expected_output="A detailed analysis of metric trends over time"
        )
        
        # Anomaly detection task
        anomaly_task = Task(
            description=base_context + """
            Focus on detecting anomalies in metrics:
            
            Specifically look for:
            1. Sudden spikes or drops
            2. Outliers and statistical anomalies
            3. Unusual combinations of metric values
            4. Deviation from expected patterns
            
            Provide a detailed analysis of metric anomalies, focusing on unusual or unexpected behavior.
            """,
            agent=self.anomaly_detector,
            expected_output="A detailed analysis of metric anomalies"
        )
        
        # Return all specialized tasks and metadata
        metrics_queries = system_metrics + application_metrics
        
        return [system_task, application_task, trend_task, anomaly_task], metrics_queries, time_range
    
    def _create_metrics_analysis_task(self, alert):
        """Create a metrics analysis task for the crew (backward compatibility)"""
        alert_id = alert.get("alert_id", "unknown")
        alert_name = alert.get("labels", {}).get("alertname", "Unknown Alert")
        service = alert.get("labels", {}).get("service", "")
        namespace = alert.get("labels", {}).get("namespace", "default")
        instance = alert.get("labels", {}).get("instance", "")
        
        # Determine which metrics to query based on alert name
        metrics_queries = []
        
        if "cpu" in alert_name.lower():
            metrics_queries.extend([
                f'cpu_usage_total{{service="{service}"}}',
                f'cpu_throttling{{service="{service}"}}'
            ])
        elif "memory" in alert_name.lower():
            metrics_queries.extend([
                f'memory_usage{{service="{service}"}}',
                f'memory_limit{{service="{service}"}}'
            ])
        elif "disk" in alert_name.lower():
            metrics_queries.extend([
                f'disk_usage{{service="{service}"}}',
                f'disk_io{{service="{service}"}}'
            ])
        elif "latency" in alert_name.lower() or "response" in alert_name.lower():
            metrics_queries.extend([
                f'http_request_duration_seconds{{service="{service}"}}',
                f'http_requests_total{{service="{service}"}}'
            ])
        else:
            # Default metrics for any service
            metrics_queries.extend([
                f'up{{service="{service}"}}',
                f'http_requests_total{{service="{service}"}}'
            ])
        
        # Time range to analyze
        time_range = self._get_time_range(alert)
        
        task = Task(
            description=f"""
            Analyze the following metrics for alert: {alert_name} (ID: {alert_id})
            
            Service: {service}
            Namespace: {namespace}
            Instance: {instance}
            
            Use these Prometheus queries to gather data:
            {', '.join(metrics_queries)}
            
            Time range to analyze: {time_range} to now
            
            Specifically look for:
            1. Sudden spikes or drops in values
            2. Gradual increases that cross thresholds
            3. Correlations between different metrics
            4. Patterns that might indicate the root cause
            
            Return a comprehensive analysis of what the metrics show, potential causes, and any recommended further investigation.
            """,
            agent=self.metric_analyzer,
            expected_output="A detailed analysis of the metrics related to the alert"
        )
        
        return task, metrics_queries, time_range
    
    async def analyze_metrics(self, alert):
        """Analyze metrics using multi-agent crewAI"""
        logger.info(f"Analyzing metrics for alert ID: {alert.get('alert_id', 'unknown')}")
        
        # Create specialized metrics analysis tasks
        tasks, metrics_queries, time_range = self._create_specialized_metrics_tasks(alert)
        
        # Create crew with specialized analyzers
        crew = Crew(
            agents=[
                self.system_metrics_analyst,
                self.application_metrics_analyst,
                self.trend_analyst,
                self.anomaly_detector
            ],
            tasks=tasks,
            verbose=True,
            process=process.MapReduce()  # Run analyses in parallel and combine results
        )
        
        # Execute crew analysis
        result = crew.kickoff()
        
        # Return both the analysis result and metadata
        metrics_data = {
            "queries": metrics_queries,
            "time_range": time_range,
            "service": alert.get("labels", {}).get("service", ""),
            "instance": alert.get("labels", {}).get("instance", "")
        }
        
        return result, metrics_data
    
    async def message_handler(self, msg):
        """Handle incoming NATS messages"""
        try:
            # Parse the alert data
            alert = json.loads(msg.data.decode())
            logger.info(f"[MetricAgent] Processing alert: {alert.get('alert_id', 'unknown')}")
            
            # Use crewAI to analyze the metrics
            analysis_result, metrics_data = await self.analyze_metrics(alert)
            
            # Determine what type of metric issue was observed based on the alert and metrics
            observed_issue = self._determine_observed_issue(alert, metrics_data)
            
            # Prepare result for the orchestrator
            result = {
                "agent": "metric", 
                "observed": observed_issue,
                "analysis": str(analysis_result),
                "alert_id": alert.get("alert_id", "unknown"),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            logger.info(f"[MetricAgent] Sending analysis for alert ID: {result['alert_id']}")
            
            # Publish result to orchestrator
            await self.js.publish("orchestrator_response", json.dumps(result).encode())
            logger.info(f"[MetricAgent] Published analysis result for alert ID: {result['alert_id']}")
            
            # Acknowledge the message
            await msg.ack()
            
        except Exception as e:
            logger.error(f"[MetricAgent] Error processing message: {str(e)}", exc_info=True)
            # Negative acknowledge the message so it can be redelivered
            await msg.nak()
    
    async def listen(self):
        """Listen for alerts from the orchestrator using NATS JetStream"""
        logger.info("[MetricAgent] Starting to listen for alerts")
        
        # Connect to NATS if not already connected
        if not self.nats_client or not self.nats_client.is_connected:
            await self.connect()
        
        # Create a durable consumer with a queue group for load balancing
        consumer_config = ConsumerConfig(
            durable_name="metric_agent",
            deliver_policy=DeliverPolicy.ALL,
            ack_policy="explicit",
            max_deliver=5,  # Retry up to 5 times
            ack_wait=60,    # Wait 60 seconds for acknowledgment
        )
        
        # Subscribe to the stream with the consumer configuration
        await self.js.subscribe(
            "metric_agent",
            cb=self.message_handler,
            queue="metric_processors",
            config=consumer_config
        )
        
        logger.info("[MetricAgent] Subscribed to metric_agent stream")
        
        # Keep the connection alive
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour, or until interrupted