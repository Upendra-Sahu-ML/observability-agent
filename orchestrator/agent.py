# File: orchestrator/agent.py
import os
import json
import time
import logging
import threading
import asyncio
import nats
from nats.js.api import StreamConfig, ConsumerConfig, DeliverPolicy
from datetime import datetime, timedelta
from crewai import Agent, Task, Crew
from crewai.llm import LLM
from dotenv import load_dotenv
from common.config import is_agent_enabled

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("orchestrator")

load_dotenv()

class OrchestratorAgent:
    def __init__(self, nats_server=None, openai_model=None, response_timeout=300):
        # Get configuration from environment variables or use defaults
        self.nats_server = nats_server or os.environ.get('NATS_URL', 'nats://nats:4222')
        self.openai_model = openai_model or os.environ.get('OPENAI_MODEL', 'gpt-4')
        self.response_timeout = response_timeout or int(os.environ.get('RESPONSE_TIMEOUT_SECONDS', 300))
        
        # NATS and JetStream will be initialized in connect() method
        self.nats_client = None
        self.js = None
        
        # Initialize CrewAI LLM
        self.llm = LLM(provider="openai", model=self.openai_model)
        logger.info(f"Initialized OpenAI model: {self.openai_model}")
        
        # Create a crewAI agent for orchestration
        self.orchestrator = Agent(
            role="Incident Coordinator",
            goal="Coordinate the analysis of incidents across multiple specialized agents",
            backstory="You are an expert at coordinating complex incident investigations, knowing exactly which specialized agents to involve and how to synthesize their findings.",
            verbose=True,
            llm=self.llm
        )
        
        # Response tracking
        self.agent_responses = {}
        self.alerts_in_progress = set()
        self.alert_timestamps = {}
        
        # Event loop for async operations
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    async def connect(self):
        """Connect to NATS server and set up JetStream"""
        try:
            # Connect to NATS server
            self.nats_client = await nats.connect(self.nats_server)
            logger.info(f"Connected to NATS server at {self.nats_server}")
            
            # Create JetStream context
            self.js = self.nats_client.jetstream()
            
            # Ensure streams exist
            await self.setup_streams()
            
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {str(e)}")
            raise
    
    async def setup_streams(self):
        """Set up the required NATS streams"""
        try:
            # Create stream for alerts
            try:
                await self.js.add_stream(name="ALERTS", 
                                     subjects=["alerts", "alerts.*"])
                logger.info("Created ALERTS stream")
            except nats.errors.Error as e:
                # Stream might already exist
                logger.info(f"ALERTS stream setup: {str(e)}")
            
            # Create stream for agent responses
            try:
                await self.js.add_stream(name="RESPONSES", 
                                     subjects=["orchestrator_response", "root_cause_result"])
                logger.info("Created RESPONSES stream")
            except nats.errors.Error as e:
                # Stream might already exist
                logger.info(f"RESPONSES stream setup: {str(e)}")
            
            # Create stream for agent-specific messages
            try:
                await self.js.add_stream(name="AGENT_TASKS", 
                                     subjects=["metric_agent", "log_agent", "deployment_agent", 
                                               "tracing_agent", "notification_agent", "postmortem_agent"])
                logger.info("Created AGENT_TASKS stream")
            except nats.errors.Error as e:
                # Stream might already exist
                logger.info(f"AGENT_TASKS stream setup: {str(e)}")
            
            # Create stream for alert data requests
            try:
                await self.js.add_stream(name="ALERT_DATA", 
                                     subjects=["alert_data_request", "alert_data_response.*"])
                logger.info("Created ALERT_DATA stream")
            except nats.errors.Error as e:
                # Stream might already exist
                logger.info(f"ALERT_DATA stream setup: {str(e)}")
            
            # Create stream for root cause analysis
            try:
                await self.js.add_stream(name="ROOT_CAUSE", 
                                     subjects=["root_cause_analysis"])
                logger.info("Created ROOT_CAUSE stream")
            except nats.errors.Error as e:
                # Stream might already exist
                logger.info(f"ROOT_CAUSE stream setup: {str(e)}")
            
        except Exception as e:
            logger.error(f"Failed to setup streams: {str(e)}")
            raise
    def handle_agent_response(self, response_data):
        """Process responses from individual agents and coordinate next steps"""
        agent_type = response_data.get('agent')
        alert_id = response_data.get('alert_id', 'default')
        
        # Store the response
        if alert_id not in self.agent_responses:
            self.agent_responses[alert_id] = {}
        
        self.agent_responses[alert_id][agent_type] = response_data
        
        # Check if we have responses from all expected agents
        expected_agents = ['metric', 'log', 'deployment', 'tracing', 'notification', 'postmortem']
        available_agents = [agent for agent in expected_agents if is_agent_enabled(agent)]
        
        if all(agent in self.agent_responses[alert_id] for agent in available_agents if agent != 'notification' and agent != 'postmortem'):
            # Create comprehensive data package for root cause analysis
            comprehensive_data = {
                'alert_id': alert_id,
                'alert': self.agent_responses[alert_id].get('original_alert', {}),
                'metrics': self.agent_responses[alert_id].get('metric', {}),
                'logs': self.agent_responses[alert_id].get('log', {}),
                'tracing': self.agent_responses[alert_id].get('tracing', {}),
                'deployments': self.agent_responses[alert_id].get('deployment', {}),
                'notifications': self.agent_responses[alert_id].get('notification', {}),
                'postmortem': self.agent_responses[alert_id].get('postmortem', {})
            }
            
            # Send comprehensive data to root cause agent for analysis
            asyncio.run_coroutine_threadsafe(
                self.js.publish("root_cause_analysis", json.dumps(comprehensive_data).encode()),
                self.loop
            )
            logger.info(f"Sent comprehensive data to root cause agent for alert {alert_id}")
            
            # Clean up after processing
            self.alerts_in_progress.remove(alert_id)
            del self.agent_responses[alert_id]
    
    def analyze_incident(self, alert_id):
        """Use crewAI to analyze the collective responses and determine root cause"""
        # Note: This method is no longer needed as we're delegating to the root cause agent
        # But keeping it for backward compatibility
        pass
    
    def enrich_alert(self, alert):
        """Analyze and enrich the alert with additional context before distributing to agents"""
        try:
            # Extract basic information from the alert
            alert_id = alert.get('id', str(hash(json.dumps(alert))))
            alert_name = alert.get('labels', {}).get('alertname', 'UnknownAlert')
            service = alert.get('labels', {}).get('service', '')
            namespace = alert.get('labels', {}).get('namespace', 'default')
            
            # Add contextual information to enrich the alert
            enriched_alert = alert.copy()
            
            # Add unique id if not present
            if 'alert_id' not in enriched_alert:
                enriched_alert['alert_id'] = alert_id
                
            # Add timestamps for tracking
            now = datetime.utcnow()
            enriched_alert['processed_at'] = now.isoformat() + 'Z'
            
            # Add incident priority based on severity
            severity = alert.get('labels', {}).get('severity', 'warning').lower()
            if severity == 'critical':
                priority = 1  # P1 - highest priority
            elif severity == 'error' or severity == 'warning':
                priority = 2  # P2
            else:
                priority = 3  # P3
                
            enriched_alert['priority'] = priority
            
            # Provide context about which agents to involve
            agents_to_involve = ['metric', 'log', 'deployment', 'tracing', 'notification', 'postmortem']
            
            # Adjust recommended agents based on alert type
            if 'memory' in alert_name.lower() or 'cpu' in alert_name.lower():
                # For resource issues, prioritize metric and deployment agents
                enriched_alert['primary_investigation'] = ['metric', 'deployment']
            elif 'error' in alert_name.lower() or 'exception' in alert_name.lower():
                # For application errors, prioritize log and tracing agents
                enriched_alert['primary_investigation'] = ['log', 'tracing']
            elif 'deployment' in alert_name.lower() or 'config' in alert_name.lower():
                # For configuration/deployment issues, prioritize deployment agent
                enriched_alert['primary_investigation'] = ['deployment']
            else:
                # Default to all agents with equal priority
                enriched_alert['primary_investigation'] = agents_to_involve
                
            # Include the full list of agents for comprehensive analysis
            enriched_alert['all_agents'] = agents_to_involve
            
            # Add additional search context based on alert type
            if service:
                search_terms = [service]
                if 'pod' in alert.get('labels', {}):
                    search_terms.append(alert['labels']['pod'])
                    
                enriched_alert['search_context'] = {
                    'service': service,
                    'namespace': namespace,
                    'related_terms': search_terms
                }
                
            # Store the timestamp for timeout tracking
            self.alert_timestamps[alert_id] = now
            
            # Store the alert using JetStream for runbook agent to access later
            # This replaces the Redis key-value storage
            asyncio.run_coroutine_threadsafe(
                self.js.publish(f"alerts.{alert_id}", json.dumps(enriched_alert).encode()),
                self.loop
            )
            logger.info(f"Stored alert {alert_id} in NATS")
                
            logger.info(f"Enriched alert {alert_id} with priority {priority}")
            return enriched_alert
            
        except Exception as e:
            logger.error(f"Error enriching alert: {str(e)}")
            # Return original alert if enrichment fails
            if 'alert_id' not in alert:
                alert['alert_id'] = alert.get('id', str(hash(json.dumps(alert))))
            return alert
    
    def check_for_timeouts(self):
        """Check for alerts that have timed out waiting for agent responses"""
        now = datetime.utcnow()
        timed_out_alerts = []
        
        for alert_id, timestamp in self.alert_timestamps.items():
            # Check if the alert has been in progress for too long
            if alert_id in self.alerts_in_progress and (now - timestamp).total_seconds() > self.response_timeout:
                logger.warning(f"Alert {alert_id} has timed out waiting for agent responses")
                
                # Check which agents have responded and which are missing
                if alert_id in self.agent_responses:
                    responding_agents = set(self.agent_responses[alert_id].keys())
                    expected_agents = set(['metric', 'log', 'deployment', 'tracing'])
                    expected_agents = {agent for agent in expected_agents if is_agent_enabled(agent)}
                    
                    missing_agents = expected_agents - responding_agents - {'original_alert', 'notification', 'postmortem'}
                    responded_agents = expected_agents.intersection(responding_agents)
                    
                    logger.warning(f"Missing responses from: {missing_agents}")
                    
                    # If we have at least some agent responses, proceed with partial data
                    if responded_agents:
                        logger.info(f"Proceeding with partial data from: {responded_agents}")
                        
                        # Create comprehensive data with what we have
                        comprehensive_data = {
                            'alert_id': alert_id,
                            'alert': self.agent_responses[alert_id].get('original_alert', {}),
                            'partial_data': True,
                            'missing_agents': list(missing_agents)
                        }
                        
                        # Add available agent data
                        for agent in responded_agents:
                            comprehensive_data[agent] = self.agent_responses[alert_id].get(agent, {})
                            
                        # Send to root cause agent with the note that it's partial data
                        asyncio.run_coroutine_threadsafe(
                            self.js.publish("root_cause_analysis", json.dumps(comprehensive_data).encode()),
                            self.loop
                        )
                        logger.info(f"Sent partial data to root cause agent for timed-out alert {alert_id}")
                        
                    timed_out_alerts.append(alert_id)
        
        # Clean up timed out alerts
        for alert_id in timed_out_alerts:
            self.alerts_in_progress.remove(alert_id)
            if alert_id in self.agent_responses:
                del self.agent_responses[alert_id]
            if alert_id in self.alert_timestamps:
                del self.alert_timestamps[alert_id]

    async def alert_message_handler(self, msg):
        """Handle incoming alert messages"""
        try:
            # Parse the alert data
            alert = json.loads(msg.data.decode())
            alert_id = alert.get('id', str(hash(json.dumps(alert))))
            
            # Enrich the alert with additional context
            enriched_alert = self.enrich_alert(alert)
            
            # Store original alert in responses for reference
            if alert_id not in self.agent_responses:
                self.agent_responses[alert_id] = {}
            self.agent_responses[alert_id]['original_alert'] = enriched_alert
            
            # Add alert to in-progress set
            self.alerts_in_progress.add(alert_id)
            self.alert_timestamps[alert_id] = datetime.now()
            
            logger.info(f"Processing alert: {alert_id} - {enriched_alert.get('labels', {}).get('alertname', 'unknown')}")
            
            # Distribute the enriched alert to specialized agents (only if they are enabled)
            if is_agent_enabled('metric'):
                await self.js.publish("metric_agent", json.dumps(enriched_alert).encode())
                logger.info(f"Sent alert {alert_id} to metric agent")
            else:
                logger.info(f"Skipping disabled metric agent for alert {alert_id}")
                
            if is_agent_enabled('log'):
                await self.js.publish("log_agent", json.dumps(enriched_alert).encode())
                logger.info(f"Sent alert {alert_id} to log agent")
            else:
                logger.info(f"Skipping disabled log agent for alert {alert_id}")
                
            if is_agent_enabled('tracing'):
                await self.js.publish("tracing_agent", json.dumps(enriched_alert).encode())
                logger.info(f"Sent alert {alert_id} to tracing agent")
            else:
                logger.info(f"Skipping disabled tracing agent for alert {alert_id}")
                
            if is_agent_enabled('deployment'):
                await self.js.publish("deployment_agent", json.dumps(enriched_alert).encode())
                logger.info(f"Sent alert {alert_id} to deployment agent")
            else:
                logger.info(f"Skipping disabled deployment agent for alert {alert_id}")
                
            if is_agent_enabled('notification'):
                await self.js.publish("notification_agent", json.dumps(enriched_alert).encode())
                logger.info(f"Sent alert {alert_id} to notification agent")
            else:
                logger.info(f"Skipping disabled notification agent for alert {alert_id}")
                
            if is_agent_enabled('postmortem'):
                await self.js.publish("postmortem_agent", json.dumps(enriched_alert).encode())
                logger.info(f"Sent alert {alert_id} to postmortem agent")
            else:
                logger.info(f"Skipping disabled postmortem agent for alert {alert_id}")
            
            logger.info(f"Distributed alert {alert_id} to enabled specialized agents")
            
            # Acknowledge the message
            await msg.ack()
            
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding alert: {str(e)}")
            await msg.nak()  # Negative acknowledge
        except Exception as e:
            logger.error(f"Error processing alert: {str(e)}", exc_info=True)
            await msg.nak()  # Negative acknowledge

    async def response_message_handler(self, msg):
        """Handle incoming agent response messages"""
        try:
            # Parse the response data
            response = json.loads(msg.data.decode())
            logger.info(f"Received agent response: {response.get('agent')} for alert {response.get('alert_id')}")
            
            # Process the response
            self.handle_agent_response(response)
            
            # Acknowledge the message
            await msg.ack()
            
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding agent response: {str(e)}")
            await msg.nak()
        except Exception as e:
            logger.error(f"Error processing agent response: {str(e)}", exc_info=True)
            await msg.nak()

    async def root_cause_message_handler(self, msg):
        """Handle incoming root cause result messages"""
        try:
            # Parse the root cause result
            result = json.loads(msg.data.decode())
            logger.info(f"Received root cause analysis for alert {result.get('alert_id')}")
            
            # Send to notification agent for alert distribution
            if is_agent_enabled('notification'):
                await self.js.publish("notification_agent", json.dumps(result).encode())
                logger.info(f"Sent root cause result to notification agent for alert {result.get('alert_id')}")
            
            # Send to postmortem agent for documentation
            if is_agent_enabled('postmortem'):
                await self.js.publish("postmortem_agent", json.dumps(result).encode())
                logger.info(f"Sent root cause result to postmortem agent for alert {result.get('alert_id')}")
            
            # Acknowledge the message
            await msg.ack()
            
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding root cause result: {str(e)}")
            await msg.nak()
        except Exception as e:
            logger.error(f"Error processing root cause result: {str(e)}", exc_info=True)
            await msg.nak()

    async def alert_data_request_handler(self, msg):
        """Handle requests for alert data"""
        try:
            # Parse the request
            request = json.loads(msg.data.decode())
            alert_id = request.get('alert_id')
            logger.info(f"Received alert data request for alert ID: {alert_id}")
            
            # Check if we have the alert data in our in-memory store
            if alert_id in self.agent_responses and 'original_alert' in self.agent_responses[alert_id]:
                alert_data = self.agent_responses[alert_id]['original_alert']
                logger.info(f"Found alert data in memory for alert ID: {alert_id}")
            else:
                # Try to get it from JetStream
                try:
                    msg = await self.js.get_msg(f"alerts.{alert_id}")
                    if msg:
                        alert_data = json.loads(msg.data.decode())
                        logger.info(f"Found alert data in JetStream for alert ID: {alert_id}")
                    else:
                        logger.warning(f"Alert data not found for alert ID: {alert_id}")
                        alert_data = {"alert_id": alert_id, "error": "Alert data not found"}
                except Exception as e:
                    logger.warning(f"Error retrieving alert data: {str(e)}")
                    alert_data = {"alert_id": alert_id, "error": "Alert data not found"}
            
            # Publish the alert data on the specific response channel for this request
            await self.js.publish(f"alert_data_response.{alert_id}", json.dumps(alert_data).encode())
            logger.info(f"Published alert data for alert ID: {alert_id}")
            
            # Acknowledge the message
            await msg.ack()
            
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding alert data request: {str(e)}")
            await msg.nak()
        except Exception as e:
            logger.error(f"Error processing alert data request: {str(e)}", exc_info=True)
            await msg.nak()

    async def timeout_checker(self):
        """Periodically check for timeouts"""
        while True:
            try:
                self.check_for_timeouts()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in timeout checker: {str(e)}")
                await asyncio.sleep(30)  # Continue checking even if there was an error

    async def setup_subscriptions(self):
        """Set up all the necessary NATS subscriptions"""
        # Create a durable consumer for alerts
        alert_consumer = ConsumerConfig(
            durable_name="orchestrator_alerts",
            deliver_policy=DeliverPolicy.ALL,
            ack_policy="explicit",
            max_deliver=3
        )
        
        # Subscribe to alerts
        await self.js.subscribe(
            "alerts",
            cb=self.alert_message_handler,
            config=alert_consumer
        )
        logger.info("Subscribed to alerts")
        
        # Create a durable consumer for agent responses
        response_consumer = ConsumerConfig(
            durable_name="orchestrator_responses",
            deliver_policy=DeliverPolicy.ALL,
            ack_policy="explicit",
            max_deliver=3
        )
        
        # Subscribe to agent responses
        await self.js.subscribe(
            "orchestrator_response",
            cb=self.response_message_handler,
            config=response_consumer
        )
        logger.info("Subscribed to agent responses")
        
        # Create a durable consumer for root cause results
        root_cause_consumer = ConsumerConfig(
            durable_name="orchestrator_root_cause",
            deliver_policy=DeliverPolicy.ALL,
            ack_policy="explicit",
            max_deliver=3
        )
        
        # Subscribe to root cause results
        await self.js.subscribe(
            "root_cause_result",
            cb=self.root_cause_message_handler,
            config=root_cause_consumer
        )
        logger.info("Subscribed to root cause results")
        
        # Create a durable consumer for alert data requests
        alert_data_consumer = ConsumerConfig(
            durable_name="orchestrator_alert_data",
            deliver_policy=DeliverPolicy.ALL,
            ack_policy="explicit",
            max_deliver=3
        )
        
        # Subscribe to alert data requests
        await self.js.subscribe(
            "alert_data_request",
            cb=self.alert_data_request_handler,
            config=alert_data_consumer
        )
        logger.info("Subscribed to alert data requests")
        
        # Start the timeout checker
        asyncio.create_task(self.timeout_checker())

    async def run_async(self):
        """Run the orchestrator agent asynchronously"""
        # Connect to NATS
        await self.connect()
        
        # Set up subscriptions
        await self.setup_subscriptions()
        
        logger.info("Orchestrator agent is running...")
        
        # Keep the connection alive
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour, or until interrupted

    def run(self):
        """Start the orchestrator agent to listen for alerts and agent responses"""
        try:
            # Run the async methods in the event loop
            self.loop.run_until_complete(self.run_async())
        except KeyboardInterrupt:
            logger.info("Orchestrator agent shutting down...")
            if self.nats_client and self.nats_client.is_connected:
                self.loop.run_until_complete(self.nats_client.close())
            self.loop.close()
        except Exception as e:
            logger.error(f"Unexpected error in orchestrator agent: {str(e)}", exc_info=True)
            if self.nats_client and self.nats_client.is_connected:
                self.loop.run_until_complete(self.nats_client.close())
            self.loop.close()
            raise