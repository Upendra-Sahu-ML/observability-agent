"""
Tracing agent for analyzing distributed trace data
"""
import os
import json
import logging
import asyncio
import nats
from nats.js.api import ConsumerConfig, DeliverPolicy
from datetime import datetime
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from langchain.tools import BaseTool, StructuredTool, tool
from dotenv import load_dotenv
from common.tools.tempo_tools import (
    TempoQueryTool,
    TempoTraceSearchTool,
    TempoServicePerformanceTool
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class TracingAgent:
    def __init__(self, tempo_url="http://tempo:3100", nats_server="nats://nats:4222"):
        # NATS connection parameters
        self.nats_server = nats_server
        self.nats_client = None
        self.js = None  # JetStream context
        
        # Tempo URL
        self.tempo_url = tempo_url
        
        # OpenAI API key from environment
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY environment variable not set")
        
        # Initialize OpenAI model
        self.llm = ChatOpenAI(model=os.environ.get("OPENAI_MODEL", "gpt-4"))
        
        # Initialize Tempo tools
        self.query_tool = TempoQueryTool(tempo_url=self.tempo_url)
        self.trace_search_tool = TempoTraceSearchTool(tempo_url=self.tempo_url)
        self.performance_tool = TempoServicePerformanceTool(tempo_url=self.tempo_url)
        
        # Convert functions to proper LangChain tools
        self.langchain_tools = [
            StructuredTool.from_function(self.query_tool.execute),
            StructuredTool.from_function(self.trace_search_tool.execute),
            StructuredTool.from_function(self.performance_tool.execute)
        ]
        
        # Create a crewAI agent for trace analysis
        self.trace_analyzer = Agent(
            role="Tracing Analyst",
            goal="Analyze distributed traces to identify performance bottlenecks and errors",
            backstory="You are an expert at analyzing distributed traces and identifying issues in service communication and performance.",
            verbose=True,
            llm=self.llm,
            tools=self.langchain_tools
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
                        subjects=["tracing_agent"]
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
    
    def _determine_observed_issue(self, alert, tracing_data, analysis_result):
        """Determine the type of tracing issue observed based on the analysis"""
        alert_name = alert.get("labels", {}).get("alertname", "").lower()
        
        # Try to extract issue type from analysis result
        result_str = str(analysis_result).lower()
        
        if "latency" in result_str or "slow" in result_str:
            return "Service latency issues"
        elif "error" in result_str or "exception" in result_str:
            return "Service errors in traces"
        elif "timeout" in result_str:
            return "Request timeouts"
        elif "dependency" in result_str:
            return "Dependency failure"
        elif "bottleneck" in result_str:
            return "Performance bottleneck"
        else:
            # Fall back to alert name based categorization
            if "latency" in alert_name:
                return "Service latency alert"
            elif "error" in alert_name:
                return "Error rate increase"
            else:
                return "Trace anomaly detected"
    
    def _create_trace_analysis_task(self, alert):
        """Create a trace analysis task for the crew"""
        alert_id = alert.get("alert_id", "unknown")
        alert_name = alert.get("labels", {}).get("alertname", "Unknown Alert")
        service = alert.get("labels", {}).get("service", "")
        
        # Determine time range - default to 15 min before alert
        time_range = "-15m"
        
        task = Task(
            description=f"""
            Analyze distributed traces for alert: {alert_name} (ID: {alert_id})
            
            Service: {service}
            
            Time range to analyze: {time_range} to now
            
            Perform the following:
            1. Search for traces related to the affected service
            2. Analyze the performance of the service and its dependencies
            3. Look for error traces and failure patterns
            
            In your analysis, focus on:
            1. Services with high latency
            2. Error codes and exception patterns
            3. Bottlenecks in service communication
            4. Changes in service performance over time
            5. Correlations between trace patterns and the alert
            
            Return a comprehensive analysis of what the traces show, potential causes, and any recommended further investigation.
            """,
            agent=self.trace_analyzer,
            expected_output="A detailed analysis of the distributed traces related to the alert"
        )
        
        return task, time_range
    
    async def analyze_traces(self, alert):
        """Analyze traces using crewAI"""
        logger.info(f"Analyzing traces for alert ID: {alert.get('alert_id', 'unknown')}")
        
        # Create trace analysis task
        task, time_range = self._create_trace_analysis_task(alert)
        
        # Create crew with trace analyzer
        crew = Crew(
            agents=[self.trace_analyzer],
            tasks=[task],
            verbose=True
        )
        
        # Execute crew analysis
        result = crew.kickoff()
        
        # Return both the analysis result and some metadata about what was analyzed
        tracing_data = {
            "time_range": time_range,
            "service": alert.get("labels", {}).get("service", "")
        }
        
        return result, tracing_data
    
    async def message_handler(self, msg):
        """Handle incoming NATS messages"""
        try:
            # Parse the alert data
            alert = json.loads(msg.data.decode())
            logger.info(f"[TracingAgent] Processing alert: {alert.get('alert_id', 'unknown')}")
            
            # Use crewAI to analyze the traces
            analysis_result, tracing_data = await self.analyze_traces(alert)
            
            # Determine what type of tracing issue was observed
            observed_issue = self._determine_observed_issue(alert, tracing_data, analysis_result)
            
            # Prepare result for the orchestrator
            result = {
                "agent": "tracing", 
                "observed": observed_issue,
                "analysis": str(analysis_result),
                "alert_id": alert.get("alert_id", "unknown"),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            logger.info(f"[TracingAgent] Sending analysis for alert ID: {result['alert_id']}")
            
            # Publish result to orchestrator
            await self.js.publish("orchestrator_response", json.dumps(result).encode())
            logger.info(f"[TracingAgent] Published analysis result for alert ID: {result['alert_id']}")
            
            # Acknowledge the message
            await msg.ack()
            
        except Exception as e:
            logger.error(f"[TracingAgent] Error processing message: {str(e)}", exc_info=True)
            # Negative acknowledge the message so it can be redelivered
            await msg.nak()
    
    async def listen(self):
        """Listen for alerts from the orchestrator using NATS JetStream"""
        logger.info("[TracingAgent] Starting to listen for alerts")
        
        # Connect to NATS if not already connected
        if not self.nats_client or not self.nats_client.is_connected:
            await self.connect()
        
        # Create a durable consumer with a queue group for load balancing
        consumer_config = ConsumerConfig(
            durable_name="tracing_agent",
            deliver_policy=DeliverPolicy.ALL,
            ack_policy="explicit",
            max_deliver=5,  # Retry up to 5 times
            ack_wait=60,    # Wait 60 seconds for acknowledgment
        )
        
        # Subscribe to the stream with the consumer configuration
        await self.js.subscribe(
            "tracing_agent",
            cb=self.message_handler,
            queue="tracing_processors",
            config=consumer_config
        )
        
        logger.info("[TracingAgent] Subscribed to tracing_agent stream")
        
        # Keep the connection alive
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour, or until interrupted