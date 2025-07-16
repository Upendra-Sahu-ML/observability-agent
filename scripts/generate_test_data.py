#!/usr/bin/env python3
"""
Test Data Generator for Observability Agent
Replaces Node.js scripts with Python implementation for generating dummy data
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

class TestDataGenerator:
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
    
    async def ensure_streams(self):
        """Ensure all required streams exist"""
        streams = {
            "ALERTS": ["alerts", "alert_responses"],
            "METRICS": ["metrics.*", "metric_analysis"],
            "LOGS": ["logs.*", "log_analysis"],
            "DEPLOYMENTS": ["deployments.*", "deployment_analysis"],
            "AGENTS": ["agent_status", "agent_responses"],
            "RUNBOOKS": ["runbooks.*", "runbook_execution"],
            "NOTIFICATIONS": ["notifications.*", "notification_status"]
        }
        
        for stream_name, subjects in streams.items():
            try:
                await self.js.stream_info(stream_name)
                logger.info(f"Stream {stream_name} already exists")
            except Exception:
                # Stream doesn't exist, create it
                try:
                    config = StreamConfig(
                        name=stream_name,
                        subjects=subjects,
                        max_msgs=10000,
                        max_bytes=100 * 1024 * 1024,  # 100MB
                        max_age=7 * 24 * 3600,  # 7 days
                        storage="file"
                    )
                    await self.js.add_stream(config)
                    logger.info(f"Created stream {stream_name}")
                except Exception as e:
                    logger.error(f"Failed to create stream {stream_name}: {e}")
    
    def generate_alert(self, alert_id: str = None) -> Dict[str, Any]:
        """Generate a realistic test alert for PetClinic and related services"""
        if not alert_id:
            alert_id = f"alert-{int(time.time())}-{random.randint(1000, 9999)}"
            
        # PetClinic-specific services and alerts
        services = ["petclinic", "postgresql", "aks-cluster"]
        petclinic_alerts = ["PetClinicHighMemoryUsage", "PetClinicSlowResponseTime", "PetClinicHighErrorRate", "PetClinicJVMGCPressure"]
        postgresql_alerts = ["PostgreSQLSlowQueries", "PostgreSQLConnectionFailure", "PostgreSQLHighConnections"]
        aks_alerts = ["AKSNodeResourcePressure", "AKSPodCrashLooping", "AKSStoragePressure"]
        severities = ["critical", "warning", "info"]
        
        service = random.choice(services)
        severity = random.choice(severities)
        
        if service == "petclinic":
            alert_type = random.choice(petclinic_alerts)
        elif service == "postgresql":
            alert_type = random.choice(postgresql_alerts)
        else:  # aks-cluster
            alert_type = random.choice(aks_alerts)
        
        return {
            "alert_id": alert_id,
            "alert_name": alert_type,
            "labels": {
                "service": service,
                "namespace": "default",
                "severity": severity,
                "environment": "production",
                "team": "petclinic-team",
                "application": "spring-boot" if service == "petclinic" else service,
                "cluster": "aks-petclinic-cluster"
            },
            "annotations": {
                "summary": f"{alert_type} detected on {service}",
                "description": f"Service {service} is experiencing {alert_type.lower()} issues in the PetClinic application",
                "runbook_url": f"https://runbooks.company.com/petclinic/{alert_type.lower()}",
                "azure_resource_id": f"/subscriptions/xxx/resourceGroups/petclinic-rg/providers/Microsoft.ContainerService/managedClusters/aks-petclinic"
            },
            "azure_monitor": {
                "workspace_id": "xxx-workspace-id",
                "query": f"customMetrics | where customDimensions.application == '{service}'",
                "threshold_exceeded": True
            },
            "kubernetes": {
                "namespace": "default",
                "deployment": service,
                "pod_selector": f"app={service}"
            },
            "timestamp": datetime.utcnow().isoformat(),
            "status": "firing"
        }
    
    def generate_metrics(self, service: str) -> Dict[str, Any]:
        """Generate realistic metrics data for PetClinic and related services"""
        base_metrics = {
            "service": service,
            "namespace": "default",
            "timestamp": datetime.utcnow().isoformat(),
            "cluster": "aks-petclinic-cluster"
        }
        
        if service == "petclinic":
            # Java/Spring Boot specific metrics
            base_metrics["metrics"] = {
                "cpu_usage": round(random.uniform(20, 80), 2),
                "memory_usage": round(random.uniform(40, 85), 2),
                "jvm_heap_used": round(random.uniform(200, 800), 2),  # MB
                "jvm_heap_max": 1024,  # MB
                "jvm_threads_live": random.randint(20, 100),
                "jvm_classes_loaded": random.randint(8000, 12000),
                "jvm_gc_pause_time": round(random.uniform(10, 200), 2),  # ms
                "request_rate": round(random.uniform(50, 300), 2),
                "error_rate": round(random.uniform(0.1, 3.0), 2),
                "response_time": round(random.uniform(100, 2000), 2),  # ms
                "http_requests_total": random.randint(1000, 10000),
                "http_requests_duration_p95": round(random.uniform(200, 1500), 2)
            }
        elif service == "postgresql":
            # PostgreSQL specific metrics
            base_metrics["metrics"] = {
                "cpu_usage": round(random.uniform(10, 70), 2),
                "memory_usage": round(random.uniform(30, 80), 2),
                "active_connections": random.randint(5, 50),
                "max_connections": 100,
                "database_size_mb": round(random.uniform(100, 500), 2),
                "query_duration_avg": round(random.uniform(10, 200), 2),  # ms
                "slow_queries": random.randint(0, 5),
                "deadlocks": random.randint(0, 2),
                "commits_per_sec": round(random.uniform(10, 100), 2),
                "rollbacks_per_sec": round(random.uniform(0, 5), 2),
                "cache_hit_ratio": round(random.uniform(85, 99), 2)
            }
        else:
            # Generic Kubernetes/AKS metrics
            base_metrics["metrics"] = {
                "cpu_usage": round(random.uniform(20, 95), 2),
                "memory_usage": round(random.uniform(30, 90), 2),
                "pod_count": random.randint(1, 10),
                "ready_pods": random.randint(1, 8),
                "network_rx_bytes": random.randint(1024, 1024*1024),
                "network_tx_bytes": random.randint(1024, 1024*1024),
                "storage_usage": round(random.uniform(20, 80), 2),
                "node_ready": random.choice([True, False])
            }
        
        return base_metrics
    
    def generate_logs(self, service: str) -> Dict[str, Any]:
        """Generate realistic log data for PetClinic and related services"""
        log_levels = ["INFO", "WARN", "ERROR", "DEBUG"]
        
        if service == "petclinic":
            # Spring Boot specific log messages
            log_messages = [
                "Started PetClinicApplication in 12.345 seconds",
                "Initializing Spring DispatcherServlet 'dispatcherServlet'",
                "HikariPool-1 - Start completed",
                "Serving request GET /owners with parameters {}",
                "JPA EntityManager creation completed",
                "Hibernate: select owner0_.id as id1_0_ from owners owner0_",
                "Processing owner registration for John Doe",
                "Vet appointment scheduled successfully",
                "Pet information updated for pet ID: 123",
                "Database query completed in 45ms",
                "Memory usage: 512MB / 1024MB (50%)",
                "GC pause: 23ms (G1Young)",
                "Connection pool stats: active=5, idle=15, max=20",
                "Failed to process request: NullPointerException",
                "Database connection timeout after 30s",
                "OutOfMemoryError: Java heap space"
            ]
        elif service == "postgresql":
            # PostgreSQL specific log messages
            log_messages = [
                "database system is ready to accept connections",
                "autovacuum: processing database 'petclinic'",
                "checkpoint starting: time",
                "checkpoint complete: wrote 42 buffers",
                "LOG: duration: 125.234 ms statement: SELECT * FROM owners",
                "connection received: host=petclinic port=5432",
                "connection authorized: user=petclinic database=petclinic",
                "slow query detected: duration 2.5s",
                "deadlock detected: process 1234 waits for process 5678",
                "ERROR: connection to database failed",
                "FATAL: password authentication failed for user 'petclinic'"
            ]
        else:
            # Generic Kubernetes/AKS log messages
            log_messages = [
                "Pod started successfully",
                "Container image pulled",
                "Readiness probe succeeded",
                "Liveness probe failed",
                "Volume mount succeeded",
                "Network policy applied",
                "Service endpoint updated",
                "ConfigMap reloaded",
                "Secret mounted successfully",
                "Pod terminating gracefully"
            ]
        
        return {
            "service": service,
            "namespace": "default",
            "timestamp": datetime.utcnow().isoformat(),
            "level": random.choice(log_levels),
            "message": random.choice(log_messages),
            "pod": f"{service}-{random.randint(10000, 99999)}-{random.choice(['abcde', 'fghij', 'klmno'])}",
            "container": service,
            "source": "application",
            "cluster": "aks-petclinic-cluster",
            "node": f"aks-nodepool1-{random.randint(10000000, 99999999)}-vmss000000"
        }
    
    def generate_deployment(self, service: str) -> Dict[str, Any]:
        """Generate realistic deployment data"""
        return {
            "service": service,
            "namespace": "default",
            "timestamp": datetime.utcnow().isoformat(),
            "deployment": {
                "name": f"{service}-deployment",
                "replicas": random.randint(2, 10),
                "ready_replicas": random.randint(1, 8),
                "image": f"company/{service}:v{random.randint(1, 5)}.{random.randint(0, 10)}.{random.randint(0, 20)}",
                "status": random.choice(["Running", "Pending", "Failed"]),
                "rollout_status": random.choice(["Complete", "InProgress", "Failed"])
            }
        }
    
    def generate_agent_status(self, agent_name: str) -> Dict[str, Any]:
        """Generate agent status data"""
        return {
            "agent_id": f"{agent_name}-{random.randint(1000, 9999)}",
            "agent_name": agent_name,
            "timestamp": datetime.utcnow().isoformat(),
            "status": random.choice(["healthy", "degraded", "unhealthy"]),
            "last_seen": datetime.utcnow().isoformat(),
            "version": f"v{random.randint(1, 3)}.{random.randint(0, 10)}.{random.randint(0, 20)}",
            "metrics": {
                "processed_alerts": random.randint(0, 100),
                "response_time": round(random.uniform(0.1, 2.0), 2),
                "error_count": random.randint(0, 5)
            }
        }
    
    async def publish_alerts(self, count: int = 10):
        """Publish test alerts"""
        logger.info(f"Publishing {count} test alerts...")
        for i in range(count):
            alert = self.generate_alert()
            await self.js.publish("alerts", json.dumps(alert).encode())
            if i % 5 == 0:
                logger.info(f"Published {i+1}/{count} alerts")
            await asyncio.sleep(0.1)  # Small delay to avoid overwhelming
        logger.info(f"Published {count} alerts successfully")
    
    async def publish_metrics(self, count: int = 50):
        """Publish test metrics for PetClinic and related services"""
        logger.info(f"Publishing {count} test metrics...")
        services = ["petclinic", "postgresql", "aks-cluster"]
        
        for i in range(count):
            service = random.choice(services)
            metrics = self.generate_metrics(service)
            await self.js.publish(f"metrics.{service}", json.dumps(metrics).encode())
            if i % 10 == 0:
                logger.info(f"Published {i+1}/{count} metrics")
            await asyncio.sleep(0.05)
        logger.info(f"Published {count} PetClinic metrics successfully")
    
    async def publish_logs(self, count: int = 100):
        """Publish test logs for PetClinic and related services"""
        logger.info(f"Publishing {count} test logs...")
        services = ["petclinic", "postgresql", "aks-cluster"]
        
        for i in range(count):
            service = random.choice(services)
            log_entry = self.generate_logs(service)
            await self.js.publish(f"logs.{service}", json.dumps(log_entry).encode())
            if i % 20 == 0:
                logger.info(f"Published {i+1}/{count} logs")
            await asyncio.sleep(0.02)
        logger.info(f"Published {count} PetClinic logs successfully")
    
    async def publish_deployments(self, count: int = 20):
        """Publish test deployments"""
        logger.info(f"Publishing {count} test deployments...")
        services = ["api-service", "web-service", "database-service", "cache-service", "auth-service"]
        
        for i in range(count):
            service = random.choice(services)
            deployment = self.generate_deployment(service)
            await self.js.publish(f"deployments.{service}", json.dumps(deployment).encode())
            if i % 5 == 0:
                logger.info(f"Published {i+1}/{count} deployments")
            await asyncio.sleep(0.1)
        logger.info(f"Published {count} deployments successfully")
    
    async def publish_agent_status(self, count: int = 20):
        """Publish agent status data"""
        logger.info(f"Publishing {count} agent status updates...")
        agents = ["observability-agent", "infrastructure-agent", "communication-agent", "root-cause-agent"]
        
        for i in range(count):
            agent = random.choice(agents)
            status = self.generate_agent_status(agent)
            await self.js.publish("agent_status", json.dumps(status).encode())
            if i % 5 == 0:
                logger.info(f"Published {i+1}/{count} agent status updates")
            await asyncio.sleep(0.1)
        logger.info(f"Published {count} agent status updates successfully")
    
    async def publish_all_data(self):
        """Publish all types of test data"""
        logger.info("Publishing comprehensive test data...")
        
        await self.ensure_streams()
        
        # Publish in parallel for better performance
        tasks = [
            self.publish_alerts(10),
            self.publish_metrics(50),
            self.publish_logs(100),
            self.publish_deployments(20),
            self.publish_agent_status(20)
        ]
        
        await asyncio.gather(*tasks)
        logger.info("All test data published successfully!")

async def main():
    parser = argparse.ArgumentParser(description='Generate test data for Observability Agent')
    parser.add_argument('--nats-url', default='nats://localhost:4222', help='NATS server URL')
    parser.add_argument('--type', choices=['alerts', 'metrics', 'logs', 'deployments', 'agents', 'all'], 
                       default='all', help='Type of data to generate')
    parser.add_argument('--count', type=int, default=50, help='Number of items to generate')
    
    args = parser.parse_args()
    
    generator = TestDataGenerator(args.nats_url)
    
    try:
        await generator.connect()
        
        if args.type == 'all':
            await generator.publish_all_data()
        elif args.type == 'alerts':
            await generator.publish_alerts(args.count)
        elif args.type == 'metrics':
            await generator.publish_metrics(args.count)
        elif args.type == 'logs':
            await generator.publish_logs(args.count)
        elif args.type == 'deployments':
            await generator.publish_deployments(args.count)
        elif args.type == 'agents':
            await generator.publish_agent_status(args.count)
            
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    finally:
        await generator.disconnect()

if __name__ == "__main__":
    asyncio.run(main())