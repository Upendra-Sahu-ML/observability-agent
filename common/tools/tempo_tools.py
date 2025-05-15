"""
Tempo tools for querying distributed tracing data
"""
import os
import logging
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urljoin
from crewai.tools import tool

# Configure logging
logger = logging.getLogger(__name__)

class TempoTools:
    """Collection of tools for working with Tempo distributed tracing data"""
    
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
    
    @tool("Query traces from Tempo distributed tracing system")
    def query_traces(self, service=None, operation=None, tags=None, minDuration=None, maxDuration=None, limit=20, start=None, end=None):
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
    
    @tool("Get detailed information about a specific trace")
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

    @tool("Analyze service latency patterns")
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
        traces = self.query_traces(service=service, start=start, end=end, limit=limit)
        
        latencies = []
        error_count = 0
        operation_latencies = {}
        
        for trace in traces.get("traces", []):
            # For simplicity, we'll use the trace duration as a proxy for service latency
            duration = trace.get("duration_ms", 0)
            latencies.append(duration)
            
            # Track operation-specific latencies if available
            operation = trace.get("root_operation", "unknown")
            if operation not in operation_latencies:
                operation_latencies[operation] = []
            operation_latencies[operation].append(duration)
        
        if not latencies:
            return {"error": "No latency data found"}
            
        # Calculate overall statistics
        stats = {
            "count": len(latencies),
            "min": min(latencies),
            "max": max(latencies),
            "avg": sum(latencies) / len(latencies),
            "p95": sorted(latencies)[int(len(latencies) * 0.95)],
            "p99": sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) >= 100 else sorted(latencies)[-1]
        }
        
        # Calculate operation-specific statistics
        operation_stats = {}
        for operation, op_latencies in operation_latencies.items():
            operation_stats[operation] = {
                "count": len(op_latencies),
                "min": min(op_latencies),
                "max": max(op_latencies),
                "avg": sum(op_latencies) / len(op_latencies),
                "p95": sorted(op_latencies)[int(len(op_latencies) * 0.95)] if len(op_latencies) >= 20 else sorted(op_latencies)[-1]
            }
        
        stats["operations"] = operation_stats
        return stats

    @tool("Analyze service dependencies from traces")
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
        # First get the traces for the service
        traces = self.query_traces(service=service, start=start, end=end, limit=limit)
        
        dependencies = {
            "upstream": {},  # Services that call this service
            "downstream": {}  # Services called by this service
        }
        
        # For each trace, get detailed information to analyze dependencies
        for trace in traces.get("traces", []):
            trace_id = trace.get("trace_id")
            if not trace_id:
                continue
                
            # Get the detailed trace
            detailed_trace = self.get_trace_by_id(trace_id)
            
            # Skip if there was an error getting the trace
            if "error" in detailed_trace:
                continue
                
            # Track services in this trace
            services_in_trace = detailed_trace.get("services", [])
            
            # If the service we're analyzing isn't in the trace, skip
            if service not in services_in_trace:
                continue
                
            # Analyze the spans to determine dependencies
            for span in detailed_trace.get("spans", []):
                span_service = span.get("attributes", {}).get("service.name", "unknown")
                
                # If the span is from our service, look for downstream dependencies
                if span_service == service:
                    # Spans with parent span ID that aren't from the same service represent upstream dependencies
                    parent_id = span.get("parent_span_id")
                    if parent_id:
                        for other_span in detailed_trace.get("spans", []):
                            if other_span.get("span_id") == parent_id:
                                upstream_service = other_span.get("attributes", {}).get("service.name", "unknown")
                                if upstream_service != service and upstream_service != "unknown":
                                    if upstream_service not in dependencies["upstream"]:
                                        dependencies["upstream"][upstream_service] = {
                                            "count": 0,
                                            "errors": 0
                                        }
                                    dependencies["upstream"][upstream_service]["count"] += 1
                    
                    # Look for child spans that represent downstream dependencies
                    span_id = span.get("span_id")
                    for other_span in detailed_trace.get("spans", []):
                        if other_span.get("parent_span_id") == span_id:
                            downstream_service = other_span.get("attributes", {}).get("service.name", "unknown")
                            if downstream_service != service and downstream_service != "unknown":
                                if downstream_service not in dependencies["downstream"]:
                                    dependencies["downstream"][downstream_service] = {
                                        "count": 0,
                                        "errors": 0
                                    }
                                dependencies["downstream"][downstream_service]["count"] += 1
                                
                                # Check for errors in the downstream service
                                if other_span.get("attributes", {}).get("error") == "true":
                                    dependencies["downstream"][downstream_service]["errors"] += 1
        
        return dependencies

    @tool("Analyze error patterns in traces")
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
        # Get traces with error tag
        traces = self.query_traces(service=service, tags={"error": "true"}, start=start, end=end, limit=limit)
        
        errors = {
            "total_error_traces": traces.get("trace_count", 0),
            "error_operations": {},
            "error_messages": {},
            "error_types": {}
        }
        
        # Also get total traces to calculate error rate
        all_traces = self.query_traces(service=service, start=start, end=end, limit=limit)
        errors["total_traces"] = all_traces.get("trace_count", 0)
        
        # Calculate error rate
        if errors["total_traces"] > 0:
            errors["error_rate"] = errors["total_error_traces"] / errors["total_traces"]
        else:
            errors["error_rate"] = 0
        
        # Analyze each error trace in detail
        for trace in traces.get("traces", []):
            trace_id = trace.get("trace_id")
            if not trace_id:
                continue
                
            # Get detailed trace information
            detailed_trace = self.get_trace_by_id(trace_id)
            
            # Skip if there was an error getting the trace
            if "error" in detailed_trace:
                continue
            
            # Look for error spans
            for span in detailed_trace.get("spans", []):
                if span.get("attributes", {}).get("error") == "true":
                    # Only count errors from the service we're analyzing
                    span_service = span.get("attributes", {}).get("service.name", "unknown")
                    if span_service != service:
                        continue
                        
                    # Track errors by operation
                    operation = span.get("name", "unknown")
                    if operation not in errors["error_operations"]:
                        errors["error_operations"][operation] = 0
                    errors["error_operations"][operation] += 1
                    
                    # Track error messages
                    error_message = span.get("attributes", {}).get("error.message", "Unknown error")
                    if error_message not in errors["error_messages"]:
                        errors["error_messages"][error_message] = 0
                    errors["error_messages"][error_message] += 1
                    
                    # Track error types
                    error_type = span.get("attributes", {}).get("error.type", "Unknown")
                    if error_type not in errors["error_types"]:
                        errors["error_types"][error_type] = 0
                    errors["error_types"][error_type] += 1
        
        return errors

    @tool("Analyze service performance using Tempo distributed tracing data")
    def analyze_service_performance(self, service, start=None, end=None, limit=100):
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
        # Set time range
        if not start:
            # Default to last hour if not specified
            start_time = datetime.utcnow() - timedelta(hours=1)
            start = start_time.isoformat() + "Z"
            
        if not end:
            end_time = datetime.utcnow()
            end = end_time.isoformat() + "Z"
        
        # Get traces for the service
        traces = self.query_traces(service=service, start=start, end=end, limit=limit)
        
        # Initialize result structure
        result = {
            "service": service,
            "time_range": {
                "start": start,
                "end": end
            },
            "trace_count": traces.get("trace_count", 0),
            "operations": {},
            "error_count": 0,
            "avg_duration_ms": 0,
            "p95_duration_ms": 0,
            "max_duration_ms": 0,
            "issues": []
        }
        
        # Extract duration statistics from the traces
        if traces.get("statistics"):
            result["avg_duration_ms"] = traces["statistics"].get("avg_duration_ms", 0)
            result["p95_duration_ms"] = traces["statistics"].get("p95_duration_ms", 0)
            result["max_duration_ms"] = traces["statistics"].get("max_duration_ms", 0)
        
        # Get error analysis
        error_analysis = self.get_error_analysis(service, start, end, limit)
        result["error_count"] = error_analysis.get("total_error_traces", 0)
        result["error_rate"] = error_analysis.get("error_rate", 0)
        
        # Extract most common error messages
        if error_analysis.get("error_messages"):
            sorted_errors = sorted(error_analysis["error_messages"].items(), key=lambda x: x[1], reverse=True)
            for message, count in sorted_errors[:5]:  # Top 5 error messages
                result["issues"].append({
                    "type": "error",
                    "message": message,
                    "count": count,
                    "operation": "various"  # We'd need to dig deeper to associate with specific operations
                })
        
        # Get latency analysis for operations
        latency_analysis = self.get_service_latency_analysis(service, start, end, limit)
        if "operations" in latency_analysis:
            # Copy operation statistics
            for op_name, op_stats in latency_analysis["operations"].items():
                result["operations"][op_name] = op_stats
                
                # Flag slow operations (p95 > 500ms as an example threshold)
                if op_stats.get("p95", 0) > 500:
                    result["issues"].append({
                        "type": "slow_operation",
                        "operation": op_name,
                        "p95_duration_ms": op_stats.get("p95", 0),
                        "count": op_stats.get("count", 0)
                    })
        
        # Get dependency analysis
        dependency_analysis = self.get_service_dependencies(service, start, end, limit)
        result["dependencies"] = dependency_analysis
        
        # Flag problematic dependencies (high error rate)
        for dep_name, dep_stats in dependency_analysis.get("downstream", {}).items():
            if dep_stats.get("count", 0) > 0 and dep_stats.get("errors", 0) / dep_stats["count"] > 0.1:
                result["issues"].append({
                    "type": "dependency_error",
                    "dependency": dep_name,
                    "error_rate": dep_stats.get("errors", 0) / dep_stats.get("count", 1),
                    "count": dep_stats.get("count", 0)
                })
        
        return result