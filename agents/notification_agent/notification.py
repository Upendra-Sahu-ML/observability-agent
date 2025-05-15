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
from common.tools.notification_tools import NotificationTools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class NotificationAgent:
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
        
        # Initialize notification tools
        self.notification_tools = NotificationTools()
        
        # Create a crewAI agent for notification management
        self.notification_manager = Agent(
            role="Notification Manager",
            goal="Manage and send notifications across different platforms",
            backstory="You are an expert at managing notifications and ensuring important information reaches the right people through appropriate channels.",
            verbose=True,
            llm=self.llm,
            tools=[
                # Direct access to notification tools
                self.notification_tools.send_slack_message,
                self.notification_tools.send_webex_message,
                self.notification_tools.create_pagerduty_incident,
                self.notification_tools.send_multi_channel_notification
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
                
                # Only create NOTIFICATIONS stream if it doesn't already exist
                if "NOTIFICATIONS" not in stream_names:
                    await self.js.add_stream(
                        name="NOTIFICATIONS", 
                        subjects=["notification_requests"]
                    )
                    logger.info("Created NOTIFICATIONS stream")
                else:
                    logger.info("NOTIFICATIONS stream already exists")
                
                # Only create AGENT_TASKS stream if it doesn't already exist
                if "AGENT_TASKS" not in stream_names:
                    await self.js.add_stream(
                        name="AGENT_TASKS", 
                        subjects=["notification_agent"]
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
    
    def _create_notification_task(self, data):
        """Create a notification task for the crew"""
        # Extract alert details
        alert_id = data.get("alert_id", "unknown")
        alert_name = data.get("labels", {}).get("alertname", "Unknown Alert")
        service = data.get("labels", {}).get("service", "unknown")
        severity = data.get("labels", {}).get("severity", "warning")
        description = data.get("annotations", {}).get("description", "No description provided")
        
        # Include any root cause analysis if available
        root_cause = data.get("root_cause", "Cause unknown - investigation in progress")
        
        # Determine which channels to use based on severity
        channels = ["slack"]  # Default to slack
        if severity.lower() in ["critical", "error"]:
            channels.append("pagerduty")  # Add pagerduty for critical alerts
        if severity.lower() == "critical":
            channels.append("webex")  # Add webex for critical alerts
            
        # Create the task for the notification agent
        task = Task(
            description=f"""
            Create notifications for an incident with the following details:
            - Alert ID: {alert_id}
            - Alert Name: {alert_name}
            - Service: {service}
            - Severity: {severity}
            - Description: {description}
            - Root Cause: {root_cause}
            
            Format the notification appropriately for each channel: {', '.join(channels)}.
            For Slack, use formatting to highlight severity.
            For PagerDuty, ensure the title is clear and actionable.
            For Webex, keep it concise but informative.
            
            Return a JSON object with the notification text for each channel and the status of each notification.
            """,
            agent=self.notification_manager,
            expected_output="A JSON object with notification text and status for each channel"
        )
        
        return task
    
    async def process_notification(self, data):
        """Process a notification request"""
        alert_id = data.get("alert_id", "unknown")
        logger.info(f"Processing notification for alert: {alert_id}")
        
        # Create notification task
        notification_task = self._create_notification_task(data)
        
        # Create crew with notification manager
        crew = Crew(
            agents=[self.notification_manager],
            tasks=[notification_task],
            verbose=True
        )
        
        # Execute crew analysis
        result = crew.kickoff()
        
        # Prepare notification result
        notification_result = {
            "agent": "notification",
            "alert_id": alert_id,
            "timestamp": self._get_current_timestamp(),
            "result": str(result)
        }
        
        # Publish result to orchestrator using JetStream
        await self.js.publish("orchestrator_response", json.dumps(notification_result).encode())
        logger.info(f"Published notification result for alert: {alert_id}")
        
        return result
    
    async def message_handler(self, msg):
        """Handle incoming NATS messages"""
        try:
            # Decode the message data
            data = json.loads(msg.data.decode())
            logger.info(f"Received notification request: {data.get('alert_id', 'unknown')}")
            
            # Process the notification
            await self.process_notification(data)
            
            # Acknowledge the message
            await msg.ack()
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            # Negative acknowledge the message so it can be redelivered
            await msg.nak()
    
    async def listen(self):
        """Listen for notification requests using NATS JetStream"""
        # Connect to NATS if not already connected
        if not self.nats_client or not self.nats_client.is_connected:
            await self.connect()
        
        logger.info("Listening for notification requests...")
        
        # Create a durable consumer with a queue group for load balancing
        consumer_config = ConsumerConfig(
            durable_name="notification_agent",
            deliver_policy=DeliverPolicy.ALL,
            ack_policy="explicit",
            max_deliver=5,  # Retry up to 5 times
            ack_wait=30,    # Wait 30 seconds for acknowledgment
        )
        
        # Subscribe to the stream with the consumer configuration
        await self.js.subscribe(
            "notification_requests",
            cb=self.message_handler,
            queue="notification_processors",
            config=consumer_config
        )
        
        logger.info("Subscribed to notification_requests stream")
        
        # Keep the connection alive
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour, or until interrupted