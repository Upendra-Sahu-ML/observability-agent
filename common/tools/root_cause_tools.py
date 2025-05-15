"""
Tools for root cause analysis of system issues.

This module provides tools for analyzing correlations between components and events,
as well as analyzing dependencies between services to help identify the root cause of issues.
"""

import logging
from typing import Dict, List, Any, Optional
from crewai.tools import tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tool functions using crewAI's modern tool pattern with decorators
@tool("Analyze correlations between different system components and events")
def correlation_analysis(events: List[Dict[str, Any]], 
                         time_window: Optional[str] = "1h", 
                         correlation_threshold: Optional[float] = 0.7, 
                         **kwargs) -> Dict[str, Any]:
    """
    Analyze correlations between different system components and events.
    
    Args:
        events (list): List of events to analyze
        time_window (str, optional): Time window for correlation analysis
        correlation_threshold (float, optional): Threshold for correlation significance
        
    Returns:
        dict: Correlation analysis results showing relationships between components
    """
    logger.info(f"Performing correlation analysis on {len(events)} events with threshold {correlation_threshold}")
    
    # This would typically involve complex correlation algorithms
    # For now, this is a placeholder implementation
    correlations = {}
    
    try:
        # Group events by component/service
        components = {}
        for event in events:
            component = event.get("component", "unknown")
            if component not in components:
                components[component] = []
            components[component].append(event)
        
        # Find temporal correlations between component events
        for comp1 in components:
            correlations[comp1] = {}
            for comp2 in components:
                if comp1 != comp2:
                    # Calculate temporal correlation (simplified)
                    # In a real implementation, this would use time series analysis
                    correlation_score = len(components[comp1]) / (len(components[comp1]) + len(components[comp2]))
                    if correlation_score >= correlation_threshold:
                        correlations[comp1][comp2] = correlation_score
        
        return {
            "correlations": correlations,
            "time_window": time_window,
            "threshold": correlation_threshold,
            "components_analyzed": list(components.keys())
        }
        
    except Exception as e:
        logger.error(f"Error during correlation analysis: {str(e)}")
        return {
            "error": str(e),
            "correlations": {},
            "time_window": time_window,
            "threshold": correlation_threshold
        }


@tool("Analyze service dependencies and their impact on the system")
def dependency_analysis(services: List[str], 
                        dependency_data: Optional[Dict[str, List[str]]] = None,
                        include_transitive: Optional[bool] = True, 
                        **kwargs) -> Dict[str, Any]:
    """
    Analyze service dependencies and their impact on the system.
    
    Args:
        services (list): List of services to analyze
        dependency_data (dict, optional): Existing dependency data
        include_transitive (bool, optional): Whether to include transitive dependencies
        
    Returns:
        dict: Dependency analysis results showing service relationships
    """
    logger.info(f"Analyzing dependencies for {len(services)} services")
    
    # Use provided dependency data or create sample data for demonstration
    dependencies = dependency_data or {}
    
    try:
        # If no dependency data is provided, this would typically be fetched from 
        # service mesh, observability platforms, or configuration management systems
        if not dependency_data:
            # Example placeholder dependency data
            for service in services:
                dependencies[service] = [
                    f"dependent-service-{i}" for i in range(1, 3)
                ]
        
        # Calculate impact graph
        impact_graph = {}
        for service in services:
            if service in dependencies:
                impact_graph[service] = {
                    "direct_dependencies": dependencies[service],
                    "dependents": []
                }
                
                # Find services that depend on this service
                for s, deps in dependencies.items():
                    if service in deps and s != service:
                        impact_graph[service]["dependents"].append(s)
        
        # Calculate transitive dependencies if requested
        if include_transitive:
            for service in services:
                if service in impact_graph:
                    transitive_deps = set()
                    queue = list(impact_graph[service]["direct_dependencies"])
                    visited = set(queue)
                    
                    while queue:
                        dep = queue.pop(0)
                        transitive_deps.add(dep)
                        if dep in dependencies:
                            for next_dep in dependencies[dep]:
                                if next_dep not in visited:
                                    visited.add(next_dep)
                                    queue.append(next_dep)
                    
                    impact_graph[service]["transitive_dependencies"] = list(transitive_deps)
        
        return {
            "impact_graph": impact_graph,
            "services_analyzed": services,
            "include_transitive": include_transitive
        }
        
    except Exception as e:
        logger.error(f"Error during dependency analysis: {str(e)}")
        return {
            "error": str(e),
            "impact_graph": {},
            "services_analyzed": services
        }