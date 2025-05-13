import os
import json
import logging
import asyncio
import nats
from nats.js.api import ConsumerConfig, DeliverPolicy
from datetime import datetime
import jinja2
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from langchain.tools import BaseTool, StructuredTool, tool
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class PostmortemAgent:
    def __init__(self, template_dir="/app/templates", nats_server="nats://nats:4222"):
        # NATS connection parameters
        self.nats_server = nats_server
        self.nats_client = None
        self.js = None  # JetStream context
        
        # Template directory
        self.template_dir = template_dir
        self.template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_dir),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
        
        # OpenAI API key from environment
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY environment variable not set")
        
        # Initialize OpenAI model
        self.llm = ChatOpenAI(model=os.environ.get("OPENAI_MODEL", "gpt-4"))
        
        # Create a crewAI agent for postmortem generation
        self.postmortem_writer = Agent(
            role="Postmortem Writer",
            goal="Create comprehensive incident postmortem documents",
            backstory="You are an expert at creating detailed, accurate postmortem documents that help teams learn from incidents.",
            verbose=True,
            llm=self.llm,
            tools=[] # Pass empty list to avoid the KeyError
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
                        subjects=["postmortem_agent"]
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
    
    def _get_current_timestamp(self):
        """Get current timestamp in ISO format"""
        return datetime.utcnow().isoformat() + "Z"
    
    async def fetch_alert_data(self, alert_id):
        """Fetch alert data from the orchestrator"""
        logger.info(f"[PostmortemAgent] Requesting alert data for alert ID: {alert_id}")
        
        # Request the alert data from the orchestrator
        request = {"alert_id": alert_id}
        await self.js.publish("alert_data_request", json.dumps(request).encode())
        
        # Create a consumer for the response
        consumer_config = ConsumerConfig(
            durable_name=f"postmortem_alert_data_{alert_id}",
            deliver_policy=DeliverPolicy.ALL,
            ack_policy="explicit",
            filter_subject=f"alert_data_response.{alert_id}"
        )
        
        # Subscribe to get the response
        sub = await self.js.subscribe(
            f"alert_data_response.{alert_id}",
            config=consumer_config
        )
        
        # Wait for the response with a timeout
        try:
            msg = await asyncio.wait_for(sub.next_msg(), timeout=10.0)
            alert_data = json.loads(msg.data.decode())
            await msg.ack()
            await sub.unsubscribe()
            logger.info(f"[PostmortemAgent] Received alert data for alert ID: {alert_id}")
            return alert_data
        except asyncio.TimeoutError:
            logger.warning(f"[PostmortemAgent] Timeout waiting for alert data for alert ID: {alert_id}")
            await sub.unsubscribe()
            return {"alert_id": alert_id, "error": "Timeout waiting for data"}
    
    def _create_postmortem_task(self, root_cause_data, alert_data):
        """Create a postmortem generation task for the crew"""
        alert_id = root_cause_data.get("alert_id", "unknown")
        root_cause = root_cause_data.get("root_cause", "Unknown root cause")
        
        # Extract details from alert data
        service = alert_data.get("labels", {}).get("service", "unknown")
        severity = alert_data.get("labels", {}).get("severity", "unknown")
        description = alert_data.get("annotations", {}).get("description", "No description provided")
        
        # Create the task for the postmortem writer
        task = Task(
            description=f"""
            Generate a comprehensive incident postmortem document for the following incident:
            
            ## Incident Information
            - Incident ID: {alert_id}
            - Service: {service}
            - Severity: {severity}
            - Description: {description}
            
            ## Root Cause Analysis
            {root_cause}
            
            Please create a detailed postmortem document that includes the following sections:
            1. Executive Summary - A brief overview of the incident
            2. Incident Timeline - When the incident was detected, acknowledged, and resolved
            3. Root Cause Analysis - Detailed explanation of what caused the incident
            4. Impact Assessment - What systems/users were affected and how
            5. Mitigation Steps - What was done to resolve the incident
            6. Prevention Measures - Steps to prevent similar incidents in the future
            7. Lessons Learned - Key takeaways from this incident
            8. Action Items - Specific tasks that should be completed to improve systems
            
            Format the document in Markdown format.
            """,
            agent=self.postmortem_writer,
            expected_output="A comprehensive incident postmortem document in Markdown format"
        )
        
        return task
    
    async def generate_postmortem(self, root_cause_data, alert_data):
        """Generate a postmortem document based on root cause analysis"""
        logger.info(f"Generating postmortem for alert ID: {root_cause_data.get('alert_id', 'unknown')}")
        
        # Create postmortem task
        postmortem_task = self._create_postmortem_task(root_cause_data, alert_data)
        
        # Create crew with postmortem writer
        crew = Crew(
            agents=[self.postmortem_writer],
            tasks=[postmortem_task],
            verbose=True
        )
        
        # Execute crew analysis
        result = crew.kickoff()
        
        return result
    
    async def message_handler(self, msg):
        """Handle incoming NATS messages"""
        try:
            # Parse the incoming message
            root_cause_data = json.loads(msg.data.decode())
            alert_id = root_cause_data.get("alert_id", "unknown")
            logger.info(f"[PostmortemAgent] Processing root cause results for alert ID: {alert_id}")
            
            # Fetch the original alert data
            alert_data = await self.fetch_alert_data(alert_id)
            
            if "error" in alert_data:
                logger.error(f"[PostmortemAgent] Failed to get alert data: {alert_data['error']}")
                # Try to proceed with limited data
                alert_data = {"alert_id": alert_id}
            
            # Generate postmortem based on root cause and alert data
            postmortem_result = await self.generate_postmortem(root_cause_data, alert_data)
            
            # Prepare result for the orchestrator
            result = {
                "agent": "postmortem",
                "postmortem": str(postmortem_result),
                "alert_id": alert_id,
                "timestamp": self._get_current_timestamp()
            }
            
            # Publish result to orchestrator
            await self.js.publish("orchestrator_response", json.dumps(result).encode())
            logger.info(f"[PostmortemAgent] Published postmortem for alert ID: {alert_id}")
            
            # Acknowledge the message
            await msg.ack()
            
        except Exception as e:
            logger.error(f"[PostmortemAgent] Error processing message: {str(e)}", exc_info=True)
            # Negative acknowledge the message so it can be redelivered
            await msg.nak()
    
    async def listen(self):
        """Listen for root cause results and generate postmortem documents"""
        logger.info("[PostmortemAgent] Starting to listen for root cause results on 'root_cause_result' and 'postmortem_agent' channels")
        
        # Connect to NATS if not already connected
        if not self.nats_client or not self.nats_client.is_connected:
            await self.connect()
        
        # Create a durable consumer for root cause results
        root_cause_consumer = ConsumerConfig(
            durable_name="postmortem_root_cause",
            deliver_policy=DeliverPolicy.ALL,
            ack_policy="explicit",
            max_deliver=3
        )
        
        # Subscribe to the root cause results
        await self.js.subscribe(
            "root_cause_result",
            cb=self.message_handler,
            queue="postmortem_processors",
            config=root_cause_consumer
        )
        
        # Create a durable consumer for direct postmortem requests
        direct_consumer = ConsumerConfig(
            durable_name="postmortem_direct",
            deliver_policy=DeliverPolicy.ALL,
            ack_policy="explicit",
            max_deliver=3
        )
        
        # Subscribe to direct postmortem requests
        await self.js.subscribe(
            "postmortem_agent",
            cb=self.message_handler,
            queue="postmortem_processors",
            config=direct_consumer
        )
        
        logger.info("[PostmortemAgent] Subscribed to root_cause_result and postmortem_agent streams")
        
        # Keep the connection alive
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour, or until interrupted