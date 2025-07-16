"""
PetClinic Application Runbooks
Collection of runbooks specific to the Spring Boot PetClinic application
"""

import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class PetClinicRunbooks:
    """Runbooks specifically designed for PetClinic application incidents"""
    
    @staticmethod
    def get_all_runbooks() -> Dict[str, Dict[str, Any]]:
        """Get all available PetClinic runbooks"""
        return {
            "petclinic_high_memory": PetClinicRunbooks.high_memory_usage_runbook(),
            "petclinic_slow_response": PetClinicRunbooks.slow_response_time_runbook(),
            "petclinic_database_connection": PetClinicRunbooks.database_connection_runbook(),
            "petclinic_startup_failure": PetClinicRunbooks.startup_failure_runbook(),
            "petclinic_high_error_rate": PetClinicRunbooks.high_error_rate_runbook(),
            "petclinic_jvm_gc_issues": PetClinicRunbooks.jvm_gc_issues_runbook(),
            "petclinic_postgresql_performance": PetClinicRunbooks.postgresql_performance_runbook(),
            "petclinic_scale_up": PetClinicRunbooks.scale_up_runbook(),
            "petclinic_rollback": PetClinicRunbooks.rollback_deployment_runbook()
        }
    
    @staticmethod
    def high_memory_usage_runbook() -> Dict[str, Any]:
        """Runbook for PetClinic high memory usage incidents"""
        return {
            "id": "petclinic_high_memory",
            "title": "PetClinic High Memory Usage Resolution",
            "description": "Resolve high memory usage in Spring Boot PetClinic application",
            "severity": "medium",
            "estimated_duration": "15 minutes",
            "tags": ["java", "jvm", "memory", "spring-boot", "petclinic"],
            "prerequisites": [
                "kubectl access to the cluster",
                "Azure Monitor access for JVM metrics",
                "Basic understanding of JVM memory management"
            ],
            "steps": [
                {
                    "step": 1,
                    "title": "Check Current Memory Usage",
                    "description": "Analyze current JVM memory usage and trends",
                    "action": "investigate",
                    "commands": [
                        "kubectl top pods -n default -l app=petclinic",
                        "kubectl describe pods -n default -l app=petclinic"
                    ],
                    "azure_query": "customMetrics | where name == 'jvm.memory.used' and customDimensions.application == 'petclinic'",
                    "expected_result": "Identify current memory usage and heap allocation",
                    "troubleshooting": "If no metrics available, check Azure Monitor configuration"
                },
                {
                    "step": 2,
                    "title": "Analyze Memory Patterns",
                    "description": "Check for memory leaks or unusual allocation patterns",
                    "action": "investigate",
                    "azure_query": "customMetrics | where name in ('jvm.memory.used', 'jvm.gc.pause') and customDimensions.application == 'petclinic'",
                    "analysis_points": [
                        "Memory usage trend over time",
                        "GC frequency and duration",
                        "Heap vs non-heap memory usage",
                        "Memory usage after GC cycles"
                    ]
                },
                {
                    "step": 3,
                    "title": "Check Application Logs for Memory Errors",
                    "description": "Look for OutOfMemoryError or memory-related warnings",
                    "action": "investigate",
                    "commands": [
                        "kubectl logs -n default -l app=petclinic --tail=200 | grep -i memory",
                        "kubectl logs -n default -l app=petclinic --tail=200 | grep -i 'OutOfMemory'"
                    ],
                    "azure_query": "ContainerLog | where ContainerName contains 'petclinic' and LogEntry contains 'memory'",
                    "look_for": ["OutOfMemoryError", "Memory allocation failed", "GC overhead limit exceeded"]
                },
                {
                    "step": 4,
                    "title": "Immediate Memory Relief",
                    "description": "Restart pods to clear memory if critical",
                    "action": "remediate",
                    "conditions": ["Memory usage > 90%", "Application showing errors"],
                    "commands": [
                        "kubectl rollout restart deployment/petclinic -n default"
                    ],
                    "wait_time": "2-3 minutes for restart completion",
                    "validation": "kubectl get pods -n default -l app=petclinic"
                },
                {
                    "step": 5,
                    "title": "Adjust JVM Memory Settings",
                    "description": "Update deployment with optimized JVM memory parameters",
                    "action": "remediate",
                    "configuration_changes": {
                        "JAVA_OPTS": "-Xms512m -Xmx1024m -XX:MaxMetaspaceSize=256m -XX:+UseG1GC",
                        "JVM_ARGS": "-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/tmp/heapdump"
                    },
                    "commands": [
                        "kubectl patch deployment petclinic -n default -p '{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"petclinic\",\"env\":[{\"name\":\"JAVA_OPTS\",\"value\":\"-Xms512m -Xmx1024m -XX:+UseG1GC\"}]}]}}}}'",
                        "kubectl rollout status deployment/petclinic -n default"
                    ]
                },
                {
                    "step": 6,
                    "title": "Scale Horizontally if Needed",
                    "description": "Increase number of replicas to distribute memory load",
                    "action": "remediate",
                    "conditions": ["Single pod struggling", "High user load"],
                    "commands": [
                        "kubectl scale deployment petclinic --replicas=3 -n default",
                        "kubectl get pods -n default -l app=petclinic -w"
                    ]
                },
                {
                    "step": 7,
                    "title": "Monitor and Validate",
                    "description": "Confirm memory usage is back to normal levels",
                    "action": "validate",
                    "monitoring": [
                        "JVM heap usage < 80%",
                        "GC pause times < 100ms",
                        "No OutOfMemoryErrors in logs",
                        "Application responding normally"
                    ],
                    "commands": [
                        "kubectl top pods -n default -l app=petclinic",
                        "curl -f http://petclinic-service/actuator/health"
                    ],
                    "duration": "Monitor for 10-15 minutes"
                }
            ],
            "rollback_plan": [
                "If scaling up causes issues, scale back down",
                "If JVM changes cause problems, revert to previous JAVA_OPTS",
                "Use kubectl rollout undo if deployment issues occur"
            ],
            "prevention": [
                "Set up memory usage alerts in Azure Monitor",
                "Implement proper JVM tuning from start",
                "Regular memory usage monitoring",
                "Load testing with realistic data volumes"
            ]
        }
    
    @staticmethod
    def database_connection_runbook() -> Dict[str, Any]:
        """Runbook for PetClinic database connectivity issues"""
        return {
            "id": "petclinic_database_connection",
            "title": "PetClinic Database Connection Issues",
            "description": "Diagnose and resolve PostgreSQL connectivity issues in PetClinic",
            "severity": "high",
            "estimated_duration": "20 minutes",
            "tags": ["database", "postgresql", "connectivity", "spring-boot", "petclinic"],
            "steps": [
                {
                    "step": 1,
                    "title": "Check Database Pod Status",
                    "description": "Verify PostgreSQL pods are running and ready",
                    "action": "investigate",
                    "commands": [
                        "kubectl get pods -n default -l app=postgresql",
                        "kubectl describe pods -n default -l app=postgresql",
                        "kubectl logs -n default -l app=postgresql --tail=50"
                    ]
                },
                {
                    "step": 2,
                    "title": "Test Database Connectivity",
                    "description": "Test connection from PetClinic to PostgreSQL",
                    "action": "investigate",
                    "commands": [
                        "kubectl exec -n default deployment/petclinic -- pg_isready -h postgresql -p 5432",
                        "kubectl exec -n default deployment/postgresql -- psql -U petclinic -d petclinic -c 'SELECT 1;'"
                    ]
                },
                {
                    "step": 3,
                    "title": "Check Connection Pool Status",
                    "description": "Verify HikariCP connection pool health in PetClinic",
                    "action": "investigate",
                    "commands": [
                        "kubectl exec -n default deployment/petclinic -- curl localhost:8080/actuator/health/db",
                        "kubectl logs -n default -l app=petclinic --tail=100 | grep -i 'connection\\|pool\\|hikari'"
                    ]
                },
                {
                    "step": 4,
                    "title": "Restart Database if Needed",
                    "description": "Restart PostgreSQL pods if they're in failed state",
                    "action": "remediate",
                    "conditions": ["PostgreSQL pods not ready", "Connection refused errors"],
                    "commands": [
                        "kubectl rollout restart deployment/postgresql -n default",
                        "kubectl wait --for=condition=ready pod -l app=postgresql -n default --timeout=300s"
                    ]
                },
                {
                    "step": 5,
                    "title": "Restart PetClinic Application",
                    "description": "Restart application to refresh connection pool",
                    "action": "remediate",
                    "commands": [
                        "kubectl rollout restart deployment/petclinic -n default",
                        "kubectl rollout status deployment/petclinic -n default"
                    ]
                },
                {
                    "step": 6,
                    "title": "Validate Database Connection",
                    "description": "Confirm application can connect and query database",
                    "action": "validate",
                    "commands": [
                        "kubectl exec -n default deployment/petclinic -- curl -f localhost:8080/actuator/health",
                        "curl -f http://petclinic-service/owners"
                    ]
                }
            ]
        }
    
    @staticmethod
    def slow_response_time_runbook() -> Dict[str, Any]:
        """Runbook for PetClinic slow response time issues"""
        return {
            "id": "petclinic_slow_response",
            "title": "PetClinic Slow Response Time Resolution",
            "description": "Diagnose and resolve slow response times in PetClinic application",
            "severity": "medium",
            "estimated_duration": "25 minutes",
            "tags": ["performance", "response-time", "spring-boot", "petclinic"],
            "steps": [
                {
                    "step": 1,
                    "title": "Check Current Response Times",
                    "description": "Measure current application response times",
                    "action": "investigate",
                    "azure_query": "requests | where cloud_RoleName == 'petclinic' | summarize avg(duration), percentile(duration, 95) by name",
                    "commands": [
                        "curl -w '%{time_total}' http://petclinic-service/",
                        "kubectl exec -n default deployment/petclinic -- curl -w '%{time_total}' localhost:8080/actuator/metrics/http.server.requests"
                    ]
                },
                {
                    "step": 2,
                    "title": "Check Database Query Performance",
                    "description": "Identify slow database queries",
                    "action": "investigate",
                    "commands": [
                        "kubectl exec -n default deployment/postgresql -- psql -U petclinic -d petclinic -c \"SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;\""
                    ]
                },
                {
                    "step": 3,
                    "title": "Analyze JVM Performance",
                    "description": "Check for GC pressure and CPU usage",
                    "action": "investigate",
                    "azure_query": "customMetrics | where name in ('jvm.gc.pause', 'process.cpu.usage') and customDimensions.application == 'petclinic'",
                    "commands": [
                        "kubectl top pods -n default -l app=petclinic"
                    ]
                },
                {
                    "step": 4,
                    "title": "Scale Application if Needed",
                    "description": "Increase replicas to handle load",
                    "action": "remediate",
                    "conditions": ["High CPU usage", "Many concurrent requests"],
                    "commands": [
                        "kubectl scale deployment petclinic --replicas=3 -n default"
                    ]
                },
                {
                    "step": 5,
                    "title": "Optimize JVM Settings",
                    "description": "Tune JVM for better performance",
                    "action": "remediate",
                    "configuration_changes": {
                        "JAVA_OPTS": "-Xms512m -Xmx1024m -XX:+UseG1GC -XX:MaxGCPauseMillis=200"
                    }
                }
            ]
        }
    
    @staticmethod
    def scale_up_runbook() -> Dict[str, Any]:
        """Runbook for scaling up PetClinic application"""
        return {
            "id": "petclinic_scale_up",
            "title": "Scale Up PetClinic Application",
            "description": "Scale PetClinic application to handle increased load",
            "severity": "low",
            "estimated_duration": "10 minutes",
            "tags": ["scaling", "performance", "petclinic"],
            "steps": [
                {
                    "step": 1,
                    "title": "Check Current Resource Usage",
                    "description": "Assess current CPU and memory usage",
                    "action": "investigate",
                    "commands": [
                        "kubectl top pods -n default -l app=petclinic",
                        "kubectl get hpa -n default"
                    ]
                },
                {
                    "step": 2,
                    "title": "Scale Application",
                    "description": "Increase replica count",
                    "action": "remediate",
                    "commands": [
                        "kubectl scale deployment petclinic --replicas=5 -n default",
                        "kubectl rollout status deployment/petclinic -n default"
                    ]
                },
                {
                    "step": 3,
                    "title": "Verify Load Distribution",
                    "description": "Ensure traffic is distributed across all pods",
                    "action": "validate",
                    "commands": [
                        "kubectl get pods -n default -l app=petclinic -o wide",
                        "kubectl get endpoints petclinic-service -n default"
                    ]
                }
            ]
        }
    
    @staticmethod
    def jvm_gc_issues_runbook() -> Dict[str, Any]:
        """Runbook for JVM garbage collection issues"""
        return {
            "id": "petclinic_jvm_gc_issues",
            "title": "PetClinic JVM Garbage Collection Issues",
            "description": "Resolve JVM GC performance issues in PetClinic",
            "severity": "medium",
            "estimated_duration": "20 minutes",
            "tags": ["jvm", "gc", "performance", "java", "petclinic"],
            "steps": [
                {
                    "step": 1,
                    "title": "Analyze GC Metrics",
                    "description": "Check GC pause times and frequency",
                    "action": "investigate",
                    "azure_query": "customMetrics | where name contains 'jvm.gc' and customDimensions.application == 'petclinic'",
                    "thresholds": {
                        "gc_pause_warning": "100ms",
                        "gc_pause_critical": "300ms",
                        "gc_frequency_warning": "more than 10 per minute"
                    }
                },
                {
                    "step": 2,
                    "title": "Check Memory Allocation Patterns",
                    "description": "Analyze heap usage and allocation rates",
                    "action": "investigate",
                    "azure_query": "customMetrics | where name in ('jvm.memory.used', 'jvm.memory.max') and customDimensions.application == 'petclinic'"
                },
                {
                    "step": 3,
                    "title": "Optimize GC Settings",
                    "description": "Apply optimized garbage collector settings",
                    "action": "remediate",
                    "configuration_changes": {
                        "JAVA_OPTS": "-Xms512m -Xmx1024m -XX:+UseG1GC -XX:MaxGCPauseMillis=200 -XX:G1HeapRegionSize=16m"
                    },
                    "commands": [
                        "kubectl patch deployment petclinic -n default -p '{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"petclinic\",\"env\":[{\"name\":\"JAVA_OPTS\",\"value\":\"-Xms512m -Xmx1024m -XX:+UseG1GC -XX:MaxGCPauseMillis=200\"}]}]}}}}'"
                    ]
                }
            ]
        }
    
    @staticmethod
    def postgresql_performance_runbook() -> Dict[str, Any]:
        """Runbook for PostgreSQL performance issues"""
        return {
            "id": "petclinic_postgresql_performance", 
            "title": "PetClinic PostgreSQL Performance Optimization",
            "description": "Optimize PostgreSQL performance for PetClinic workload",
            "severity": "medium",
            "estimated_duration": "30 minutes",
            "tags": ["database", "postgresql", "performance", "petclinic"],
            "steps": [
                {
                    "step": 1,
                    "title": "Check Database Performance Metrics",
                    "description": "Analyze current database performance",
                    "action": "investigate",
                    "commands": [
                        "kubectl exec -n default deployment/postgresql -- psql -U petclinic -d petclinic -c \"SELECT * FROM pg_stat_activity WHERE state = 'active';\""
                    ]
                },
                {
                    "step": 2,
                    "title": "Identify Slow Queries",
                    "description": "Find queries taking longer than expected",
                    "action": "investigate",
                    "commands": [
                        "kubectl exec -n default deployment/postgresql -- psql -U petclinic -d petclinic -c \"SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;\""
                    ]
                },
                {
                    "step": 3,
                    "title": "Check Index Usage",
                    "description": "Verify indexes are being used effectively",
                    "action": "investigate",
                    "commands": [
                        "kubectl exec -n default deployment/postgresql -- psql -U petclinic -d petclinic -c \"SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch FROM pg_stat_user_indexes ORDER BY idx_scan DESC;\""
                    ]
                }
            ]
        }
    
    @staticmethod
    def startup_failure_runbook() -> Dict[str, Any]:
        """Runbook for PetClinic startup failures"""
        return {
            "id": "petclinic_startup_failure",
            "title": "PetClinic Application Startup Failure",
            "description": "Diagnose and resolve PetClinic startup issues",
            "severity": "high",
            "estimated_duration": "15 minutes",
            "tags": ["startup", "spring-boot", "configuration", "petclinic"],
            "steps": [
                {
                    "step": 1,
                    "title": "Check Pod Status",
                    "description": "Verify pod startup status and errors",
                    "action": "investigate",
                    "commands": [
                        "kubectl get pods -n default -l app=petclinic",
                        "kubectl describe pods -n default -l app=petclinic"
                    ]
                },
                {
                    "step": 2,
                    "title": "Check Application Logs",
                    "description": "Look for startup errors in application logs",
                    "action": "investigate",
                    "commands": [
                        "kubectl logs -n default -l app=petclinic --tail=100",
                        "kubectl logs -n default -l app=petclinic --previous"
                    ]
                },
                {
                    "step": 3,
                    "title": "Verify Configuration",
                    "description": "Check environment variables and configuration",
                    "action": "investigate",
                    "commands": [
                        "kubectl get configmap -n default",
                        "kubectl describe deployment petclinic -n default"
                    ]
                }
            ]
        }
    
    @staticmethod
    def high_error_rate_runbook() -> Dict[str, Any]:
        """Runbook for high error rate in PetClinic"""
        return {
            "id": "petclinic_high_error_rate",
            "title": "PetClinic High Error Rate Resolution",
            "description": "Investigate and resolve high error rates in PetClinic application",
            "severity": "high",
            "estimated_duration": "20 minutes",
            "tags": ["errors", "debugging", "spring-boot", "petclinic"],
            "steps": [
                {
                    "step": 1,
                    "title": "Check Error Rate Metrics",
                    "description": "Analyze current error rates and patterns",
                    "action": "investigate",
                    "azure_query": "requests | where cloud_RoleName == 'petclinic' | summarize error_rate = countif(success == false) * 100.0 / count() by bin(timestamp, 5m)"
                },
                {
                    "step": 2,
                    "title": "Analyze Error Logs", 
                    "description": "Identify common error patterns",
                    "action": "investigate",
                    "commands": [
                        "kubectl logs -n default -l app=petclinic --tail=200 | grep -i error",
                        "kubectl logs -n default -l app=petclinic --tail=200 | grep -i exception"
                    ]
                },
                {
                    "step": 3,
                    "title": "Check Application Health",
                    "description": "Verify application health endpoints",
                    "action": "investigate",
                    "commands": [
                        "kubectl exec -n default deployment/petclinic -- curl localhost:8080/actuator/health"
                    ]
                }
            ]
        }
    
    @staticmethod
    def rollback_deployment_runbook() -> Dict[str, Any]:
        """Runbook for rolling back PetClinic deployment"""
        return {
            "id": "petclinic_rollback",
            "title": "Rollback PetClinic Deployment",
            "description": "Rollback PetClinic to previous working version",
            "severity": "high",
            "estimated_duration": "10 minutes",
            "tags": ["rollback", "deployment", "recovery", "petclinic"],
            "steps": [
                {
                    "step": 1,
                    "title": "Check Deployment History",
                    "description": "View recent deployment history",
                    "action": "investigate",
                    "commands": [
                        "kubectl rollout history deployment/petclinic -n default",
                        "kubectl get replicasets -n default -l app=petclinic"
                    ]
                },
                {
                    "step": 2,
                    "title": "Rollback to Previous Version",
                    "description": "Execute rollback to last stable version",
                    "action": "remediate",
                    "commands": [
                        "kubectl rollout undo deployment/petclinic -n default",
                        "kubectl rollout status deployment/petclinic -n default"
                    ]
                },
                {
                    "step": 3,
                    "title": "Verify Rollback Success",
                    "description": "Confirm application is working after rollback",
                    "action": "validate",
                    "commands": [
                        "kubectl get pods -n default -l app=petclinic",
                        "curl -f http://petclinic-service/"
                    ]
                }
            ]
        }