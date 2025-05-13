import os
import json
import logging
import asyncio
import nats
from nats.js.api import ConsumerConfig, DeliverPolicy
from datetime import datetime
from crewai import Agent, Task, Crew
from crewai.tasks import TaskOutput
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from common.tools.deployment_tools import (
    GitChangeTool,
    ArgoCDTool,
    KubeDeploymentTool
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class DeploymentAgent:
    def __init__(self, argocd_server="https://argocd-server.argocd:443", 
                 git_repo_path="/app/repo", nats_server="nats://nats:4222"):
        # NATS connection parameters
        self.nats_server = nats_server
        self.nats_client = None
        self.js = None  # JetStream context
        
        # Deployment tools configuration
        self.argocd_server = argocd_server
        self.git_repo_path = git_repo_path
        
        # OpenAI API key from environment
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY environment variable not set")
        
        # Initialize OpenAI model
        self.llm = ChatOpenAI(model=os.environ.get("OPENAI_MODEL", "gpt-4"))
        
        # Initialize deployment tools
        self.git_tool = GitChangeTool(repo_path=self.git_repo_path)
        self.argocd_tool = ArgoCDTool(server=self.argocd_server)
        self.kube_tool = KubeDeploymentTool()
        
        # Create a crewAI agent for deployment analysis
        self.deployment_analyzer = Agent(
            role="Deployment Analyzer",
            goal="Analyze deployment configurations and recent changes to identify issues",
            backstory="You are an expert at analyzing deployment configurations, git changes, and ArgoCD state to identify issues with deployments.",
            verbose=True,
            llm=self.llm,
            tools=[
                self.git_tool.execute, 
                self.argocd_tool.execute,
                self.kube_tool.execute
            ]
        )
    
    async def connect(self):
        """Connect to NATS server and set up JetStream"""
        # Connect to NATS server
        self.nats_client = await nats.connect(self.nats_server)
        logger.info(f"Connected to NATS server at {self.nats_server}")
        
        # Create JetStream context
        self.js = self.nats_client.jetstream()
        
        # Ensure streams exist
        try:
            # Create stream for agent tasks
            await self.js.add_stream(
                name="AGENT_TASKS", 
                subjects=["deployment_agent"]
            )
            logger.info("Created or confirmed AGENT_TASKS stream")
            
            # Create stream for responses
            await self.js.add_stream(
                name="RESPONSES", 
                subjects=["orchestrator_response"]
            )
            logger.info("Created or confirmed RESPONSES stream")
            
        except nats.errors.Error as e:
            # Stream might already exist
            logger.info(f"Stream setup: {str(e)}")
    
    def _determine_observed_issue(self, alert, deployment_data):
        """Determine the type of deployment issue observed based on the alert and deployment data"""
        alert_name = alert.get("labels", {}).get("alertname", "").lower()
        
        if "failed" in alert_name or "failure" in alert_name:
            return "Deployment failure"
        elif "config" in alert_name:
            return "Configuration issue"
        elif "rollback" in alert_name:
            return "Rollback triggered"
        elif "version" in alert_name:
            return "Version mismatch"
        elif "health" in alert_name:
            return "Unhealthy deployment"
        else:
            # Fallback to a generic issue
            return "Deployment configuration issue"
    
    def _create_deployment_analysis_task(self, alert):
        """Create a deployment analysis task for the crew"""
        alert_id = alert.get("alert_id", "unknown")
        alert_name = alert.get("labels", {}).get("alertname", "Unknown Alert")
        service = alert.get("labels", {}).get("service", "")
        namespace = alert.get("labels", {}).get("namespace", "default")
        
        task = Task(
            description=f"""
            Analyze the deployment status and configuration for alert: {alert_name} (ID: {alert_id})
            
            Service: {service}
            Namespace: {namespace}
            
            Perform the following:
            1. Check recent Git changes for the service
            2. Analyze ArgoCD deployment status if available
            3. Check Kubernetes deployment configuration and status
            
            In your analysis, focus on:
            1. Recent configuration changes that might have caused issues
            2. Deployment status and health
            3. Configuration inconsistencies
            4. Resource constraints or misconfigurations
            5. Correlations between deployment changes and the alert
            
            Return a comprehensive analysis of what the deployment data shows, potential causes, and any recommended further investigation.
            """,
            agent=self.deployment_analyzer,
            expected_output="A detailed analysis of the deployment configuration and status related to the alert"
        )
        
        return task
    
    async def analyze_deployment_config(self, alert):
        """Analyze deployment configuration using crewAI"""
        logger.info(f"Analyzing deployment configuration for alert ID: {alert.get('alert_id', 'unknown')}")
        
        # Create deployment analysis task
        task = self._create_deployment_analysis_task(alert)
        
        # Create crew with deployment analyzer
        crew = Crew(
            agents=[self.deployment_analyzer],
            tasks=[task],
            verbose=True
        )
        
        # Execute crew analysis
        result = crew.kickoff()
        
        # Return both the analysis result and some metadata
        deployment_data = {
            "service": alert.get("labels", {}).get("service", ""),
            "namespace": alert.get("labels", {}).get("namespace", "default")
        }
        
        return result, deployment_data
    
    async def message_handler(self, msg):
        """Handle incoming NATS messages"""
        try:
            # Parse the alert data
            alert = json.loads(msg.data.decode())
            logger.info(f"[DeploymentAgent] Processing alert: {alert.get('alert_id', 'unknown')}")
            
            # Use crewAI to analyze the deployment
            analysis_result, deployment_data = await self.analyze_deployment_config(alert)
            
            # Determine what type of deployment issue was observed
            observed_issue = self._determine_observed_issue(alert, deployment_data)
            
            # Prepare result for the orchestrator
            result = {
                "agent": "deployment", 
                "observed": observed_issue,
                "analysis": str(analysis_result),
                "alert_id": alert.get("alert_id", "unknown"),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            logger.info(f"[DeploymentAgent] Sending analysis for alert ID: {result['alert_id']}")
            
            # Publish result to orchestrator
            await self.js.publish("orchestrator_response", json.dumps(result).encode())
            logger.info(f"[DeploymentAgent] Published analysis result for alert ID: {result['alert_id']}")
            
            # Acknowledge the message
            await msg.ack()
            
        except Exception as e:
            logger.error(f"[DeploymentAgent] Error processing message: {str(e)}", exc_info=True)
            # Negative acknowledge the message so it can be redelivered
            await msg.nak()
    
    async def listen(self):
        """Listen for alerts from the orchestrator using NATS JetStream"""
        logger.info("[DeploymentAgent] Starting to listen for alerts")
        
        # Connect to NATS if not already connected
        if not self.nats_client or not self.nats_client.is_connected:
            await self.connect()
        
        # Create a durable consumer with a queue group for load balancing
        consumer_config = ConsumerConfig(
            durable_name="deployment_agent",
            deliver_policy=DeliverPolicy.ALL,
            ack_policy="explicit",
            max_deliver=5,  # Retry up to 5 times
            ack_wait=60,    # Wait 60 seconds for acknowledgment
        )
        
        # Subscribe to the stream with the consumer configuration
        await self.js.subscribe(
            "deployment_agent",
            cb=self.message_handler,
            queue="deployment_processors",
            config=consumer_config
        )
        
        logger.info("[DeploymentAgent] Subscribed to deployment_agent stream")
        
        # Keep the connection alive
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour, or until interrupted