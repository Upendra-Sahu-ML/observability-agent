#!/usr/bin/env python3

import json
import time
import random
import argparse
import asyncio
import nats
from datetime import datetime
import logging
import uuid
import signal
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AlertPublisher:
    def __init__(self, nats_server='nats://nats:4222'):
        """Initialize the alert publisher with NATS connection details"""
        self.nats_server = nats_server
        self.nats_client = None
        self.js = None
        self.alert_types = {
            'cpu': self._generate_cpu_alert,
            'memory': self._generate_memory_alert,
            'latency': self._generate_latency_alert,
            'error_rate': self._generate_error_rate_alert,
            'deployment': self._generate_deployment_alert
        }

    async def connect(self):
        """Connect to NATS server and set up JetStream"""
        try:
            # Connect to NATS server
            self.nats_client = await nats.connect(self.nats_server)
            logger.info(f"Connected to NATS server at {self.nats_server}")
            
            # Create JetStream context
            self.js = self.nats_client.jetstream()
            logger.info("JetStream context initialized")
            
            # Check if ALERTS stream exists
            try:
                await self.js.stream_info("ALERTS")
                logger.info("ALERTS stream already exists")
            except Exception:
                # Create ALERTS stream if it doesn't exist
                await self.js.add_stream(
                    name="ALERTS",
                    subjects=["alerts", "alerts.*"]
                )
                logger.info("Created ALERTS stream")
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {str(e)}")
            raise

    async def disconnect(self):
        """Disconnect from NATS server"""
        if self.nats_client and self.nats_client.is_connected:
            await self.nats_client.close()
            logger.info("Disconnected from NATS server")

    def _generate_cpu_alert(self):
        """Generate a CPU usage alert"""
        return {
            "id": str(uuid.uuid4()),
            "labels": {
                "alertname": "HighCpuUsage",
                "service": random.choice(["payment-service", "api-gateway", "user-service"]),
                "severity": random.choice(["warning", "critical"]),
                "environment": random.choice(["prod", "staging"]),
                "instance": f"instance-{random.randint(1, 5)}",
                "namespace": "default"
            },
            "annotations": {
                "summary": "High CPU usage detected",
                "description": "CPU usage above threshold for service",
                "value": f"{random.randint(80, 100)}%",
                "threshold": "80%"
            },
            "startsAt": datetime.utcnow().isoformat() + "Z"
        }

    def _generate_memory_alert(self):
        """Generate a memory usage alert"""
        return {
            "id": str(uuid.uuid4()),
            "labels": {
                "alertname": "HighMemoryUsage",
                "service": random.choice(["payment-service", "api-gateway", "user-service"]),
                "severity": random.choice(["warning", "critical"]),
                "environment": random.choice(["prod", "staging"]),
                "instance": f"instance-{random.randint(1, 5)}",
                "namespace": "default"
            },
            "annotations": {
                "summary": "High memory usage detected",
                "description": "Memory usage above threshold for service",
                "value": f"{random.randint(85, 100)}%",
                "threshold": "85%"
            },
            "startsAt": datetime.utcnow().isoformat() + "Z"
        }

    def _generate_latency_alert(self):
        """Generate a latency alert"""
        return {
            "id": str(uuid.uuid4()),
            "labels": {
                "alertname": "HighLatency",
                "service": random.choice(["payment-service", "api-gateway", "user-service"]),
                "severity": random.choice(["warning", "critical"]),
                "environment": random.choice(["prod", "staging"]),
                "endpoint": random.choice(["/api/v1/payments", "/api/v1/users", "/api/v1/orders"]),
                "namespace": "default"
            },
            "annotations": {
                "summary": "High latency detected",
                "description": "Request latency above threshold",
                "value": f"{random.uniform(1.5, 3.0):.2f}s",
                "threshold": "1s"
            },
            "startsAt": datetime.utcnow().isoformat() + "Z"
        }

    def _generate_error_rate_alert(self):
        """Generate an error rate alert"""
        return {
            "id": str(uuid.uuid4()),
            "labels": {
                "alertname": "HighErrorRate",
                "service": random.choice(["payment-service", "api-gateway", "user-service"]),
                "severity": random.choice(["warning", "critical"]),
                "environment": random.choice(["prod", "staging"]),
                "error_type": random.choice(["5xx", "4xx", "timeout"]),
                "namespace": "default"
            },
            "annotations": {
                "summary": "High error rate detected",
                "description": "Error rate above threshold",
                "value": f"{random.uniform(5, 20):.2f}%",
                "threshold": "5%"
            },
            "startsAt": datetime.utcnow().isoformat() + "Z"
        }

    def _generate_deployment_alert(self):
        """Generate a deployment alert"""
        return {
            "id": str(uuid.uuid4()),
            "labels": {
                "alertname": "DeploymentFailed",
                "service": random.choice(["payment-service", "api-gateway", "user-service"]),
                "severity": "critical",
                "environment": random.choice(["prod", "staging"]),
                "version": f"v{random.randint(1, 10)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
                "namespace": "default"
            },
            "annotations": {
                "summary": "Deployment failed or stuck",
                "description": "Deployment is in failed or stuck state",
                "status": random.choice(["failed", "stuck"])
            },
            "startsAt": datetime.utcnow().isoformat() + "Z"
        }

    async def publish_alert(self, alert_type):
        """Publish a single alert of the specified type"""
        if alert_type not in self.alert_types:
            raise ValueError(f"Unknown alert type: {alert_type}")

        alert = self.alert_types[alert_type]()
        
        # Ensure connection
        if not self.nats_client or not self.nats_client.is_connected:
            await self.connect()
        
        # Publish to NATS
        await self.js.publish("alerts", json.dumps(alert).encode())
        
        logger.info(f"Published {alert_type} alert: {alert['id']}")
        return alert

    async def publish_random_alert(self):
        """Publish a random alert"""
        alert_type = random.choice(list(self.alert_types.keys()))
        return await self.publish_alert(alert_type)

async def run(args):
    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(publisher)))
    
    # Create publisher
    publisher = AlertPublisher(args.nats_server)
    
    try:
        # Connect to NATS
        await publisher.connect()
        
        # Publish alerts
        for i in range(args.count):
            if args.alert_type == 'random':
                await publisher.publish_random_alert()
            else:
                await publisher.publish_alert(args.alert_type)
            
            if i < args.count - 1:  # Don't sleep after the last alert
                await asyncio.sleep(args.interval)
                
        # Allow time for messages to be processed
        await asyncio.sleep(1)
        
        # Disconnect
        await publisher.disconnect()
        
    except Exception as e:
        logger.error(f"Error publishing alerts: {str(e)}")
        await publisher.disconnect()

async def shutdown(publisher):
    logger.info("Shutting down...")
    await publisher.disconnect()
    sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description='Publish sample alerts to NATS JetStream')
    parser.add_argument('--nats-server', default='nats://nats:4222', 
                        help='NATS server URL (default: nats://nats:4222)')
    parser.add_argument('--alert-type', 
                        choices=['cpu', 'memory', 'latency', 'error_rate', 'deployment', 'random'],
                        default='random', help='Type of alert to publish')
    parser.add_argument('--interval', type=int, default=5, 
                        help='Interval between alerts in seconds (default: 5)')
    parser.add_argument('--count', type=int, default=1, 
                        help='Number of alerts to publish (default: 1)')

    args = parser.parse_args()

    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        logger.info("Alert publishing stopped by user")
    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == '__main__':
    main()