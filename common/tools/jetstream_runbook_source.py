import json
import logging
import os
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JetstreamRunbookSource:
    """
    A runbook source that fetches runbooks from NATS JetStream
    This allows the runbook agent to use runbooks that were added through the UI
    """
    
    def __init__(self, js=None):
        """
        Initialize the JetStream runbook source
        
        Args:
            js: JetStream client instance
        """
        self.js = js
    
    def set_js(self, js):
        """
        Set the JetStream client
        
        Args:
            js: JetStream client instance
        """
        self.js = js
    
    async def fetch_runbook(self, identifier):
        """
        Fetch a runbook from NATS JetStream
        
        Args:
            identifier (dict): Dictionary containing alert information
        
        Returns:
            dict: Runbook data with steps
        """
        if not self.js:
            logger.warning("JetStream client not set, cannot fetch runbooks from JetStream")
            return {"found": False, "message": "JetStream client not available"}
        
        # Extract alert name and service
        alert_name = identifier.get('labels', {}).get('alertname', '')
        service = identifier.get('labels', {}).get('service', '')
        
        if not alert_name:
            return {"found": False, "message": "No alert name provided"}
        
        try:
            # Check if RUNBOOKS stream exists
            try:
                await self.js.stream_info('RUNBOOKS')
            except Exception as e:
                logger.warning(f"RUNBOOKS stream not found: {str(e)}")
                return {"found": False, "message": "RUNBOOKS stream not found"}
            
            # Create a consumer for the RUNBOOKS stream
            consumer_config = {
                "durable_name": "runbook_fetch",
                "ack_policy": "explicit",
                "deliver_policy": "all"
            }
            
            consumer = await self.js.consumer('RUNBOOKS', consumer_config)
            
            # Fetch all runbooks
            batch = await consumer.fetch(batch=100)
            
            runbooks = []
            for msg in batch:
                try:
                    data = json.loads(msg.data.decode())
                    await msg.ack()
                    runbooks.append(data)
                except Exception as e:
                    logger.error(f"Error parsing runbook message: {str(e)}")
                    await msg.nak()
            
            # Find matching runbook
            # First try to match both alert name and service
            if service:
                for runbook in runbooks:
                    title = runbook.get('title', '').lower()
                    rb_service = runbook.get('service', '').lower()
                    
                    if (alert_name.lower() in title and 
                        service.lower() == rb_service.lower()):
                        return self._format_runbook(runbook, alert_name, service)
            
            # Then try to match just the alert name
            for runbook in runbooks:
                title = runbook.get('title', '').lower()
                
                if alert_name.lower() in title:
                    return self._format_runbook(runbook, alert_name, service)
            
            # No matching runbook found
            return {"found": False, "message": f"No matching runbook found for {alert_name}"}
            
        except Exception as e:
            logger.error(f"Error fetching runbook from JetStream: {str(e)}")
            return {"found": False, "message": f"Error: {str(e)}"}
    
    def _format_runbook(self, runbook, alert_name, service):
        """
        Format a runbook from JetStream into the expected format
        
        Args:
            runbook (dict): Runbook data from JetStream
            alert_name (str): Alert name
            service (str): Service name
            
        Returns:
            dict: Formatted runbook data
        """
        # Extract steps from the runbook
        steps = []
        
        # If the runbook has steps, use them
        if 'steps' in runbook and isinstance(runbook['steps'], list):
            steps = runbook['steps']
        # Otherwise, try to parse steps from content
        elif 'content' in runbook:
            steps = self._parse_steps(runbook['content'])
        
        return {
            "alertName": alert_name,
            "service": service,
            "steps": steps,
            "found": True,
            "source": f"JetStream: {runbook.get('id', 'unknown')}"
        }
    
    def _parse_steps(self, content):
        """
        Parse steps from markdown content
        
        Args:
            content (str): Markdown content
            
        Returns:
            list: List of steps
        """
        steps = []
        lines = content.split('\n')
        
        for line in lines:
            # Match numbered list items (e.g., "1. Step one")
            if line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '0.')):
                step = line.strip().split('. ', 1)
                if len(step) > 1:
                    steps.append(step[1])
            # Match bullet points (- Step one or * Step one)
            elif line.strip().startswith(('-', '*')):
                step = line.strip()[1:].strip()
                if step:
                    steps.append(step)
        
        return steps
