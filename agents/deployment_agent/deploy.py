import os
import json
import logging
import asyncio
import nats
from nats.js.api import ConsumerConfig, DeliverPolicy
from datetime import datetime
from typing import Any, Dict
from crewai import Agent, Task, Crew
from crewai.llm import LLM
from crewai.tools import tool
from dotenv import load_dotenv
from common.tools.git_tools import GitTools
from common.tools.argocd_tools import ArgoCDTools
from common.tools.kube_tools import KubernetesTools
from common.tools.deployment_tools import DeploymentTools

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
        self.llm = LLM(model=os.environ.get("OPENAI_MODEL", "gpt-4"))
        
        # Initialize deployment tools
        self.git_tool = GitTools()
        self.argocd_tool = ArgoCDTools(argocd_api_url=self.argocd_server)
        self.kube_tool = KubernetesTools()
        self.deployment_status_tool = DeploymentTools()
        
        # Create a crewAI agent for deployment management with direct references to tool methods
        self.deployment_manager = Agent(
            role="Deployment Manager",
            goal="Monitor and manage deployments to ensure system stability",
            backstory="You are an expert at managing deployments and ensuring smooth rollouts while maintaining system stability.",
            verbose=True,
            llm=self.llm,
            tools=[
                # Git tools for repository analysis
                self.git_tool.get_recent_commits,
                self.git_tool.get_commit_diff,
                self.git_tool.get_file_history,
                self.git_tool.get_file_at_commit,
                self.git_tool.get_modified_files,
                self.git_tool.get_branches,
                
                # ArgoCD tools for deployment management
                self.argocd_tool.get_application,
                self.argocd_tool.get_application_resource_tree,
                self.argocd_tool.get_application_events,
                self.argocd_tool.get_application_sync_status,
                self.argocd_tool.get_project,
                self.argocd_tool.sync_application,
                
                # Kubernetes tools for cluster analysis
                self.kube_tool.get_deployments,
                self.kube_tool.get_pods,
                self.kube_tool.get_pod_logs,
                self.kube_tool.get_deployment_events,
                self.kube_tool.get_service,
                self.kube_tool.get_pod_metrics,
                self.kube_tool.get_namespaces,
                self.kube_tool.get_nodes,
                
                # DeploymentTools for deployment analysis
                self.deployment_status_tool.list_deployments,
                self.deployment_status_tool.get_deployment_history,
                self.deployment_status_tool.check_deployment_status,
                self.deployment_status_tool.analyze_deployment_failures,
                self.deployment_status_tool.compare_deployments,
                self.deployment_status_tool.rollback_deployment,
                self.deployment_status_tool.get_deployment_metrics,
                self.deployment_status_tool.list_deployment_events
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
                
                # Only create AGENT_TASKS stream if it doesn't already exist
                if "AGENT_TASKS" not in stream_names:
                    await self.js.add_stream(
                        name="AGENT_TASKS", 
                        subjects=["agent.>", "deployment_agent"]
                    )
                    logger.info("Created AGENT_TASKS stream")
                else:
                    # Update the stream to ensure it includes our subject
                    try:
                        stream_info = await self.js.stream_info("AGENT_TASKS")
                        current_subjects = stream_info.config.subjects
                        
                        if "deployment_agent" not in current_subjects:
                            # Add our subject to the existing list
                            new_subjects = current_subjects + ["deployment_agent"]
                            await self.js.update_stream(
                                config={"name": "AGENT_TASKS", "subjects": new_subjects}
                            )
                            logger.info("Updated AGENT_TASKS stream to include deployment_agent subject")
                    except Exception as e:
                        logger.warning(f"Failed to update AGENT_TASKS stream: {str(e)}")
                        
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
            agent=self.deployment_manager,
            expected_output="A detailed analysis of the deployment configuration and status related to the alert"
        )
        
        return task
    
    async def analyze_deployment_config(self, alert):
        """Analyze deployment configuration using crewAI"""
        logger.info(f"Analyzing deployment configuration for alert ID: {alert.get('alert_id', 'unknown')}")
        
        # Create deployment analysis task
        task = self._create_deployment_analysis_task(alert)
        
        # Create crew with deployment manager
        crew = Crew(
            agents=[self.deployment_manager],
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
        
        try:
            # First check if the AGENT_TASKS stream exists
            stream_exists = False
            try:
                stream_info = await self.js.stream_info("AGENT_TASKS")
                if "deployment_agent" in stream_info.config.subjects:
                    stream_exists = True
                    logger.info("[DeploymentAgent] AGENT_TASKS stream found with deployment_agent subject")
                else:
                    # Try to update the stream to include our subject
                    try:
                        current_subjects = stream_info.config.subjects
                        new_subjects = current_subjects + ["deployment_agent"]
                        await self.js.update_stream(
                            name="AGENT_TASKS",
                            subjects=new_subjects
                        )
                        stream_exists = True
                        logger.info("[DeploymentAgent] Updated AGENT_TASKS stream to include deployment_agent subject")
                    except Exception as e:
                        logger.warning(f"[DeploymentAgent] Failed to update AGENT_TASKS stream: {str(e)}")
            except nats.js.errors.NotFoundError:
                logger.warning("[DeploymentAgent] AGENT_TASKS stream not found, will create it")
            except Exception as e:
                logger.warning(f"[DeploymentAgent] Error checking stream: {str(e)}")
            
            # If stream doesn't exist or didn't have our subject, create it
            if not stream_exists:
                try:
                    # Create the stream explicitly
                    await self.js.add_stream(
                        name="AGENT_TASKS",
                        subjects=["deployment_agent", "metric_agent", "log_agent", "tracing_agent", 
                                 "root_cause_agent", "notification_agent", "postmortem_agent", "runbook_agent"]
                    )
                    logger.info("[DeploymentAgent] Created AGENT_TASKS stream")
                    stream_exists = True
                except nats.js.errors.BadRequestError as e:
                    if "already in use" in str(e):
                        # Stream exists but maybe with different subjects
                        logger.info("[DeploymentAgent] AGENT_TASKS stream already exists")
                        stream_exists = True
                    else:
                        logger.error(f"[DeploymentAgent] Failed to create AGENT_TASKS stream: {str(e)}")
                except Exception as e:
                    logger.error(f"[DeploymentAgent] Failed to create AGENT_TASKS stream: {str(e)}")
            
            # Only proceed with subscription if the stream exists
            if stream_exists:
                # Subscribe to the stream with the consumer configuration
                subscription = await self.js.subscribe(
                    "deployment_agent",
                    cb=self.message_handler,
                    queue="deployment_processors",
                    config=consumer_config
                )
                
                logger.info("[DeploymentAgent] Subscribed to deployment_agent stream")
                
                # Keep the connection alive
                while True:
                    await asyncio.sleep(3600)  # Sleep for an hour, or until interrupted
            else:
                logger.error("[DeploymentAgent] Cannot subscribe: AGENT_TASKS stream not available")
                # Retry periodically
                while True:
                    logger.info("[DeploymentAgent] Will retry stream setup in 30 seconds...")
                    await asyncio.sleep(30)
                    # Try calling listen again after delay
                    return await self.listen()
                    
        except nats.js.errors.NotFoundError as e:
            logger.error(f"[DeploymentAgent] Stream not found error: {str(e)}")
            # Wait and retry
            logger.info("[DeploymentAgent] Will retry stream setup in 30 seconds...")
            await asyncio.sleep(30)
            # Try calling listen again after delay
            return await self.listen()
            
        except Exception as e:
            logger.error(f"[DeploymentAgent] Unexpected error in listen(): {str(e)}", exc_info=True)
            # Wait and retry
            logger.info("[DeploymentAgent] Will retry in 30 seconds...")
            await asyncio.sleep(30)
            # Try calling listen again after delay
            return await self.listen()