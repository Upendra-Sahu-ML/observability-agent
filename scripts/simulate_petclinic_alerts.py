#!/usr/bin/env python3
"""
PetClinic Alert Simulation Script
Generates realistic alerts for the PetClinic application running on AKS with Azure Monitor
"""

import json
import random
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any
import argparse
import logging
import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import nats
    from nats.js.api import StreamConfig
except ImportError:
    print("Please install nats-py: pip install nats-py")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PetClinicAlertSimulator:
    def __init__(self, nats_url="nats://localhost:4222"):
        self.nats_url = nats_url
        self.nc = None
        self.js = None
        
    async def connect(self):
        """Connect to NATS server"""
        try:
            self.nc = await nats.connect(self.nats_url)
            self.js = self.nc.jetstream()
            logger.info(f"Connected to NATS at {self.nats_url}")
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from NATS server"""
        if self.nc:
            await self.nc.close()
            logger.info("Disconnected from NATS")
    
    def generate_petclinic_jvm_memory_alert(self, severity="warning") -> Dict[str, Any]:
        """Generate JVM memory usage alert for PetClinic"""
        memory_usage = 85 if severity == "warning" else 95
        alert_id = f"petclinic-memory-{int(time.time())}-{random.randint(1000, 9999)}"
        
        return {
            "alert_id": alert_id,
            "alert_name": "PetClinicHighMemoryUsage",
            "labels": {
                "service": "petclinic",
                "namespace": "default",
                "severity": severity,
                "environment": "production",
                "team": "petclinic-team",
                "application": "spring-boot",
                "component": "jvm",
                "cluster": "aks-petclinic-cluster"
            },
            "annotations": {
                "summary": f"PetClinic JVM memory usage is {memory_usage}%",
                "description": f"The PetClinic application is experiencing high memory usage ({memory_usage}%). This may indicate a memory leak or insufficient heap size configuration.",
                "runbook_url": "https://runbooks.company.com/petclinic/memory-issues",
                "dashboard_url": "https://portal.azure.com/#view/Microsoft_Azure_Monitoring",
                "azure_resource_id": "/subscriptions/xxx/resourceGroups/petclinic-rg/providers/Microsoft.ContainerService/managedClusters/aks-petclinic"
            },
            "azure_monitor": {
                "workspace_id": "xxx-workspace-id",
                "query": "customMetrics | where name == 'jvm.memory.used' and customDimensions.application == 'petclinic'",
                "metric_value": memory_usage,
                "threshold": 80
            },
            "kubernetes": {
                "namespace": "default",
                "deployment": "petclinic",
                "pod_selector": "app=petclinic",
                "container": "petclinic"
            },
            "timestamp": datetime.utcnow().isoformat(),
            "status": "firing",
            "generator_url": "Azure Monitor Alert Rule",
            "incident_context": {
                "business_impact": "Medium - Users may experience slow response times",
                "affected_users": random.randint(50, 200),
                "geographic_impact": "All regions"
            }
        }
    
    def generate_petclinic_slow_response_alert(self, severity="warning") -> Dict[str, Any]:
        """Generate slow response time alert for PetClinic"""
        response_time = 2500 if severity == "warning" else 5000  # milliseconds
        alert_id = f"petclinic-slowresponse-{int(time.time())}-{random.randint(1000, 9999)}"
        
        return {
            "alert_id": alert_id,
            "alert_name": "PetClinicSlowResponseTime",
            "labels": {
                "service": "petclinic",
                "namespace": "default",
                "severity": severity,
                "environment": "production",
                "team": "petclinic-team",
                "application": "spring-boot",
                "component": "web",
                "endpoint": "/owners",
                "cluster": "aks-petclinic-cluster"
            },
            "annotations": {
                "summary": f"PetClinic response time is {response_time}ms",
                "description": f"The PetClinic application response time has increased to {response_time}ms, which is above the acceptable threshold of 2000ms. This may indicate database issues, high load, or performance degradation.",
                "runbook_url": "https://runbooks.company.com/petclinic/performance-issues"
            },
            "azure_monitor": {
                "workspace_id": "xxx-workspace-id",
                "query": "requests | where cloud_RoleName == 'petclinic' | summarize avg(duration)",
                "metric_value": response_time,
                "threshold": 2000
            },
            "kubernetes": {
                "namespace": "default",
                "deployment": "petclinic",
                "pod_selector": "app=petclinic"
            },
            "timestamp": datetime.utcnow().isoformat(),
            "status": "firing",
            "incident_context": {
                "business_impact": "High - Users experiencing slow page loads",
                "affected_users": random.randint(100, 500),
                "affected_endpoints": ["/owners", "/pets", "/vets"]
            }
        }
    
    def generate_petclinic_database_connection_alert(self, severity="critical") -> Dict[str, Any]:
        """Generate database connection failure alert for PetClinic"""
        alert_id = f"petclinic-dbconnection-{int(time.time())}-{random.randint(1000, 9999)}"
        
        return {
            "alert_id": alert_id,
            "alert_name": "PetClinicDatabaseConnectionFailure",
            "labels": {
                "service": "petclinic",
                "namespace": "default",
                "severity": severity,
                "environment": "production",
                "team": "petclinic-team",
                "application": "spring-boot",
                "component": "database",
                "database": "postgresql",
                "cluster": "aks-petclinic-cluster"
            },
            "annotations": {
                "summary": "PetClinic cannot connect to PostgreSQL database",
                "description": "The PetClinic application is experiencing database connectivity issues. Multiple connection attempts to PostgreSQL have failed. This will cause application errors and data access failures.",
                "runbook_url": "https://runbooks.company.com/petclinic/database-connection"
            },
            "azure_monitor": {
                "workspace_id": "xxx-workspace-id", 
                "query": "exceptions | where cloud_RoleName == 'petclinic' and type contains 'SQL'",
                "error_count": random.randint(10, 50),
                "threshold": 5
            },
            "kubernetes": {
                "namespace": "default",
                "deployment": "petclinic",
                "pod_selector": "app=petclinic",
                "related_services": ["postgresql"]
            },
            "timestamp": datetime.utcnow().isoformat(),
            "status": "firing",
            "incident_context": {
                "business_impact": "Critical - Application completely unavailable",
                "affected_users": "All users",
                "data_impact": "No data access possible"
            }
        }
    
    def generate_petclinic_high_error_rate_alert(self, severity="warning") -> Dict[str, Any]:
        """Generate high error rate alert for PetClinic"""
        error_rate = 15 if severity == "warning" else 25  # percentage
        alert_id = f"petclinic-errorrate-{int(time.time())}-{random.randint(1000, 9999)}"
        
        return {
            "alert_id": alert_id,
            "alert_name": "PetClinicHighErrorRate",
            "labels": {
                "service": "petclinic",
                "namespace": "default",
                "severity": severity,
                "environment": "production",
                "team": "petclinic-team",
                "application": "spring-boot",
                "component": "web",
                "cluster": "aks-petclinic-cluster"
            },
            "annotations": {
                "summary": f"PetClinic error rate is {error_rate}%",
                "description": f"The PetClinic application is experiencing a high error rate of {error_rate}%. This indicates potential issues with application logic, database connectivity, or external dependencies.",
                "runbook_url": "https://runbooks.company.com/petclinic/high-error-rate"
            },
            "azure_monitor": {
                "workspace_id": "xxx-workspace-id",
                "query": "requests | where cloud_RoleName == 'petclinic' | summarize error_rate = countif(success == false) * 100.0 / count()",
                "metric_value": error_rate,
                "threshold": 10
            },
            "kubernetes": {
                "namespace": "default",
                "deployment": "petclinic",
                "pod_selector": "app=petclinic"
            },
            "timestamp": datetime.utcnow().isoformat(),
            "status": "firing",
            "incident_context": {
                "business_impact": "Medium - Some users experiencing errors",
                "affected_users": random.randint(25, 100),
                "error_types": ["500 Internal Server Error", "502 Bad Gateway", "Database Connection Error"]
            }
        }
    
    def generate_postgresql_performance_alert(self, severity="warning") -> Dict[str, Any]:
        """Generate PostgreSQL performance alert"""
        slow_query_time = 3000 if severity == "warning" else 8000  # milliseconds
        alert_id = f"postgresql-performance-{int(time.time())}-{random.randint(1000, 9999)}"
        
        return {
            "alert_id": alert_id,
            "alert_name": "PostgreSQLSlowQueries",
            "labels": {
                "service": "postgresql",
                "namespace": "default",
                "severity": severity,
                "environment": "production",
                "team": "petclinic-team",
                "component": "database",
                "database": "postgresql",
                "cluster": "aks-petclinic-cluster"
            },
            "annotations": {
                "summary": f"PostgreSQL queries taking {slow_query_time}ms on average",
                "description": f"PostgreSQL database is experiencing slow query performance with average execution time of {slow_query_time}ms. This may impact PetClinic application responsiveness.",
                "runbook_url": "https://runbooks.company.com/postgresql/performance"
            },
            "azure_monitor": {
                "workspace_id": "xxx-workspace-id",
                "query": "customMetrics | where name == 'postgresql.query.time' and customDimensions.database == 'petclinic'",
                "metric_value": slow_query_time,
                "threshold": 2000
            },
            "kubernetes": {
                "namespace": "default",
                "deployment": "postgresql",
                "pod_selector": "app=postgresql"
            },
            "timestamp": datetime.utcnow().isoformat(),
            "status": "firing",
            "incident_context": {
                "business_impact": "Medium - Slower user experience",
                "affected_queries": ["SELECT FROM owners", "SELECT FROM pets", "SELECT FROM visits"]
            }
        }
    
    def generate_aks_node_pressure_alert(self, severity="warning") -> Dict[str, Any]:
        """Generate AKS node resource pressure alert"""
        cpu_usage = 85 if severity == "warning" else 95
        alert_id = f"aks-nodepressure-{int(time.time())}-{random.randint(1000, 9999)}"
        
        return {
            "alert_id": alert_id,
            "alert_name": "AKSNodeResourcePressure",
            "labels": {
                "service": "aks-cluster",
                "namespace": "kube-system",
                "severity": severity,
                "environment": "production",
                "team": "platform-team",
                "component": "infrastructure",
                "node": f"aks-nodepool1-{random.randint(10000000, 99999999)}-vmss000000",
                "cluster": "aks-petclinic-cluster"
            },
            "annotations": {
                "summary": f"AKS node CPU usage is {cpu_usage}%",
                "description": f"One or more AKS nodes are experiencing high resource usage ({cpu_usage}% CPU). This may impact all applications running on the cluster including PetClinic.",
                "runbook_url": "https://runbooks.company.com/aks/node-pressure"
            },
            "azure_monitor": {
                "workspace_id": "xxx-workspace-id",
                "query": "Perf | where ObjectName == 'K8SNode' and CounterName == 'cpuUsageNanoCores'",
                "metric_value": cpu_usage,
                "threshold": 80
            },
            "kubernetes": {
                "node_name": f"aks-nodepool1-{random.randint(10000000, 99999999)}-vmss000000",
                "affected_namespaces": ["default", "kube-system"]
            },
            "timestamp": datetime.utcnow().isoformat(),
            "status": "firing",
            "incident_context": {
                "business_impact": "High - May affect all applications",
                "affected_services": ["petclinic", "postgresql", "system-services"]
            }
        }
    
    def generate_petclinic_jvm_gc_alert(self, severity="warning") -> Dict[str, Any]:
        """Generate JVM garbage collection alert for PetClinic"""
        gc_pause_time = 200 if severity == "warning" else 500  # milliseconds
        alert_id = f"petclinic-jvmgc-{int(time.time())}-{random.randint(1000, 9999)}"
        
        return {
            "alert_id": alert_id,
            "alert_name": "PetClinicJVMGCPressure",
            "labels": {
                "service": "petclinic",
                "namespace": "default",
                "severity": severity,
                "environment": "production",
                "team": "petclinic-team",
                "application": "spring-boot",
                "component": "jvm-gc",
                "cluster": "aks-petclinic-cluster"
            },
            "annotations": {
                "summary": f"PetClinic JVM GC pause time is {gc_pause_time}ms",
                "description": f"The PetClinic application is experiencing long garbage collection pauses ({gc_pause_time}ms). This may cause request timeouts and poor user experience.",
                "runbook_url": "https://runbooks.company.com/petclinic/jvm-gc-tuning"
            },
            "azure_monitor": {
                "workspace_id": "xxx-workspace-id",
                "query": "customMetrics | where name == 'jvm.gc.pause' and customDimensions.application == 'petclinic'",
                "metric_value": gc_pause_time,
                "threshold": 100
            },
            "kubernetes": {
                "namespace": "default",
                "deployment": "petclinic",
                "pod_selector": "app=petclinic"
            },
            "timestamp": datetime.utcnow().isoformat(),
            "status": "firing",
            "incident_context": {
                "business_impact": "Medium - Users may experience timeouts",
                "gc_type": "G1Young" if gc_pause_time < 300 else "G1Full"
            }
        }
    
    async def simulate_incident_scenario(self, scenario: str = "database_outage"):
        """Simulate a complete incident scenario with multiple related alerts"""
        logger.info(f"Simulating incident scenario: {scenario}")
        
        if scenario == "database_outage":
            # Simulate database outage scenario
            alerts = [
                self.generate_petclinic_database_connection_alert("critical"),
                self.generate_petclinic_high_error_rate_alert("critical"),
                self.generate_postgresql_performance_alert("critical")
            ]
            
        elif scenario == "memory_pressure":
            # Simulate memory pressure scenario
            alerts = [
                self.generate_petclinic_jvm_memory_alert("warning"),
                self.generate_petclinic_jvm_gc_alert("warning"),
                self.generate_petclinic_slow_response_alert("warning")
            ]
            
        elif scenario == "high_load":
            # Simulate high load scenario
            alerts = [
                self.generate_petclinic_slow_response_alert("warning"),
                self.generate_petclinic_high_error_rate_alert("warning"),
                self.generate_aks_node_pressure_alert("warning")
            ]
            
        elif scenario == "deployment_issues":
            # Simulate deployment-related issues
            alerts = [
                self.generate_petclinic_high_error_rate_alert("critical"),
                self.generate_petclinic_slow_response_alert("critical")
            ]
        else:
            # Random scenario
            alert_generators = [
                self.generate_petclinic_jvm_memory_alert,
                self.generate_petclinic_slow_response_alert,
                self.generate_petclinic_database_connection_alert,
                self.generate_petclinic_high_error_rate_alert,
                self.generate_postgresql_performance_alert,
                self.generate_petclinic_jvm_gc_alert
            ]
            
            alerts = [random.choice(alert_generators)("warning")]
        
        # Publish alerts with some delay between them
        for i, alert in enumerate(alerts):
            await self.js.publish("alerts", json.dumps(alert).encode())
            logger.info(f"Published alert {i+1}/{len(alerts)}: {alert['alert_name']} - {alert['alert_id']}")
            
            if i < len(alerts) - 1:
                await asyncio.sleep(random.uniform(2, 8))  # Random delay between alerts
        
        logger.info(f"Completed incident scenario: {scenario} with {len(alerts)} alerts")
    
    async def simulate_continuous_monitoring(self, duration_minutes: int = 30):
        """Simulate continuous monitoring with periodic alerts"""
        logger.info(f"Starting continuous monitoring simulation for {duration_minutes} minutes")
        
        end_time = datetime.utcnow() + timedelta(minutes=duration_minutes)
        
        while datetime.utcnow() < end_time:
            # Generate a random alert every 2-5 minutes
            wait_time = random.uniform(120, 300)  # 2-5 minutes
            
            alert_generators = [
                (self.generate_petclinic_jvm_memory_alert, 0.3),
                (self.generate_petclinic_slow_response_alert, 0.25),
                (self.generate_petclinic_high_error_rate_alert, 0.2),
                (self.generate_postgresql_performance_alert, 0.15),
                (self.generate_petclinic_jvm_gc_alert, 0.1)
            ]
            
            # Weighted random selection
            total_weight = sum(weight for _, weight in alert_generators)
            r = random.uniform(0, total_weight)
            cumulative_weight = 0
            
            for generator, weight in alert_generators:
                cumulative_weight += weight
                if r <= cumulative_weight:
                    severity = random.choices(["warning", "critical"], weights=[0.7, 0.3])[0]
                    alert = generator(severity)
                    await self.js.publish("alerts", json.dumps(alert).encode())
                    logger.info(f"Published monitoring alert: {alert['alert_name']} - {alert['alert_id']}")
                    break
            
            await asyncio.sleep(wait_time)
        
        logger.info("Continuous monitoring simulation completed")

async def main():
    parser = argparse.ArgumentParser(description='Simulate PetClinic alerts for testing')
    parser.add_argument('--nats-url', default='nats://localhost:4222', help='NATS server URL')
    parser.add_argument('--scenario', choices=['database_outage', 'memory_pressure', 'high_load', 'deployment_issues', 'random'], 
                       default='random', help='Incident scenario to simulate')
    parser.add_argument('--continuous', type=int, help='Run continuous monitoring for X minutes')
    parser.add_argument('--count', type=int, default=1, help='Number of alert scenarios to generate')
    
    args = parser.parse_args()
    
    simulator = PetClinicAlertSimulator(args.nats_url)
    
    try:
        await simulator.connect()
        
        if args.continuous:
            await simulator.simulate_continuous_monitoring(args.continuous)
        else:
            for i in range(args.count):
                await simulator.simulate_incident_scenario(args.scenario)
                if i < args.count - 1:
                    await asyncio.sleep(random.uniform(10, 30))  # Wait between scenarios
                    
    except Exception as e:
        logger.error(f"Simulation error: {e}")
        sys.exit(1)
    finally:
        await simulator.disconnect()

if __name__ == "__main__":
    asyncio.run(main())