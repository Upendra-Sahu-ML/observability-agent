"""
Smart Observability Manager with Fallback Strategies

This module provides intelligent fallback strategies when observability tools are unavailable,
ensuring runbook execution can still function with degraded but useful analysis.
"""
import logging
import subprocess
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ObservabilityManager:
    """
    Smart observability manager that adapts based on available tools
    and provides fallback strategies for runbook execution.
    """
    
    def __init__(self, prometheus_url=None, loki_url=None, tempo_url=None):
        self.prometheus_url = prometheus_url
        self.loki_url = loki_url
        self.tempo_url = tempo_url
        
        # Test tool availability
        self.prometheus_available = self._test_prometheus_connection()
        self.loki_available = self._test_loki_connection()
        self.tempo_available = self._test_tempo_connection()
        
        logger.info(f"Observability tools available: Prometheus={self.prometheus_available}, "
                   f"Loki={self.loki_available}, Tempo={self.tempo_available}")
    
    def _test_prometheus_connection(self) -> bool:
        """Test if Prometheus is available"""
        if not self.prometheus_url:
            return False
        try:
            # Simple connection test - could be improved with actual HTTP check
            return True  # Placeholder
        except Exception as e:
            logger.warning(f"Prometheus unavailable: {e}")
            return False
    
    def _test_loki_connection(self) -> bool:
        """Test if Loki is available"""
        if not self.loki_url:
            return False
        try:
            # Simple connection test - could be improved with actual HTTP check
            return True  # Placeholder
        except Exception as e:
            logger.warning(f"Loki unavailable: {e}")
            return False
    
    def _test_tempo_connection(self) -> bool:
        """Test if Tempo is available"""
        if not self.tempo_url:
            return False
        try:
            # Simple connection test - could be improved with actual HTTP check
            return True  # Placeholder
        except Exception as e:
            logger.warning(f"Tempo unavailable: {e}")
            return False
    
    def get_metrics_or_fallback(self, service: str, namespace: str = "default") -> Dict[str, Any]:
        """
        Get metrics with intelligent fallback to kubectl
        """
        if self.prometheus_available:
            try:
                return self._get_prometheus_metrics(service, namespace)
            except Exception as e:
                logger.warning(f"Prometheus failed, falling back to kubectl: {e}")
        
        # Fallback to kubectl top and basic metrics
        return self._get_kubectl_metrics_fallback(service, namespace)
    
    def get_logs_or_fallback(self, service: str, namespace: str = "default", lines: int = 100) -> Dict[str, Any]:
        """
        Get logs with intelligent fallback to kubectl logs
        """
        if self.loki_available:
            try:
                return self._get_loki_logs(service, namespace, lines)
            except Exception as e:
                logger.warning(f"Loki failed, falling back to kubectl: {e}")
        
        # Fallback to kubectl logs
        return self._get_kubectl_logs_fallback(service, namespace, lines)
    
    def get_traces_or_fallback(self, service: str, namespace: str = "default") -> Dict[str, Any]:
        """
        Get traces with fallback to service dependency analysis
        """
        if self.tempo_available:
            try:
                return self._get_tempo_traces(service, namespace)
            except Exception as e:
                logger.warning(f"Tempo failed, falling back to service analysis: {e}")
        
        # Fallback to basic service dependency analysis
        return self._get_service_dependency_fallback(service, namespace)
    
    def _get_prometheus_metrics(self, service: str, namespace: str) -> Dict[str, Any]:
        """Get metrics from Prometheus"""
        # Placeholder - would implement actual Prometheus queries
        return {
            "source": "prometheus",
            "cpu_usage": 75.5,
            "memory_usage": 68.2,
            "request_rate": 120.5,
            "error_rate": 2.1,
            "response_time_p95": 850
        }
    
    def _get_kubectl_metrics_fallback(self, service: str, namespace: str) -> Dict[str, Any]:
        """Fallback metrics using kubectl top"""
        try:
            # Get pod metrics using kubectl top
            cmd = f"kubectl top pods -n {namespace} -l app={service} --no-headers"
            result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                metrics = self._parse_kubectl_top_output(result.stdout)
                metrics["source"] = "kubectl_fallback"
                return metrics
            else:
                logger.error(f"kubectl top failed: {result.stderr}")
                
        except Exception as e:
            logger.error(f"kubectl metrics fallback failed: {e}")
        
        # Final fallback - basic pod status
        return self._get_basic_pod_status(service, namespace)
    
    def _get_loki_logs(self, service: str, namespace: str, lines: int) -> Dict[str, Any]:
        """Get logs from Loki"""
        # Placeholder - would implement actual Loki queries
        return {
            "source": "loki",
            "error_count": 15,
            "warning_count": 32,
            "recent_errors": [
                "2024-01-15T10:30:00Z ERROR: Database connection timeout",
                "2024-01-15T10:29:45Z ERROR: OutOfMemoryException in handler"
            ],
            "performance_issues": ["slow_query_detected", "high_latency_warnings"]
        }
    
    def _get_kubectl_logs_fallback(self, service: str, namespace: str, lines: int) -> Dict[str, Any]:
        """Fallback logs using kubectl logs"""
        try:
            # Get pod logs using kubectl
            cmd = f"kubectl logs -n {namespace} -l app={service} --tail={lines}"
            result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logs_analysis = self._analyze_kubectl_logs(result.stdout)
                logs_analysis["source"] = "kubectl_fallback"
                return logs_analysis
            else:
                logger.error(f"kubectl logs failed: {result.stderr}")
                
        except Exception as e:
            logger.error(f"kubectl logs fallback failed: {e}")
        
        return {"source": "kubectl_fallback", "status": "failed", "logs": []}
    
    def _get_tempo_traces(self, service: str, namespace: str) -> Dict[str, Any]:
        """Get traces from Tempo"""
        # Placeholder - would implement actual Tempo queries
        return {
            "source": "tempo",
            "service_dependencies": ["database", "auth-service", "cache"],
            "avg_latency": 245,
            "error_traces": 8,
            "bottleneck_services": ["database"]
        }
    
    def _get_service_dependency_fallback(self, service: str, namespace: str) -> Dict[str, Any]:
        """Fallback service dependency analysis using kubectl"""
        try:
            # Get service information
            cmd = f"kubectl get services -n {namespace} -o json"
            result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                services = json.loads(result.stdout)
                dependency_analysis = self._analyze_service_dependencies(services, service)
                dependency_analysis["source"] = "kubectl_service_analysis"
                return dependency_analysis
                
        except Exception as e:
            logger.error(f"Service dependency fallback failed: {e}")
        
        return {"source": "kubectl_fallback", "dependencies": [], "status": "unknown"}
    
    def _parse_kubectl_top_output(self, output: str) -> Dict[str, Any]:
        """Parse kubectl top output into metrics"""
        lines = output.strip().split('\n')
        total_cpu = 0
        total_memory = 0
        pod_count = 0
        
        for line in lines:
            if line.strip():
                parts = line.split()
                if len(parts) >= 3:
                    cpu_str = parts[1].replace('m', '')
                    memory_str = parts[2].replace('Mi', '')
                    
                    try:
                        total_cpu += int(cpu_str)
                        total_memory += int(memory_str)
                        pod_count += 1
                    except ValueError:
                        continue
        
        return {
            "cpu_usage_millicores": total_cpu,
            "memory_usage_mb": total_memory,
            "pod_count": pod_count,
            "avg_cpu_per_pod": total_cpu / pod_count if pod_count > 0 else 0,
            "avg_memory_per_pod": total_memory / pod_count if pod_count > 0 else 0
        }
    
    def _analyze_kubectl_logs(self, logs: str) -> Dict[str, Any]:
        """Analyze kubectl logs for error patterns"""
        lines = logs.split('\n')
        errors = []
        warnings = []
        
        error_keywords = ['ERROR', 'Exception', 'Failed', 'timeout', 'OutOfMemory']
        warning_keywords = ['WARN', 'WARNING', 'slow', 'retry', 'degraded']
        
        for line in lines:
            line_upper = line.upper()
            if any(keyword.upper() in line_upper for keyword in error_keywords):
                errors.append(line.strip())
            elif any(keyword.upper() in line_upper for keyword in warning_keywords):
                warnings.append(line.strip())
        
        return {
            "error_count": len(errors),
            "warning_count": len(warnings),
            "recent_errors": errors[-10:],  # Last 10 errors
            "recent_warnings": warnings[-10:],  # Last 10 warnings
            "total_lines": len(lines)
        }
    
    def _analyze_service_dependencies(self, services_json: Dict, target_service: str) -> Dict[str, Any]:
        """Analyze service dependencies from kubectl output"""
        dependencies = []
        
        try:
            for service in services_json.get('items', []):
                service_name = service.get('metadata', {}).get('name', '')
                if service_name != target_service:
                    dependencies.append(service_name)
            
            return {
                "dependencies": dependencies,
                "dependency_count": len(dependencies),
                "analysis_method": "kubectl_service_discovery"
            }
        except Exception as e:
            logger.error(f"Service dependency analysis failed: {e}")
            return {"dependencies": [], "dependency_count": 0}
    
    def _get_basic_pod_status(self, service: str, namespace: str) -> Dict[str, Any]:
        """Get basic pod status as final fallback"""
        try:
            cmd = f"kubectl get pods -n {namespace} -l app={service} -o json"
            result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                pods = json.loads(result.stdout)
                return self._analyze_pod_status(pods)
                
        except Exception as e:
            logger.error(f"Basic pod status failed: {e}")
        
        return {
            "source": "basic_fallback",
            "status": "unknown",
            "pods": [],
            "healthy_pods": 0,
            "total_pods": 0
        }
    
    def _analyze_pod_status(self, pods_json: Dict) -> Dict[str, Any]:
        """Analyze pod status from kubectl output"""
        total_pods = 0
        healthy_pods = 0
        pod_statuses = []
        
        try:
            for pod in pods_json.get('items', []):
                total_pods += 1
                pod_name = pod.get('metadata', {}).get('name', 'unknown')
                phase = pod.get('status', {}).get('phase', 'Unknown')
                
                if phase == 'Running':
                    healthy_pods += 1
                
                pod_statuses.append({
                    "name": pod_name,
                    "phase": phase,
                    "ready": phase == 'Running'
                })
            
            return {
                "source": "kubectl_pod_status",
                "total_pods": total_pods,
                "healthy_pods": healthy_pods,
                "pod_health_ratio": healthy_pods / total_pods if total_pods > 0 else 0,
                "pods": pod_statuses
            }
        except Exception as e:
            logger.error(f"Pod status analysis failed: {e}")
            return {"total_pods": 0, "healthy_pods": 0, "pods": []}
    
    def get_comprehensive_incident_context(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get comprehensive incident context using all available tools with smart fallbacks
        """
        service = alert.get('labels', {}).get('service', 'unknown')
        namespace = alert.get('labels', {}).get('namespace', 'default')
        
        context = {
            "alert": alert,
            "service": service,
            "namespace": namespace,
            "timestamp": datetime.now().isoformat(),
            "analysis_capabilities": {
                "prometheus": self.prometheus_available,
                "loki": self.loki_available,
                "tempo": self.tempo_available
            }
        }
        
        # Get metrics with fallback
        context["metrics"] = self.get_metrics_or_fallback(service, namespace)
        
        # Get logs with fallback
        context["logs"] = self.get_logs_or_fallback(service, namespace)
        
        # Get traces with fallback (optional)
        context["traces"] = self.get_traces_or_fallback(service, namespace)
        
        # Determine incident classification based on available data
        context["incident_classification"] = self._classify_incident(context)
        
        return context
    
    def _classify_incident(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify incident based on available observability data
        """
        classification = {
            "type": "unknown",
            "severity": "medium",
            "confidence": "low",
            "runbook_hints": []
        }
        
        metrics = context.get("metrics", {})
        logs = context.get("logs", {})
        
        # Classify based on metrics
        if metrics.get("cpu_usage", 0) > 80:
            classification["type"] = "resource_constraint"
            classification["runbook_hints"].append("cpu_scaling")
        
        if metrics.get("memory_usage", 0) > 85:
            classification["type"] = "resource_constraint"
            classification["runbook_hints"].append("memory_scaling")
        
        if metrics.get("error_rate", 0) > 5:
            classification["type"] = "application_error"
            classification["runbook_hints"].append("error_investigation")
        
        # Classify based on logs
        if logs.get("error_count", 0) > 10:
            classification["type"] = "application_error"
            classification["runbook_hints"].append("log_analysis")
        
        # Determine severity
        if (metrics.get("cpu_usage", 0) > 95 or 
            metrics.get("error_rate", 0) > 10 or 
            logs.get("error_count", 0) > 50):
            classification["severity"] = "high"
        
        # Set confidence based on data availability
        data_sources = 0
        if context["analysis_capabilities"]["prometheus"]:
            data_sources += 1
        if context["analysis_capabilities"]["loki"]:
            data_sources += 1
        if context["analysis_capabilities"]["tempo"]:
            data_sources += 1
        
        if data_sources >= 2:
            classification["confidence"] = "high"
        elif data_sources == 1:
            classification["confidence"] = "medium"
        
        return classification