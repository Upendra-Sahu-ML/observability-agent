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
from dotenv import load_dotenv
from common.tools.root_cause_tools import correlation_analysis, dependency_analysis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class RootCauseAgent:
    def __init__(self, nats_server="nats://nats:4222"):
        # NATS connection parameters
        self.nats_server = nats_server
        self.nats_client = None
        self.js = None  # JetStream context
        
        # OpenAI API key from environment
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY environment variable not set")
        
        # Initialize OpenAI model
        self.llm = LLM(model=os.environ.get("OPENAI_MODEL", "gpt-4"))
        
        # Create a crewAI agent for root cause analysis
        self.root_cause_analyzer = Agent(
            role="Root Cause Analyzer",
            goal="Identify the root cause of system issues by analyzing correlations and dependencies",
            backstory="You are an expert at analyzing system issues and identifying their root causes by examining correlations between events and service dependencies.",
            verbose=True,
            llm=self.llm,
            tools=[correlation_analysis, dependency_analysis]
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
                
                # Only create ROOT_CAUSE stream if it doesn't already exist
                if "ROOT_CAUSE" not in stream_names:
                    await self.js.add_stream(
                        name="ROOT_CAUSE", 
                        subjects=["root_cause_analysis", "root_cause_result"]
                    )
                    logger.info("Created ROOT_CAUSE stream")
                else:
                    logger.info("ROOT_CAUSE stream already exists")
                
            except nats.errors.Error as e:
                # Print error but don't raise - we can still work with existing streams
                logger.warning(f"Stream setup error: {str(e)}")
        
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {str(e)}")
            raise
    
    def _get_current_timestamp(self):
        """Get current timestamp in ISO format"""
        return datetime.utcnow().isoformat() + "Z"
    
    def _create_root_cause_task(self, data):
        """Create a root cause analysis task for the crew"""
        alert_id = data.get("alert_id", "unknown")
        alert_data = data.get("alert", {})
        metric_data = data.get("metrics", {})
        log_data = data.get("logs", {})
        tracing_data = data.get("tracing", {})
        deployment_data = data.get("deployments", {})
        
        # Check if we're working with partial data
        partial_data = data.get("partial_data", False)
        missing_agents = data.get("missing_agents", [])
        
        # Prepare data description
        data_description = f"""
        ## Alert Information
        - Alert ID: {alert_id}
        - Alert Name: {alert_data.get('labels', {}).get('alertname', 'Unknown')}
        - Service: {alert_data.get('labels', {}).get('service', 'Unknown')}
        - Severity: {alert_data.get('labels', {}).get('severity', 'Unknown')}
        - Timestamp: {alert_data.get('startsAt', 'Unknown')}
        
        ## Metric Agent Analysis
        {metric_data.get('analysis', 'No metric data available' if 'metric' in missing_agents else 'No analysis provided')}
        
        ## Log Agent Analysis
        {log_data.get('analysis', 'No log data available' if 'log' in missing_agents else 'No analysis provided')}
        
        ## Tracing Agent Analysis
        {tracing_data.get('analysis', 'No tracing data available' if 'tracing' in missing_agents else 'No analysis provided')}
        
        ## Deployment Agent Analysis
        {deployment_data.get('analysis', 'No deployment data available' if 'deployment' in missing_agents else 'No analysis provided')}
        """
        
        task_instruction = f"""
        Based on the information provided by the specialized agents, determine the most likely root cause of this incident.
        
        {'NOTE: This is partial data. Some agent responses are missing.' if partial_data else ''}
        
        Return your analysis in the following format:
        1. Identified Root Cause - A clear statement of what caused the incident
        2. Confidence Level - How confident you are in this assessment (low, medium, high)
        3. Supporting Evidence - Key data points that support your conclusion
        4. Recommended Actions - Suggested steps to resolve the issue
        5. Prevention - How to prevent similar incidents in the future
        """
        
        task = Task(
            description=data_description + task_instruction,
            agent=self.root_cause_analyzer,
            expected_output="A comprehensive root cause analysis with recommended actions"
        )
        
        return task
    
    async def analyze_root_cause(self, data):
        """Analyze root cause using crewAI"""
        logger.info(f"Analyzing root cause for alert ID: {data.get('alert_id', 'unknown')}")
        
        # Create root cause task
        root_cause_task = self._create_root_cause_task(data)
        
        # Create crew with root cause analyzer
        crew = Crew(
            agents=[self.root_cause_analyzer],
            tasks=[root_cause_task],
            verbose=True
        )
        
        # Execute crew analysis
        result = crew.kickoff()
        
        return result
    
    async def message_handler(self, msg):
        """Handle incoming NATS messages"""
        try:
            # Decode the message data
            data = json.loads(msg.data.decode())
            alert_id = data.get("alert_id", "unknown")
            logger.info(f"[RootCauseAgent] Processing comprehensive data for alert ID: {alert_id}")
            
            # Use crewAI to analyze root cause using the analyses from other agents
            analysis_result = await self.analyze_root_cause(data)
            
            # Prepare and publish result
            result = {
                "agent": "root_cause",
                "root_cause": str(analysis_result),
                "alert_id": alert_id,
                "timestamp": self._get_current_timestamp()
            }
            
            # Publish the result using JetStream
            await self.js.publish("root_cause_result", json.dumps(result).encode())
            logger.info(f"[RootCauseAgent] Published root cause analysis result for alert ID: {alert_id}")
            
            # Acknowledge the message
            await msg.ack()
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            # Negative acknowledge the message so it can be redelivered
            await msg.nak()
    
    async def listen(self):
        """Listen for comprehensive data from the orchestrator and publish root cause analysis"""
        logger.info("[RootCauseAgent] Starting to listen for comprehensive data on 'root_cause_analysis' channel")
        
        # Connect to NATS if not already connected
        if not self.nats_client or not self.nats_client.is_connected:
            await self.connect()
        
        # Create a durable consumer with a queue group for load balancing
        consumer_config = ConsumerConfig(
            durable_name="root_cause_agent",
            deliver_policy=DeliverPolicy.ALL,
            ack_policy="explicit",
            max_deliver=5,  # Retry up to 5 times
            ack_wait=60,    # Wait 60 seconds for acknowledgment
        )
        
        # Subscribe to the stream with the consumer configuration
        await self.js.subscribe(
            "root_cause_analysis",
            cb=self.message_handler,
            queue="root_cause_processors",
            config=consumer_config
        )
        
        logger.info("Subscribed to root_cause_analysis stream")
        
        # Keep the connection alive
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour, or until interrupted