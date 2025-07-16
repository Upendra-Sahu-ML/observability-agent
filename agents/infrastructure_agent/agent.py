"""
Consolidated Infrastructure Agent

This agent combines deployment and runbook functionality into a single efficient container.
It provides comprehensive infrastructure management including deployment analysis and
automated runbook execution while reducing operational complexity.
"""
import os
import json
import logging
import asyncio
import nats
from nats.js.api import ConsumerConfig, DeliverPolicy
from datetime import datetime, timezone
from typing import Any, Dict
from crewai import Agent, Task, Crew
from crewai.llm import LLM
from crewai.tools import tool
from crewai import Process
from dotenv import load_dotenv

# Import simplified tools manager
from common.simplified_tools import SimplifiedToolManager
from common.stream_config import get_publish_subject
from common.agent_status import start_agent_status_publishing

# Legacy tools for fallback (if needed)
from common.tools.git_tools import GitTools
from common.tools.argocd_tools import ArgoCDTools
from common.tools.kube_tools import KubernetesTools
from common.tools.deployment_tools import DeploymentTools
from common.tools.runbook_tools import RunbookSearchTool, RunbookExecutionTool
from common.tools.jetstream_runbook_source import JetstreamRunbookSource

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class InfrastructureAgent:
    """
    Consolidated agent that combines deployment and runbook management.
    
    This agent replaces the separate deployment_agent and runbook_agent
    with a single efficient implementation that provides end-to-end infrastructure
    management from deployment analysis to automated remediation.
    """
    
    def __init__(self, 
                 argocd_server="https://argocd-server.argocd:443",
                 git_repo_path="/app/repo",
                 runbook_dir="/runbooks",
                 nats_server="nats://nats:4222"):
        
        # NATS connection parameters
        self.nats_server = nats_server
        self.nats_client = None
        self.js = None  # JetStream context
        
        # Infrastructure configuration
        self.argocd_server = argocd_server
        self.git_repo_path = git_repo_path
        self.runbook_dir = runbook_dir
        
        # OpenAI API key from environment
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY environment variable not set")
        
        # Initialize OpenAI model
        self.llm = LLM(model=os.environ.get("OPENAI_MODEL", "gpt-4"))
        
        # Initialize simplified tool manager (15 essential tools instead of 50+)
        self.simplified_tools = SimplifiedToolManager(
            deployment_tools=DeploymentTools(),
            runbook_tools=RunbookExecutionTool()
        )
        
        # Initialize legacy tools for fallback if needed
        self._initialize_legacy_tools()
        
        # Agent status publisher (will be initialized after NATS connection)
        self.status_publisher = None
        
        # Create specialized analysis agents
        self._create_infrastructure_agents()
    
    def _initialize_legacy_tools(self):
        """Initialize legacy tools for fallback if simplified tools are unavailable"""
        # Deployment tools (from deployment_agent)
        self.git_tool = GitTools()
        self.argocd_tool = ArgoCDTools(argocd_api_url=self.argocd_server)
        self.kube_tool = KubernetesTools()
        self.deployment_tools = DeploymentTools()
        
        # Runbook tools (from runbook_agent)
        self.jetstream_runbook_source = JetstreamRunbookSource()
        self.runbook_search_tool = RunbookSearchTool(
            runbook_dir=self.runbook_dir,
            additional_sources=[self.jetstream_runbook_source]
        )
        self.runbook_execution_tool = RunbookExecutionTool()
    
    def _create_infrastructure_agents(self):
        """Create specialized agents for different infrastructure management domains"""
        
        # === COMPREHENSIVE DEPLOYMENT & CONFIGURATION ANALYST ===
        self.deployment_configuration_analyst = Agent(
            role="Infrastructure Deployment & Configuration Analyst",
            goal="Analyze deployment configurations, Git repository changes, ArgoCD application status, and Kubernetes cluster state to identify infrastructure-related issues that could be causing incidents",
            backstory="""You are an expert at analyzing infrastructure and deployment issues with deep knowledge of:
            
            **Git Repository Analysis**: Understanding code changes, configuration modifications, deployment manifest updates, and how recent commits might impact system behavior.
            
            **ArgoCD Deployment Management**: Analyzing GitOps deployment status, sync issues, application health, resource sync failures, and deployment rollout problems.
            
            **Kubernetes Cluster Analysis**: Understanding pod status, deployment configurations, service mesh issues, resource constraints, node problems, and cluster-level events.
            
            **Configuration Analysis**: Identifying misconfigurations in deployments, services, ingress, config maps, secrets, and how configuration drift affects system stability.
            
            **Infrastructure Correlation**: Understanding how infrastructure changes, deployment events, and configuration modifications can cascade to cause application-level alerts and incidents.""",
            verbose=True,  # Keep detailed for quality analysis
            llm=self.llm,
            tools=self.simplified_tools.get_tools_for_agent("infrastructure")
        )
        
        # === COMPREHENSIVE RUNBOOK MANAGER ===
        self.runbook_manager = Agent(
            role="Infrastructure Runbook Manager",
            goal="Find the most relevant runbooks for infrastructure issues, adapt them to specific incident contexts, and execute remediation steps safely to resolve deployment and infrastructure problems",
            backstory="""You are an expert at runbook management and infrastructure remediation with deep expertise in:
            
            **Runbook Discovery**: Finding the most appropriate runbooks from knowledge bases based on infrastructure analysis, alert types, and deployment issues.
            
            **Context Adaptation**: Customizing generic runbooks to address specific infrastructure problems, deployment failures, and configuration issues identified during analysis.
            
            **Safe Execution**: Executing runbook steps safely with proper validation, rollback capabilities, and monitoring for success or failure during remediation attempts.
            
            **Infrastructure Remediation**: Understanding deployment rollbacks, service restarts, configuration fixes, resource scaling, and other infrastructure remediation techniques.
            
            **Integration with Analysis**: Using deployment and configuration analysis findings to select and customize the most effective remediation approach.""",
            verbose=True,  # Keep detailed for quality analysis
            llm=self.llm,
            tools=self.simplified_tools.get_tools_for_agent("infrastructure")
        )
    
    async def connect(self):
        """Connect to NATS server and set up JetStream"""
        try:
            # Connect to NATS server
            self.nats_client = await nats.connect(self.nats_server)
            logger.info(f"[InfrastructureAgent] Connected to NATS server at {self.nats_server}")
            
            # Create JetStream context
            self.js = self.nats_client.jetstream()
            
            # Initialize agent status publisher
            try:
                self.status_publisher = await start_agent_status_publishing(
                    agent_id="infrastructure-agent",
                    agent_name="Infrastructure Agent",
                    js=self.js,
                    publish_interval=30  # Publish status every 30 seconds
                )
                logger.info("[InfrastructureAgent] Agent status publishing started")
            except Exception as e:
                logger.warning(f"[InfrastructureAgent] Failed to start agent status publishing: {e}")
            
            # Set JetStream client in the runbook source
            self.jetstream_runbook_source.set_js(self.js)
            logger.info("[InfrastructureAgent] JetStream client set in runbook source")
            
            return True
            
        except Exception as e:
            logger.error(f"[InfrastructureAgent] Failed to connect to NATS: {str(e)}", exc_info=True)
            raise
    
    def _determine_infrastructure_issue(self, alert, analysis_results):
        """Determine the primary infrastructure issue based on analysis results"""
        alert_name = alert.get("labels", {}).get("alertname", "").lower()
        
        # Combine all analysis results
        combined_analysis = "\n".join([
            str(result) for result in analysis_results.values() if result
        ]).lower()
        
        # Priority-based issue classification for infrastructure
        if "deployment" in combined_analysis and ("failed" in combined_analysis or "error" in combined_analysis):
            return "Deployment failure detected"
        elif "configuration" in combined_analysis and ("mismatch" in combined_analysis or "invalid" in combined_analysis):
            return "Configuration issue identified"
        elif "rollback" in combined_analysis:
            return "Rollback required"
        elif "version" in combined_analysis and ("conflict" in combined_analysis or "mismatch" in combined_analysis):
            return "Version compatibility issue"
        elif "resource" in combined_analysis and ("limit" in combined_analysis or "quota" in combined_analysis):
            return "Resource constraint detected"
        elif "health" in combined_analysis and ("unhealthy" in combined_analysis or "failing" in combined_analysis):
            return "Service health issue"
        elif "sync" in combined_analysis and ("failed" in combined_analysis or "error" in combined_analysis):
            return "ArgoCD sync failure"
        else:
            # Fall back to alert-based categorization
            if "deployment" in alert_name:
                return "Deployment-related alert"
            elif "config" in alert_name:
                return "Configuration alert"
            elif "resource" in alert_name:
                return "Resource alert"
            else:
                return "Infrastructure anomaly detected"
    
    def _create_infrastructure_tasks(self, alert, context_data=None):
        """Create comprehensive infrastructure analysis and remediation tasks"""
        alert_id = alert.get("alert_id", "unknown")
        alert_name = alert.get("labels", {}).get("alertname", "Unknown Alert")
        service = alert.get("labels", {}).get("service", "")
        namespace = alert.get("labels", {}).get("namespace", "default")
        
        # Base context information
        base_context = f"""
        Alert: {alert_name} (ID: {alert_id})
        Service: {service}
        Namespace: {namespace}
        """
        
        if context_data:
            base_context += f"\nAdditional Context: {json.dumps(context_data, indent=2)}"
        
        # === DEPLOYMENT ANALYSIS TASK ===
        deployment_analysis_task = Task(
            description=base_context + """
            Perform comprehensive deployment analysis:
            
            1. Check recent Git changes for the service repository
            2. Analyze ArgoCD application status and sync history
            3. Examine Kubernetes deployment configuration and status
            4. Review deployment events and pod status
            5. Compare current deployment with previous stable versions
            6. Identify configuration changes that might have caused issues
            
            Focus on:
            - Recent configuration changes and their impact
            - Deployment status and health indicators
            - Resource constraints or misconfigurations
            - Version compatibility issues
            - Rollback feasibility and requirements
            
            Provide detailed findings about deployment-related causes of the alert.
            """,
            agent=self.deployment_analyzer,
            expected_output="Comprehensive deployment analysis with specific configuration and deployment issues identified"
        )
        
        # === CONFIGURATION ANALYSIS TASK ===
        config_analysis_task = Task(
            description=base_context + """
            Analyze configuration changes and their infrastructure impact:
            
            1. Review configuration file changes in recent commits
            2. Compare current vs previous configuration states
            3. Identify misconfigurations or invalid settings
            4. Analyze resource allocation and limits
            5. Check environment variable and secret configurations
            
            Focus on:
            - Configuration drift from known good states
            - Resource allocation issues
            - Environment-specific configuration problems
            - Dependencies and service configuration mismatches
            
            Provide specific configuration issues that could cause the alert.
            """,
            agent=self.configuration_analyst,
            expected_output="Detailed configuration analysis with specific misconfigurations identified"
        )
        
        # === RUNBOOK SEARCH TASK ===
        runbook_search_task = Task(
            description=base_context + """
            After deployment and configuration analysis is complete, search for relevant runbooks:
            
            1. Search existing runbooks based on the identified infrastructure issues
            2. Find runbooks that match the alert type and service
            3. Prioritize runbooks by relevance to the specific problems found
            4. Consider runbooks for similar infrastructure issues
            5. Identify gaps where new runbooks might be needed
            
            Based on the deployment and configuration analysis findings, recommend the most appropriate runbooks for remediation.
            """,
            agent=self.runbook_finder,
            expected_output="List of relevant runbooks with prioritization for the infrastructure issues identified"
        )
        
        # === RUNBOOK ADAPTATION TASK ===
        runbook_adaptation_task = Task(
            description=base_context + """
            Based on the deployment analysis and found runbooks, create or adapt runbooks:
            
            1. Review the specific infrastructure issues identified
            2. Adapt existing runbooks for the current context
            3. Generate custom runbook steps if no suitable runbook exists
            4. Include specific service, namespace, and configuration details
            5. Add verification steps to confirm resolution
            6. Include rollback procedures if needed
            
            Create actionable runbook steps tailored to the specific infrastructure problems.
            """,
            agent=self.runbook_adapter,
            expected_output="Customized runbook with specific steps for the identified infrastructure issues"
        )
        
        # === ORCHESTRATION TASK ===
        orchestration_task = Task(
            description=base_context + """
            Orchestrate the complete infrastructure response:
            
            1. Synthesize findings from deployment and configuration analysis
            2. Evaluate the severity and urgency of infrastructure issues
            3. Determine the most appropriate remediation approach
            4. Coordinate runbook execution if automatic remediation is safe
            5. Provide comprehensive recommendations for manual intervention if needed
            6. Establish monitoring criteria for validating resolution
            
            Provide a coordinated infrastructure response plan with clear next steps.
            """,
            agent=self.infrastructure_orchestrator,
            expected_output="Comprehensive infrastructure response plan with prioritized remediation steps"
        )
        
        return [
            deployment_analysis_task,
            config_analysis_task,
            runbook_search_task,
            runbook_adaptation_task,
            orchestration_task
        ]
    
    async def analyze_infrastructure(self, alert, context_data=None):
        """Perform comprehensive infrastructure analysis and remediation planning"""
        logger.info(f"[InfrastructureAgent] Starting infrastructure analysis for alert ID: {alert.get('alert_id', 'unknown')}")
        
        # Create comprehensive infrastructure tasks
        tasks = self._create_infrastructure_tasks(alert, context_data)
        
        # Create crew with all infrastructure agents
        crew = Crew(
            agents=[
                self.deployment_analyzer,
                self.configuration_analyst,
                self.runbook_finder,
                self.runbook_adapter,
                self.infrastructure_orchestrator
            ],
            tasks=tasks,
            verbose=True,
            process=Process.sequential()  # Run in sequence for coordinated analysis
        )
        
        # Execute comprehensive analysis
        results = crew.kickoff()
        
        # Store data in appropriate streams for UI consumption
        await self._publish_infrastructure_data(alert, results)
        
        # Collect metadata about what was analyzed
        infrastructure_data = {
            "service": alert.get("labels", {}).get("service", ""),
            "namespace": alert.get("labels", {}).get("namespace", "default"),
            "argocd_server": self.argocd_server,
            "components_analyzed": ["deployment", "configuration", "runbooks"]
        }
        
        return results, infrastructure_data
    
    async def execute_runbook(self, runbook_data, execution_context):
        """Execute a runbook with the infrastructure context"""
        logger.info(f"[InfrastructureAgent] Executing runbook: {runbook_data.get('id', 'unknown')}")
        
        try:
            # Create runbook execution task
            execution_task = Task(
                description=f"""
                Execute the following runbook in the infrastructure context:
                
                Runbook: {runbook_data.get('title', 'Unknown')}
                Context: {json.dumps(execution_context, indent=2)}
                
                Steps to execute:
                {json.dumps(runbook_data.get('steps', []), indent=2)}
                
                For each step:
                1. Validate prerequisites and safety conditions
                2. Execute the step using appropriate infrastructure tools
                3. Verify the step completed successfully
                4. Monitor for any adverse effects
                5. Proceed to next step or abort if issues detected
                
                Provide detailed execution results and any issues encountered.
                """,
                agent=self.runbook_executor,
                expected_output="Detailed execution results with success/failure status for each step"
            )
            
            # Create execution crew
            execution_crew = Crew(
                agents=[self.runbook_executor],
                tasks=[execution_task],
                verbose=True
            )
            
            # Execute runbook
            execution_results = execution_crew.kickoff()
            
            # Publish execution results
            await self._publish_runbook_execution(runbook_data, execution_context, execution_results)
            
            return execution_results
            
        except Exception as e:
            logger.error(f"[InfrastructureAgent] Error executing runbook: {str(e)}", exc_info=True)
            return {"error": str(e), "status": "failed"}
    
    async def _publish_infrastructure_data(self, alert, analysis_results):
        """Publish infrastructure data to appropriate streams for UI consumption"""
        try:
            service = alert.get("labels", {}).get("service", "unknown")
            alert_id = alert.get("alert_id", "unknown")
            timestamp = datetime.now().isoformat()
            
            # Publish to DEPLOYMENTS stream
            deployment_data = {
                "alert_id": alert_id,
                "service": service,
                "timestamp": timestamp,
                "analysis": str(analysis_results),
                "agent": "infrastructure",
                "namespace": alert.get("labels", {}).get("namespace", "default")
            }
            await self.js.publish(f"deployments.{service}", json.dumps(deployment_data).encode())
            
            logger.info(f"[InfrastructureAgent] Published infrastructure data for service {service}")
            
        except Exception as e:
            logger.error(f"[InfrastructureAgent] Error publishing infrastructure data: {str(e)}", exc_info=True)
    
    async def _publish_runbook_execution(self, runbook_data, context, results):
        """Publish runbook execution results to appropriate streams"""
        try:
            execution_record = {
                "id": f"exec-{runbook_data.get('id', 'unknown')}-{int(datetime.now().timestamp())}",
                "runbook_id": runbook_data.get("id", "unknown"),
                "runbook_title": runbook_data.get("title", "Unknown"),
                "context": context,
                "results": str(results),
                "timestamp": datetime.now().isoformat(),
                "agent": "infrastructure"
            }
            
            await self.js.publish("runbook.execution.infrastructure", json.dumps(execution_record).encode())
            logger.info(f"[InfrastructureAgent] Published runbook execution results")
            
        except Exception as e:
            logger.error(f"[InfrastructureAgent] Error publishing runbook execution: {str(e)}", exc_info=True)
    
    async def message_handler(self, msg):
        """Handle incoming NATS messages for infrastructure analysis"""
        try:
            # Parse the message data
            data = json.loads(msg.data.decode())
            
            # Handle different message types
            if "alert_id" in data:
                # This is an alert for infrastructure analysis
                await self._handle_alert_message(data, msg)
            elif "runbook_id" in data:
                # This is a runbook execution request
                await self._handle_runbook_execution(data, msg)
            else:
                logger.warning(f"[InfrastructureAgent] Unknown message type: {data}")
                await msg.ack()
                
        except Exception as e:
            logger.error(f"[InfrastructureAgent] Error processing message: {str(e)}", exc_info=True)
            await msg.nak()
    
    async def _handle_alert_message(self, alert, msg):
        """Handle alert messages for infrastructure analysis"""
        try:
            # Ensure alert_id is set
            if 'alert_id' not in alert and 'id' in alert:
                alert['alert_id'] = alert['id']
            
            logger.info(f"[InfrastructureAgent] Processing alert: {alert.get('alert_id', 'unknown')}")
            
            # Perform comprehensive infrastructure analysis
            analysis_results, infrastructure_data = await self.analyze_infrastructure(alert)
            
            # Determine the primary infrastructure issue
            observed_issue = self._determine_infrastructure_issue(alert, analysis_results)
            
            # Prepare result for the orchestrator
            result = {
                "agent": "infrastructure",
                "observed": observed_issue,
                "analysis": {
                    "deployment": str(analysis_results),
                    "configuration": str(analysis_results),
                    "runbooks": str(analysis_results)
                },
                "alert_id": alert.get("alert_id", "unknown"),
                "timestamp": datetime.now().isoformat(),
                "infrastructure_data": infrastructure_data
            }
            
            logger.info(f"[InfrastructureAgent] Sending analysis for alert ID: {result['alert_id']}")
            
            # Publish result to orchestrator
            await self.js.publish(get_publish_subject("orchestrator_response"), json.dumps(result).encode())
            logger.info(f"[InfrastructureAgent] Published analysis result for alert ID: {result['alert_id']}")
            
            # Acknowledge the message
            await msg.ack()
            
        except Exception as e:
            logger.error(f"[InfrastructureAgent] Error processing alert: {str(e)}", exc_info=True)
            await msg.nak()
    
    async def _handle_runbook_execution(self, execution_request, msg):
        """Handle runbook execution requests"""
        try:
            logger.info(f"[InfrastructureAgent] Processing runbook execution: {execution_request.get('runbook_id', 'unknown')}")
            
            # Execute the runbook
            execution_results = await self.execute_runbook(
                execution_request.get("runbook", {}),
                execution_request.get("context", {})
            )
            
            # Acknowledge the message
            await msg.ack()
            
        except Exception as e:
            logger.error(f"[InfrastructureAgent] Error executing runbook: {str(e)}", exc_info=True)
            await msg.nak()
    
    async def listen(self):
        """Listen for infrastructure analysis requests and runbook executions"""
        logger.info("[InfrastructureAgent] Starting to listen for infrastructure requests")
        
        try:
            # Connect to NATS if not already connected
            if not self.nats_client or not self.nats_client.is_connected:
                await self.connect()
            
            # Create consumer for infrastructure analysis
            analysis_consumer_config = ConsumerConfig(
                durable_name="infrastructure_agent",
                deliver_policy=DeliverPolicy.ALL,
                ack_policy="explicit",
                max_deliver=5,  # Retry up to 5 times
                ack_wait=180,   # Wait 3 minutes for acknowledgment (infrastructure operations can take time)
            )
            
            # Subscribe to infrastructure analysis requests
            await self.js.subscribe(
                "infrastructure_agent",  # New consolidated subject
                cb=self.message_handler,
                queue="infrastructure_processors",
                stream="AGENT_TASKS",
                config=analysis_consumer_config
            )
            
            logger.info("[InfrastructureAgent] Subscribed to infrastructure_agent subject")
            
            # Create consumer for runbook execution requests
            execution_consumer_config = ConsumerConfig(
                durable_name="infrastructure_runbook_executor",
                deliver_policy=DeliverPolicy.ALL,
                ack_policy="explicit",
                max_deliver=3,  # Retry up to 3 times
                ack_wait=120,   # Wait 2 minutes for acknowledgment
            )
            
            # Subscribe to runbook execution requests
            await self.js.subscribe(
                "runbook.execute.infrastructure",
                cb=self.message_handler,
                queue="infrastructure_executors",
                stream="RUNBOOK_EXECUTIONS",
                config=execution_consumer_config
            )
            
            logger.info("[InfrastructureAgent] Subscribed to runbook execution requests")
            
            # Keep the connection alive
            while True:
                await asyncio.sleep(3600)  # Sleep for an hour, or until interrupted
                logger.info("[InfrastructureAgent] Still listening for infrastructure requests")
                
        except Exception as e:
            logger.error(f"[InfrastructureAgent] Error in listen(): {str(e)}", exc_info=True)
            # Stop status publishing if there's an error
            if self.status_publisher:
                try:
                    await self.status_publisher.stop_publishing()
                    logger.info("[InfrastructureAgent] Agent status publishing stopped")
                except Exception as pub_e:
                    logger.warning(f"[InfrastructureAgent] Error stopping status publisher: {pub_e}")
            # Wait and retry
            logger.info("[InfrastructureAgent] Will retry in 30 seconds...")
            await asyncio.sleep(30)
            # Try calling listen again after delay
            return await self.listen()

if __name__ == "__main__":
    async def main():
        agent = InfrastructureAgent()
        await agent.listen()
    
    asyncio.run(main())