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
        """Generate a realistic test alert"""
        if not alert_id:
            alert_id = f"alert-{int(time.time())}-{random.randint(1000, 9999)}"
            
        services = ["api-service", "web-service", "database-service", "cache-service", "auth-service"]
        alert_types = ["HighCPUUsage", "HighMemoryUsage", "HighErrorRate", "ServiceDown", "HighLatency"]
        severities = ["critical", "warning", "info"]
        
        service = random.choice(services)
        alert_type = random.choice(alert_types)
        severity = random.choice(severities)
        
        return {
            "alert_id": alert_id,
            "alert_name": alert_type,
            "labels": {
                "service": service,
                "namespace": "default",
                "severity": severity,
                "environment": "production",
                "team": "platform"
            },
            "annotations": {
                "summary": f"{alert_type} detected on {service}",
                "description": f"Service {service} is experiencing {alert_type.lower()} issues",
                "runbook_url": f"https://runbooks.company.com/{alert_type.lower()}"
            },
            "timestamp": datetime.utcnow().isoformat(),
            "status": "firing"
        }
    
    def generate_metrics(self, service: str) -> Dict[str, Any]:
        """Generate realistic metrics data"""
        return {
            "service": service,
            "namespace": "default",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "cpu_usage": round(random.uniform(20, 95), 2),
                "memory_usage": round(random.uniform(30, 90), 2),
                "request_rate": round(random.uniform(100, 1000), 2),
                "error_rate": round(random.uniform(0.1, 5.0), 2),
                "response_time": round(random.uniform(50, 500), 2),
                "active_connections": random.randint(10, 200)
            }
        }
    
    def generate_logs(self, service: str) -> Dict[str, Any]:
        """Generate realistic log data"""
        log_levels = ["INFO", "WARN", "ERROR", "DEBUG"]
        log_messages = [
            "Request processed successfully",
            "Database connection established",
            "Cache miss for key",
            "Authentication successful",
            "Rate limit exceeded",
            "Internal server error",
            "Connection timeout",
            "Memory allocation failed"
        ]
        
        return {
            "service": service,
            "namespace": "default",
            "timestamp": datetime.utcnow().isoformat(),
            "level": random.choice(log_levels),
            "message": random.choice(log_messages),
            "pod": f"{service}-{random.randint(1000, 9999)}",
            "container": service,
            "source": "application"
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
        """Publish test metrics"""
        logger.info(f"Publishing {count} test metrics...")
        services = ["api-service", "web-service", "database-service", "cache-service", "auth-service"]
        
        for i in range(count):
            service = random.choice(services)
            metrics = self.generate_metrics(service)
            await self.js.publish(f"metrics.{service}", json.dumps(metrics).encode())
            if i % 10 == 0:
                logger.info(f"Published {i+1}/{count} metrics")
            await asyncio.sleep(0.05)
        logger.info(f"Published {count} metrics successfully")
    
    async def publish_logs(self, count: int = 100):
        """Publish test logs"""
        logger.info(f"Publishing {count} test logs...")
        services = ["api-service", "web-service", "database-service", "cache-service", "auth-service"]
        
        for i in range(count):
            service = random.choice(services)
            log_entry = self.generate_logs(service)
            await self.js.publish(f"logs.{service}", json.dumps(log_entry).encode())
            if i % 20 == 0:
                logger.info(f"Published {i+1}/{count} logs")
            await asyncio.sleep(0.02)
        logger.info(f"Published {count} logs successfully")
    
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