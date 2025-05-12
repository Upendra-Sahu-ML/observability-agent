"""
Tempo tools for querying distributed tracing data
"""
import os
import logging
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urljoin
from common.tools.base import AgentTool

# Configure logging
logger = logging.getLogger(__name__)

class TempoTraceTool(AgentTool):
    """Tool for querying traces from Tempo"""
    
    def __init__(self, tempo_url=None):
        """
        Initialize Tempo client
        
        Args:
            tempo_url (str, optional): Tempo API URL
        """
        self.tempo_url = tempo_url or os.environ.get('TEMPO_URL')
        
        if not self.tempo_url:
            logger.warning("Tempo URL not provided, using default: http://tempo:3100")
            self.tempo_url = "http://tempo:3100"
    
    @property
    def name(self):
        return "tempo_traces"
    
    @property
    def description(self):
        return "Query traces from Tempo distributed tracing system"
    
    def execute(self, service=None, operation=None, tags=None, minDuration=None, maxDuration=None, limit=20, start=None, end=None):
        """
        Query traces from Tempo
        
        Args:
            service (str, optional): Filter by service name
            operation (str, optional): Filter by operation name
            tags (dict, optional): Filter by tags/attributes (key-value pairs)
            minDuration (str, optional): Minimum duration (e.g., "100ms", "1.5s", "1h")
            maxDuration (str, optional): Maximum duration (e.g., "100ms", "1.5s", "1h")
            limit (int, optional): Maximum number of traces to return
            start (str, optional): Start time in ISO format (e.g., "2023-01-01T00:00:00Z")
            end (str, optional): End time in ISO format (e.g., "2023-01-01T01:00:00Z")
            
        Returns:
            dict: Trace information
        """
        try:
            # Build the query
            query_params = {}
            
            if service:
                query_params["service"] = service
            
            if operation:
                query_params["operation"] = operation
                
            if tags:
                for key, value in tags.items():
                    query_params[f"tag.{key}"] = value
            
            if minDuration:
                query_params["minDuration"] = minDuration
                
            if maxDuration:
                query_params["maxDuration"] = maxDuration
                
            if limit:
                query_params["limit"] = str(limit)
                
            # Set time range
            if not start:
                # Default to last hour if not specified
                start_time = datetime.utcnow() - timedelta(hours=1)
                start = start_time.isoformat() + "Z"
                
            if not end:
                end_time = datetime.utcnow()
                end = end_time.isoformat() + "Z"
                
            query_params["start"] = start
            query_params["end"] = end
            
            # Make the API request to Tempo
            url = urljoin(self.tempo_url, "/api/search")
            response = requests.get(url, params=query_params)
            response.raise_for_status()
            
            traces = response.json().get("traces", [])
            
            # Process and analyze the traces
            result = {
                "query": {
                    "service": service,
                    "operation": operation,
                    "tags": tags,
                    "minDuration": minDuration,
                    "maxDuration": maxDuration,
                    "start": start,
                    "end": end
                },
                "trace_count": len(traces),
                "traces": []
            }
            
            for trace in traces:
                trace_detail = {
                    "trace_id": trace.get("traceID"),
                    "root_service": trace.get("rootServiceName"),
                    "root_operation": trace.get("rootTraceName"),
                    "duration_ms": trace.get("durationMs"),
                    "start_time_unix_nano": trace.get("startTimeUnixNano"),
                    "timestamp": datetime.fromtimestamp(trace.get("startTimeUnixNano", 0) / 1_000_000_000).isoformat() if trace.get("startTimeUnixNano") else None
                }
                result["traces"].append(trace_detail)
            
            # Sort by duration (longest first) to highlight potential issues
            result["traces"].sort(key=lambda x: x.get("duration_ms", 0), reverse=True)
            
            # Calculate statistics about the traces
            if result["traces"]:
                durations = [t.get("duration_ms", 0) for t in result["traces"]]
                result["statistics"] = {
                    "avg_duration_ms": sum(durations) / len(durations),
                    "max_duration_ms": max(durations),
                    "min_duration_ms": min(durations),
                    "p95_duration_ms": sorted(durations)[int(len(durations) * 0.95)] if len(durations) >= 20 else None,
                    "p99_duration_ms": sorted(durations)[int(len(durations) * 0.99)] if len(durations) >= 100 else None
                }
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying Tempo: {str(e)}")
            return {"error": str(e), "status_code": getattr(e.response, "status_code", None) if hasattr(e, "response") else None}
    
    def get_trace_by_id(self, trace_id):
        """
        Get detailed information about a specific trace
        
        Args:
            trace_id (str): Trace ID
            
        Returns:
            dict: Detailed trace information
        """
        try:
            # Make the API request to Tempo
            url = urljoin(self.tempo_url, f"/api/traces/{trace_id}")
            response = requests.get(url)
            response.raise_for_status()
            
            trace_data = response.json()
            
            # Process and analyze the trace
            result = {
                "trace_id": trace_id,
                "span_count": 0,
                "services": set(),
                "operations": set(),
                "duration_ms": 0,
                "spans": []
            }
            
            for batch in trace_data.get("batches", []):
                for resource in batch.get("resource", {}).get("attributes", []):
                    if resource.get("key") == "service.name":
                        result["services"].add(resource.get("value", {}).get("stringValue", ""))
                
                for span in batch.get("spans", []):
                    span_info = {
                        "span_id": span.get("spanId"),
                        "parent_span_id": span.get("parentSpanId"),
                        "name": span.get("name"),
                        "kind": span.get("kind"),
                        "start_time_unix_nano": span.get("startTimeUnixNano"),
                        "end_time_unix_nano": span.get("endTimeUnixNano"),
                        "attributes": {},
                        "events": []
                    }
                    
                    # Calculate span duration
                    if span.get("startTimeUnixNano") and span.get("endTimeUnixNano"):
                        span_duration_ms = (int(span.get("endTimeUnixNano", 0)) - int(span.get("startTimeUnixNano", 0))) / 1_000_000
                        span_info["duration_ms"] = span_duration_ms
                        
                        # Update trace duration if this is the root span
                        if not span.get("parentSpanId") and span_duration_ms > result["duration_ms"]:
                            result["duration_ms"] = span_duration_ms
                    
                    # Extract attributes
                    for attr in span.get("attributes", []):
                        key = attr.get("key")
                        value_obj = attr.get("value", {})
                        
                        if "stringValue" in value_obj:
                            span_info["attributes"][key] = value_obj.get("stringValue")
                        elif "intValue" in value_obj:
                            span_info["attributes"][key] = value_obj.get("intValue")
                        elif "doubleValue" in value_obj:
                            span_info["attributes"][key] = value_obj.get("doubleValue")
                        elif "boolValue" in value_obj:
                            span_info["attributes"][key] = value_obj.get("boolValue")
                    
                    # Record operation name
                    if "operation" in span_info["attributes"]:
                        result["operations"].add(span_info["attributes"]["operation"])
                    
                    # Extract events
                    for event in span.get("events", []):
                        event_info = {
                            "name": event.get("name"),
                            "time_unix_nano": event.get("timeUnixNano"),
                            "attributes": {}
                        }
                        
                        for attr in event.get("attributes", []):
                            key = attr.get("key")
                            value_obj = attr.get("value", {})
                            
                            if "stringValue" in value_obj:
                                event_info["attributes"][key] = value_obj.get("stringValue")
                            elif "intValue" in value_obj:
                                event_info["attributes"][key] = value_obj.get("intValue")
                            elif "doubleValue" in value_obj:
                                event_info["attributes"][key] = value_obj.get("doubleValue")
                            elif "boolValue" in value_obj:
                                event_info["attributes"][key] = value_obj.get("boolValue")
                        
                        span_info["events"].append(event_info)
                    
                    result["spans"].append(span_info)
                    result["span_count"] += 1
            
            # Convert sets to lists for JSON serialization
            result["services"] = list(result["services"])
            result["operations"] = list(result["operations"])
            
            # Create a span tree to better analyze the trace structure
            span_map = {span["span_id"]: span for span in result["spans"]}
            root_spans = []
            
            for span in result["spans"]:
                if not span["parent_span_id"] or span["parent_span_id"] not in span_map:
                    root_spans.append(span)
                elif span["parent_span_id"] in span_map:
                    parent = span_map[span["parent_span_id"]]
                    if "children" not in parent:
                        parent["children"] = []
                    parent["children"].append(span)
            
            result["root_spans"] = root_spans
            
            # Identify potential issues in the trace
            result["issues"] = []
            
            # Look for long-running spans
            for span in result["spans"]:
                if span.get("duration_ms", 0) > 1000:  # Spans longer than 1 second
                    result["issues"].append({
                        "type": "long_duration",
                        "span_id": span["span_id"],
                        "span_name": span["name"],
                        "duration_ms": span["duration_ms"],
                        "severity": "warning"
                    })
            
            # Look for error spans
            for span in result["spans"]:
                if span.get("attributes", {}).get("error") == "true":
                    result["issues"].append({
                        "type": "error",
                        "span_id": span["span_id"],
                        "span_name": span["name"],
                        "error_message": span.get("attributes", {}).get("error.message", "Unknown error"),
                        "severity": "error"
                    })
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting trace from Tempo: {str(e)}")
            return {"error": str(e), "status_code": getattr(e.response, "status_code", None) if hasattr(e, "response") else None}

    def get_service_latency_analysis(self, service, start=None, end=None, limit=100):
        """
        Analyze service latency patterns
        
        Args:
            service (str): Service name to analyze
            start (str, optional): Start time
            end (str, optional): End time
            limit (int, optional): Maximum number of traces to analyze
            
        Returns:
            dict: Latency analysis results
        """
        traces = self.execute(service=service, start=start, end=end, limit=limit)
        
        latencies = []
        error_count = 0
        operation_latencies = {}
        
        for trace in traces.get("traces", []):
            for span in trace.get("spans", []):
                if span.get("serviceName") == service:
                    duration = span.get("durationNanos", 0) / 1e6  # Convert to milliseconds
                    latencies.append(duration)
                    
                    # Track operation-specific latencies
                    operation = span.get("operationName", "unknown")
                    if operation not in operation_latencies:
                        operation_latencies[operation] = []
                    operation_latencies[operation].append(duration)
                    
                    # Count errors
                    if span.get("tags", {}).get("error", False):
                        error_count += 1
        
        if not latencies:
            return {"error": "No latency data found"}
            
        # Calculate overall statistics
        stats = {
            "count": len(latencies),
            "min": min(latencies),
            "max": max(latencies),
            "avg": sum(latencies) / len(latencies),
            "p95": sorted(latencies)[int(len(latencies) * 0.95)],
            "p99": sorted(latencies)[int(len(latencies) * 0.99)],
            "error_count": error_count,
            "error_rate": error_count / len(latencies) if latencies else 0
        }
        
        # Calculate operation-specific statistics
        operation_stats = {}
        for operation, op_latencies in operation_latencies.items():
            operation_stats[operation] = {
                "count": len(op_latencies),
                "min": min(op_latencies),
                "max": max(op_latencies),
                "avg": sum(op_latencies) / len(op_latencies),
                "p95": sorted(op_latencies)[int(len(op_latencies) * 0.95)],
                "p99": sorted(op_latencies)[int(len(op_latencies) * 0.99)]
            }
        
        stats["operations"] = operation_stats
        return stats

    def get_service_dependencies(self, service, start=None, end=None, limit=100):
        """
        Analyze service dependencies from traces
        
        Args:
            service (str): Service name to analyze
            start (str, optional): Start time
            end (str, optional): End time
            limit (int, optional): Maximum number of traces to analyze
            
        Returns:
            dict: Service dependency analysis
        """
        traces = self.execute(service=service, start=start, end=end, limit=limit)
        
        dependencies = {
            "upstream": {},  # Services that call this service
            "downstream": {}  # Services called by this service
        }
        
        for trace in traces.get("traces", []):
            spans = trace.get("spans", [])
            
            # Find the service's span
            service_span = None
            for span in spans:
                if span.get("serviceName") == service:
                    service_span = span
                    break
            
            if not service_span:
                continue
                
            # Analyze upstream dependencies
            for span in spans:
                if span.get("parentSpanId") == service_span.get("spanId"):
                    upstream_service = span.get("serviceName")
                    if upstream_service not in dependencies["upstream"]:
                        dependencies["upstream"][upstream_service] = {
                            "count": 0,
                            "errors": 0,
                            "avg_latency": 0,
                            "latencies": []
                        }
                    
                    dep = dependencies["upstream"][upstream_service]
                    dep["count"] += 1
                    if span.get("tags", {}).get("error", False):
                        dep["errors"] += 1
                    
                    latency = span.get("durationNanos", 0) / 1e6
                    dep["latencies"].append(latency)
                    dep["avg_latency"] = sum(dep["latencies"]) / len(dep["latencies"])
            
            # Analyze downstream dependencies
            for span in spans:
                if span.get("spanId") == service_span.get("parentSpanId"):
                    downstream_service = span.get("serviceName")
                    if downstream_service not in dependencies["downstream"]:
                        dependencies["downstream"][downstream_service] = {
                            "count": 0,
                            "errors": 0,
                            "avg_latency": 0,
                            "latencies": []
                        }
                    
                    dep = dependencies["downstream"][downstream_service]
                    dep["count"] += 1
                    if span.get("tags", {}).get("error", False):
                        dep["errors"] += 1
                    
                    latency = span.get("durationNanos", 0) / 1e6
                    dep["latencies"].append(latency)
                    dep["avg_latency"] = sum(dep["latencies"]) / len(dep["latencies"])
        
        return dependencies

    def get_error_analysis(self, service, start=None, end=None, limit=100):
        """
        Analyze error patterns in traces
        
        Args:
            service (str): Service name to analyze
            start (str, optional): Start time
            end (str, optional): End time
            limit (int, optional): Maximum number of traces to analyze
            
        Returns:
            dict: Error analysis results
        """
        traces = self.execute(service=service, start=start, end=end, limit=limit)
        
        errors = {
            "total_traces": 0,
            "error_traces": 0,
            "error_operations": {},
            "error_causes": {},
            "error_services": {}
        }
        
        for trace in traces.get("traces", []):
            errors["total_traces"] += 1
            has_error = False
            
            for span in trace.get("spans", []):
                if span.get("tags", {}).get("error", False):
                    has_error = True
                    
                    # Track error by operation
                    operation = span.get("operationName", "unknown")
                    if operation not in errors["error_operations"]:
                        errors["error_operations"][operation] = 0
                    errors["error_operations"][operation] += 1
                    
                    # Track error by service
                    service_name = span.get("serviceName", "unknown")
                    if service_name not in errors["error_services"]:
                        errors["error_services"][service_name] = 0
                    errors["error_services"][service_name] += 1
                    
                    # Track error causes
                    error_message = span.get("tags", {}).get("error.message", "unknown")
                    if error_message not in errors["error_causes"]:
                        errors["error_causes"][error_message] = 0
                    errors["error_causes"][error_message] += 1
            
            if has_error:
                errors["error_traces"] += 1
        
        # Calculate error rates
        if errors["total_traces"] > 0:
            errors["error_rate"] = errors["error_traces"] / errors["total_traces"]
        else:
            errors["error_rate"] = 0
            
        return errors

