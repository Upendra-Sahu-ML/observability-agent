import os
import redis
import json
import logging
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from common.tools.runbook_tools import RunbookFetchTool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class RunbookAgent:
    def __init__(self, redis_host=None, redis_port=None, openai_model=None):
        # Get configuration from environment variables or use defaults
        self.redis_host = redis_host or os.environ.get('REDIS_HOST', 'redis')
        self.redis_port = redis_port or int(os.environ.get('REDIS_PORT', 6379))
        self.openai_model = openai_model or os.environ.get('OPENAI_MODEL', 'gpt-4')
        
        # Initialize Redis client
        self.redis_client = redis.Redis(host=self.redis_host, port=self.redis_port)
        logger.info(f"Initialized Redis connection to {self.redis_host}:{self.redis_port}")
        
        # Initialize OpenAI model
        self.llm = ChatOpenAI(model=self.openai_model)
        logger.info(f"Initialized OpenAI model: {self.openai_model}")
        
        # Initialize runbook fetch tool
        self.runbook_fetch_tool = RunbookFetchTool()
        
        # Create a crewAI agent for runbook enhancement
        self.runbook_enhancer = Agent(
            role="Runbook Enhancement Specialist",
            goal="Validate and enhance runbooks with root cause analysis to provide accurate remediation steps",
            backstory="Expert at understanding system issues and translating complex root cause findings into practical remediation steps. You're skilled at validating existing runbooks and filling in any gaps based on the actual incident cause.",
            verbose=True,
            llm=self.llm
        )
    
    def fetch_runbook(self, alert_data):
        """Fetch the runbook for a given alert using the runbook fetch tool"""
        try:
            # Use the runbook fetch tool to get runbooks from different sources
            runbook_data = self.runbook_fetch_tool.fetch(alert_data)
            
            if runbook_data.get("found", False):
                logger.info(f"[RunbookAgent] Successfully fetched runbook for alert: {runbook_data.get('alertName')} from {runbook_data.get('source', 'unknown source')}")
            else:
                logger.warning(f"[RunbookAgent] No runbook found for alert: {alert_data.get('labels', {}).get('alertname', 'unknown')}")
                
            return runbook_data
                
        except Exception as e:
            logger.error(f"[RunbookAgent] Exception fetching runbook: {str(e)}")
            return {
                "alertName": alert_data.get('labels', {}).get('alertname', 'unknown'),
                "steps": [],
                "found": False,
                "message": f"Exception fetching runbook: {str(e)}"
            }
    
    def enhance_runbook(self, root_cause_data, runbook_data, alert_data):
        """Enhance the runbook using root cause analysis and LLM reasoning"""
        
        # Extract the root cause analysis
        root_cause_analysis = root_cause_data.get('root_cause', 'No root cause analysis available')
        
        # Get runbook steps
        runbook_steps = runbook_data.get('steps', [])
        runbook_found = runbook_data.get('found', False)
        runbook_source = runbook_data.get('source', 'Unknown source')
        
        # Format the steps for the prompt
        formatted_steps = "\n".join([f"Step {i+1}: {step}" for i, step in enumerate(runbook_steps)])
        if not formatted_steps:
            formatted_steps = "No predefined steps available."
        
        # Extract alert information for context
        alert_name = alert_data.get('labels', {}).get('alertname', 'Unknown Alert')
        service = alert_data.get('labels', {}).get('service', '')
        namespace = alert_data.get('labels', {}).get('namespace', 'default')
        summary = alert_data.get('annotations', {}).get('summary', '')
        description = alert_data.get('annotations', {}).get('description', '')
        
        # Create enhancement task
        enhancement_task = Task(
            description=f"""
            Evaluate and enhance the runbook for a system alert based on root cause analysis.
            
            ALERT INFORMATION:
            Alert Name: {alert_name}
            Service: {service}
            Namespace: {namespace}
            Summary: {summary}
            Description: {description}
            
            EXISTING RUNBOOK:
            Source: {runbook_source}
            {formatted_steps}
            Runbook Found: {runbook_found}
            
            ROOT CAUSE ANALYSIS:
            {root_cause_analysis}
            
            Your task:
            1. Evaluate whether the existing runbook steps (if any) are appropriate for addressing the identified root cause
            2. Identify any missing steps, incorrect steps, or steps that need modification
            3. Provide a complete, enhanced runbook with clear, actionable steps to resolve the issue
            4. Each step should be concise yet detailed enough for an operator to execute
            5. Include verification steps to confirm the issue has been resolved
            6. If the existing runbook is completely appropriate, state so and explain why
            
            Format your output as a numbered list of steps, followed by a brief explanation of your changes.
            """,
            agent=self.runbook_enhancer,
            expected_output="A comprehensive, enhanced runbook with actionable steps to resolve the alert, based on the root cause analysis"
        )
        
        # Create crew with the runbook enhancer agent
        crew = Crew(
            agents=[self.runbook_enhancer],
            tasks=[enhancement_task],
            verbose=True
        )
        
        # Execute the crew workflow
        result = crew.kickoff()
        return result

    def listen(self):
        """Listen for root cause results and generate enhanced runbooks"""
        logger.info("[RunbookAgent] Starting to listen for root cause results on 'root_cause_result' channel")
        
        try:
            pubsub = self.redis_client.pubsub()
            pubsub.subscribe("root_cause_result")
            
            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        # Parse the incoming message
                        root_cause_data = json.loads(message['data'])
                        alert_id = root_cause_data.get("alert_id", "unknown")
                        logger.info(f"[RunbookAgent] Processing root cause results for alert ID: {alert_id}")
                        
                        # We need to fetch the original alert data
                        # First try to get it from Redis cache
                        alert_data_str = self.redis_client.get(f"alert:{alert_id}")
                        
                        if alert_data_str:
                            alert_data = json.loads(alert_data_str)
                        else:
                            # Request the alert data from the orchestrator if not in cache
                            self.redis_client.publish("alert_data_request", json.dumps({"alert_id": alert_id}))
                            logger.info(f"[RunbookAgent] Requested alert data for alert ID: {alert_id}")
                            
                            # Wait for the response with a timeout
                            response_pubsub = self.redis_client.pubsub()
                            response_pubsub.subscribe(f"alert_data_response:{alert_id}")
                            
                            # Wait for up to 10 seconds for a response
                            import time
                            start_time = time.time()
                            alert_data = None
                            
                            while time.time() - start_time < 10:
                                message = response_pubsub.get_message(timeout=1)
                                if message and message['type'] == 'message':
                                    alert_data = json.loads(message['data'])
                                    break
                                time.sleep(0.1)
                            
                            if not alert_data:
                                logger.error(f"[RunbookAgent] Timed out waiting for alert data for alert ID: {alert_id}")
                                continue
                        
                        # Fetch the runbook for this alert using our new tools
                        runbook_data = self.fetch_runbook(alert_data)
                        
                        # Use crewAI to enhance the runbook using root cause analysis
                        enhanced_runbook = self.enhance_runbook(root_cause_data, runbook_data, alert_data)
                        
                        # Prepare and publish the enhanced runbook
                        result = {
                            "agent": "runbook",
                            "alert_id": alert_id,
                            "enhanced_runbook": str(enhanced_runbook),
                            "original_runbook": runbook_data,
                            "timestamp": self._get_current_timestamp()
                        }
                        
                        self.redis_client.publish("enhanced_runbook", json.dumps(result))
                        logger.info(f"[RunbookAgent] Published enhanced runbook for alert ID: {alert_id}")
                    
                    except json.JSONDecodeError as e:
                        logger.error(f"[RunbookAgent] Error decoding JSON data: {str(e)}")
                    except Exception as e:
                        logger.error(f"[RunbookAgent] Error processing message: {str(e)}", exc_info=True)
        
        except redis.RedisError as e:
            logger.error(f"[RunbookAgent] Redis connection error: {str(e)}")
            # Wait and attempt to reconnect
            import time
            time.sleep(5)
            logger.info("[RunbookAgent] Attempting to reconnect to Redis...")
            self.redis_client = redis.Redis(host=self.redis_host, port=self.redis_port)
            self.listen()  # Recursive call to restart listening
    
    def _get_current_timestamp(self):
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"