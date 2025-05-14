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
from common.tools.runbook_tools import RunbookFetchTool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class RunbookAgent:
    def __init__(self, nats_server="nats://nats:4222"):
        # NATS connection parameters
        self.nats_server = nats_server
        self.nats_client = None
        self.js = None  # JetStream context
        
        # OpenAI API key from environment
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY environment variable not set")
        
        # Get runbook directory from environment and set it as an environment variable for RunbookFetchTool
        runbook_dir = os.environ.get("RUNBOOK_DIR", "/app/runbooks")
        os.environ["RUNBOOK_LOCAL_PATH"] = runbook_dir
        
        # Initialize OpenAI model
        self.llm = ChatOpenAI(model=os.environ.get("OPENAI_MODEL", "gpt-4"))
        
        # Initialize runbook tools - no parameters needed as it uses environment variables
        self.runbook_tool = RunbookFetchTool()
        
        # Convert function to proper LangChain tool
        self.langchain_tools = [
            StructuredTool.from_function(self.runbook_tool.fetch)
        ]
        
        # Create a crewAI agent for runbook management
        self.runbook_manager = Agent(
            role="Runbook Manager",
            goal="Provide the most relevant runbook procedures based on incident data",
            backstory="You are an expert at managing runbooks and selecting the most appropriate remediation steps for incidents.",
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
            
            # Check if we can get the stream info, this confirms the connection works
            try:
                # Just check if we can access streams - we don't need to create them
                # since they're likely already created by the orchestrator or other agents
                streams = await self.js.streams_info()
                logger.info(f"Successfully connected to JetStream. Found {len(streams)} streams.")
                
                # Log the existing stream names and subjects for debugging
                stream_details = {}
                for stream in streams:
                    stream_details[stream.config.name] = stream.config.subjects
                logger.info(f"Existing streams: {stream_details}")
                
                # We'll skip stream creation entirely since other agents have likely created them
                # This avoids the 'subjects overlap with an existing stream' error
                
            except nats.errors.Error as e:
                # Just log the error but continue - we can still work with the connection
                logger.warning(f"Could not get streams info: {str(e)}")
    
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {str(e)}")
            raise
    
    def _get_current_timestamp(self):
        """Get current timestamp in ISO format"""
        return datetime.utcnow().isoformat() + "Z"
    
    async def fetch_alert_data(self, alert_id):
        """Fetch alert data from the orchestrator"""
        logger.info(f"[RunbookAgent] Requesting alert data for alert ID: {alert_id}")
        
        # Request the alert data from the orchestrator
        request = {"alert_id": alert_id}
        await self.js.publish("alert_data_request", json.dumps(request).encode())
        
        # Create a consumer for the response
        consumer_config = ConsumerConfig(
            durable_name=f"runbook_alert_data_{alert_id}",
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
            logger.info(f"[RunbookAgent] Received alert data for alert ID: {alert_id}")
            return alert_data
        except asyncio.TimeoutError:
            logger.warning(f"[RunbookAgent] Timeout waiting for alert data for alert ID: {alert_id}")
            await sub.unsubscribe()
            return {"alert_id": alert_id, "error": "Timeout waiting for data"}
    
    def _create_runbook_task(self, root_cause_data, alert_data):
        """Create a runbook generation task for the crew"""
        alert_id = root_cause_data.get("alert_id", "unknown")
        root_cause = root_cause_data.get("root_cause", "Unknown root cause")
        
        # Extract details from alert data
        service = alert_data.get("labels", {}).get("service", "unknown")
        severity = alert_data.get("labels", {}).get("severity", "unknown")
        description = alert_data.get("annotations", {}).get("description", "No description provided")
        
        # Create the task for the runbook manager
        task = Task(
            description=f"""
            Generate runbook instructions for addressing the following incident:
            
            ## Alert Information
            - Alert ID: {alert_id}
            - Service: {service}
            - Severity: {severity}
            - Description: {description}
            
            ## Root Cause Analysis
            {root_cause}
            
            Please search for relevant runbooks in our repository and enhance them with specific instructions
            based on the root cause analysis. If no specific runbook exists, generate appropriate steps.
            
            Format your response as a clear, step-by-step guide that an on-call engineer can follow.
            Include verification steps to confirm that the issue has been resolved.
            """,
            agent=self.runbook_manager,
            expected_output="A comprehensive runbook with step-by-step instructions"
        )
        
        return task
    
    async def generate_runbook(self, root_cause_data, alert_data):
        """Generate an enhanced runbook based on root cause analysis"""
        logger.info(f"Generating runbook for alert ID: {root_cause_data.get('alert_id', 'unknown')}")
        
        # Create runbook task
        runbook_task = self._create_runbook_task(root_cause_data, alert_data)
        
        # Create crew with runbook manager
        crew = Crew(
            agents=[self.runbook_manager],
            tasks=[runbook_task],
            verbose=True
        )
        
        # Execute crew analysis
        result = crew.kickoff()
        
        return result
    
    async def message_handler(self, msg):
        """Handle incoming NATS messages for root cause results"""
        try:
            # Parse the incoming message
            root_cause_data = json.loads(msg.data.decode())
            alert_id = root_cause_data.get("alert_id", "unknown")
            logger.info(f"[RunbookAgent] Processing root cause results for alert ID: {alert_id}")
            
            # Fetch the original alert data
            alert_data = await self.fetch_alert_data(alert_id)
            
            if "error" in alert_data:
                logger.error(f"[RunbookAgent] Failed to get alert data: {alert_data['error']}")
                # Try to proceed with limited data
                alert_data = {"alert_id": alert_id}
            
            # Generate runbook based on root cause and alert data
            runbook_result = await self.generate_runbook(root_cause_data, alert_data)
            
            # Prepare result for the orchestrator
            result = {
                "agent": "runbook",
                "runbook": str(runbook_result),
                "alert_id": alert_id,
                "timestamp": self._get_current_timestamp()
            }
            
            # Publish result to orchestrator
            await self.js.publish("orchestrator_response", json.dumps(result).encode())
            logger.info(f"[RunbookAgent] Published runbook for alert ID: {alert_id}")
            
            # Acknowledge the message
            await msg.ack()
            
        except Exception as e:
            logger.error(f"[RunbookAgent] Error processing message: {str(e)}", exc_info=True)
            # Negative acknowledge the message so it can be redelivered
            await msg.nak()
    
    async def listen(self):
        """Listen for root cause results and generate enhanced runbooks"""
        logger.info("[RunbookAgent] Starting to listen for root cause results on 'root_cause_result' channel")
        
        # Connect to NATS if not already connected
        if not self.nats_client or not self.nats_client.is_connected:
            await self.connect()
        
        # Create a durable consumer with a queue group for load balancing
        consumer_config = ConsumerConfig(
            durable_name="runbook_agent",
            deliver_policy=DeliverPolicy.ALL,
            ack_policy="explicit",
            max_deliver=5,  # Retry up to 5 times
            ack_wait=120,   # Wait 2 minutes for acknowledgment (runbook generation can take time)
        )
        
        # Subscribe to the stream with the consumer configuration
        await self.js.subscribe(
            "root_cause_result",
            cb=self.message_handler,
            queue="runbook_processors",
            config=consumer_config
        )
        
        logger.info("[RunbookAgent] Subscribed to root_cause_result stream")
        
        # Keep the connection alive
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour, or until interrupted