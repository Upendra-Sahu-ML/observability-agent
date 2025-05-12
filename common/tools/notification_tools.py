import os
import json
import logging
from typing import Dict, Any
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from pagerduty_sdk import PagerDutyClient
from webexteamssdk import WebexTeamsAPI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SlackNotificationTool:
    """Tool for sending notifications to Slack"""
    
    def __init__(self):
        """Initialize the Slack notification tool"""
        self.client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
        self.default_channel = os.environ.get("SLACK_DEFAULT_CHANNEL", "#incidents")
    
    def execute(self, message: str, channel: str = None) -> Dict[str, Any]:
        """
        Send a message to Slack
        
        Args:
            message (str): The message to send
            channel (str, optional): The channel to send to. Defaults to default_channel.
            
        Returns:
            Dict[str, Any]: Response from Slack API
        """
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
            return {"status": "error", "error": str(e)}
    
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
        self.client = PagerDutyClient(token=os.environ.get("PAGERDUTY_API_TOKEN"))
    
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
        try:
            response = self.client.incidents.create(
                title=title,
                description=description,
                urgency=severity,
                service_id=os.environ.get("PAGERDUTY_SERVICE_ID")
            )
            return {"status": "success", "response": response}
        except Exception as e:
            logger.error(f"Error creating PagerDuty incident: {str(e)}")
            return {"status": "error", "error": str(e)}

class WebexNotificationTool:
    """Tool for sending notifications to Webex Teams"""
    
    def __init__(self):
        """Initialize the Webex notification tool"""
        self.client = WebexTeamsAPI(access_token=os.environ.get("WEBEX_ACCESS_TOKEN"))
        self.default_room_id = os.environ.get("WEBEX_DEFAULT_ROOM_ID")
    
    def execute(self, message: str, room_id: str = None) -> Dict[str, Any]:
        """
        Send a message to Webex Teams
        
        Args:
            message (str): The message to send
            room_id (str, optional): The room ID to send to. Defaults to default_room_id.
            
        Returns:
            Dict[str, Any]: Response from Webex API
        """
        try:
            room_id = room_id or self.default_room_id
            response = self.client.messages.create(
                roomId=room_id,
                markdown=message
            )
            return {"status": "success", "response": response}
        except Exception as e:
            logger.error(f"Error sending Webex message: {str(e)}")
            return {"status": "error", "error": str(e)} 