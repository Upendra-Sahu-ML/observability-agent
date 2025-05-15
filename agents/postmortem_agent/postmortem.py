import os
import json
import logging
import asyncio
import nats
from nats.js.api import ConsumerConfig, DeliverPolicy
from datetime import datetime
from crewai import Agent, Task, Crew
from crewai.llm import LLM
from crewai.tools import tool
from crewai import process
from dotenv import load_dotenv
from common.tools.knowledge_tools import PostmortemTemplateTool, PostmortemGeneratorTool, RunbookUpdateTool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class PostmortemAgent:
    def __init__(self, template_dir="/templates", nats_server="nats://nats:4222"):
        # NATS connection parameters
        self.nats_server = nats_server
        self.nats_client = None
        self.js = None  # JetStream context
        
        # Template configuration
        self.template_dir = template_dir
        
        # OpenAI API key from environment
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY environment variable not set")
        
        # Initialize OpenAI model
        self.llm = LLM(model=os.environ.get("OPENAI_MODEL", "gpt-4"))
        
        # Initialize postmortem tools
        self.template_tool = PostmortemTemplateTool(template_dir=self.template_dir)
        self.generator_tool = PostmortemGeneratorTool()
        self.runbook_update_tool = RunbookUpdateTool()
        
        # Create specialized agents for different aspects of postmortem generation
        self.technical_analyst = Agent(
            role="Technical Incident Analyst",
            goal="Analyze technical details of incidents and determine precise root causes",
            backstory="You are an expert at parsing technical incident data and determining exact root causes with supporting evidence.",
            verbose=True,
            llm=self.llm,
            tools=[
                self.template_tool.get_template,
                self.generator_tool.generate_postmortem
            ]
        )
        
        self.impact_analyst = Agent(
            role="Business Impact Analyst",
            goal="Assess the business and user impact of incidents",
            backstory="You specialize in determining how incidents affect business operations, customers, and revenue.",
            verbose=True,
            llm=self.llm,
            tools=[
                self.template_tool.get_template,
                self.generator_tool.generate_postmortem
            ]
        )
        
        self.timeline_constructor = Agent(
            role="Incident Timeline Constructor",
            goal="Create detailed chronological timelines of incidents",
            backstory="You excel at organizing events in chronological order and identifying key inflection points during incidents.",
            verbose=True,
            llm=self.llm,
            tools=[
                self.template_tool.get_template,
                self.generator_tool.generate_postmortem
            ]
        )
        
        self.remediation_planner = Agent(
            role="Remediation Planner",
            goal="Develop comprehensive plans to prevent future incidents",
            backstory="You are an expert at converting incident learnings into actionable prevention plans and concrete followup items.",
            verbose=True,
            llm=self.llm,
            tools=[
                self.runbook_update_tool.update_runbook,
                self.runbook_update_tool.create_runbook
            ]
        )
        
        self.postmortem_editor = Agent(
            role="Postmortem Editor",
            goal="Create clear, comprehensive postmortem documents that synthesize all analyses",
            backstory="You excel at combining technical details, timelines, impact assessments, and remediation plans into cohesive, well-structured documents.",
            verbose=True,
            llm=self.llm,
            tools=[
                self.template_tool.fill_template,
                self.generator_tool.generate_postmortem
            ]
        )
        
        # Keep the original postmortem generator for backward compatibility
        self.postmortem_generator_agent = Agent(
            role="Postmortem Generator",
            goal="Generate comprehensive postmortem documents for incidents",
            backstory="You are an expert at creating detailed postmortem documents that capture incident details, root causes, and lessons learned.",
            verbose=True,
            llm=self.llm,
            tools=[
                # Template tools
                self.template_tool.get_template,
                self.template_tool.fill_template,
                
                # Generator tool
                self.generator_tool.generate_postmortem,
                
                # Runbook update tools
                self.runbook_update_tool.update_runbook,
                self.runbook_update_tool.create_runbook
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
                        subjects=["postmortem_agent"]
                    )
                    logger.info("Created AGENT_TASKS stream")
                else:
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
    
    def _get_current_timestamp(self):
        """Get current timestamp in ISO format"""
        return datetime.utcnow().isoformat() + "Z"
    
    async def fetch_alert_data(self, alert_id):
        """Fetch alert data from the orchestrator"""
        logger.info(f"[PostmortemAgent] Requesting alert data for alert ID: {alert_id}")
        
        # Request the alert data from the orchestrator
        request = {"alert_id": alert_id}
        await self.js.publish("alert_data_request", json.dumps(request).encode())
        
        # Create a consumer for the response
        consumer_config = ConsumerConfig(
            durable_name=f"postmortem_alert_data_{alert_id}",
            deliver_policy=DeliverPolicy.ALL,
            ack_policy="explicit",
            filter_subject=f"alert_data_response.{alert_id}"
        )
        
        # Subscribe to get the response
        sub = await self.js.subscribe(
            f"alert_data_response.{alert_id}",
            config=consumer_config
        )
        
        # Wait for the response with a timeout
        try:
            msg = await asyncio.wait_for(sub.next_msg(), timeout=10.0)
            alert_data = json.loads(msg.data.decode())
            await msg.ack()
            await sub.unsubscribe()
            logger.info(f"[PostmortemAgent] Received alert data for alert ID: {alert_id}")
            return alert_data
        except asyncio.TimeoutError:
            logger.warning(f"[PostmortemAgent] Timeout waiting for alert data for alert ID: {alert_id}")
            await sub.unsubscribe()
            return {"alert_id": alert_id, "error": "Timeout waiting for data"}
    
    def _create_specialized_postmortem_tasks(self, root_cause_data, alert_data):
        """Create specialized postmortem generation tasks for each analyst"""
        alert_id = root_cause_data.get("alert_id", "unknown")
        root_cause = root_cause_data.get("root_cause", "Unknown root cause")
        
        # Extract details from alert data
        service = alert_data.get("labels", {}).get("service", "unknown")
        severity = alert_data.get("labels", {}).get("severity", "unknown")
        description = alert_data.get("annotations", {}).get("description", "No description provided")
        
        # Common incident information that all agents will use
        incident_info = f"""
        ## Incident Information
        - Incident ID: {alert_id}
        - Service: {service}
        - Severity: {severity}
        - Description: {description}
        
        ## Root Cause Analysis
        {root_cause}
        """
        
        # Task for technical analysis
        technical_task = Task(
            description=incident_info + """
            Analyze the technical aspects of this incident:
            1. Identify the exact technical root cause and failure mechanisms
            2. Determine which systems and components were involved
            3. Explain how the systems failed and interacted during the incident
            4. Identify any technical debt or system limitations that contributed
            
            Format your analysis in markdown format, focusing on technical precision.
            """,
            agent=self.technical_analyst,
            expected_output="A technical analysis section for the postmortem"
        )
        
        # Task for impact analysis
        impact_task = Task(
            description=incident_info + """
            Analyze the business and user impact of this incident:
            1. Determine which users or customers were affected and how
            2. Quantify the impact (e.g., downtime, errors, latency)
            3. Assess any financial, reputation, or compliance implications
            4. Identify any customer or stakeholder communications needed
            
            Format your analysis in markdown format, focusing on clear impact statements.
            """,
            agent=self.impact_analyst,
            expected_output="An impact analysis section for the postmortem"
        )
        
        # Task for timeline construction
        timeline_task = Task(
            description=incident_info + """
            Construct a detailed timeline of this incident:
            1. When the incident began (based on available evidence)
            2. When it was detected and by what means
            3. Key actions taken during response
            4. Resolution timing and verification
            
            Present this as a chronological timeline in markdown format.
            """,
            agent=self.timeline_constructor,
            expected_output="A detailed incident timeline section for the postmortem"
        )
        
        # Task for remediation planning
        remediation_task = Task(
            description=incident_info + """
            Develop a comprehensive remediation and prevention plan:
            1. Immediate actions needed to prevent recurrence
            2. Medium-term improvements to increase resilience
            3. Long-term architectural or process changes
            4. Specific, actionable follow-up items with suggested owners
            
            Format your plan in markdown with clear, actionable items.
            """,
            agent=self.remediation_planner,
            expected_output="A remediation and prevention plan section for the postmortem"
        )
        
        # Task for final document compilation
        editor_task = Task(
            description="""
            As the Postmortem Editor, you will receive analyses from four specialists:
            1. Technical analysis of the root cause
            2. Business and user impact assessment
            3. Detailed incident timeline
            4. Remediation and prevention plan
            
            Your job is to compile these into a cohesive, well-structured postmortem document following this outline:
            1. Executive Summary - A brief overview synthesizing key points from all analyses
            2. Incident Timeline - From the timeline constructor
            3. Technical Root Cause - From the technical analyst
            4. Impact Assessment - From the impact analyst
            5. Mitigation Steps - Based on the timeline and technical analysis
            6. Prevention Measures - From the remediation planner
            7. Lessons Learned - Synthesize insights from all sections
            8. Action Items - From the remediation planner, organized by priority
            
            Format the document in professional Markdown format.
            """,
            agent=self.postmortem_editor,
            expected_output="A complete, well-structured postmortem document"
        )
        
        # Return all specialized tasks
        return [technical_task, impact_task, timeline_task, remediation_task, editor_task]
    
    def _create_postmortem_task(self, root_cause_data, alert_data):
        """Create a postmortem generation task for the crew (backward compatibility)"""
        alert_id = root_cause_data.get("alert_id", "unknown")
        root_cause = root_cause_data.get("root_cause", "Unknown root cause")
        
        # Extract details from alert data
        service = alert_data.get("labels", {}).get("service", "unknown")
        severity = alert_data.get("labels", {}).get("severity", "unknown")
        description = alert_data.get("annotations", {}).get("description", "No description provided")
        
        # Create the task for the postmortem writer
        task = Task(
            description=f"""
            Generate a comprehensive incident postmortem document for the following incident:
            
            ## Incident Information
            - Incident ID: {alert_id}
            - Service: {service}
            - Severity: {severity}
            - Description: {description}
            
            ## Root Cause Analysis
            {root_cause}
            
            Please create a detailed postmortem document that includes the following sections:
            1. Executive Summary - A brief overview of the incident
            2. Incident Timeline - When the incident was detected, acknowledged, and resolved
            3. Root Cause Analysis - Detailed explanation of what caused the incident
            4. Impact Assessment - What systems/users were affected and how
            5. Mitigation Steps - What was done to resolve the incident
            6. Prevention Measures - Steps to prevent similar incidents in the future
            7. Lessons Learned - Key takeaways from this incident
            8. Action Items - Specific tasks that should be completed to improve systems
            
            Format the document in Markdown format.
            """,
            agent=self.postmortem_generator_agent,
            expected_output="A comprehensive incident postmortem document in Markdown format"
        )
        
        return task
    
    async def generate_postmortem(self, root_cause_data, alert_data):
        """Generate a postmortem document using multi-agent crewAI"""
        logger.info(f"Generating postmortem for alert ID: {root_cause_data.get('alert_id', 'unknown')}")
        
        # Create specialized postmortem tasks
        specialized_tasks = self._create_specialized_postmortem_tasks(root_cause_data, alert_data)
        
        # Create crew with specialized agents and sequential process
        crew = Crew(
            agents=[
                self.technical_analyst,
                self.impact_analyst,
                self.timeline_constructor,
                self.remediation_planner,
                self.postmortem_editor
            ],
            tasks=specialized_tasks,
            verbose=True,
            process=process.Sequential()
        )
        
        # Execute crew analysis
        result = crew.kickoff()
        
        return result
    
    async def message_handler(self, msg):
        """Handle incoming NATS messages"""
        try:
            # Parse the incoming message
            root_cause_data = json.loads(msg.data.decode())
            alert_id = root_cause_data.get("alert_id", "unknown")
            logger.info(f"[PostmortemAgent] Processing root cause results for alert ID: {alert_id}")
            
            # Fetch the original alert data
            alert_data = await self.fetch_alert_data(alert_id)
            
            if "error" in alert_data:
                logger.error(f"[PostmortemAgent] Failed to get alert data: {alert_data['error']}")
                # Try to proceed with limited data
                alert_data = {"alert_id": alert_id}
            
            # Generate postmortem based on root cause and alert data
            postmortem_result = await self.generate_postmortem(root_cause_data, alert_data)
            
            # Prepare result for the orchestrator
            result = {
                "agent": "postmortem",
                "postmortem": str(postmortem_result),
                "alert_id": alert_id,
                "timestamp": self._get_current_timestamp()
            }
            
            # Publish result to orchestrator
            await self.js.publish("orchestrator_response", json.dumps(result).encode())
            logger.info(f"[PostmortemAgent] Published postmortem for alert ID: {alert_id}")
            
            # Acknowledge the message
            await msg.ack()
            
        except Exception as e:
            logger.error(f"[PostmortemAgent] Error processing message: {str(e)}", exc_info=True)
            # Negative acknowledge the message so it can be redelivered
            await msg.nak()
    
    async def listen(self):
        """Listen for root cause results and generate postmortem documents"""
        logger.info("[PostmortemAgent] Starting to listen for root cause results on 'root_cause_result' and 'postmortem_agent' channels")
        
        # Connect to NATS if not already connected
        if not self.nats_client or not self.nats_client.is_connected:
            await self.connect()
        
        # Create a durable consumer for root cause results
        root_cause_consumer = ConsumerConfig(
            durable_name="postmortem_root_cause",
            deliver_policy=DeliverPolicy.ALL,
            ack_policy="explicit",
            max_deliver=3
        )
        
        # Subscribe to the root cause results
        await self.js.subscribe(
            "root_cause_result",
            cb=self.message_handler,
            queue="postmortem_processors",
            config=root_cause_consumer
        )
        
        # Create a durable consumer for direct postmortem requests
        direct_consumer = ConsumerConfig(
            durable_name="postmortem_direct",
            deliver_policy=DeliverPolicy.ALL,
            ack_policy="explicit",
            max_deliver=3
        )
        
        # Subscribe to direct postmortem requests
        await self.js.subscribe(
            "postmortem_agent",
            cb=self.message_handler,
            queue="postmortem_processors",
            config=direct_consumer
        )
        
        logger.info("[PostmortemAgent] Subscribed to root_cause_result and postmortem_agent streams")
        
        # Keep the connection alive
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour, or until interrupted