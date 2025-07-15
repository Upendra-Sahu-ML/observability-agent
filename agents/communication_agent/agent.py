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
# Import simplified tools manager
from common.simplified_tools import SimplifiedToolManager

# Legacy tools for fallback (if needed)
from common.tools.notification_tools import NotificationTools
from common.tools.knowledge_tools import PostmortemTemplateTool, PostmortemGeneratorTool, RunbookUpdateTool
from common.tools.status_tools import StatusPublisher

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class CommunicationAgent:
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
        
        # Initialize simplified tool manager (15 essential tools instead of 50+)
        self.simplified_tools = SimplifiedToolManager(
            notification_tools=NotificationTools()
        )
        
        # Initialize legacy tools for fallback if needed
        self._initialize_legacy_tools()
        
        # Create specialized agents for different aspects of communication
        self._create_communication_agents()
    
    def _initialize_legacy_tools(self):
        """Initialize legacy tools for fallback if simplified tools are unavailable"""
        # Initialize notification tools
        self.notification_tools = NotificationTools()
        
        # Initialize postmortem tools
        self.template_tool = PostmortemTemplateTool(template_dir=self.template_dir)
        self.generator_tool = PostmortemGeneratorTool()
        self.runbook_update_tool = RunbookUpdateTool()
        
        # Initialize status publisher
        self.status_publisher = StatusPublisher(nats_server=self.nats_server)
        
    def _create_communication_agents(self):
        """Create specialized agents for communication tasks"""
        
        # Comprehensive Notification Manager
        self.notification_manager = Agent(
            role="Intelligent Notification Manager",
            goal="Analyze alert severity and context to determine appropriate notification channels, craft clear incident communications, and ensure the right people are notified through the most effective channels based on incident severity and impact",
            backstory="""You are an expert at incident communication and notification management with deep expertise in:
            
            **Alert Prioritization**: Understanding alert severity levels, business impact assessment, and determining urgency based on affected services, user impact, and system criticality.
            
            **Channel Strategy**: Knowing when to use different notification channels - Slack for team coordination, WebEx for management escalation, PagerDuty for on-call emergency response.
            
            **Message Crafting**: Creating clear, actionable incident notifications that include essential information like affected services, impact scope, severity level, and initial response actions.
            
            **Escalation Management**: Understanding escalation paths based on incident severity, response time requirements, and when to involve different teams or management levels.
            
            **Multi-Channel Coordination**: Managing notifications across multiple platforms to ensure consistent messaging and avoid communication gaps during incidents.""",
            verbose=True,  # Keep detailed for quality analysis
            llm=self.llm,
            tools=self.simplified_tools.get_tools_for_agent("communication")
        )
        
        # Comprehensive Postmortem Analyst
        self.postmortem_analyst = Agent(
            role="Comprehensive Postmortem Analyst",
            goal="Create detailed, actionable postmortem documents that analyze technical root causes, assess business impact, construct incident timelines, and develop comprehensive remediation plans to prevent future occurrences",
            backstory="""You are an expert at incident analysis and postmortem creation with deep expertise in:
            
            **Technical Root Cause Analysis**: Analyzing complex technical incidents, understanding system interactions, identifying the precise technical causes of failures, and distinguishing between root causes and contributing factors.
            
            **Business Impact Assessment**: Evaluating how technical incidents affect business operations, quantifying user impact, revenue implications, and customer experience degradation.
            
            **Timeline Construction**: Creating detailed chronological narratives of incidents, identifying key decision points, response actions, and the sequence of events that led to resolution.
            
            **Remediation Planning**: Developing comprehensive action plans to prevent recurrence, including immediate fixes, system improvements, process changes, and monitoring enhancements.
            
            **Document Creation**: Synthesizing complex technical analysis into clear, actionable postmortem documents that serve both technical teams and business stakeholders.""",
            verbose=True,  # Keep detailed for quality analysis
            llm=self.llm,
            tools=self.simplified_tools.get_tools_for_agent("communication")
        )
    
    async def connect(self):
        """Connect to NATS server and set up JetStream"""
        try:
            # Connect to NATS server
            self.nats_client = await nats.connect(self.nats_server)
            logger.info(f"Connected to NATS server at {self.nats_server}")
            
            # Create JetStream context
            self.js = self.nats_client.jetstream()
            
            # Initialize status publisher
            await self.status_publisher.connect()
            
            # Publish initial status
            await self.status_publisher.publish_status("communication", "starting", {
                "message": "Communication Agent initializing"
            })
            
            logger.info("Communication Agent connected and status published")
            
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {str(e)}")
            raise
    
    def _get_current_timestamp(self):
        """Get current timestamp in ISO format"""
        return datetime.utcnow().isoformat() + "Z"
    
    async def fetch_alert_data(self, alert_id):
        """Fetch alert data from the orchestrator"""
        logger.info(f"[CommunicationAgent] Requesting alert data for alert ID: {alert_id}")
        
        # Request the alert data from the orchestrator
        request = {"alert_id": alert_id}
        await self.js.publish("alert_data_request", json.dumps(request).encode())
        
        # Create a consumer for the response
        consumer_config = ConsumerConfig(
            durable_name=f"communication_alert_data_{alert_id}",
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
            logger.info(f"[CommunicationAgent] Received alert data for alert ID: {alert_id}")
            return alert_data
        except asyncio.TimeoutError:
            logger.warning(f"[CommunicationAgent] Timeout waiting for alert data for alert ID: {alert_id}")
            await sub.unsubscribe()
            return {"alert_id": alert_id, "error": "Timeout waiting for data"}
    
    def _create_notification_tasks(self, data):
        """Create notification tasks for immediate alert processing"""
        # Extract alert details
        alert_id = data.get("alert_id", "unknown")
        alert_name = data.get("labels", {}).get("alertname", "Unknown Alert")
        service = data.get("labels", {}).get("service", "unknown")
        severity = data.get("labels", {}).get("severity", "warning")
        description = data.get("annotations", {}).get("description", "No description provided")
        
        # Include any root cause analysis if available
        root_cause = data.get("root_cause", "Cause unknown - investigation in progress")
        
        # Common incident information
        incident_info = f"""
        ## Alert Information
        - Alert ID: {alert_id}
        - Alert Name: {alert_name}
        - Service: {service}
        - Severity: {severity}
        - Description: {description}
        - Root Cause: {root_cause}
        """
        
        # Task for alert prioritization
        prioritization_task = Task(
            description=incident_info + """
            Analyze this alert and determine the appropriate notification strategy:
            1. Which communication channels should be used (Slack, PagerDuty, WebEx)
            2. What is the appropriate urgency level
            3. Who should be notified (engineering, management, customers)
            4. What is the escalation timeline
            
            Base your decisions on the severity level and service impact.
            Return a JSON object with your recommendations.
            """,
            agent=self.alert_prioritizer,
            expected_output="A JSON object with notification strategy recommendations"
        )
        
        # Task for sending notifications
        notification_task = Task(
            description=incident_info + """
            Based on the prioritization analysis, send appropriate notifications:
            1. Format messages appropriately for each channel
            2. For Slack: Use formatting to highlight severity and include key details
            3. For PagerDuty: Ensure title is clear and actionable for on-call engineers
            4. For WebEx: Keep concise but informative for management updates
            
            Send notifications to the channels recommended by the Alert Prioritizer.
            Return a JSON object with the notification results and status.
            """,
            agent=self.notification_manager,
            expected_output="A JSON object with notification results and delivery status"
        )
        
        return [prioritization_task, notification_task]
    
    def _create_postmortem_tasks(self, root_cause_data, alert_data):
        """Create specialized postmortem generation tasks"""
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
        
        return [technical_task, impact_task, timeline_task, remediation_task, editor_task]
    
    async def process_notification(self, data):
        """Process a notification request using multi-agent analysis"""
        alert_id = data.get("alert_id", "unknown")
        logger.info(f"[CommunicationAgent] Processing notification for alert: {alert_id}")
        
        await self.status_publisher.publish_status("communication", "processing", {
            "alert_id": alert_id,
            "action": "notification"
        })
        
        # Create notification tasks
        notification_tasks = self._create_notification_tasks(data)
        
        # Create crew with notification agents
        crew = Crew(
            agents=[self.alert_prioritizer, self.notification_manager],
            tasks=notification_tasks,
            verbose=True,
            process=process.Sequential()
        )
        
        # Execute crew analysis
        result = crew.kickoff()
        
        # Prepare notification result
        notification_result = {
            "agent": "communication",
            "sub_function": "notification",
            "alert_id": alert_id,
            "timestamp": self._get_current_timestamp(),
            "result": str(result)
        }
        
        # Publish result to orchestrator
        await self.js.publish("orchestrator_response", json.dumps(notification_result).encode())
        logger.info(f"[CommunicationAgent] Published notification result for alert: {alert_id}")
        
        await self.status_publisher.publish_status("communication", "completed", {
            "alert_id": alert_id,
            "action": "notification",
            "result": "success"
        })
        
        return result
    
    async def generate_postmortem(self, root_cause_data, alert_data):
        """Generate a postmortem document using multi-agent analysis"""
        alert_id = root_cause_data.get("alert_id", "unknown")
        logger.info(f"[CommunicationAgent] Generating postmortem for alert ID: {alert_id}")
        
        await self.status_publisher.publish_status("communication", "processing", {
            "alert_id": alert_id,
            "action": "postmortem"
        })
        
        # Create specialized postmortem tasks
        postmortem_tasks = self._create_postmortem_tasks(root_cause_data, alert_data)
        
        # Create crew with postmortem agents and sequential process
        crew = Crew(
            agents=[
                self.technical_analyst,
                self.impact_analyst,
                self.timeline_constructor,
                self.remediation_planner,
                self.postmortem_editor
            ],
            tasks=postmortem_tasks,
            verbose=True,
            process=process.Sequential()
        )
        
        # Execute crew analysis
        result = crew.kickoff()
        
        await self.status_publisher.publish_status("communication", "completed", {
            "alert_id": alert_id,
            "action": "postmortem",
            "result": "success"
        })
        
        return result
    
    async def notification_message_handler(self, msg):
        """Handle incoming NATS messages for notifications"""
        try:
            # Decode the message data
            data = json.loads(msg.data.decode())
            alert_id = data.get("alert_id", "unknown")
            logger.info(f"[CommunicationAgent] Received notification request: {alert_id}")
            
            # Process the notification
            await self.process_notification(data)
            
            # Acknowledge the message
            await msg.ack()
            
        except Exception as e:
            logger.error(f"[CommunicationAgent] Error processing notification message: {str(e)}", exc_info=True)
            await self.status_publisher.publish_status("communication", "error", {
                "action": "notification",
                "error": str(e)
            })
            # Negative acknowledge the message so it can be redelivered
            await msg.nak()
    
    async def postmortem_message_handler(self, msg):
        """Handle incoming NATS messages for postmortem generation"""
        try:
            # Parse the incoming message
            root_cause_data = json.loads(msg.data.decode())
            alert_id = root_cause_data.get("alert_id", "unknown")
            logger.info(f"[CommunicationAgent] Processing postmortem for alert ID: {alert_id}")
            
            # Fetch the original alert data
            alert_data = await self.fetch_alert_data(alert_id)
            
            if "error" in alert_data:
                logger.error(f"[CommunicationAgent] Failed to get alert data: {alert_data['error']}")
                # Try to proceed with limited data
                alert_data = {"alert_id": alert_id}
            
            # Generate postmortem based on root cause and alert data
            postmortem_result = await self.generate_postmortem(root_cause_data, alert_data)
            
            # Prepare result for the orchestrator
            result = {
                "agent": "communication",
                "sub_function": "postmortem",
                "postmortem": str(postmortem_result),
                "alert_id": alert_id,
                "timestamp": self._get_current_timestamp()
            }
            
            # Publish result to orchestrator
            await self.js.publish("orchestrator_response", json.dumps(result).encode())
            logger.info(f"[CommunicationAgent] Published postmortem for alert ID: {alert_id}")
            
            # Acknowledge the message
            await msg.ack()
            
        except Exception as e:
            logger.error(f"[CommunicationAgent] Error processing postmortem message: {str(e)}", exc_info=True)
            await self.status_publisher.publish_status("communication", "error", {
                "action": "postmortem",
                "error": str(e)
            })
            # Negative acknowledge the message so it can be redelivered
            await msg.nak()
    
    async def communication_message_handler(self, msg):
        """Handle incoming NATS messages for the communication agent"""
        try:
            # Parse the incoming message
            data = json.loads(msg.data.decode())
            alert_id = data.get("alert_id", "unknown")
            task_type = data.get("task_type", "notification")  # Default to notification
            
            logger.info(f"[CommunicationAgent] Processing {task_type} for alert ID: {alert_id}")
            
            if task_type == "notification":
                await self.process_notification(data)
            elif task_type == "postmortem":
                # For postmortem, we need root cause data
                if "root_cause" in data:
                    root_cause_data = data
                    alert_data = await self.fetch_alert_data(alert_id)
                    if "error" in alert_data:
                        alert_data = {"alert_id": alert_id}
                    
                    postmortem_result = await self.generate_postmortem(root_cause_data, alert_data)
                    
                    result = {
                        "agent": "communication",
                        "sub_function": "postmortem",
                        "postmortem": str(postmortem_result),
                        "alert_id": alert_id,
                        "timestamp": self._get_current_timestamp()
                    }
                    
                    await self.js.publish("orchestrator_response", json.dumps(result).encode())
                    logger.info(f"[CommunicationAgent] Published postmortem for alert ID: {alert_id}")
                else:
                    logger.warning(f"[CommunicationAgent] Postmortem task missing root_cause data for alert: {alert_id}")
            else:
                logger.warning(f"[CommunicationAgent] Unknown task type: {task_type}")
            
            # Acknowledge the message
            await msg.ack()
            
        except Exception as e:
            logger.error(f"[CommunicationAgent] Error processing communication message: {str(e)}", exc_info=True)
            await self.status_publisher.publish_status("communication", "error", {
                "alert_id": data.get("alert_id", "unknown"),
                "error": str(e)
            })
            # Negative acknowledge the message so it can be redelivered
            await msg.nak()
    
    async def listen(self):
        """Listen for communication requests using NATS JetStream"""
        # Connect to NATS if not already connected
        if not self.nats_client or not self.nats_client.is_connected:
            await self.connect()
        
        logger.info("[CommunicationAgent] Starting to listen for communication requests")
        
        await self.status_publisher.publish_status("communication", "active", {
            "message": "Communication Agent listening for requests"
        })
        
        # Create consumer for consolidated communication agent
        communication_consumer = ConsumerConfig(
            durable_name="communication_agent",
            deliver_policy=DeliverPolicy.ALL,
            ack_policy="explicit",
            max_deliver=3
        )
        
        # Subscribe to the consolidated communication agent stream
        await self.js.subscribe(
            "communication_agent",
            cb=self.communication_message_handler,
            queue="communication_processors",
            config=communication_consumer,
            stream="AGENT_TASKS"
        )
        
        # Create consumer for notification requests (backward compatibility)
        notification_consumer = ConsumerConfig(
            durable_name="communication_notification",
            deliver_policy=DeliverPolicy.ALL,
            ack_policy="explicit",
            max_deliver=3
        )
        
        # Subscribe to notification requests
        await self.js.subscribe(
            "notification_requests",
            cb=self.notification_message_handler,
            queue="communication_processors",
            config=notification_consumer
        )
        
        # Create consumer for postmortem requests (from root cause results)
        postmortem_consumer = ConsumerConfig(
            durable_name="communication_postmortem",
            deliver_policy=DeliverPolicy.ALL,
            ack_policy="explicit",
            max_deliver=3
        )
        
        # Subscribe to root cause results for postmortem generation
        await self.js.subscribe(
            "root_cause_result",
            cb=self.postmortem_message_handler,
            queue="communication_processors",
            config=postmortem_consumer,
            stream="ROOT_CAUSE"
        )
        
        logger.info("[CommunicationAgent] Subscribed to communication_agent, notification_requests, and root_cause_result streams")
        
        # Keep the connection alive
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour, or until interrupted

async def main():
    """Main function to run the Communication Agent"""
    agent = CommunicationAgent()
    
    try:
        await agent.listen()
    except KeyboardInterrupt:
        logger.info("Communication Agent shutting down...")
    except Exception as e:
        logger.error(f"Communication Agent error: {e}")
    finally:
        if agent.nats_client:
            await agent.nats_client.close()

if __name__ == "__main__":
    asyncio.run(main())