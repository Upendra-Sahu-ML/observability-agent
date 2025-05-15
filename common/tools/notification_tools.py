import os
import json
import logging
from typing import Dict, Any, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from pdpyras import APISession as PagerDutyClient
from webexteamssdk import WebexTeamsAPI
from crewai.tools import tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationTools:
    """Tools for sending notifications to various platforms"""
    
    def __init__(self):
        """Initialize notification tools for various platforms"""
        # Slack setup
        self.slack_token = os.environ.get("SLACK_BOT_TOKEN")
        self.slack_default_channel = os.environ.get("SLACK_DEFAULT_CHANNEL", "#incidents")
        self.slack_client = None
        
        if self.slack_token:
            self.slack_client = WebClient(token=self.slack_token)
        else:
            logger.warning("SLACK_BOT_TOKEN not provided. Slack notifications will be disabled.")
            
        # PagerDuty setup
        self.pagerduty_token = os.environ.get("PAGERDUTY_API_TOKEN")
        self.pagerduty_service_id = os.environ.get("PAGERDUTY_SERVICE_ID")
        self.pagerduty_client = None
        
        if self.pagerduty_token:
            try:
                self.pagerduty_client = PagerDutyClient(self.pagerduty_token)
            except ValueError as e:
                logger.warning(f"Failed to initialize PagerDuty client: {str(e)}")
        else:
            logger.warning("PAGERDUTY_API_TOKEN not provided. PagerDuty notifications will be disabled.")
            
        if not self.pagerduty_service_id:
            logger.warning("PAGERDUTY_SERVICE_ID not provided. PagerDuty incidents cannot be created.")
            
        # Webex Teams setup
        self.webex_token = os.environ.get("WEBEX_ACCESS_TOKEN")
        self.webex_default_room_id = os.environ.get("WEBEX_DEFAULT_ROOM_ID")
        self.webex_client = None
        
        if self.webex_token:
            try:
                self.webex_client = WebexTeamsAPI(access_token=self.webex_token)
            except Exception as e:
                logger.warning(f"Failed to initialize Webex Teams client: {str(e)}")
        else:
            logger.warning("WEBEX_ACCESS_TOKEN not provided. Webex Teams notifications will be disabled.")
            
        if not self.webex_default_room_id:
            logger.warning("WEBEX_DEFAULT_ROOM_ID not provided. Webex Teams messages will require explicit room ID.")
    
    @tool("Send a notification to Slack")
    def send_slack_message(self, message: str, channel: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a message to Slack
        
        Args:
            message (str): The message to send
            channel (str, optional): The channel to send to. Uses default channel if not specified.
            
        Returns:
            Dict[str, Any]: Response from Slack API
        """
        if not self.slack_client:
            logger.warning("Slack client not initialized. Cannot send notification.")
            return {
                "status": "error", 
                "error": "Slack client not initialized. SLACK_BOT_TOKEN may be missing.",
                "message": message
            }
            
        try:
            channel = channel or self.slack_default_channel
            response = self.slack_client.chat_postMessage(
                channel=channel,
                text=message,
                blocks=self._create_slack_blocks(message)
            )
            return {"status": "success", "response": str(response)}
        except SlackApiError as e:
            logger.error(f"Error sending Slack message: {str(e)}")
            return {"status": "error", "error": str(e), "message": message}
    
    def _create_slack_blocks(self, message: str) -> list:
        """Create Slack message blocks for rich formatting"""
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            }
        ]

    @tool("Create an incident in PagerDuty")
    def create_pagerduty_incident(self, title: str, description: str, severity: str = "critical") -> Dict[str, Any]:
        """
        Create a PagerDuty incident
        
        Args:
            title (str): The incident title
            description (str): The incident description
            severity (str, optional): The incident severity - "critical", "warning", "error", or "info"
            
        Returns:
            Dict[str, Any]: Response from PagerDuty API
        """
        if not self.pagerduty_client:
            logger.warning("PagerDuty client not initialized. Cannot create incident.")
            return {
                "status": "error", 
                "error": "PagerDuty client not initialized. PAGERDUTY_API_TOKEN may be missing.",
                "title": title,
                "description": description
            }
            
        if not self.pagerduty_service_id:
            logger.warning("PagerDuty service ID not provided. Cannot create incident.")
            return {
                "status": "error", 
                "error": "PagerDuty service ID not provided. PAGERDUTY_SERVICE_ID may be missing.",
                "title": title,
                "description": description
            }
            
        try:
            # Convert severity to urgency (PD uses "high" instead of "critical")
            urgency = "high" if severity == "critical" else "low"
            
            # Create the incident
            response = self.pagerduty_client.create_incident(
                title=title,
                service=self.pagerduty_service_id,
                description=description,
                urgency=urgency
            )
            
            # Extract the incident ID and URL from the response for easier reference
            incident_id = response.get("id") if isinstance(response, dict) else None
            incident_url = response.get("html_url") if isinstance(response, dict) else None
            
            return {
                "status": "success", 
                "incident_id": incident_id,
                "incident_url": incident_url,
                "response": str(response)
            }
        except Exception as e:
            logger.error(f"Error creating PagerDuty incident: {str(e)}")
            return {"status": "error", "error": str(e), "title": title, "description": description}

    @tool("Send a notification to Webex Teams")
    def send_webex_message(self, message: str, room_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a message to Webex Teams
        
        Args:
            message (str): The message to send
            room_id (str, optional): The room ID to send to. Uses default room if not specified.
            
        Returns:
            Dict[str, Any]: Response from Webex API
        """
        if not self.webex_client:
            logger.warning("Webex Teams client not initialized. Cannot send message.")
            return {
                "status": "error", 
                "error": "Webex Teams client not initialized. WEBEX_ACCESS_TOKEN may be missing.",
                "message": message
            }
            
        # Use provided room_id or default, but if neither is available, return an error
        room_id = room_id or self.webex_default_room_id
        if not room_id:
            logger.warning("Webex Teams room ID not provided. Cannot send message.")
            return {
                "status": "error", 
                "error": "Webex Teams room ID not provided. Either pass room_id parameter or set WEBEX_DEFAULT_ROOM_ID.",
                "message": message
            }
            
        try:
            response = self.webex_client.messages.create(
                roomId=room_id,
                markdown=message
            )
            return {"status": "success", "response": str(response)}
        except Exception as e:
            logger.error(f"Error sending Webex Teams message: {str(e)}")
            return {"status": "error", "error": str(e), "message": message}

    @tool("Send notifications to multiple channels at once")
    def send_multi_channel_notification(self, message: str, title: str = None, 
                                       send_slack: bool = True, slack_channel: str = None,
                                       send_pagerduty: bool = False, severity: str = "warning",
                                       send_webex: bool = False, webex_room_id: str = None) -> Dict[str, Any]:
        """
        Send notifications to multiple channels at once
        
        Args:
            message (str): The message to send
            title (str, optional): Title for the message (for PagerDuty)
            send_slack (bool, optional): Whether to send to Slack, defaults to True
            slack_channel (str, optional): Slack channel to send to
            send_pagerduty (bool, optional): Whether to send to PagerDuty, defaults to False
            severity (str, optional): PagerDuty severity, defaults to "warning"
            send_webex (bool, optional): Whether to send to Webex Teams, defaults to False
            webex_room_id (str, optional): Webex Teams room ID to send to
            
        Returns:
            Dict[str, Any]: Combined results from all notification channels
        """
        results = {}
        
        # For PagerDuty, we need a title
        if not title and send_pagerduty:
            title = message.split('\n')[0] if '\n' in message else message[:50] + "..."
        
        # Send to Slack if requested
        if send_slack:
            slack_result = self.send_slack_message(message, channel=slack_channel)
            results["slack"] = slack_result
        
        # Send to PagerDuty if requested
        if send_pagerduty:
            pd_result = self.create_pagerduty_incident(title, message, severity=severity)
            results["pagerduty"] = pd_result
        
        # Send to Webex Teams if requested
        if send_webex:
            webex_result = self.send_webex_message(message, room_id=webex_room_id)
            results["webex"] = webex_result
        
        # Determine overall status
        success_count = sum(1 for channel, result in results.items() if result.get("status") == "success")
        if not results:
            overall_status = "error"
            error_message = "No notification channels were specified"
        elif success_count == len(results):
            overall_status = "success"
            error_message = None
        elif success_count > 0:
            overall_status = "partial_success"
            error_message = f"{len(results) - success_count} out of {len(results)} channels failed"
        else:
            overall_status = "error"
            error_message = "All notification channels failed"
        
        return {
            "status": overall_status,
            "error": error_message,
            "channels": list(results.keys()),
            "results": results
        }