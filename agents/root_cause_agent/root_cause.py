import os
import redis
import json
import logging
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class RootCauseAgent:
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
        
        # Root cause synthesizer agent - doesn't need direct tool access
        # It works purely with the analyses provided by specialized agents
        self.synthesizer = Agent(
            role="Root Cause Synthesizer",
            goal="Synthesize analyses from specialized agents to determine the most likely root cause",
            backstory="Expert at combining insights from multiple sources to identify the true cause of complex system issues.",
            verbose=True,
            llm=self.llm
        )

    def analyze_root_cause(self, comprehensive_data):
        """Analyze the root cause using the analyses provided by other agents"""
        
        # Extract the analyses provided by specialized agents
        metric_analysis = comprehensive_data.get('metrics', {}).get('analysis', 'No metric analysis available')
        log_analysis = comprehensive_data.get('logs', {}).get('analysis', 'No log analysis available')
        deployment_analysis = comprehensive_data.get('deployments', {}).get('analysis', 'No deployment analysis available')
        tracing_analysis = comprehensive_data.get('tracing', {}).get('analysis', 'No tracing analysis available')
        
        # Extract alert information for context
        alert_data = comprehensive_data.get('alert', {})
        service = alert_data.get('labels', {}).get('service', '')
        namespace = alert_data.get('labels', {}).get('namespace', 'default')
        
        # Create a synthesis task that uses the specialized agent analyses
        synthesis_task = Task(
            description=f"""
            Analyze and synthesize the following specialized analyses to determine the root cause:
            
            ALERT CONTEXT:
            Service: {service}
            Namespace: {namespace}
            Alert Data: {json.dumps(alert_data)}
            
            METRIC ANALYSIS:
            {metric_analysis}
            
            LOG ANALYSIS:
            {log_analysis}
            
            DEPLOYMENT ANALYSIS:
            {deployment_analysis}
            
            TRACING ANALYSIS:
            {tracing_analysis}
            
            Based on these analyses, determine the most likely root cause of the incident.
            Provide specific evidence from each analysis that supports your conclusion.
            Suggest remediation steps that address the identified root cause.
            """,
            agent=self.synthesizer,
            expected_output="Comprehensive root cause determination with high confidence, supporting evidence, and suggested remediation steps"
        )
        
        # Create crew with just the synthesizer agent
        crew = Crew(
            agents=[self.synthesizer],
            tasks=[synthesis_task],
            verbose=True
        )
        
        # Execute the crew workflow
        result = crew.kickoff()
        return result

    def listen(self):
        """Listen for comprehensive data from the orchestrator and publish root cause analysis"""
        logger.info("[RootCauseAgent] Starting to listen for comprehensive data on 'root_cause_analysis' channel")
        
        try:
            pubsub = self.redis_client.pubsub()
            pubsub.subscribe("root_cause_analysis")
            
            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        # Parse the incoming message
                        data = json.loads(message['data'])
                        alert_id = data.get("alert_id", "unknown")
                        logger.info(f"[RootCauseAgent] Processing comprehensive data for alert ID: {alert_id}")
                        
                        # Use crewAI to analyze root cause using the analyses from other agents
                        analysis_result = self.analyze_root_cause(data)
                        
                        # Prepare and publish result
                        result = {
                            "agent": "root_cause",
                            "root_cause": str(analysis_result),
                            "alert_id": alert_id,
                            "timestamp": self._get_current_timestamp()
                        }
                        
                        self.redis_client.publish("root_cause_result", json.dumps(result))
                        logger.info(f"[RootCauseAgent] Published root cause analysis result for alert ID: {alert_id}")
                    
                    except json.JSONDecodeError as e:
                        logger.error(f"[RootCauseAgent] Error decoding JSON data: {str(e)}")
                    except Exception as e:
                        logger.error(f"[RootCauseAgent] Error processing message: {str(e)}", exc_info=True)
        
        except redis.RedisError as e:
            logger.error(f"[RootCauseAgent] Redis connection error: {str(e)}")
            # Wait and attempt to reconnect
            import time
            time.sleep(5)
            logger.info("[RootCauseAgent] Attempting to reconnect to Redis...")
            self.redis_client = redis.Redis(host=self.redis_host, port=self.redis_port)
            self.listen()  # Recursive call to restart listening
    
    def _get_current_timestamp(self):
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"