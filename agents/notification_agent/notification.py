import os
import json
import logging
import redis
from datetime import datetime
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from common.tools.notification_tools import (
    SlackNotificationTool,
    PagerDutyNotificationTool,
    WebexNotificationTool
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class NotificationAgent:
    def __init__(self, redis_host='redis', redis_port=6379):
        """Initialize the notification agent"""
        self.redis_client = redis.Redis(host=redis_host, port=redis_port)
        
        # Initialize OpenAI model
        self.llm = ChatOpenAI(model="gpt-4")
        
        # Initialize notification tools
        self.slack_tool = SlackNotificationTool()
        self.pagerduty_tool = PagerDutyNotificationTool()
        self.webex_tool = WebexNotificationTool()
        
        # Create a crewAI agent for notification management
        self.notification_manager = Agent(
            role="Notification Manager",
            goal="Manage and coordinate notifications across different channels",
            backstory="You are an expert at managing incident notifications and ensuring the right information reaches the right people through the right channels.",
            verbose=True,
            llm=self.llm,
            tools=[
                self.slack_tool.execute,
                self.pagerduty_tool.execute,
                self.webex_tool.execute
            ]
        )
        
        logger.info("Notification agent initialized")

    def _get_current_timestamp(self):
        """Get current timestamp in ISO format"""
        return datetime.utcnow().isoformat()

    def _create_notification_task(self, data):
        """Create a task for managing notifications"""
        return Task(
            description=f"Manage notifications for the following data: {json.dumps(data)}",
            agent=self.notification_manager
        )

    def process_notification(self, data):
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
        
        # Publish result to orchestrator
        self.redis_client.publish("orchestrator_response", json.dumps(notification_result))
        logger.info(f"Published notification result for alert: {alert_id}")
        
        return result

    def listen(self):
        """Listen for notification requests"""
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe("notification_requests")
        logger.info("Listening for notification requests...")
        
        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        logger.info(f"Received notification request: {data.get('alert_id', 'unknown')}")
                        
                        # Process the notification
                        result = self.process_notification(data)
                        logger.info(f"Completed processing notification: {data.get('alert_id', 'unknown')}")
                        
                    except Exception as e:
                        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        except redis.RedisError as e:
            logger.error(f"Redis connection error: {str(e)}", exc_info=True)
            # Try to reconnect
            self.redis_client = redis.Redis(host='redis', port=redis_port)
            self.listen()  # Recursive call to restart listening 