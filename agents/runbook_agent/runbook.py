import os
import json
import logging
import asyncio
import nats
from nats.js.api import ConsumerConfig, DeliverPolicy
from datetime import datetime, timezone
from crewai import Agent, Task, Crew
from crewai.llm import LLM
from crewai.tools import tool
from crewai import process
from dotenv import load_dotenv
from common.tools.runbook_tools import RunbookSearchTool, RunbookExecutionTool
from common.tools.jetstream_runbook_source import JetstreamRunbookSource

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class RunbookAgent:
    def __init__(self, runbook_dir="/runbooks", nats_server="nats://nats:4222"):
        # NATS connection parameters
        self.nats_server = nats_server
        self.nats_client = None
        self.js = None  # JetStream context

        # Runbook configuration
        self.runbook_dir = runbook_dir

        # OpenAI API key from environment
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY environment variable not set")

        # Initialize OpenAI model
        self.llm = LLM(model=os.environ.get("OPENAI_MODEL", "gpt-4"))

        # Initialize JetStream runbook source
        self.jetstream_runbook_source = JetstreamRunbookSource()

        # Initialize runbook tools with JetStream source
        self.runbook_search_tool = RunbookSearchTool(
            runbook_dir=self.runbook_dir,
            additional_sources=[self.jetstream_runbook_source]
        )
        self.runbook_execution_tool = RunbookExecutionTool()

        # Create specialized agents for different aspects of runbook management
        self.runbook_finder = Agent(
            role="Runbook Finder",
            goal="Find the most relevant existing runbooks for a given incident",
            backstory="You excel at searching, categorizing, and selecting the most appropriate runbooks from the knowledge base based on incident details and root cause analysis.",
            verbose=True,
            llm=self.llm,
            tools=[
                self.runbook_search_tool.search_runbooks,
                self.runbook_search_tool.get_runbook_by_alert
            ]
        )

        self.runbook_adapter = Agent(
            role="Runbook Adapter",
            goal="Adapt and enhance existing runbooks for the specific incident context",
            backstory="You specialize in customizing generic runbooks to address the specific details and nuances of the current incident based on root cause analysis.",
            verbose=True,
            llm=self.llm,
            tools=[
                self.runbook_execution_tool.generate_custom_runbook
            ]
        )

        self.runbook_validator = Agent(
            role="Runbook Validator",
            goal="Validate runbook steps and ensure they will resolve the incident",
            backstory="You carefully review runbook steps for completeness, correctness, and safety. You ensure the steps directly address the root cause and include verification methods.",
            verbose=True,
            llm=self.llm,
            tools=[
                self.runbook_execution_tool.track_execution
            ]
        )

        self.automation_expert = Agent(
            role="Automation Expert",
            goal="Automate runbook execution where possible and provide clear execution instructions",
            backstory="You excel at determining which runbook steps can be automated and preparing detailed instructions for steps that require human intervention.",
            verbose=True,
            llm=self.llm,
            tools=[
                self.runbook_execution_tool.execute_runbook
            ]
        )

        # Keep the original runbook executor for backward compatibility
        self.runbook_executor = Agent(
            role="Runbook Executor",
            goal="Find and execute appropriate runbooks for incident resolution",
            backstory="You are an expert at finding and executing runbooks to resolve system incidents.",
            verbose=True,
            llm=self.llm,
            tools=[
                # Runbook search tools
                self.runbook_search_tool.search_runbooks,
                self.runbook_search_tool.get_runbook_by_alert,

                # Runbook execution tools
                self.runbook_execution_tool.execute_runbook,
                self.runbook_execution_tool.track_execution,
                self.runbook_execution_tool.generate_custom_runbook
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

            # Set JetStream client in the JetStream runbook source
            self.jetstream_runbook_source.set_js(self.js)
            logger.info("JetStream client set in runbook source")

            # Check if we can get the stream info, this confirms the connection works
            try:
                # Check existing streams
                streams = await self.js.streams_info()
                logger.info(f"Successfully connected to JetStream. Found {len(streams)} streams.")

                # Log the existing stream names and subjects for debugging
                stream_details = {}
                for stream in streams:
                    stream_details[stream.config.name] = stream.config.subjects
                logger.info(f"Existing streams: {stream_details}")

                # Check if RESPONSES stream exists and contains the root_cause_result subject
                responses_stream_exists = False
                has_root_cause_result = False
                runbook_executions_exists = False

                for stream in streams:
                    if stream.config.name == "RESPONSES":
                        responses_stream_exists = True
                        if "root_cause_result" in stream.config.subjects:
                            has_root_cause_result = True
                            logger.info("RESPONSES stream includes root_cause_result subject")
                    elif stream.config.name == "RUNBOOK_EXECUTIONS":
                        runbook_executions_exists = True
                        logger.info("RUNBOOK_EXECUTIONS stream exists")

                # If RESPONSES stream exists but doesn't have root_cause_result subject, add it
                if responses_stream_exists and not has_root_cause_result:
                    try:
                        # Get the current config
                        stream_info = await self.js.stream_info("RESPONSES")
                        current_config = stream_info.config

                        # Add the root_cause_result subject and update the stream
                        new_subjects = current_config.subjects + ["root_cause_result"]
                        current_config.subjects = new_subjects

                        # Update the stream with new subjects
                        await self.js.update_stream(config=current_config)
                        logger.info("Updated RESPONSES stream to include root_cause_result subject")
                    except Exception as e:
                        logger.error(f"Error updating RESPONSES stream: {str(e)}")

                # If RESPONSES stream doesn't exist, we need to create it
                if not responses_stream_exists:
                    try:
                        from nats.js.api import StreamConfig
                        # Create RESPONSES stream with root_cause_result subject
                        responses_config = StreamConfig(
                            name="RESPONSES",
                            subjects=["orchestrator_response", "root_cause_result"],
                            retention="limits",
                            max_msgs=10000,
                            max_bytes=1024*1024*100,  # 100MB
                            max_age=3600*24*7,  # 7 days
                            storage="memory",
                            discard="old"
                        )

                        await self.js.add_stream(config=responses_config)
                        logger.info("Created RESPONSES stream with orchestrator_response and root_cause_result subjects")
                    except Exception as e:
                        logger.error(f"Error creating RESPONSES stream: {str(e)}")

                # Create RUNBOOK_EXECUTIONS stream if it doesn't exist
                if not runbook_executions_exists:
                    try:
                        from nats.js.api import StreamConfig
                        # Create RUNBOOK_EXECUTIONS stream
                        executions_config = StreamConfig(
                            name="RUNBOOK_EXECUTIONS",
                            subjects=["runbook.execute", "runbook.status.*"],
                            retention="limits",
                            max_msgs=10000,
                            max_bytes=1024*1024*100,  # 100MB
                            max_age=3600*24*7,  # 7 days
                            storage="memory",
                            discard="old"
                        )

                        await self.js.add_stream(config=executions_config)
                        logger.info("Created RUNBOOK_EXECUTIONS stream")
                    except Exception as e:
                        logger.error(f"Error creating RUNBOOK_EXECUTIONS stream: {str(e)}")

                # Set JetStream client in the runbook execution tool
                self.runbook_execution_tool.set_jetstream(self.js)

            except nats.errors.Error as e:
                # Just log the error but continue - we can still work with the connection
                logger.warning(f"Could not get streams info: {str(e)}")

        except Exception as e:
            logger.error(f"Failed to connect to NATS: {str(e)}")
            raise

    def _get_current_timestamp(self):
        """Get current timestamp in ISO format"""
        return datetime.now(timezone.utc).isoformat()

    async def fetch_alert_data(self, alert_id):
        """Fetch alert data from the orchestrator"""
        logger.info(f"[RunbookAgent] Requesting alert data for alert ID: {alert_id}")

        # Request the alert data from the orchestrator
        request = {"alert_id": alert_id}
        await self.js.publish("alert_data_request", json.dumps(request).encode())

        # Create a consumer for the response
        consumer_config = ConsumerConfig(
            durable_name=f"runbook_alert_data_{alert_id}",
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
            logger.info(f"[RunbookAgent] Received alert data for alert ID: {alert_id}")
            return alert_data
        except asyncio.TimeoutError:
            logger.warning(f"[RunbookAgent] Timeout waiting for alert data for alert ID: {alert_id}")
            await sub.unsubscribe()
            return {"alert_id": alert_id, "error": "Timeout waiting for data"}

    def _create_specialized_runbook_tasks(self, root_cause_data, alert_data):
        """Create specialized runbook tasks for the crew"""
        alert_id = root_cause_data.get("alert_id", "unknown")
        root_cause = root_cause_data.get("root_cause", "Unknown root cause")

        # Extract details from alert data
        service = alert_data.get("labels", {}).get("service", "unknown")
        severity = alert_data.get("labels", {}).get("severity", "unknown")
        description = alert_data.get("annotations", {}).get("description", "No description provided")

        # Common incident information for all agents
        incident_info = f"""
        ## Alert Information
        - Alert ID: {alert_id}
        - Service: {service}
        - Severity: {severity}
        - Description: {description}

        ## Root Cause Analysis
        {root_cause}
        """

        # Task for finding relevant runbooks
        finder_task = Task(
            description=incident_info + """
            Search for runbooks that are relevant to this incident. Focus on:
            1. Runbooks specific to this service or similar services
            2. Runbooks addressing similar root causes or symptoms
            3. Runbooks that match the technical components mentioned in the root cause analysis

            Return:
            1. A list of relevant runbooks with brief descriptions
            2. The full content of the most relevant runbook
            3. An explanation of why you selected these runbooks
            """,
            agent=self.runbook_finder,
            expected_output="A detailed list of relevant runbooks and the content of the most applicable one"
        )

        # Task for adapting runbooks
        adapter_task = Task(
            description="""
            Based on the runbooks found by the Runbook Finder, adapt them to the specific incident context.

            1. Modify generic steps to address the specific root cause identified
            2. Add any missing steps necessary for this particular incident
            3. Remove any steps that are not applicable
            4. Ensure the steps directly address the identified root cause

            Return a customized runbook with detailed step-by-step instructions.
            """,
            agent=self.runbook_adapter,
            expected_output="A customized runbook specifically adapted for this incident"
        )

        # Task for validating runbook steps
        validator_task = Task(
            description="""
            Review and validate the customized runbook:

            1. Verify that each step is technically correct and safe to execute
            2. Ensure the steps directly address the identified root cause
            3. Confirm that the steps are ordered logically
            4. Add verification steps after each major action
            5. Identify any potential risks or side effects

            Return the validated runbook with any necessary corrections and added verification steps.
            """,
            agent=self.runbook_validator,
            expected_output="A validated and improved runbook with verification steps"
        )

        # Task for automation recommendations
        automation_task = Task(
            description="""
            Analyze the validated runbook and:

            1. Identify which steps can be safely automated
            2. Provide detailed execution instructions for steps requiring human intervention
            3. Include commands and scripts for automation where applicable
            4. Format the final runbook for easy execution by on-call engineers

            Return the final runbook with automation recommendations and detailed execution instructions.
            """,
            agent=self.automation_expert,
            expected_output="A final runbook with automation recommendations and execution instructions"
        )

        # Return all specialized tasks
        return [finder_task, adapter_task, validator_task, automation_task]

    def _create_runbook_task(self, root_cause_data, alert_data):
        """Create a runbook generation task for the crew (backward compatibility)"""
        alert_id = root_cause_data.get("alert_id", "unknown")
        root_cause = root_cause_data.get("root_cause", "Unknown root cause")

        # Extract details from alert data
        service = alert_data.get("labels", {}).get("service", "unknown")
        severity = alert_data.get("labels", {}).get("severity", "unknown")
        description = alert_data.get("annotations", {}).get("description", "No description provided")

        # Create the task for the runbook manager
        task = Task(
            description=f"""
            Generate runbook instructions for addressing the following incident:

            ## Alert Information
            - Alert ID: {alert_id}
            - Service: {service}
            - Severity: {severity}
            - Description: {description}

            ## Root Cause Analysis
            {root_cause}

            Please search for relevant runbooks in our repository and enhance them with specific instructions
            based on the root cause analysis. If no specific runbook exists, generate appropriate steps.

            Format your response as a clear, step-by-step guide that an on-call engineer can follow.
            Include verification steps to confirm that the issue has been resolved.
            """,
            agent=self.runbook_executor,
            expected_output="A comprehensive runbook with step-by-step instructions"
        )

        return task

    async def generate_runbook(self, root_cause_data, alert_data):
        """Generate an enhanced runbook using multi-agent crewAI"""
        logger.info(f"Generating runbook for alert ID: {root_cause_data.get('alert_id', 'unknown')}")

        # Create runbook task
        runbook_task = self._create_runbook_task(root_cause_data, alert_data)

        # Create crew with runbook manager

        # Create specialized runbook tasks
        specialized_tasks = self._create_specialized_runbook_tasks(root_cause_data, alert_data)

        # Create crew with specialized agents
        crew = Crew(
            agents=[
                self.runbook_finder,
                self.runbook_adapter,
                self.runbook_validator,
                self.automation_expert
            ],
            tasks=specialized_tasks,
            verbose=True,
            process=process.Sequential()
        )

        # Execute crew analysis
        result = crew.kickoff()

        return result

    async def message_handler(self, msg):
        """Handle incoming NATS messages for root cause results"""
        try:
            # Parse the incoming message
            root_cause_data = json.loads(msg.data.decode())
            alert_id = root_cause_data.get("alert_id", "unknown")
            logger.info(f"[RunbookAgent] Processing root cause results for alert ID: {alert_id}")

            # Fetch the original alert data
            alert_data = await self.fetch_alert_data(alert_id)

            if "error" in alert_data:
                logger.error(f"[RunbookAgent] Failed to get alert data: {alert_data['error']}")
                # Try to proceed with limited data
                alert_data = {"alert_id": alert_id}

            # Generate runbook based on root cause and alert data
            runbook_result = await self.generate_runbook(root_cause_data, alert_data)

            # Prepare result for the orchestrator
            result = {
                "agent": "runbook",
                "runbook": str(runbook_result),
                "alert_id": alert_id,
                "timestamp": self._get_current_timestamp()
            }

            # Publish result to orchestrator
            await self.js.publish("orchestrator_response", json.dumps(result).encode())
            logger.info(f"[RunbookAgent] Published runbook for alert ID: {alert_id}")

            # Acknowledge the message
            await msg.ack()

        except Exception as e:
            logger.error(f"[RunbookAgent] Error processing message: {str(e)}", exc_info=True)
            # Negative acknowledge the message so it can be redelivered
            await msg.nak()

    async def execution_handler(self, msg):
        """Handle incoming NATS messages for runbook execution requests"""
        try:
            # Parse the incoming message
            execution_request = json.loads(msg.data.decode())
            execution_id = execution_request.get("executionId", "unknown")
            runbook_id = execution_request.get("runbookId", "unknown")
            runbook = execution_request.get("runbook", {})

            logger.info(f"[RunbookAgent] Received execution request for runbook ID: {runbook_id}, execution ID: {execution_id}")

            # Extract steps from the runbook
            steps = runbook.get("steps", [])

            if not steps:
                logger.warning(f"[RunbookAgent] No steps found in runbook: {runbook_id}")
                # Acknowledge the message even though there are no steps
                await msg.ack()
                return

            # Execute the runbook using the execution tool
            self.runbook_execution_tool.execute_runbook(
                runbook_id=runbook_id,
                steps=steps,
                execution_id=execution_id
            )

            logger.info(f"[RunbookAgent] Started execution of runbook: {runbook_id}, execution ID: {execution_id}")

            # Acknowledge the message
            await msg.ack()

        except Exception as e:
            logger.error(f"[RunbookAgent] Error processing execution request: {str(e)}", exc_info=True)
            # Negative acknowledge the message so it can be redelivered
            await msg.nak()

    async def listen(self):
        """Listen for root cause results and generate enhanced runbooks"""
        logger.info("[RunbookAgent] Starting to listen for root cause results and runbook execution requests")

        # Connect to NATS if not already connected
        if not self.nats_client or not self.nats_client.is_connected:
            await self.connect()

        # Create a durable consumer for root cause results
        root_cause_consumer = ConsumerConfig(
            durable_name="runbook_agent",
            deliver_policy=DeliverPolicy.ALL,
            ack_policy="explicit",
            max_deliver=5,  # Retry up to 5 times
            ack_wait=120,   # Wait 2 minutes for acknowledgment (runbook generation can take time)
        )

        # Subscribe to the root cause results
        await self.js.subscribe(
            "root_cause_result",
            cb=self.message_handler,
            queue="runbook_processors",
            config=root_cause_consumer
        )

        logger.info("[RunbookAgent] Subscribed to root_cause_result stream")

        # Create a durable consumer for runbook execution requests
        execution_consumer = ConsumerConfig(
            durable_name="runbook_executor",
            deliver_policy=DeliverPolicy.ALL,
            ack_policy="explicit",
            max_deliver=3,  # Retry up to 3 times
            ack_wait=30,    # Wait 30 seconds for acknowledgment
        )

        # Subscribe to the runbook execution requests
        await self.js.subscribe(
            "runbook.execute",
            cb=self.execution_handler,
            queue="runbook_executors",
            config=execution_consumer
        )

        logger.info("[RunbookAgent] Subscribed to runbook.execute stream")

        # Keep the connection alive
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour, or until interrupted