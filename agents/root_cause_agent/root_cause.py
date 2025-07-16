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
from common.agent_status import start_agent_status_publishing

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
        
        # Agent status publisher (will be initialized after NATS connection)
        self.status_publisher = None

        # Create comprehensive consolidated agents for root cause analysis
        self.technical_systems_analyzer = Agent(
            role="Technical Systems Analyst",
            goal="Analyze infrastructure, application, database, and system-level issues to identify technical root causes by examining resource constraints, configuration problems, and software failures",
            backstory="""You are an expert at analyzing technical system failures with deep knowledge of:
            
            **Infrastructure Analysis**: Understanding server hardware issues, virtualization problems, cloud infrastructure failures, resource exhaustion, and capacity constraints that can cause system-wide incidents.
            
            **Application Analysis**: Identifying application bugs, memory leaks, performance bottlenecks, code-level issues, runtime errors, and software configuration problems that manifest as service failures.
            
            **Database Analysis**: Analyzing database performance issues, query optimization problems, connection pool exhaustion, locking issues, storage constraints, and data corruption that affect application functionality.
            
            **System Integration**: Understanding how infrastructure, application, and database layers interact and how issues in one layer can cascade to cause failures in others.""",
            verbose=True,  # Keep detailed for quality analysis
            llm=self.llm,
            tools=[correlation_analysis, dependency_analysis]
        )

        self.network_communication_analyzer = Agent(
            role="Network & Service Communication Analyst", 
            goal="Analyze network connectivity, service-to-service communication, DNS issues, and distributed system communication patterns to identify connectivity-related root causes",
            backstory="""You are an expert at analyzing network and service communication issues with deep knowledge of:
            
            **Network Connectivity**: Understanding network failures, routing problems, bandwidth constraints, packet loss, and connectivity issues between services, regions, or data centers.
            
            **Service Communication**: Analyzing API failures, service mesh issues, load balancer problems, circuit breaker activations, and microservice communication patterns.
            
            **DNS and Service Discovery**: Identifying DNS resolution failures, service discovery issues, endpoint availability problems, and service registration/deregistration issues.
            
            **Distributed System Patterns**: Understanding how network partitions, latency spikes, and connectivity issues affect distributed system behavior and can cause cascading failures.""",
            verbose=True,  # Keep detailed for quality analysis
            llm=self.llm,
            tools=[correlation_analysis, dependency_analysis]
        )

        self.root_cause_synthesizer = Agent(
            role="Root Cause Synthesis Specialist",
            goal="Synthesize technical systems analysis and network communication findings with evidence from all other agents to determine the most likely root cause and provide comprehensive incident analysis",
            backstory="""You are an expert at root cause determination and incident analysis synthesis with deep expertise in:
            
            **Multi-Domain Analysis**: Combining insights from technical systems analysis, network analysis, and all specialized agent findings to understand complex incident scenarios.
            
            **Evidence Correlation**: Connecting evidence from observability data, infrastructure analysis, and communication patterns to build comprehensive incident narratives.
            
            **Root Cause Determination**: Distinguishing between root causes, contributing factors, and symptoms to identify the primary issue that triggered the incident cascade.
            
            **Confidence Assessment**: Evaluating the strength of evidence and providing confidence levels in root cause determinations based on available data quality and correlation strength.""",
            verbose=True,  # Keep detailed for quality analysis
            llm=self.llm,
            tools=[correlation_analysis, dependency_analysis]
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
            
            # Initialize agent status publisher
            try:
                self.status_publisher = await start_agent_status_publishing(
                    agent_id="root-cause-agent",
                    agent_name="Root Cause Agent",
                    js=self.js,
                    publish_interval=30  # Publish status every 30 seconds
                )
                logger.info("[RootCauseAgent] Agent status publishing started")
            except Exception as e:
                logger.warning(f"[RootCauseAgent] Failed to start agent status publishing: {e}")

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

                # Define required streams with their subjects (matching ConfigMap)
                stream_definitions = {
                    "ROOT_CAUSE": ["root_cause_analysis", "root_cause_result", "rootcause.>"],
                    "RESPONSES": ["orchestrator_response"],
                    "AGENT_TASKS": ["root_cause_agent"]
                }

                # Check if required streams exist (rely on ConfigMap for creation)
                for stream_name in stream_definitions.keys():
                    if stream_name in stream_names:
                        logger.info(f"✓ {stream_name} stream exists")
                    else:
                        logger.warning(f"✗ {stream_name} stream missing - should be created by ConfigMap")
                        # Don't create streams here - rely on centralized ConfigMap creation

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

    async def _store_root_cause_data(self, data, analysis_result):
        """Store root cause analysis data for UI consumption"""
        try:
            alert_data = data.get("alert", {})
            alert_id = data.get("alert_id", "unknown")
            service = alert_data.get("labels", {}).get("service", "unknown-service")

            # Extract confidence and cause from analysis result
            analysis_text = str(analysis_result)
            confidence = self._extract_confidence(analysis_text)
            cause = self._extract_cause(analysis_text)

            # Create root cause record for UI
            root_cause_record = {
                "id": f"rc-{alert_id}-{int(datetime.now(datetime.timezone.utc).timestamp())}",
                "alertId": alert_id,
                "service": service,
                "cause": cause,
                "confidence": confidence,
                "timestamp": datetime.now(datetime.timezone.utc).isoformat(),
                "details": analysis_text,
                "analysis": {
                    "cause": cause,
                    "confidence": confidence,
                    "evidence": self._extract_evidence(analysis_text),
                    "recommendation": self._extract_recommendation(analysis_text)
                }
            }

            # Publish to ROOT_CAUSE stream for UI consumption
            subject = f"rootcause.{service}"
            await self.js.publish(subject, json.dumps(root_cause_record).encode())
            logger.info(f"[RootCauseAgent] Stored root cause data for service {service}")

        except Exception as e:
            logger.error(f"[RootCauseAgent] Error storing root cause data: {str(e)}")

    def _extract_confidence(self, analysis_text):
        """Extract confidence level from analysis text"""
        import re

        # Look for confidence patterns
        confidence_patterns = [
            r'confidence[:\s]+([0-9]+(?:\.[0-9]+)?)',
            r'([0-9]+(?:\.[0-9]+)?)\s*%?\s*confidence',
            r'high confidence',
            r'medium confidence',
            r'low confidence'
        ]

        analysis_lower = analysis_text.lower()

        for pattern in confidence_patterns:
            match = re.search(pattern, analysis_lower)
            if match:
                if 'high' in match.group(0):
                    return 0.9
                elif 'medium' in match.group(0):
                    return 0.7
                elif 'low' in match.group(0):
                    return 0.4
                else:
                    try:
                        value = float(match.group(1))
                        return value if value <= 1.0 else value / 100.0
                    except (ValueError, IndexError):
                        continue

        return 0.6  # Default confidence

    def _extract_cause(self, analysis_text):
        """Extract the main cause from analysis text"""
        # Simple extraction - look for key phrases
        lines = analysis_text.split('\n')

        for line in lines:
            line_lower = line.lower().strip()
            if any(keyword in line_lower for keyword in ['root cause:', 'identified root cause', 'cause:', 'primary cause']):
                # Extract the cause after the keyword
                cause = line.split(':', 1)[-1].strip()
                if cause and len(cause) > 10:  # Ensure it's substantial
                    return cause[:200]  # Limit length

        # Fallback: use first substantial line
        for line in lines:
            if len(line.strip()) > 20:
                return line.strip()[:200]

        return "Root cause analysis completed"

    def _extract_evidence(self, analysis_text):
        """Extract evidence from analysis text"""
        evidence = []
        lines = analysis_text.split('\n')

        for line in lines:
            line_lower = line.lower().strip()
            if any(keyword in line_lower for keyword in ['evidence:', 'supporting evidence', 'data shows', 'indicates']):
                evidence.append(line.strip())

        return evidence[:3]  # Limit to top 3 pieces of evidence

    def _extract_recommendation(self, analysis_text):
        """Extract recommendation from analysis text"""
        lines = analysis_text.split('\n')

        for line in lines:
            line_lower = line.lower().strip()
            if any(keyword in line_lower for keyword in ['recommendation:', 'recommended action', 'suggest', 'should']):
                recommendation = line.split(':', 1)[-1].strip()
                if recommendation and len(recommendation) > 10:
                    return recommendation[:300]

        return "Review the analysis and take appropriate action"

    def _get_current_timestamp(self):
        """Get current timestamp in ISO format"""
        return datetime.now(datetime.timezone.utc).isoformat()

    async def alert_handler(self, msg):
        """Handle individual alert messages from orchestrator"""
        try:
            # Decode the alert data
            alert = json.loads(msg.data.decode())
            alert_id = alert.get("alert_id", "unknown")
            logger.info(f"[RootCauseAgent] Received individual alert: {alert_id}")

            # Store alert for later comprehensive analysis
            # For now, just acknowledge - comprehensive analysis happens later
            logger.info(f"[RootCauseAgent] Stored alert {alert_id} for comprehensive analysis")

            # Acknowledge the message
            await msg.ack()

        except Exception as e:
            logger.error(f"Error processing alert: {str(e)}", exc_info=True)
            await msg.nak()

    async def comprehensive_handler(self, msg):
        """Handle comprehensive data from orchestrator (renamed from message_handler)"""
        try:
            # Decode the message data
            data = json.loads(msg.data.decode())
            alert_id = data.get("alert_id", "unknown")
            logger.info(f"[RootCauseAgent] Processing comprehensive data for alert ID: {alert_id}")

            # Use crewAI to analyze root cause using the analyses from other agents
            analysis_result = await self.analyze_root_cause(data)

            # Prepare result for orchestrator
            orchestrator_result = {
                "agent": "root_cause",
                "root_cause": str(analysis_result),
                "alert_id": alert_id,
                "timestamp": self._get_current_timestamp()
            }

            # Store root cause data for UI consumption
            await self._store_root_cause_data(data, analysis_result)

            # Publish the result to orchestrator using JetStream
            await self.js.publish("root_cause_result", json.dumps(orchestrator_result).encode())
            logger.info(f"[RootCauseAgent] Published root cause analysis result for alert ID: {alert_id}")

            # Acknowledge the message
            await msg.ack()

        except Exception as e:
            logger.error(f"Error processing comprehensive data: {str(e)}", exc_info=True)
            # Negative acknowledge the message so it can be redelivered
            await msg.nak()



    async def listen(self):
        """Listen for alerts and comprehensive data from the orchestrator"""
        logger.info("[RootCauseAgent] Starting to listen for alerts and comprehensive data")

        try:
            # Connect to NATS if not already connected
            if not self.nats_client or not self.nats_client.is_connected:
                await self.connect()

            # Create a durable consumer for individual alerts
            alert_consumer_config = ConsumerConfig(
                durable_name="root_cause_alerts",
                deliver_policy=DeliverPolicy.ALL,
                ack_policy="explicit",
                max_deliver=5,  # Retry up to 5 times
                ack_wait=60,    # Wait 60 seconds for acknowledgment
            )

            # Subscribe to individual alerts from orchestrator
            await self.js.subscribe(
                "root_cause_agent",
                cb=self.alert_handler,
                queue="root_cause_alert_processors",
                stream="AGENT_TASKS",
                config=alert_consumer_config
            )

            logger.info("Subscribed to root_cause_agent subject for individual alerts")

            # Create a durable consumer for comprehensive data
            comprehensive_consumer_config = ConsumerConfig(
                durable_name="root_cause_comprehensive",
                deliver_policy=DeliverPolicy.ALL,
                ack_policy="explicit",
                max_deliver=5,  # Retry up to 5 times
                ack_wait=60,    # Wait 60 seconds for acknowledgment
            )

            # Subscribe to comprehensive data from orchestrator
            await self.js.subscribe(
                "root_cause_analysis",
                cb=self.comprehensive_handler,
                queue="root_cause_comprehensive_processors",
                stream="ROOT_CAUSE",
                config=comprehensive_consumer_config
            )

            logger.info("Subscribed to root_cause_analysis subject for comprehensive data")

            # Keep the connection alive
            while True:
                await asyncio.sleep(3600)  # Sleep for an hour, or until interrupted
                
        except Exception as e:
            logger.error(f"[RootCauseAgent] Error in listen(): {str(e)}", exc_info=True)
            # Stop status publishing if there's an error
            if self.status_publisher:
                try:
                    await self.status_publisher.stop_publishing()
                    logger.info("[RootCauseAgent] Agent status publishing stopped")
                except Exception as pub_e:
                    logger.warning(f"[RootCauseAgent] Error stopping status publisher: {pub_e}")
            # Wait and retry
            logger.info("[RootCauseAgent] Will retry in 30 seconds...")
            await asyncio.sleep(30)
            # Try calling listen again after delay
            return await self.listen()