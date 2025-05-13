import os
import json
import logging
from typing import Dict, Any
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from pdpyras import APISession as PagerDutyClient  # Changed from pagerduty import to pdpyras
from webexteamssdk import WebexTeamsAPI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SlackNotificationTool:
    """Tool for sending notifications to Slack"""
    
    def __init__(self):
        """Initialize the Slack notification tool"""
        self.slack_token = os.environ.get("SLACK_BOT_TOKEN")
        self.default_channel = os.environ.get("SLACK_DEFAULT_CHANNEL", "#incidents")
        self.client = None
        
        # Only initialize the client if token is available
        if self.slack_token:
            self.client = WebClient(token=self.slack_token)
        else:
            logger.warning("SLACK_BOT_TOKEN not provided. Slack notifications will be disabled.")
    
    def execute(self, message: str, channel: str = None) -> Dict[str, Any]:
        """
        Send a message to Slack
        
        Args:
            message (str): The message to send
            channel (str, optional): The channel to send to. Defaults to default_channel.
            
        Returns:
            Dict[str, Any]: Response from Slack API
        """
        # If client is not initialized, return a graceful error
        if not self.client:
            logger.warning("Slack client not initialized. Cannot send notification.")
            return {
                "status": "error", 
                "error": "Slack client not initialized. SLACK_BOT_TOKEN may be missing.",
                "message": message  # Return the message for debugging
            }
            
        try:
            channel = channel or self.default_channel
            response = self.client.chat_postMessage(
                channel=channel,
                text=message,
                blocks=self._create_blocks(message)
            )
            return {"status": "success", "response": response}
        except SlackApiError as e:
            logger.error(f"Error sending Slack message: {str(e)}")
            return {"status": "error", "error": str(e), "message": message}
    
    def _create_blocks(self, message: str) -> list:
        """Create Slack message blocks"""
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            }
        ]

class PagerDutyNotificationTool:
    """Tool for sending notifications to PagerDuty"""
    
    def __init__(self):
        """Initialize the PagerDuty notification tool"""
        self.api_token = os.environ.get("PAGERDUTY_API_TOKEN")
        self.service_id = os.environ.get("PAGERDUTY_SERVICE_ID")
        self.client = None
        
        # Only initialize the client if token is available
        if self.api_token:
            try:
                self.client = PagerDutyClient(self.api_token)
            except ValueError as e:
                logger.warning(f"Failed to initialize PagerDuty client: {str(e)}")
                logger.warning("PagerDuty notifications will be disabled.")
        else:
            logger.warning("PAGERDUTY_API_TOKEN not provided. PagerDuty notifications will be disabled.")
            
        # Check for service ID
        if not self.service_id:
            logger.warning("PAGERDUTY_SERVICE_ID not provided. PagerDuty incidents cannot be created.")
    
    def execute(self, title: str, description: str, severity: str = "critical") -> Dict[str, Any]:
        """
        Create a PagerDuty incident
        
        Args:
            title (str): The incident title
            description (str): The incident description
            severity (str, optional): The incident severity. Defaults to "critical".
            
        Returns:
            Dict[str, Any]: Response from PagerDuty API
        """
        # If client is not initialized or service ID is missing, return a graceful error
        if not self.client:
            logger.warning("PagerDuty client not initialized. Cannot create incident.")
            return {
                "status": "error", 
                "error": "PagerDuty client not initialized. PAGERDUTY_API_TOKEN may be missing.",
                "title": title,
                "description": description
            }
            
        if not self.service_id:
            logger.warning("PagerDuty service ID not provided. Cannot create incident.")
            return {
                "status": "error", 
                "error": "PagerDuty service ID not provided. PAGERDUTY_SERVICE_ID may be missing.",
                "title": title,
                "description": description
            }
            
        try:
            # pdpyras uses a different API than what was previously implemented
            # Convert severity to urgency (PD uses "high" instead of "critical")
            urgency = "high" if severity == "critical" else severity
            
            # Create the incident using pdpyras API
            response = self.client.create_incident(
                title=title,
                service=self.service_id,
                description=description,
                urgency=urgency
            )
            return {"status": "success", "response": str(response)}
        except Exception as e:
            logger.error(f"Error creating PagerDuty incident: {str(e)}")
            return {"status": "error", "error": str(e), "title": title, "description": description}

class WebexNotificationTool:
    """Tool for sending notifications to Webex Teams"""
    
    def __init__(self):
        """Initialize the Webex notification tool"""
        self.access_token = os.environ.get("WEBEX_ACCESS_TOKEN")
        self.default_room_id = os.environ.get("WEBEX_DEFAULT_ROOM_ID")
        self.client = None
        
        # Only initialize the client if token is available
        if self.access_token:
            try:
                self.client = WebexTeamsAPI(access_token=self.access_token)
            except Exception as e:
                logger.warning(f"Failed to initialize Webex Teams client: {str(e)}")
                logger.warning("Webex Teams notifications will be disabled.")
        else:
            logger.warning("WEBEX_ACCESS_TOKEN not provided. Webex Teams notifications will be disabled.")
            
        # Check for room ID
        if not self.default_room_id:
            logger.warning("WEBEX_DEFAULT_ROOM_ID not provided. Webex Teams messages will require explicit room ID.")
    
    def execute(self, message: str, room_id: str = None) -> Dict[str, Any]:
        """
        Send a message to Webex Teams
        
        Args:
            message (str): The message to send
            room_id (str, optional): The room ID to send to. Defaults to default_room_id.
            
        Returns:
            Dict[str, Any]: Response from Webex API
        """
        # If client is not initialized, return a graceful error
        if not self.client:
            logger.warning("Webex Teams client not initialized. Cannot send message.")
            return {
                "status": "error", 
                "error": "Webex Teams client not initialized. WEBEX_ACCESS_TOKEN may be missing.",
                "message": message
            }
            
        # Use provided room_id or default, but if neither is available, return an error
        room_id = room_id or self.default_room_id
        if not room_id:
            logger.warning("Webex Teams room ID not provided. Cannot send message.")
            return {
                "status": "error", 
                "error": "Webex Teams room ID not provided. Either pass room_id parameter or set WEBEX_DEFAULT_ROOM_ID.",
                "message": message
            }
            
        try:
            response = self.client.messages.create(
                roomId=room_id,
                markdown=message
            )
            return {"status": "success", "response": response}
        except Exception as e:
            logger.error(f"Error sending Webex Teams message: {str(e)}")
            return {"status": "error", "error": str(e), "message": message}