import os
import json
import logging
import redis
from datetime import datetime
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from common.tools.knowledge_tools import (
    KnowledgeBaseTool,
    PostmortemTemplateTool,
    RunbookUpdateTool
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class PostmortemAgent:
    def __init__(self, redis_host='redis', redis_port=6379):
        """Initialize the postmortem agent"""
        self.redis_client = redis.Redis(host=redis_host, port=redis_port)
        
        # Initialize OpenAI model
        self.llm = ChatOpenAI(model="gpt-4")
        
        # Initialize knowledge tools
        self.knowledge_base_tool = KnowledgeBaseTool()
        self.postmortem_template_tool = PostmortemTemplateTool()
        self.runbook_update_tool = RunbookUpdateTool()
        
        # Create a crewAI agent for postmortem analysis
        self.postmortem_analyzer = Agent(
            role="Postmortem Analyst",
            goal="Generate comprehensive post-incident reports and update knowledge base",
            backstory="You are an expert at analyzing incidents, generating detailed postmortems, and maintaining a knowledge base of lessons learned.",
            verbose=True,
            llm=self.llm,
            tools=[
                self.knowledge_base_tool.execute,
                self.postmortem_template_tool.execute,
                self.runbook_update_tool.execute
            ]
        )
        
        logger.info("Postmortem agent initialized")

    def _get_current_timestamp(self):
        """Get current timestamp in ISO format"""
        return datetime.utcnow().isoformat()

    def _create_postmortem_task(self, data):
        """Create a task for generating postmortem"""
        return Task(
            description=f"Generate postmortem and update knowledge base for the following incident: {json.dumps(data)}",
            agent=self.postmortem_analyzer
        )

    def process_postmortem(self, data):
        """Process a postmortem request"""
        alert_id = data.get("alert_id", "unknown")
        logger.info(f"Processing postmortem for alert: {alert_id}")
        
        # Create postmortem task
        postmortem_task = self._create_postmortem_task(data)
        
        # Create crew with postmortem analyzer
        crew = Crew(
            agents=[self.postmortem_analyzer],
            tasks=[postmortem_task],
            verbose=True
        )
        
        # Execute crew analysis
        result = crew.kickoff()
        
        # Prepare postmortem result
        postmortem_result = {
            "agent": "postmortem",
            "alert_id": alert_id,
            "timestamp": self._get_current_timestamp(),
            "result": str(result)
        }
        
        # Publish result to orchestrator
        self.redis_client.publish("orchestrator_response", json.dumps(postmortem_result))
        logger.info(f"Published postmortem result for alert: {alert_id}")
        
        return result

    def listen(self):
        """Listen for postmortem requests"""
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe("postmortem_requests")
        logger.info("Listening for postmortem requests...")
        
        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        logger.info(f"Received postmortem request: {data.get('alert_id', 'unknown')}")
                        
                        # Process the postmortem
                        result = self.process_postmortem(data)
                        logger.info(f"Completed processing postmortem: {data.get('alert_id', 'unknown')}")
                        
                    except Exception as e:
                        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        except redis.RedisError as e:
            logger.error(f"Redis connection error: {str(e)}", exc_info=True)
            # Try to reconnect
            self.redis_client = redis.Redis(host='redis', port=redis_port)
            self.listen()  # Recursive call to restart listening 