# File: orchestrator/agent.py
import redis
import json
import os
import time
import logging
import threading
from datetime import datetime, timedelta
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from common.config import is_agent_enabled

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("orchestrator")

load_dotenv()

class OrchestratorAgent:
    def __init__(self, redis_host=None, redis_port=None, openai_model=None, response_timeout=300):
        # Get configuration from environment variables or use defaults
        self.redis_host = redis_host or os.environ.get('REDIS_HOST', 'redis')
        self.redis_port = redis_port or int(os.environ.get('REDIS_PORT', 6379))
        self.openai_model = openai_model or os.environ.get('OPENAI_MODEL', 'gpt-4')
        self.response_timeout = response_timeout or int(os.environ.get('RESPONSE_TIMEOUT_SECONDS', 300))
        
        try:
            # Initialize Redis client
            self.redis_client = redis.Redis(host=self.redis_host, port=self.redis_port)
            logger.info(f"Connected to Redis at {self.redis_host}:{self.redis_port}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise
        
        # Initialize OpenAI model
        self.llm = ChatOpenAI(model=self.openai_model)
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
        if all(agent in self.agent_responses[alert_id] for agent in expected_agents):
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
            self.redis_client.publish("root_cause_analysis", json.dumps(comprehensive_data))
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
            
            # Store the alert in Redis for runbook agent to access later
            # Use a key with 24-hour expiration
            self.redis_client.setex(
                f"alert:{alert_id}", 
                86400,  # 24 hours in seconds
                json.dumps(enriched_alert)
            )
            logger.info(f"Stored alert {alert_id} in Redis cache for 24 hours")
                
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
        
        for alert_id in list(self.alerts_in_progress):
            if alert_id in self.alert_timestamps:
                start_time = self.alert_timestamps[alert_id]
                elapsed = now - start_time
                
                if elapsed.total_seconds() > self.response_timeout:
                    logger.warning(f"Alert {alert_id} timed out after {elapsed.total_seconds()} seconds")
                    
                    # Check which agents responded and which didn't
                    responded_agents = set(self.agent_responses.get(alert_id, {}).keys()) - {'original_alert'}
                    expected_agents = {'metric', 'log', 'deployment', 'tracing', 'notification', 'postmortem'}
                    missing_agents = expected_agents - responded_agents
                    
                    logger.warning(f"Missing responses from agents: {missing_agents}")
                    
                    # If we have at least some responses, continue with what we have
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
                        self.redis_client.publish("root_cause_analysis", json.dumps(comprehensive_data))
                        logger.info(f"Sent partial data to root cause agent for timed-out alert {alert_id}")
                        
                    timed_out_alerts.append(alert_id)
        
        # Clean up timed out alerts
        for alert_id in timed_out_alerts:
            self.alerts_in_progress.remove(alert_id)
            if alert_id in self.agent_responses:
                del self.agent_responses[alert_id]
            if alert_id in self.alert_timestamps:
                del self.alert_timestamps[alert_id]
        
    def run(self):
        """Start the orchestrator agent to listen for alerts and agent responses"""
        try:
            # Listen for initial alerts
            alert_pubsub = self.redis_client.pubsub()
            alert_pubsub.subscribe("alerts")
            
            # Listen for agent responses
            response_pubsub = self.redis_client.pubsub()
            response_pubsub.subscribe("orchestrator_response")
            
            # Listen for root cause results
            root_cause_pubsub = self.redis_client.pubsub()
            root_cause_pubsub.subscribe("root_cause_result")
            
            # Listen for alert data requests from the runbook agent
            alert_request_pubsub = self.redis_client.pubsub()
            alert_request_pubsub.subscribe("alert_data_request")
            
            logger.info("Listening for alerts and agent responses...")
            
            # Start the response listener in a separate thread
            def listen_for_responses():
                try:
                    for message in response_pubsub.listen():
                        if message['type'] == 'message':
                            try:
                                response = json.loads(message['data'])
                                logger.info(f"Received agent response: {response.get('agent')} for alert {response.get('alert_id')}")
                                self.handle_agent_response(response)
                            except json.JSONDecodeError as e:
                                logger.error(f"Error decoding agent response: {str(e)}")
                            except Exception as e:
                                logger.error(f"Error processing agent response: {str(e)}", exc_info=True)
                except redis.RedisError as e:
                    logger.error(f"Redis error in response listener: {str(e)}")
                    # Attempt to reconnect
                    time.sleep(5)
                    self.redis_client = redis.Redis(host=self.redis_host, port=self.redis_port)
                    listen_for_responses()  # Recursively restart
            
            # Start the root cause listener in a separate thread
            def listen_for_root_cause():
                try:
                    for message in root_cause_pubsub.listen():
                        if message['type'] == 'message':
                            try:
                                result = json.loads(message['data'])
                                logger.info(f"Received root cause analysis for alert {result.get('alert_id')}")
                                
                                # Send to notification agent for alert distribution
                                if is_agent_enabled('notification'):
                                    self.redis_client.publish("notification_agent", json.dumps(result))
                                    logger.info(f"Sent root cause result to notification agent for alert {result.get('alert_id')}")
                                
                                # Send to postmortem agent for documentation
                                if is_agent_enabled('postmortem'):
                                    self.redis_client.publish("postmortem_agent", json.dumps(result))
                                    logger.info(f"Sent root cause result to postmortem agent for alert {result.get('alert_id')}")
                                
                            except json.JSONDecodeError as e:
                                logger.error(f"Error decoding root cause result: {str(e)}")
                            except Exception as e:
                                logger.error(f"Error processing root cause result: {str(e)}", exc_info=True)
                except redis.RedisError as e:
                    logger.error(f"Redis error in root cause listener: {str(e)}")
                    # Attempt to reconnect
                    time.sleep(5)
                    self.redis_client = redis.Redis(host=self.redis_host, port=self.redis_port)
                    listen_for_root_cause()  # Recursively restart
            
            # Start the alert data request listener in a separate thread
            def listen_for_alert_data_requests():
                try:
                    for message in alert_request_pubsub.listen():
                        if message['type'] == 'message':
                            try:
                                request = json.loads(message['data'])
                                alert_id = request.get('alert_id')
                                logger.info(f"Received alert data request for alert ID: {alert_id}")
                                
                                # Check if we have the alert data in our in-memory store
                                if alert_id in self.agent_responses and 'original_alert' in self.agent_responses[alert_id]:
                                    alert_data = self.agent_responses[alert_id]['original_alert']
                                    logger.info(f"Found alert data in memory for alert ID: {alert_id}")
                                else:
                                    # Try to get it from Redis
                                    alert_data_str = self.redis_client.get(f"alert:{alert_id}")
                                    if alert_data_str:
                                        alert_data = json.loads(alert_data_str)
                                        logger.info(f"Found alert data in Redis for alert ID: {alert_id}")
                                    else:
                                        logger.warning(f"Alert data not found for alert ID: {alert_id}")
                                        alert_data = {"alert_id": alert_id, "error": "Alert data not found"}
                                
                                # Publish the alert data on the specific response channel for this request
                                self.redis_client.publish(f"alert_data_response:{alert_id}", json.dumps(alert_data))
                                logger.info(f"Published alert data for alert ID: {alert_id}")
                                
                            except json.JSONDecodeError as e:
                                logger.error(f"Error decoding alert data request: {str(e)}")
                            except Exception as e:
                                logger.error(f"Error processing alert data request: {str(e)}", exc_info=True)
                except redis.RedisError as e:
                    logger.error(f"Redis error in alert data request listener: {str(e)}")
                    # Attempt to reconnect
                    time.sleep(5)
                    self.redis_client = redis.Redis(host=self.redis_host, port=self.redis_port)
                    listen_for_alert_data_requests()  # Recursively restart
            
            # Start timeout checker in a separate thread
            def check_timeouts_periodically():
                while True:
                    try:
                        self.check_for_timeouts()
                        time.sleep(30)  # Check every 30 seconds
                    except Exception as e:
                        logger.error(f"Error in timeout checker: {str(e)}")
                        time.sleep(30)  # Continue checking even if there was an error
            
            # Start threads
            response_thread = threading.Thread(target=listen_for_responses)
            response_thread.daemon = True
            response_thread.start()
            
            root_cause_thread = threading.Thread(target=listen_for_root_cause)
            root_cause_thread.daemon = True
            root_cause_thread.start()
            
            alert_request_thread = threading.Thread(target=listen_for_alert_data_requests)
            alert_request_thread.daemon = True
            alert_request_thread.start()
            
            timeout_thread = threading.Thread(target=check_timeouts_periodically)
            timeout_thread.daemon = True
            timeout_thread.start()
            
            # Main loop for processing alerts
            while True:
                try:
                    # Process each message from the alert channel
                    message = alert_pubsub.get_message(timeout=1)
                    if message and message['type'] == 'message':
                        try:
                            alert = json.loads(message['data'])
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
                                self.redis_client.publish("metric_agent", json.dumps(enriched_alert))
                                logger.info(f"Sent alert {alert_id} to metric agent")
                            else:
                                logger.info(f"Skipping disabled metric agent for alert {alert_id}")
                                
                            if is_agent_enabled('log'):
                                self.redis_client.publish("log_agent", json.dumps(enriched_alert))
                                logger.info(f"Sent alert {alert_id} to log agent")
                            else:
                                logger.info(f"Skipping disabled log agent for alert {alert_id}")
                                
                            if is_agent_enabled('tracing'):
                                self.redis_client.publish("tracing_agent", json.dumps(enriched_alert))
                                logger.info(f"Sent alert {alert_id} to tracing agent")
                            else:
                                logger.info(f"Skipping disabled tracing agent for alert {alert_id}")
                                
                            if is_agent_enabled('deployment'):
                                self.redis_client.publish("deployment_agent", json.dumps(enriched_alert))
                                logger.info(f"Sent alert {alert_id} to deployment agent")
                            else:
                                logger.info(f"Skipping disabled deployment agent for alert {alert_id}")
                                
                            if is_agent_enabled('notification'):
                                self.redis_client.publish("notification_agent", json.dumps(enriched_alert))
                                logger.info(f"Sent alert {alert_id} to notification agent")
                            else:
                                logger.info(f"Skipping disabled notification agent for alert {alert_id}")
                                
                            if is_agent_enabled('postmortem'):
                                self.redis_client.publish("postmortem_agent", json.dumps(enriched_alert))
                                logger.info(f"Sent alert {alert_id} to postmortem agent")
                            else:
                                logger.info(f"Skipping disabled postmortem agent for alert {alert_id}")
                            
                            logger.info(f"Distributed alert {alert_id} to enabled specialized agents")
                            
                        except json.JSONDecodeError as e:
                            logger.error(f"Error decoding alert: {str(e)}")
                        except Exception as e:
                            logger.error(f"Error processing alert: {str(e)}", exc_info=True)
                    
                    # Small sleep to prevent CPU spinning when there are no messages
                    time.sleep(0.1)
                    
                except redis.RedisError as e:
                    logger.error(f"Redis error in main loop: {str(e)}")
                    # Attempt to reconnect
                    time.sleep(5)
                    self.redis_client = redis.Redis(host=self.redis_host, port=self.redis_port)
                    alert_pubsub = self.redis_client.pubsub()
                    alert_pubsub.subscribe("alerts")
                    
        except KeyboardInterrupt:
            logger.info("Orchestrator agent shutting down...")
        except Exception as e:
            logger.error(f"Unexpected error in orchestrator agent: {str(e)}", exc_info=True)
            raise