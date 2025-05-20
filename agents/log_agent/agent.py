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
from common.tools.log_tools import (
    LokiQueryTool,
    PodLogTool,
    FileLogTool
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class LogAgent:
    def __init__(self, loki_url="http://loki:3100", log_directory="/var/log", nats_server="nats://nats:4222"):
        # NATS connection parameters
        self.nats_server = nats_server
        self.nats_client = None
        self.js = None  # JetStream context
        
        # Log sources configuration
        self.loki_url = loki_url
        self.log_directory = log_directory
        
        # OpenAI API key from environment
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY environment variable not set")
        
        # Initialize OpenAI model
        self.llm = LLM(model=os.environ.get("OPENAI_MODEL", "gpt-4"))
        
        # Initialize log tools
        self.loki_tool = LokiQueryTool(loki_url=self.loki_url)
        self.pod_log_tool = PodLogTool()
        self.file_log_tool = FileLogTool()
        
        # Create specialized agents for different aspects of log analysis
        self.error_log_analyzer = Agent(
            role="Error Log Analyzer",
            goal="Identify error patterns and exception traces in logs",
            backstory="You are an expert at parsing error messages, exceptions, and stack traces to pinpoint the exact source of application failures and bugs.",
            verbose=True,
            llm=self.llm,
            tools=[
                self.loki_tool.query_logs,
                self.loki_tool.find_error_patterns,
                self.loki_tool.get_service_errors,
                self.pod_log_tool.pod_logs,
                self.file_log_tool.grep_logs
            ]
        )
        
        self.performance_log_analyzer = Agent(
            role="Performance Log Analyzer",
            goal="Identify performance degradation patterns in logs",
            backstory="You specialize in analyzing log entries related to system performance, including latency indicators, slow queries, and resource utilization patterns.",
            verbose=True,
            llm=self.llm,
            tools=[
                self.loki_tool.query_logs,
                self.loki_tool.get_service_latency,
                self.pod_log_tool.get_logs_by_label,
                self.file_log_tool.file_logs
            ]
        )
        
        self.security_log_analyzer = Agent(
            role="Security Log Analyzer",
            goal="Identify potential security incidents in logs",
            backstory="You focus on detecting security-related issues in logs, including unauthorized access attempts, permission issues, and suspicious activity patterns.",
            verbose=True,
            llm=self.llm,
            tools=[
                self.loki_tool.query_logs,
                self.pod_log_tool.get_logs_by_label,
                self.file_log_tool.grep_logs
            ]
        )
        
        self.correlation_analyzer = Agent(
            role="Log Correlation Analyzer",
            goal="Correlate patterns across different log sources",
            backstory="You excel at connecting related events across different log sources and systems to identify cascading failures and root causes.",
            verbose=True,
            llm=self.llm,
            tools=[
                self.loki_tool.query_logs,
                self.pod_log_tool.list_pods,
                self.file_log_tool.list_log_files
            ]
        )
        
        # Keep the original log analyzer for backward compatibility
        self.log_analyzer = Agent(
            role="Log Analyzer",
            goal="Analyze log data to identify patterns and anomalies",
            backstory="You are an expert at analyzing application logs and identifying error patterns that could indicate system issues.",
            verbose=True,
            llm=self.llm,
            tools=[
                # Loki query tools
                self.loki_tool.query_logs,
                self.loki_tool.find_error_patterns,
                self.loki_tool.get_service_latency,
                self.loki_tool.get_service_errors,
                
                # Kubernetes pod log tools
                self.pod_log_tool.pod_logs,
                self.pod_log_tool.get_logs_by_label,
                self.pod_log_tool.list_pods,
                
                # File log tools
                self.file_log_tool.file_logs,
                self.file_log_tool.grep_logs,
                self.file_log_tool.list_log_files
            ]
        )
    
    def _determine_observed_issue(self, alert, logs_data, analysis_result):
        """Determine the type of log issue observed based on the analysis"""
        alert_name = alert.get("labels", {}).get("alertname", "").lower()
        
        # Try to extract issue type from analysis result
        result_str = str(analysis_result).lower()
        
        if "out of memory" in result_str or "oom" in result_str:
            return "Out of memory error"
        elif "exception" in result_str or "error" in result_str:
            if "connection" in result_str or "timeout" in result_str:
                return "Connection or timeout error"
            elif "database" in result_str or "sql" in result_str:
                return "Database error"
            else:
                return "Application exception"
        elif "warning" in result_str:
            return "Application warning"
        elif "timeout" in result_str:
            return "Request timeout"
        elif "restart" in result_str or "crash" in result_str:
            return "Service restart or crash"
        else:
            # Fall back to alert name based categorization
            if "error" in alert_name:
                return "Error rate increase"
            elif "latency" in alert_name:
                return "Latency issue indicated in logs"
            else:
                return "Log anomaly detected"
    
    def _create_specialized_log_tasks(self, alert):
        """Create specialized log analysis tasks for each analyzer"""
        alert_id = alert.get("alert_id", "unknown")
        alert_name = alert.get("labels", {}).get("alertname", "Unknown Alert")
        service = alert.get("labels", {}).get("service", "")
        namespace = alert.get("labels", {}).get("namespace", "default")
        pod = alert.get("labels", {}).get("pod", "")
        
        # Determine time range - default to 15 min before alert
        time_range = "-15m"
        
        # Base context information that all analyzers will use
        base_context = f"""
        Alert: {alert_name} (ID: {alert_id})
        Service: {service}
        Namespace: {namespace}
        Pod: {pod}
        Time range to analyze: {time_range} to now
        """
        
        # Error analysis task
        error_task = Task(
            description=base_context + """
            Focus on analyzing error and exception patterns in the logs:
            
            1. Identify all error messages, exceptions, and stack traces
            2. Categorize errors by type and severity
            3. Look for patterns in error frequency or timing
            4. Identify the specific components or code paths that are failing
            5. Determine if errors correlate with the alert timing
            
            Provide a detailed analysis of error patterns found, their likely causes, and suggestions for further investigation.
            """,
            agent=self.error_log_analyzer,
            expected_output="A detailed analysis of error patterns in the logs"
        )
        
        # Performance analysis task
        performance_task = Task(
            description=base_context + """
            Focus on analyzing performance-related log entries:
            
            1. Identify slow operations, high latency indicators, and timeouts
            2. Look for resource constraints (memory, CPU, connections, etc.)
            3. Analyze timing patterns and performance degradation trends
            4. Identify specific endpoints, queries, or operations that are slow
            5. Determine if performance issues correlate with the alert timing
            
            Provide a detailed analysis of performance patterns found, their likely causes, and suggestions for further investigation.
            """,
            agent=self.performance_log_analyzer,
            expected_output="A detailed analysis of performance-related patterns in the logs"
        )
        
        # Security analysis task
        security_task = Task(
            description=base_context + """
            Focus on analyzing security-related log entries:
            
            1. Look for authentication failures or access denied messages
            2. Identify any permission issues or authorization failures
            3. Check for unusual access patterns or suspicious activity
            4. Look for configuration issues that might impact security
            5. Determine if security issues correlate with the alert timing
            
            Provide a detailed analysis of security patterns found, their likely implications, and suggestions for further investigation.
            """,
            agent=self.security_log_analyzer,
            expected_output="A detailed analysis of security-related patterns in the logs"
        )
        
        # Correlation analysis task
        correlation_task = Task(
            description=base_context + """
            After the other analysts have completed their work, review their findings and:
            
            1. Identify connections between different types of log entries
            2. Correlate events across different log sources
            3. Establish a likely sequence of events leading to the alert
            4. Synthesize the findings into a coherent narrative
            5. Determine the most likely primary issue based on all log evidence
            
            Provide a comprehensive correlation analysis that ties together the findings from all log sources and types.
            """,
            agent=self.correlation_analyzer,
            expected_output="A correlation analysis connecting patterns across different log sources"
        )
        
        return [error_task, performance_task, security_task, correlation_task], time_range
    
    def _create_log_analysis_task(self, alert):
        """Create a log analysis task for the crew (backward compatibility)"""
        alert_id = alert.get("alert_id", "unknown")
        alert_name = alert.get("labels", {}).get("alertname", "Unknown Alert")
        service = alert.get("labels", {}).get("service", "")
        namespace = alert.get("labels", {}).get("namespace", "default")
        pod = alert.get("labels", {}).get("pod", "")
        
        # Determine time range - default to 15 min before alert
        time_range = "-15m"
        
        task = Task(
            description=f"""
            Analyze logs for alert: {alert_name} (ID: {alert_id})
            
            Service: {service}
            Namespace: {namespace}
            Pod: {pod}
            
            Time range to analyze: {time_range} to now
            
            Perform the following:
            1. Query Loki for logs related to the service
            2. If the pod name is available, get Kubernetes pod logs
            3. Check relevant application log files
            
            In your analysis, focus on:
            1. Error messages and stack traces
            2. Warning messages that might indicate issues
            3. Timing of errors relative to the alert
            4. Patterns or trends in log volume or error types
            5. Correlations between different error messages
            
            Return a comprehensive analysis of what the logs show, potential causes, and any recommended further investigation.
            """,
            agent=self.log_analyzer,
            expected_output="A detailed analysis of the logs related to the alert"
        )
        
        return task, time_range
    
    async def analyze_logs(self, alert):
        """Analyze logs using multi-agent crewAI"""
        logger.info(f"Analyzing logs for alert ID: {alert.get('alert_id', 'unknown')}")
        
        # Create specialized log analysis tasks
        tasks, time_range = self._create_specialized_log_tasks(alert)
        
        # Create crew with specialized analyzers
        crew = Crew(
            agents=[
                self.error_log_analyzer,
                self.performance_log_analyzer,
                self.security_log_analyzer,
                self.correlation_analyzer
            ],
            tasks=tasks,
            verbose=True,
            process=process.Sequential()
        )
        
        # Execute crew analysis
        result = crew.kickoff()
        
        # Return both the analysis result and metadata
        logs_data = {
            "time_range": time_range,
            "service": alert.get("labels", {}).get("service", ""),
            "pod": alert.get("labels", {}).get("pod", "")
        }
        
        return result, logs_data
    
    async def connect(self):
        """Establish connection to NATS server and set up JetStream context"""
        logger.info(f"[LogAgent] Connecting to NATS server: {self.nats_server}")
        
        try:
            # Connect to NATS server
            self.nats_client = await nats.connect(self.nats_server)
            logger.info("[LogAgent] Connected to NATS server")
            
            # Initialize JetStream context
            self.js = self.nats_client.jetstream()
            logger.info("[LogAgent] JetStream context initialized")
            
            return True
        except Exception as e:
            logger.error(f"[LogAgent] Failed to connect to NATS: {str(e)}", exc_info=True)
            raise
    
    async def message_handler(self, msg):
        """Handle incoming NATS messages"""
        try:
            # Parse the alert data
            alert = json.loads(msg.data.decode())
            logger.info(f"[LogAgent] Processing alert: {alert.get('alert_id', 'unknown')}")
            
            # Use crewAI to analyze the logs
            analysis_result, logs_data = await self.analyze_logs(alert)
            
            # Determine what type of log issue was observed
            observed_issue = self._determine_observed_issue(alert, logs_data, analysis_result)
            
            # Prepare result for the orchestrator
            result = {
                "agent": "log", 
                "observed": observed_issue,
                "analysis": str(analysis_result),
                "alert_id": alert.get("alert_id", "unknown"),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            logger.info(f"[LogAgent] Sending analysis for alert ID: {result['alert_id']}")
            
            # Publish result to orchestrator
            await self.js.publish("orchestrator_response", json.dumps(result).encode())
            logger.info(f"[LogAgent] Published analysis result for alert ID: {result['alert_id']}")
            
            # Acknowledge the message
            await msg.ack()
            
        except Exception as e:
            logger.error(f"[LogAgent] Error processing message: {str(e)}", exc_info=True)
            # Negative acknowledge the message so it can be redelivered
            await msg.nak()
    
    async def listen(self):
        """
        Listen for alert messages on the log_agent subject.
        This method establishes a connection to NATS if not already connected,
        creates durable consumers, and sets up message handlers.
        """
        logger.info("[LogAgent] Starting to listen for alerts")
        
        if not self.nats_client or not self.nats_client.is_connected:
            await self.connect()
        
        try:
            # Ensure the alerts stream exists with proper configuration
            stream_config = {
                "name": "ALERTS",
                "subjects": ["alerts.>"],
                "retention": "limits",
                "max_consumers": -1,
                "max_msgs_per_subject": 10000,
                "max_msgs": 100000,
                "max_bytes": 1024 * 1024 * 1024,  # 1GB
                "discard": "old",
                "max_age": 86400 * 30,  # 30 days
                "storage": "file",
                "num_replicas": 1,
            }
            
            try:
                # Try to get the stream info first to see if it exists
                await self.js.stream_info("ALERTS")
                logger.info("[LogAgent] Connected to existing ALERTS stream")
            except Exception:
                # Create the stream if it doesn't exist
                await self.js.add_stream(**stream_config)
                logger.info("[LogAgent] Created ALERTS stream with configuration")
            
            # Consumer configuration
            consumer_config = ConsumerConfig(
                durable_name="log_agent_consumer",
                deliver_policy=DeliverPolicy.ALL,
                ack_wait=60,  # 60 seconds
                max_deliver=10,  # Maximum redelivery attempts
            )
            
            # Create durable consumer for the log agent
            await self.js.subscribe(
                "alerts.log",
                cb=self.message_handler,
                durable="log_agent_consumer",
                config=consumer_config,
                manual_ack=True
            )
            
            logger.info("[LogAgent] Subscribed to alerts.log subject")
            
            # Keep the application running
            while True:
                await asyncio.sleep(600)  # Sleep for 10 minutes
                logger.info("[LogAgent] Still listening for alerts")
                
        except Exception as e:
            logger.error(f"[LogAgent] Error while listening: {str(e)}", exc_info=True)
            # Try to reconnect if there's an issue
            if self.nats_client and self.nats_client.is_connected:
                await self.nats_client.close()
            self.nats_client = None
            self.js = None
            # Wait a bit before trying to reconnect
            await asyncio.sleep(5)
            # Recursive call to try listening again
            await self.listen()