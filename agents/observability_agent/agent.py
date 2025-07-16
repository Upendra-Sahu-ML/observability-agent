"""
Consolidated Observability Agent

This agent combines metric, log, and tracing analysis into a single efficient container.
It provides comprehensive observability data analysis while reducing operational complexity.
"""
import os
import json
import logging
import asyncio
import nats
from nats.js.api import ConsumerConfig, DeliverPolicy
from datetime import datetime, timedelta
from crewai import Agent, Task, Crew
from crewai.llm import LLM
from crewai.tools import tool
from crewai import Process
from dotenv import load_dotenv

# Import simplified tools and observability manager
from common.simplified_tools import SimplifiedToolManager
from common.stream_config import get_publish_subject
from common.agent_status import start_agent_status_publishing
from common.observability_manager import ObservabilityManager

# Legacy tools for fallback (if needed)
from common.tools.metric_tools import PrometheusQueryTool, MetricAnalysisTool
from common.tools.log_tools import LokiQueryTool, PodLogTool, FileLogTool
from common.tools.tempo_tools import TempoTools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class ObservabilityAgent:
    """
    Consolidated agent that combines metric, log, and tracing analysis.
    
    This agent replaces the separate metric_agent, log_agent, and tracing_agent
    with a single efficient implementation that can analyze all observability data.
    """
    
    def __init__(self, 
                 prometheus_url="http://prometheus:9090",
                 loki_url="http://loki:3100", 
                 tempo_url="http://tempo:3200",
                 log_directory="/var/log",
                 nats_server="nats://nats:4222"):
        
        # NATS connection parameters
        self.nats_server = nats_server
        self.nats_client = None
        self.js = None  # JetStream context
        
        # Observability data source configurations
        self.prometheus_url = prometheus_url
        self.loki_url = loki_url
        self.tempo_url = tempo_url
        self.log_directory = log_directory
        
        # OpenAI API key from environment
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY environment variable not set")
        
        # Initialize OpenAI model
        self.llm = LLM(model=os.environ.get("OPENAI_MODEL", "gpt-4"))
        
        # Initialize smart observability manager with fallback strategies
        self.observability_manager = ObservabilityManager(
            prometheus_url=self.prometheus_url,
            loki_url=self.loki_url,
            tempo_url=self.tempo_url
        )
        
        # Initialize simplified tool manager (15 essential tools instead of 50+)
        self.simplified_tools = SimplifiedToolManager(
            observability_manager=self.observability_manager
        )
        
        # Initialize legacy tools for fallback if needed
        self._initialize_legacy_tools()
        
        # Agent status publisher (will be initialized after NATS connection)
        self.status_publisher = None
        
        # Create specialized analysis agents
        self._create_analysis_agents()
    
    def _initialize_legacy_tools(self):
        """Initialize legacy tools for fallback if simplified tools are unavailable"""
        # Metric tools (from metric_agent)
        self.prometheus_tool = PrometheusQueryTool(prometheus_url=self.prometheus_url)
        self.metric_analysis_tool = MetricAnalysisTool()
        
        # Log tools (from log_agent)
        self.loki_tool = LokiQueryTool(loki_url=self.loki_url)
        self.pod_log_tool = PodLogTool()
        self.file_log_tool = FileLogTool()
        
        # Tracing tools (from tracing_agent)
        self.tempo_tools = TempoTools(tempo_url=self.tempo_url)
    
    def _create_analysis_agents(self):
        """Create single unified observability analyst"""
        
        # === UNIFIED OBSERVABILITY ANALYST ===
        self.unified_observability_analyst = Agent(
            role="Unified Observability Analyst",
            goal="Analyze metrics, logs, and traces comprehensively to understand incident patterns, correlate findings across all observability domains, and provide actionable insights for runbook selection and incident response",
            backstory="""You are an expert at comprehensive observability analysis with the ability to work across all data sources. Your expertise includes:
            
            **Multi-Domain Analysis**: You can analyze metrics from Prometheus, logs from Loki/Kubernetes, and traces from Tempo, adapting your analysis based on what data sources are available.
            
            **Intelligent Prioritization**: You focus your analysis on the most relevant data for the specific incident, whether that's resource metrics for performance issues, error logs for application failures, or trace data for service communication problems.
            
            **Fallback Strategies**: When observability tools are unavailable, you can work with basic Kubernetes data, alert information, and manual inspection to still provide valuable incident analysis.
            
            **Runbook-Focused Analysis**: Your analysis is specifically designed to help select and execute the most appropriate runbook for incident remediation, providing context that helps with both runbook selection and execution validation.
            
            **Efficient Correlation**: You efficiently correlate findings across metrics, logs, and traces to provide a unified incident narrative that supports automated response decisions.""",
            verbose=True,  # Keep detailed for quality analysis
            llm=self.llm,
            tools=self.simplified_tools.get_tools_for_agent("observability") + [
                # Add specialized analysis function
                self._analyze_comprehensive_incident
            ]
        )
    
    @tool
    def _analyze_comprehensive_incident(self, incident_data: dict) -> str:
        """
        Perform comprehensive incident analysis using all available observability data.
        This replaces the multiple specialized analysis tools with one intelligent function.
        """
        try:
            # Use the observability manager to get comprehensive context
            context = self.observability_manager.get_comprehensive_incident_context(incident_data)
            
            # Extract key incident details
            service = incident_data.get('labels', {}).get('service', 'unknown')
            namespace = incident_data.get('labels', {}).get('namespace', 'default')
            alert_name = incident_data.get('alert_name', 'unknown')
            
            # Build comprehensive analysis
            analysis = {
                "incident_classification": context.get('incident_classification', 'unknown'),
                "service_health": context.get('service_health', {}),
                "metrics_summary": context.get('metrics_summary', {}),
                "recent_errors": context.get('recent_errors', []),
                "suggested_actions": context.get('suggested_actions', []),
                "runbook_recommendations": context.get('runbook_recommendations', [])
            }
            
            return f"Comprehensive analysis for {service}: {json.dumps(analysis, indent=2)}"
            
        except Exception as e:
            logger.error(f"Failed comprehensive incident analysis: {e}")
            return f"Analysis failed: {e}"
    
    async def connect(self):
        """Connect to NATS server and set up JetStream"""
        try:
            # Connect to NATS server
            self.nats_client = await nats.connect(self.nats_server)
            logger.info(f"[ObservabilityAgent] Connected to NATS server at {self.nats_server}")
            
            # Create JetStream context
            self.js = self.nats_client.jetstream()
            
            # Initialize agent status publisher
            try:
                self.status_publisher = await start_agent_status_publishing(
                    agent_id="observability-agent",
                    agent_name="Observability Agent",
                    js=self.js,
                    publish_interval=30  # Publish status every 30 seconds
                )
                logger.info("[ObservabilityAgent] Agent status publishing started")
            except Exception as e:
                logger.warning(f"[ObservabilityAgent] Failed to start agent status publishing: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"[ObservabilityAgent] Failed to connect to NATS: {str(e)}", exc_info=True)
            raise
    
    def _determine_observability_issue(self, alert, analysis_results):
        """Determine the primary observability issue based on all analysis results"""
        alert_name = alert.get("labels", {}).get("alertname", "").lower()
        
        # Combine all analysis results
        combined_analysis = "\n".join([
            str(result) for result in analysis_results.values() if result
        ]).lower()
        
        # Priority-based issue classification
        if "out of memory" in combined_analysis or "oom" in combined_analysis:
            return "Memory exhaustion detected"
        elif "cpu" in combined_analysis and ("high" in combined_analysis or "saturated" in combined_analysis):
            return "CPU saturation detected"
        elif "error rate" in combined_analysis or "exception" in combined_analysis:
            return "Application error increase"
        elif "latency" in combined_analysis or "slow" in combined_analysis:
            return "Performance degradation"
        elif "timeout" in combined_analysis:
            return "Request timeout issues"
        elif "bottleneck" in combined_analysis:
            return "Performance bottleneck identified"
        elif "dependency" in combined_analysis:
            return "Service dependency failure"
        else:
            # Fall back to alert-based categorization
            if "error" in alert_name:
                return "Error rate alert"
            elif "latency" in alert_name:
                return "Latency alert"
            elif "memory" in alert_name:
                return "Memory alert"
            elif "cpu" in alert_name:
                return "CPU alert"
            else:
                return "Observability anomaly detected"
    
    def _create_observability_tasks(self, alert):
        """Create comprehensive observability analysis tasks"""
        alert_id = alert.get("alert_id", "unknown")
        alert_name = alert.get("labels", {}).get("alertname", "Unknown Alert")
        service = alert.get("labels", {}).get("service", "")
        namespace = alert.get("labels", {}).get("namespace", "default")
        pod = alert.get("labels", {}).get("pod", "")
        
        # Determine time range - default to 15 min before alert
        time_range = "-15m"
        
        # Base context information that all analyzers will use
        base_context = f"""
        Alert: {alert_name} (ID: {alert_id})
        Service: {service}
        Namespace: {namespace}
        Pod: {pod}
        Time range to analyze: {time_range} to now
        """
        
        # === UNIFIED OBSERVABILITY ANALYSIS ===
        unified_analysis_task = Task(
            description=base_context + """
            Perform comprehensive observability analysis for this incident using all available data sources:
            
            **Adaptive Analysis Strategy:**
            Based on available observability tools, prioritize your analysis:
            1. If Prometheus is available: Analyze metrics (CPU, memory, request rates, error rates)
            2. If Loki is available: Analyze logs (errors, performance, operational events)  
            3. If Tempo is available: Analyze traces (service dependencies, latency patterns)
            4. If tools are unavailable: Use Kubernetes data and alert information
            
            **Multi-Domain Correlation:**
            1. **Metrics Analysis**: Resource utilization, performance trends, error rates
            2. **Log Analysis**: Error patterns, exceptions, operational events
            3. **Trace Analysis**: Service interactions, dependency issues (if available)
            4. **Cross-Correlation**: Connect findings across all domains
            
            **Runbook-Focused Insights:**
            Provide analysis specifically designed for runbook selection:
            1. **Issue Classification**: Is this a resource, application, network, or dependency issue?
            2. **Severity Assessment**: How critical is the impact and how quickly must it be resolved?
            3. **Remediation Context**: What specific conditions exist that would affect runbook execution?
            4. **Validation Criteria**: What metrics/logs should be monitored to verify fix success?
            
            **Key Questions for Runbook Selection:**
            - What type of incident is this (performance, error, resource, dependency)?
            - What specific services/components are affected?
            - What observable symptoms can guide runbook selection?
            - What conditions should be met to consider the incident resolved?
            - Are there any contraindications for automated remediation?
            
            **Fallback Analysis:**
            If observability tools are limited, focus on:
            - Alert details and severity
            - Basic Kubernetes pod/service status
            - Recent deployment or configuration changes
            - Historical incident patterns
            
            Provide actionable analysis that directly supports intelligent runbook selection and execution validation.
            """,
            agent=self.unified_observability_analyst,
            expected_output="Comprehensive observability analysis with issue classification, severity assessment, runbook selection guidance, and validation criteria for incident remediation"
        )
        
        return [unified_analysis_task]
    
    async def analyze_observability_data(self, alert):
        """Perform comprehensive observability analysis using all data sources"""
        logger.info(f"[ObservabilityAgent] Starting comprehensive analysis for alert ID: {alert.get('alert_id', 'unknown')}")
        
        # Create comprehensive analysis tasks
        tasks, time_range = self._create_observability_tasks(alert)
        
        # Create crew with all analyzers
        crew = Crew(
            agents=[
                self.system_metrics_analyst,
                self.application_metrics_analyst,
                self.error_log_analyzer,
                self.performance_log_analyzer,
                self.trace_analyzer,
                self.correlation_analyst
            ],
            tasks=tasks,
            verbose=True,
            process=Process.sequential()  # Run in sequence to allow correlation
        )
        
        # Execute comprehensive analysis
        results = crew.kickoff()
        
        # Store data in appropriate streams for UI consumption
        await self._publish_observability_data(alert, results, time_range)
        
        # Collect metadata about what was analyzed
        observability_data = {
            "time_range": time_range,
            "service": alert.get("labels", {}).get("service", ""),
            "namespace": alert.get("labels", {}).get("namespace", "default"),
            "pod": alert.get("labels", {}).get("pod", ""),
            "data_sources": ["prometheus", "loki", "tempo"]
        }
        
        return results, observability_data
    
    async def _publish_observability_data(self, alert, analysis_results, time_range):
        """Publish observability data to appropriate streams for UI consumption"""
        try:
            service = alert.get("labels", {}).get("service", "unknown")
            alert_id = alert.get("alert_id", "unknown")
            timestamp = datetime.now().isoformat()
            
            # Publish to METRICS stream
            metrics_data = {
                "alert_id": alert_id,
                "service": service,
                "timestamp": timestamp,
                "time_range": time_range,
                "analysis": str(analysis_results),
                "data_source": "prometheus"
            }
            await self.js.publish(f"metrics.{service}", json.dumps(metrics_data).encode())
            
            # Publish to LOGS stream  
            logs_data = {
                "alert_id": alert_id,
                "service": service,
                "timestamp": timestamp,
                "time_range": time_range,
                "analysis": str(analysis_results),
                "data_source": "loki"
            }
            await self.js.publish(f"logs.{service}", json.dumps(logs_data).encode())
            
            # Publish to TRACES stream
            traces_data = {
                "alert_id": alert_id,
                "service": service,
                "timestamp": timestamp,
                "time_range": time_range,
                "analysis": str(analysis_results),
                "data_source": "tempo"
            }
            await self.js.publish(f"traces.{service}", json.dumps(traces_data).encode())
            
            logger.info(f"[ObservabilityAgent] Published observability data for service {service}")
            
        except Exception as e:
            logger.error(f"[ObservabilityAgent] Error publishing observability data: {str(e)}", exc_info=True)
    
    async def message_handler(self, msg):
        """Handle incoming NATS messages for observability analysis"""
        try:
            # Parse the alert data
            alert = json.loads(msg.data.decode())
            
            # Ensure alert_id is set
            if 'alert_id' not in alert and 'id' in alert:
                alert['alert_id'] = alert['id']
            
            logger.info(f"[ObservabilityAgent] Processing alert: {alert.get('alert_id', 'unknown')}")
            
            # Perform comprehensive observability analysis
            analysis_results, observability_data = await self.analyze_observability_data(alert)
            
            # Determine the primary observability issue
            observed_issue = self._determine_observability_issue(alert, analysis_results)
            
            # Prepare consolidated result for the orchestrator
            result = {
                "agent": "observability",
                "observed": observed_issue,
                "analysis": {
                    "metrics": str(analysis_results),
                    "logs": str(analysis_results),
                    "traces": str(analysis_results),
                    "correlation": str(analysis_results)
                },
                "alert_id": alert.get("alert_id", "unknown"),
                "timestamp": datetime.now().isoformat(),
                "data_sources": observability_data["data_sources"]
            }
            
            logger.info(f"[ObservabilityAgent] Sending analysis for alert ID: {result['alert_id']}")
            
            # Publish result to orchestrator
            await self.js.publish(get_publish_subject("orchestrator_response"), json.dumps(result).encode())
            logger.info(f"[ObservabilityAgent] Published analysis result for alert ID: {result['alert_id']}")
            
            # Acknowledge the message
            await msg.ack()
            
        except Exception as e:
            logger.error(f"[ObservabilityAgent] Error processing message: {str(e)}", exc_info=True)
            # Negative acknowledge the message so it can be redelivered
            await msg.nak()
    
    async def listen(self):
        """Listen for alerts from the orchestrator"""
        logger.info("[ObservabilityAgent] Starting to listen for alerts")
        
        try:
            # Connect to NATS if not already connected
            if not self.nats_client or not self.nats_client.is_connected:
                await self.connect()
            
            # Create a durable consumer for observability analysis
            consumer_config = ConsumerConfig(
                durable_name="observability_agent",
                deliver_policy=DeliverPolicy.ALL,
                ack_policy="explicit",
                max_deliver=5,  # Retry up to 5 times
                ack_wait=120,   # Wait 2 minutes for acknowledgment (analysis can take time)
            )
            
            # Subscribe to observability analysis requests
            await self.js.subscribe(
                "observability_agent",  # New consolidated subject
                cb=self.message_handler,
                queue="observability_processors",
                stream="AGENT_TASKS",
                config=consumer_config
            )
            
            logger.info("[ObservabilityAgent] Subscribed to observability_agent subject")
            
            # Keep the connection alive
            while True:
                await asyncio.sleep(3600)  # Sleep for an hour, or until interrupted
                logger.info("[ObservabilityAgent] Still listening for observability analysis requests")
                
        except Exception as e:
            logger.error(f"[ObservabilityAgent] Error in listen(): {str(e)}", exc_info=True)
            # Stop status publishing if there's an error
            if self.status_publisher:
                try:
                    await self.status_publisher.stop_publishing()
                    logger.info("[ObservabilityAgent] Agent status publishing stopped")
                except Exception as pub_e:
                    logger.warning(f"[ObservabilityAgent] Error stopping status publisher: {pub_e}")
            # Wait and retry
            logger.info("[ObservabilityAgent] Will retry in 30 seconds...")
            await asyncio.sleep(30)
            # Try calling listen again after delay
            return await self.listen()

if __name__ == "__main__":
    async def main():
        agent = ObservabilityAgent()
        await agent.listen()
    
    asyncio.run(main())