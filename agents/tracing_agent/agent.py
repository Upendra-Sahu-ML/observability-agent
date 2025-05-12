"""
Tracing agent for analyzing distributed trace data
"""
import os
import json
import logging
import asyncio
from datetime import datetime, timedelta

import redis

from common.tools.tempo_tools import TempoTraceTool, TempoServiceTool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TracingAgent:
    """Agent for analyzing and correlating distributed trace data"""
    
    def __init__(self, tempo_url=None, services_to_monitor=None, redis_host='redis', redis_port=6379):
        """
        Initialize the tracing agent
        
        Args:
            tempo_url (str, optional): URL for Tempo API
            services_to_monitor (list, optional): List of services to actively monitor
            redis_host (str, optional): Redis host
            redis_port (int, optional): Redis port
        """
        self.tempo_url = tempo_url or os.environ.get('TEMPO_URL')
        self.services_to_monitor = services_to_monitor or os.environ.get('SERVICES_TO_MONITOR', '').split(',')
        
        # Clean up empty entries
        self.services_to_monitor = [s.strip() for s in self.services_to_monitor if s.strip()]
        
        # Initialize Redis client
        self.redis_client = redis.Redis(host=redis_host, port=redis_port)
        
        # Initialize tools
        self.trace_tool = TempoTraceTool(tempo_url=self.tempo_url)
        self.service_tool = TempoServiceTool(tempo_url=self.tempo_url)
        
        # Cache for service performance baselines
        self.service_baselines = {}
        
        logger.info(f"Tracing agent initialized, monitoring services: {', '.join(self.services_to_monitor) if self.services_to_monitor else 'None'}")
    
    async def find_traces_for_timerange(self, start, end, service=None, operation=None, min_duration=None, limit=50):
        """
        Find traces for a specific time range
        
        Args:
            start (str): Start time in ISO format
            end (str): End time in ISO format
            service (str, optional): Filter by service name
            operation (str, optional): Filter by operation name
            min_duration (str, optional): Minimum duration (e.g., "100ms", "1.5s")
            limit (int, optional): Maximum number of traces to return
            
        Returns:
            dict: Trace information
        """
        trace_results = self.trace_tool.execute(
            service=service,
            operation=operation,
            minDuration=min_duration,
            limit=limit,
            start=start,
            end=end
        )
        
        return trace_results
    
    async def analyze_trace(self, trace_id):
        """
        Perform detailed analysis of a specific trace
        
        Args:
            trace_id (str): Trace ID to analyze
            
        Returns:
            dict: Analysis of the trace including potential issues
        """
        trace_details = self.trace_tool.get_trace_by_id(trace_id)
        
        if "error" in trace_details:
            return {"error": f"Failed to analyze trace: {trace_details['error']}"}
        
        analysis = {
            "trace_id": trace_id,
            "services_involved": trace_details.get("services", []),
            "total_duration_ms": trace_details.get("duration_ms", 0),
            "span_count": trace_details.get("span_count", 0),
            "issues": trace_details.get("issues", []),
            "recommendations": []
        }
        
        # Add service-specific performance recommendations
        if analysis.get("total_duration_ms", 0) > 1000:  # Trace longer than 1 second
            analysis["recommendations"].append({
                "type": "performance",
                "description": "This trace is taking longer than 1 second to complete, which may impact user experience.",
                "suggestion": "Consider optimizing the slowest spans in this trace."
            })
        
        # Check for error spans and provide recommendations
        error_issues = [issue for issue in trace_details.get("issues", []) if issue.get("type") == "error"]
        if error_issues:
            analysis["recommendations"].append({
                "type": "error_handling",
                "description": f"Found {len(error_issues)} error(s) in this trace.",
                "suggestion": "Investigate the error messages and consider adding better error handling or retries."
            })
        
        # Check for long-duration spans
        long_duration_spans = [issue for issue in trace_details.get("issues", []) if issue.get("type") == "long_duration"]
        if long_duration_spans:
            analysis["recommendations"].append({
                "type": "bottleneck",
                "description": f"Found {len(long_duration_spans)} slow span(s) that may be bottlenecks.",
                "suggestion": "Consider optimizing these operations or making them asynchronous if possible."
            })
        
        return analysis
    
    async def build_service_baseline(self, service, duration_hours=24):
        """
        Build a performance baseline for a service
        
        Args:
            service (str): Service name
            duration_hours (int, optional): Number of hours of data to include in baseline
            
        Returns:
            dict: Service performance baseline
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=duration_hours)
        
        start = start_time.isoformat() + "Z"
        end = end_time.isoformat() + "Z"
        
        service_analysis = self.service_tool.execute(
            service=service,
            start=start,
            end=end,
            limit=500  # Use more traces for an accurate baseline
        )
        
        if "error" in service_analysis:
            return {"error": f"Failed to build baseline for service {service}: {service_analysis['error']}"}
        
        baseline = {
            "service": service,
            "time_range": {
                "start": start,
                "end": end,
                "duration_hours": duration_hours
            },
            "trace_count": service_analysis.get("trace_count", 0),
            "operations": {},
            "avg_duration_ms": service_analysis.get("avg_duration_ms", 0),
            "p95_duration_ms": service_analysis.get("p95_duration_ms", 0),
            "error_rate": service_analysis.get("error_count", 0) / max(service_analysis.get("trace_count", 1), 1)
        }
        
        # Store operation-specific baselines
        for op_name, op_info in service_analysis.get("operations", {}).items():
            baseline["operations"][op_name] = {
                "avg_duration_ms": op_info.get("avg_duration_ms", 0),
                "p95_duration_ms": op_info.get("p95_duration_ms", 0),
                "sample_count": op_info.get("count", 0)
            }
        
        # Cache the baseline
        self.service_baselines[service] = baseline
        
        return baseline
    
    async def compare_to_baseline(self, service, current_analysis):
        """
        Compare current service performance to baseline
        
        Args:
            service (str): Service name
            current_analysis (dict): Current service analysis
            
        Returns:
            dict: Comparison results with anomalies
        """
        if service not in self.service_baselines:
            await self.build_service_baseline(service)
            
        baseline = self.service_baselines.get(service, {})
        
        if "error" in baseline:
            return {"error": f"Cannot compare to baseline: {baseline['error']}"}
        
        comparison = {
            "service": service,
            "baseline_time_range": baseline.get("time_range", {}),
            "current_time_range": current_analysis.get("time_range", {}),
            "anomalies": [],
            "overall_status": "normal"
        }
        
        # Compare overall service performance
        baseline_p95 = baseline.get("p95_duration_ms", 0)
        current_p95 = current_analysis.get("p95_duration_ms", 0)
        
        if baseline_p95 > 0 and current_p95 > baseline_p95 * 1.5:
            comparison["anomalies"].append({
                "type": "service_slowdown",
                "description": f"Service performance degraded: p95 latency increased from {baseline_p95:.2f}ms to {current_p95:.2f}ms",
                "severity": "high" if current_p95 > baseline_p95 * 2 else "medium",
                "baseline_value": baseline_p95,
                "current_value": current_p95,
                "percentage_change": ((current_p95 - baseline_p95) / baseline_p95) * 100
            })
            comparison["overall_status"] = "degraded"
            
        # Compare error rates
        baseline_error_rate = baseline.get("error_rate", 0)
        current_error_count = current_analysis.get("error_count", 0)
        current_trace_count = max(current_analysis.get("trace_count", 1), 1)
        current_error_rate = current_error_count / current_trace_count
        
        if baseline_error_rate > 0 and current_error_rate > baseline_error_rate * 1.5:
            comparison["anomalies"].append({
                "type": "increased_errors",
                "description": f"Error rate increased from {baseline_error_rate:.2%} to {current_error_rate:.2%}",
                "severity": "high" if current_error_rate > baseline_error_rate * 2 else "medium",
                "baseline_value": baseline_error_rate,
                "current_value": current_error_rate,
                "percentage_change": ((current_error_rate - baseline_error_rate) / baseline_error_rate) * 100
            })
            comparison["overall_status"] = "degraded"
            
        # Compare operation performance
        for op_name, current_op in current_analysis.get("operations", {}).items():
            baseline_op = baseline.get("operations", {}).get(op_name, {})
            
            if not baseline_op:
                comparison["anomalies"].append({
                    "type": "new_operation",
                    "description": f"New operation detected: {op_name}",
                    "severity": "info",
                    "operation": op_name
                })
                continue
                
            baseline_op_p95 = baseline_op.get("p95_duration_ms", 0)
            current_op_p95 = current_op.get("p95_duration_ms", 0)
            
            if baseline_op_p95 > 0 and current_op_p95 > baseline_op_p95 * 1.5:
                comparison["anomalies"].append({
                    "type": "operation_slowdown",
                    "description": f"Operation '{op_name}' performance degraded: p95 latency increased from {baseline_op_p95:.2f}ms to {current_op_p95:.2f}ms",
                    "severity": "high" if current_op_p95 > baseline_op_p95 * 2 else "medium",
                    "operation": op_name,
                    "baseline_value": baseline_op_p95,
                    "current_value": current_op_p95,
                    "percentage_change": ((current_op_p95 - baseline_op_p95) / baseline_op_p95) * 100
                })
                
                if comparison["overall_status"] != "degraded":
                    comparison["overall_status"] = "warning"
        
        return comparison
    
    async def find_related_traces(self, alert_time, service=None, error_type=None, window_minutes=15):
        """
        Find traces related to an alert
        
        Args:
            alert_time (str): Time of the alert in ISO format
            service (str, optional): Service name related to the alert
            error_type (str, optional): Type of error to look for
            window_minutes (int, optional): Time window in minutes around the alert
            
        Returns:
            dict: Related traces and analysis
        """
        # Parse the alert time and create a window around it
        alert_dt = datetime.fromisoformat(alert_time.replace('Z', '+00:00'))
        start_dt = alert_dt - timedelta(minutes=window_minutes)
        end_dt = alert_dt + timedelta(minutes=window_minutes)
        
        start = start_dt.isoformat() + "Z"
        end = end_dt.isoformat() + "Z"
        
        # Search for traces
        query_params = {
            "start": start,
            "end": end,
            "limit": 50
        }
        
        if service:
            query_params["service"] = service
        
        # If error type is specified, look for error traces
        if error_type:
            query_params["tags"] = {"error": "true"}
            
        traces = self.trace_tool.execute(**query_params)
        
        # Analyze results
        result = {
            "alert_time": alert_time,
            "time_window": {
                "start": start,
                "end": end,
                "minutes": window_minutes * 2
            },
            "service": service,
            "error_type": error_type,
            "trace_count": traces.get("trace_count", 0),
            "traces": traces.get("traces", []),
            "analysis": {}
        }
        
        # If we have traces, analyze patterns
        if result["trace_count"] > 0:
            trace_durations = [t.get("duration_ms", 0) for t in result["traces"]]
            
            result["analysis"] = {
                "avg_duration_ms": sum(trace_durations) / len(trace_durations),
                "max_duration_ms": max(trace_durations),
                "min_duration_ms": min(trace_durations),
                "services_involved": set()
            }
            
            # Get unique services involved
            for trace in result["traces"][:5]:  # Limit to first 5 traces for efficiency
                trace_id = trace.get("trace_id")
                if trace_id:
                    trace_details = self.trace_tool.get_trace_by_id(trace_id)
                    result["analysis"]["services_involved"].update(trace_details.get("services", []))
            
            # Convert to list for JSON serialization
            result["analysis"]["services_involved"] = list(result["analysis"]["services_involved"])
            
            # Check for bottlenecks
            if result["trace_count"] >= 5:
                long_duration_threshold = result["analysis"]["avg_duration_ms"] * 2
                long_traces = [t for t in result["traces"] if t.get("duration_ms", 0) > long_duration_threshold]
                
                if long_traces:
                    result["analysis"]["potential_bottlenecks"] = [
                        {
                            "trace_id": t.get("trace_id"),
                            "duration_ms": t.get("duration_ms"),
                            "root_service": t.get("root_service"),
                            "root_operation": t.get("root_operation")
                        }
                        for t in long_traces[:3]  # Top 3 slowest traces
                    ]
            
        return result
    
    async def monitor_services(self):
        """
        Continuously monitor services for performance issues
        Returns results to the orchestrator
        """
        logger.info("Starting service monitoring loop")
        
        while True:
            for service in self.services_to_monitor:
                try:
                    # Analyze the last 5 minutes of data
                    end_time = datetime.utcnow()
                    start_time = end_time - timedelta(minutes=5)
                    
                    start = start_time.isoformat() + "Z"
                    end = end_time.isoformat() + "Z"
                    
                    current_analysis = self.service_tool.execute(
                        service=service,
                        start=start,
                        end=end
                    )
                    
                    if "error" in current_analysis:
                        logger.warning(f"Error analyzing service {service}: {current_analysis['error']}")
                        continue
                    
                    # Compare with baseline
                    comparison = await self.compare_to_baseline(service, current_analysis)
                    
                    # Report issues if found
                    if comparison.get("anomalies"):
                        logger.info(f"Found {len(comparison['anomalies'])} anomalies for service {service}")
                        
                        # Here you would send this data to the orchestrator
                        # For now we just log it
                        for anomaly in comparison["anomalies"]:
                            logger.warning(f"Service {service} anomaly: {anomaly['description']}")
                    
                except Exception as e:
                    logger.error(f"Error monitoring service {service}: {str(e)}")
            
            # Wait before checking again
            await asyncio.sleep(60)  # Check every minute
    
    async def analyze_alert(self, alert_data):
        """
        Analyze tracing data related to an alert
        
        Args:
            alert_data (dict): Alert information
            
        Returns:
            dict: Tracing analysis results
        """
        logger.info(f"Analyzing alert: {alert_data}")
        
        # Extract alert information
        alert_id = alert_data.get("alert_id", "unknown")
        alert_time = alert_data.get("startsAt", datetime.utcnow().isoformat() + "Z")
        service = alert_data.get("labels", {}).get("service")
        
        # Find related traces
        related_traces = await self.find_related_traces(
            alert_time=alert_time,
            service=service,
            window_minutes=15
        )
        
        # Build a comprehensive analysis
        analysis = {
            "alert_id": alert_id,
            "service": service,
            "alert_time": alert_time,
            "related_traces": related_traces
        }
        
        # If we found traces, analyze the most relevant ones
        if related_traces.get("trace_count", 0) > 0:
            # Analyze the slowest trace in detail
            slowest_traces = sorted(related_traces.get("traces", []), 
                                   key=lambda x: x.get("duration_ms", 0), 
                                   reverse=True)
            
            if slowest_traces:
                slowest_trace_id = slowest_traces[0].get("trace_id")
                if slowest_trace_id:
                    detailed_analysis = await self.analyze_trace(slowest_trace_id)
                    analysis["detailed_trace_analysis"] = detailed_analysis
            
            # If we have a service, compare current performance to baseline
            if service:
                # Get current service performance
                end_time = datetime.utcnow()
                start_time = datetime.fromisoformat(alert_time.replace('Z', '+00:00')) - timedelta(minutes=15)
                
                start = start_time.isoformat() + "Z"
                end = end_time.isoformat() + "Z"
                
                current_analysis = self.service_tool.execute(
                    service=service,
                    start=start,
                    end=end
                )
                
                if "error" not in current_analysis:
                    # Compare to baseline
                    comparison = await self.compare_to_baseline(service, current_analysis)
                    analysis["service_comparison"] = comparison
        
        # Send response to orchestrator
        response = {
            "agent": "tracing",
            "alert_id": alert_id,
            "analysis": analysis
        }
        
        return response
        
    def listen(self):
        """Listen for alerts from the orchestrator"""
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe("tracing_agent")
        
        logger.info("[TracingAgent] Listening for alerts on Redis channel 'tracing_agent'")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    alert_data = json.loads(message["data"])
                    logger.info(f"[TracingAgent] Received alert: {alert_data}")
                    
                    # Process alert asynchronously
                    response = loop.run_until_complete(self.analyze_alert(alert_data))
                    
                    # Send response back to orchestrator
                    self.redis_client.publish("orchestrator_response", json.dumps(response))
                    logger.info(f"[TracingAgent] Sent response for alert: {alert_data.get('alert_id', 'unknown')}")
                except Exception as e:
                    logger.error(f"[TracingAgent] Error processing alert: {str(e)}", exc_info=True)