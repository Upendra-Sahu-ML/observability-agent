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
from crewai import Process
from dotenv import load_dotenv
from common.tools.root_cause_tools import correlation_analysis, dependency_analysis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class RootCauseAgent:
    def __init__(self, nats_server="nats://nats:4222"):
        # NATS connection parameters
        self.nats_server = nats_server
        self.nats_client = None
        self.js = None  # JetStream context

        # OpenAI API key from environment
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY environment variable not set")

        # Initialize OpenAI model
        self.llm = LLM(model=os.environ.get("OPENAI_MODEL", "gpt-4"))

        # Create specialized agents for root cause analysis
        self.infrastructure_analyzer = Agent(
            role="Infrastructure Analyst",
            goal="Identify infrastructure-related causes of incidents",
            backstory="You analyze server, network, load balancer, and cloud infrastructure issues. You focus on hardware and system-level problems that could cause outages or performance degradation.",
            verbose=True,
            llm=self.llm,
            tools=[correlation_analysis, dependency_analysis]
        )

        self.application_analyzer = Agent(
            role="Application Analyst",
            goal="Identify application-level causes of incidents",
            backstory="You analyze code-level, memory, and runtime issues in applications. You focus on application bugs, memory leaks, and code performance problems.",
            verbose=True,
            llm=self.llm,
            tools=[correlation_analysis, dependency_analysis]
        )

        self.database_analyzer = Agent(
            role="Database Analyst",
            goal="Identify database-related causes of incidents",
            backstory="You analyze database performance, query issues, and data storage problems. You focus on slow queries, locking, and database resource constraints.",
            verbose=True,
            llm=self.llm,
            tools=[correlation_analysis, dependency_analysis]
        )

        self.network_analyzer = Agent(
            role="Network Analyst",
            goal="Identify network and connectivity causes of incidents",
            backstory="You analyze network connections, latency issues, and routing problems. You focus on connectivity failures, DNS issues, and network throughput.",
            verbose=True,
            llm=self.llm,
            tools=[correlation_analysis, dependency_analysis]
        )

        self.root_cause_manager = Agent(
            role="Root Cause Manager",
            goal="Synthesize analysis from specialized agents to determine the most likely root cause",
            backstory="You are an expert at managing root cause investigations, coordinating different specialists, and synthesizing their findings into a comprehensive analysis.",
            verbose=True,
            llm=self.llm
        )

        # Keep the original root cause analyzer for backward compatibility
        self.root_cause_analyzer = Agent(
            role="Root Cause Analyzer",
            goal="Identify the root cause of system issues by analyzing correlations and dependencies",
            backstory="You are an expert at analyzing system issues and identifying their root causes by examining correlations between events and service dependencies.",
            verbose=True,
            llm=self.llm,
            tools=[correlation_analysis, dependency_analysis]
        )

    async def connect(self):
        """Connect to NATS server and set up JetStream"""
        try:
            # Connect to NATS server
            self.nats_client = await nats.connect(self.nats_server)
            logger.info(f"Connected to NATS server at {self.nats_server}")

            # Create JetStream context
            self.js = self.nats_client.jetstream()

            # Check if streams exist, create them if they don't
            try:
                # Look up streams first
                streams = []
                try:
                    streams = await self.js.streams_info()
                except Exception as e:
                    logger.warning(f"Failed to get streams info: {str(e)}")

                # Get stream names
                stream_names = [stream.config.name for stream in streams]

                # Define required streams with their subjects
                stream_definitions = {
                    "ROOT_CAUSE": ["root_cause_analysis", "root_cause_result", "rootcause", "rootcause.*"],
                    "RESPONSES": ["orchestrator_response"]
                }

                # Create required streams if they don't exist
                for stream_name, subjects in stream_definitions.items():
                    if stream_name in stream_names:
                        logger.info(f"{stream_name} stream exists")

                        # Check if the stream has all the required subjects
                        try:
                            stream_info = await self.js.stream_info(stream_name)
                            current_subjects = stream_info.config.subjects

                            # Check if any subjects are missing
                            missing_subjects = [subj for subj in subjects if subj not in current_subjects]

                            if missing_subjects:
                                # Update the stream with the missing subjects
                                updated_subjects = current_subjects + missing_subjects
                                await self.js.update_stream(name=stream_name, subjects=updated_subjects)
                                logger.info(f"Updated {stream_name} stream with subjects: {missing_subjects}")
                        except Exception as e:
                            logger.warning(f"Failed to update {stream_name} stream: {str(e)}")
                    else:
                        try:
                            # Create the stream
                            await self.js.add_stream(name=stream_name, subjects=subjects)
                            logger.info(f"Created {stream_name} stream with subjects: {subjects}")
                        except Exception as e:
                            logger.error(f"Failed to create {stream_name} stream: {str(e)}")

            except nats.errors.Error as e:
                # Print error but don't raise - we can still work with existing streams
                logger.warning(f"Stream setup error: {str(e)}")

        except Exception as e:
            logger.error(f"Failed to connect to NATS: {str(e)}")
            raise

    def _get_current_timestamp(self):
        """Get current timestamp in ISO format"""
        return datetime.now(datetime.timezone.utc).isoformat()

    def _create_specialized_root_cause_tasks(self, data):
        """Create specialized root cause analysis tasks for each analyst"""
        alert_id = data.get("alert_id", "unknown")
        alert_data = data.get("alert", {})
        metric_data = data.get("metrics", {})
        log_data = data.get("logs", {})
        tracing_data = data.get("tracing", {})
        deployment_data = data.get("deployments", {})

        # Check if we're working with partial data
        partial_data = data.get("partial_data", False)
        missing_agents = data.get("missing_agents", [])

        # Prepare base data description that all agents will use
        base_data_description = f"""
        ## Alert Information
        - Alert ID: {alert_id}
        - Alert Name: {alert_data.get('labels', {}).get('alertname', 'Unknown')}
        - Service: {alert_data.get('labels', {}).get('service', 'Unknown')}
        - Severity: {alert_data.get('labels', {}).get('severity', 'Unknown')}
        - Timestamp: {alert_data.get('startsAt', 'Unknown')}

        ## Metric Agent Analysis
        {metric_data.get('analysis', 'No metric data available' if 'metric' in missing_agents else 'No analysis provided')}

        ## Log Agent Analysis
        {log_data.get('analysis', 'No log data available' if 'log' in missing_agents else 'No analysis provided')}

        ## Tracing Agent Analysis
        {tracing_data.get('analysis', 'No tracing data available' if 'tracing' in missing_agents else 'No analysis provided')}

        ## Deployment Agent Analysis
        {deployment_data.get('analysis', 'No deployment data available' if 'deployment' in missing_agents else 'No analysis provided')}
        """

        # Infrastructure task
        infrastructure_task = Task(
            description=base_data_description + """
            Based on this data, analyze for infrastructure-related root causes. Focus on:
            - Hardware or system-level failures
            - Resource exhaustion (CPU, memory, disk)
            - Cloud infrastructure issues
            - Load balancer or proxy problems
            - Operating system issues

            Return your analysis with:
            1. Potential infrastructure causes
            2. Confidence level for each cause
            3. Supporting evidence from the data
            4. Remediation recommendations
            """,
            agent=self.infrastructure_analyzer,
            expected_output="An analysis of potential infrastructure-related root causes"
        )

        # Application task
        application_task = Task(
            description=base_data_description + """
            Based on this data, analyze for application-related root causes. Focus on:
            - Code bugs or exceptions
            - Memory leaks or garbage collection issues
            - Application performance bottlenecks
            - Runtime configuration problems
            - Threading or concurrency issues

            Return your analysis with:
            1. Potential application causes
            2. Confidence level for each cause
            3. Supporting evidence from the data
            4. Remediation recommendations
            """,
            agent=self.application_analyzer,
            expected_output="An analysis of potential application-related root causes"
        )

        # Database task
        database_task = Task(
            description=base_data_description + """
            Based on this data, analyze for database-related root causes. Focus on:
            - Slow queries or inefficient database operations
            - Database locking or blocking issues
            - Schema or data model problems
            - Database resource constraints
            - Connection pool issues

            Return your analysis with:
            1. Potential database causes
            2. Confidence level for each cause
            3. Supporting evidence from the data
            4. Remediation recommendations
            """,
            agent=self.database_analyzer,
            expected_output="An analysis of potential database-related root causes"
        )

        # Network task
        network_task = Task(
            description=base_data_description + """
            Based on this data, analyze for network-related root causes. Focus on:
            - Network connectivity failures
            - DNS resolution issues
            - Latency or throughput problems
            - Service mesh or network routing issues
            - Network security or firewall problems

            Return your analysis with:
            1. Potential network causes
            2. Confidence level for each cause
            3. Supporting evidence from the data
            4. Remediation recommendations
            """,
            agent=self.network_analyzer,
            expected_output="An analysis of potential network-related root causes"
        )

        # Manager task (synthesize results)
        manager_task = Task(
            description="""
            Synthesize the analyses from the specialized root cause agents to determine the most likely root cause.
            Review all evidence and evaluate the confidence levels provided by each specialist.

            Return your final analysis in the following format:
            1. Identified Root Cause - A clear statement of what caused the incident
            2. Confidence Level - How confident you are in this assessment (low, medium, high)
            3. Supporting Evidence - Key data points that support your conclusion
            4. Recommended Actions - Suggested steps to resolve the issue
            5. Prevention - How to prevent similar incidents in the future
            """,
            agent=self.root_cause_manager,
            expected_output="A comprehensive root cause analysis with recommended actions"
        )

        # Return all specialized tasks
        return [infrastructure_task, application_task, database_task, network_task, manager_task]

    def _create_root_cause_task(self, data):
        """Create a root cause analysis task for the crew (backward compatibility)"""
        alert_id = data.get("alert_id", "unknown")
        alert_data = data.get("alert", {})
        metric_data = data.get("metrics", {})
        log_data = data.get("logs", {})
        tracing_data = data.get("tracing", {})
        deployment_data = data.get("deployments", {})

        # Check if we're working with partial data
        partial_data = data.get("partial_data", False)
        missing_agents = data.get("missing_agents", [])

        # Prepare data description
        data_description = f"""
        ## Alert Information
        - Alert ID: {alert_id}
        - Alert Name: {alert_data.get('labels', {}).get('alertname', 'Unknown')}
        - Service: {alert_data.get('labels', {}).get('service', 'Unknown')}
        - Severity: {alert_data.get('labels', {}).get('severity', 'Unknown')}
        - Timestamp: {alert_data.get('startsAt', 'Unknown')}

        ## Metric Agent Analysis
        {metric_data.get('analysis', 'No metric data available' if 'metric' in missing_agents else 'No analysis provided')}

        ## Log Agent Analysis
        {log_data.get('analysis', 'No log data available' if 'log' in missing_agents else 'No analysis provided')}

        ## Tracing Agent Analysis
        {tracing_data.get('analysis', 'No tracing data available' if 'tracing' in missing_agents else 'No analysis provided')}

        ## Deployment Agent Analysis
        {deployment_data.get('analysis', 'No deployment data available' if 'deployment' in missing_agents else 'No analysis provided')}
        """

        task_instruction = f"""
        Based on the information provided by the specialized agents, determine the most likely root cause of this incident.

        {'NOTE: This is partial data. Some agent responses are missing.' if partial_data else ''}

        Return your analysis in the following format:
        1. Identified Root Cause - A clear statement of what caused the incident
        2. Confidence Level - How confident you are in this assessment (low, medium, high)
        3. Supporting Evidence - Key data points that support your conclusion
        4. Recommended Actions - Suggested steps to resolve the issue
        5. Prevention - How to prevent similar incidents in the future
        """

        task = Task(
            description=data_description + task_instruction,
            agent=self.root_cause_analyzer,
            expected_output="A comprehensive root cause analysis with recommended actions"
        )

        return task

    async def analyze_root_cause(self, data):
        """Analyze root cause using multi-agent crewAI"""
        logger.info(f"Analyzing root cause for alert ID: {data.get('alert_id', 'unknown')}")

        # Create specialized root cause tasks
        specialized_tasks = self._create_specialized_root_cause_tasks(data)

        # Create crew with specialized analyzers
        crew = Crew(
            agents=[
                self.infrastructure_analyzer,
                self.application_analyzer,
                self.database_analyzer,
                self.network_analyzer,
                self.root_cause_manager
            ],
            tasks=specialized_tasks,
            verbose=True,
            process=Process.hierarchical,
            manager_agent=self.root_cause_manager
        )

        # Execute crew analysis
        result = crew.kickoff()

        return result

    async def message_handler(self, msg):
        """Handle incoming NATS messages"""
        try:
            # Decode the message data
            data = json.loads(msg.data.decode())
            alert_id = data.get("alert_id", "unknown")
            logger.info(f"[RootCauseAgent] Processing comprehensive data for alert ID: {alert_id}")

            # Use crewAI to analyze root cause using the analyses from other agents
            analysis_result = await self.analyze_root_cause(data)

            # Prepare and publish result
            result = {
                "agent": "root_cause",
                "root_cause": str(analysis_result),
                "alert_id": alert_id,
                "timestamp": self._get_current_timestamp()
            }

            # Publish the result using JetStream
            await self.js.publish("root_cause_result", json.dumps(result).encode())
            logger.info(f"[RootCauseAgent] Published root cause analysis result for alert ID: {alert_id}")

            # Acknowledge the message
            await msg.ack()

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            # Negative acknowledge the message so it can be redelivered
            await msg.nak()

    async def listen(self):
        """Listen for comprehensive data from the orchestrator and publish root cause analysis"""
        logger.info("[RootCauseAgent] Starting to listen for comprehensive data on 'root_cause_analysis' channel")

        # Connect to NATS if not already connected
        if not self.nats_client or not self.nats_client.is_connected:
            await self.connect()

        # Create a durable consumer with a queue group for load balancing
        consumer_config = ConsumerConfig(
            durable_name="root_cause_agent",
            deliver_policy=DeliverPolicy.ALL,
            ack_policy="explicit",
            max_deliver=5,  # Retry up to 5 times
            ack_wait=60,    # Wait 60 seconds for acknowledgment
        )

        # Subscribe to the stream with the consumer configuration
        await self.js.subscribe(
            "root_cause_analysis",
            cb=self.message_handler,
            queue="root_cause_processors",
            config=consumer_config
        )

        logger.info("Subscribed to root_cause_analysis stream")

        # Keep the connection alive
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour, or until interrupted