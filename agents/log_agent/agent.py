import os
import json
import logging
import asyncio
import nats
from nats.js.api import ConsumerConfig, DeliverPolicy
from datetime import datetime
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
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
        self.llm = ChatOpenAI(model=os.environ.get("OPENAI_MODEL", "gpt-4"))
        
        # Initialize log tools
        self.loki_tool = LokiQueryTool(loki_url=self.loki_url)
        self.pod_log_tool = PodLogTool()
        self.file_log_tool = FileLogTool(log_directory=self.log_directory)
        
        # Create a crewAI agent for log analysis
        self.log_analyzer = Agent(
            role="Log Analyzer",
            goal="Analyze log data to identify patterns and anomalies",
            backstory="You are an expert at analyzing application logs and identifying error patterns that could indicate system issues.",
            verbose=True,
            llm=self.llm,
            tools=[
                self.loki_tool.execute, 
                self.pod_log_tool.execute,
                self.file_log_tool.execute
            ]
        )
    
    async def connect(self):
        """Connect to NATS server and set up JetStream"""
        # Connect to NATS server
        self.nats_client = await nats.connect(self.nats_server)
        logger.info(f"Connected to NATS server at {self.nats_server}")
        
        # Create JetStream context
        self.js = self.nats_client.jetstream()
        
        # Ensure streams exist
        try:
            # Create stream for agent tasks
            await self.js.add_stream(
                name="AGENT_TASKS", 
                subjects=["log_agent"]
            )
            logger.info("Created or confirmed AGENT_TASKS stream")
            
            # Create stream for responses
            await self.js.add_stream(
                name="RESPONSES", 
                subjects=["orchestrator_response"]
            )
            logger.info("Created or confirmed RESPONSES stream")
            
        except nats.errors.Error as e:
            # Stream might already exist
            logger.info(f"Stream setup: {str(e)}")
    
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
    
    def _create_log_analysis_task(self, alert):
        """Create a log analysis task for the crew"""
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
        """Analyze logs using crewAI"""
        logger.info(f"Analyzing logs for alert ID: {alert.get('alert_id', 'unknown')}")
        
        # Create log analysis task
        task, time_range = self._create_log_analysis_task(alert)
        
        # Create crew with log analyzer
        crew = Crew(
            agents=[self.log_analyzer],
            tasks=[task],
            verbose=True
        )
        
        # Execute crew analysis
        result = crew.kickoff()
        
        # Return both the analysis result and some metadata about what was analyzed
        logs_data = {
            "time_range": time_range,
            "service": alert.get("labels", {}).get("service", ""),
            "pod": alert.get("labels", {}).get("pod", "")
        }
        
        return result, logs_data
    
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
        """Listen for alerts from the orchestrator using NATS JetStream"""
        logger.info("[LogAgent] Starting to listen for alerts")
        
        # Connect to NATS if not already connected
        if not self.nats_client or not self.nats_client.is_connected:
            await self.connect()
        
        # Create a durable consumer with a queue group for load balancing
        consumer_config = ConsumerConfig(
            durable_name="log_agent",
            deliver_policy=DeliverPolicy.ALL,
            ack_policy="explicit",
            max_deliver=5,  # Retry up to 5 times
            ack_wait=60,    # Wait 60 seconds for acknowledgment
        )
        
        # Subscribe to the stream with the consumer configuration
        await self.js.subscribe(
            "log_agent",
            cb=self.message_handler,
            queue="log_processors",
            config=consumer_config
        )
        
        logger.info("[LogAgent] Subscribed to log_agent stream")
        
        # Keep the connection alive
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour, or until interrupted