class TempoServiceTool(AgentTool):
    """Tool for analyzing service performance using Tempo"""
    
    def __init__(self, tempo_url=None):
        """
        Initialize Tempo client
        
        Args:
            tempo_url (str, optional): Tempo API URL
        """
        self.tempo_url = tempo_url or os.environ.get('TEMPO_URL')
        
        if not self.tempo_url:
            logger.warning("Tempo URL not provided, using default: http://tempo:3100")
            self.tempo_url = "http://tempo:3100"
    
    @property
    def name(self):
        return "tempo_service_analysis"
    
    @property
    def description(self):
        return "Analyze service performance using Tempo distributed tracing data"
    
    def execute(self, service, start=None, end=None, limit=100):
        """
        Analyze service performance using Tempo
        
        Args:
            service (str): Service name to analyze
            start (str, optional): Start time in ISO format (e.g., "2023-01-01T00:00:00Z")
            end (str, optional): End time in ISO format (e.g., "2023-01-01T01:00:00Z")
            limit (int, optional): Maximum number of traces to analyze
            
        Returns:
            dict: Service performance analysis
        """
        try:
            # Set time range
            if not start:
                # Default to last hour if not specified
                start_time = datetime.utcnow() - timedelta(hours=1)
                start = start_time.isoformat() + "Z"
                
            if not end:
                end_time = datetime.utcnow()
                end = end_time.isoformat() + "Z"
            
            # Query traces for the service
            query_params = {
                "service": service,
                "start": start,
                "end": end,
                "limit": str(limit)
            }
            
            # Make the API request to Tempo
            url = urljoin(self.tempo_url, "/api/search")
            response = requests.get(url, params=query_params)
            response.raise_for_status()
            
            traces = response.json().get("traces", [])
            
            # Initialize result structure
            result = {
                "service": service,
                "time_range": {
                    "start": start,
                    "end": end
                },
                "trace_count": len(traces),
                "operations": {},
                "error_count": 0,
                "avg_duration_ms": 0,
                "p95_duration_ms": 0,
                "max_duration_ms": 0,
                "issues": []
            }
            
            # Process traces to get detailed information
            durations = []
            operation_durations = {}
            
            for trace in traces:
                duration_ms = trace.get("durationMs", 0)
                durations.append(duration_ms)
                
                # Get the trace details to check for errors and analyze operations
                trace_id = trace.get("traceID")
                trace_details_url = urljoin(self.tempo_url, f"/api/traces/{trace_id}")
                trace_response = requests.get(trace_details_url)
                
                if trace_response.status_code == 200:
                    trace_data = trace_response.json()
                    
                    for batch in trace_data.get("batches", []):
                        for span in batch.get("spans", []):
                            # Check if this span belongs to our service
                            service_found = False
                            for resource in batch.get("resource", {}).get("attributes", []):
                                if resource.get("key") == "service.name" and resource.get("value", {}).get("stringValue") == service:
                                    service_found = True
                                    break
                            
                            if not service_found:
                                continue
                            
                            # Extract span information
                            span_name = span.get("name", "unknown")
                            
                            # Calculate span duration
                            span_duration_ms = 0
                            if span.get("startTimeUnixNano") and span.get("endTimeUnixNano"):
                                span_duration_ms = (int(span.get("endTimeUnixNano", 0)) - int(span.get("startTimeUnixNano", 0))) / 1_000_000
                            
                            # Track operation durations
                            if span_name not in operation_durations:
                                operation_durations[span_name] = []
                            operation_durations[span_name].append(span_duration_ms)
                            
                            # Check for errors
                            for attr in span.get("attributes", []):
                                if attr.get("key") == "error" and attr.get("value", {}).get("boolValue", False):
                                    result["error_count"] += 1
                                    
                                    # Extract error details
                                    error_message = "Unknown error"
                                    for error_attr in span.get("attributes", []):
                                        if error_attr.get("key") == "error.message":
                                            error_message = error_attr.get("value", {}).get("stringValue", "Unknown error")
                                    
                                    result["issues"].append({
                                        "type": "error",
                                        "trace_id": trace_id,
                                        "span_id": span.get("spanId"),
                                        "operation": span_name,
                                        "error_message": error_message,
                                        "timestamp": datetime.fromtimestamp(int(span.get("startTimeUnixNano", 0)) / 1_000_000_000).isoformat() if span.get("startTimeUnixNano") else None
                                    })
            
            # Calculate overall statistics
            if durations:
                result["avg_duration_ms"] = sum(durations) / len(durations)
                result["max_duration_ms"] = max(durations)
                durations.sort()
                result["p95_duration_ms"] = durations[int(len(durations) * 0.95)] if len(durations) >= 20 else durations[-1]
            
            # Calculate per-operation statistics
            for operation, op_durations in operation_durations.items():
                if op_durations:
                    op_durations.sort()
                    operation_info = {
                        "count": len(op_durations),
                        "avg_duration_ms": sum(op_durations) / len(op_durations),
                        "max_duration_ms": max(op_durations),
                        "p95_duration_ms": op_durations[int(len(op_durations) * 0.95)] if len(op_durations) >= 20 else op_durations[-1]
                    }
                    
                    # Identify slow operations (p95 > 500ms)
                    if operation_info["p95_duration_ms"] > 500:
                        result["issues"].append({
                            "type": "slow_operation",
                            "operation": operation,
                            "p95_duration_ms": operation_info["p95_duration_ms"],
                            "avg_duration_ms": operation_info["avg_duration_ms"],
                            "count": operation_info["count"]
                        })
                    
                    result["operations"][operation] = operation_info
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error analyzing service performance: {str(e)}")
            return {"error": str(e), "status_code": getattr(e.response, "status_code", None) if hasattr(e, "response") else None}