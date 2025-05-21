#!/usr/bin/env python3

import json
import time
import random
import argparse
import asyncio
import nats
from datetime import datetime, timedelta
import logging
import uuid
import signal
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedAlertPublisher:
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
            'deployment': self._generate_deployment_alert,
            'disk': self._generate_disk_alert,
            'network': self._generate_network_alert,
            'database': self._generate_database_alert
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

    def _generate_alert_base(self, alert_type, service=None, resolved=False, status=None):
        """Generate base alert structure with common fields"""
        if not service:
            service = random.choice(["payment-service", "api-gateway", "user-service", "order-service", "inventory-service"])
        
        # Generate timestamps
        now = datetime.utcnow()
        
        if resolved:
            # For resolved alerts, set a random start time in the past and an end time
            start_time = now - timedelta(minutes=random.randint(5, 60))
            end_time = now - timedelta(minutes=random.randint(1, 4))
            alert_status = "resolved"
        else:
            # For active alerts, set start time to now and no end time
            start_time = now
            end_time = None
            alert_status = status or random.choice(["open", "acknowledged", "in_progress"])
        
        return {
            "id": f"alert-{uuid.uuid4().hex[:8]}",
            "service": service,
            "startsAt": start_time.isoformat() + "Z",
            "endsAt": end_time.isoformat() + "Z" if end_time else None,
            "status": alert_status
        }

    def _generate_cpu_alert(self, service=None, resolved=False, status=None):
        """Generate a CPU usage alert"""
        base = self._generate_alert_base("cpu", service, resolved, status)
        value = random.randint(80, 100)
        
        return {
            "id": base["id"],
            "labels": {
                "alertname": "HighCpuUsage",
                "service": base["service"],
                "severity": "critical",
                "environment": random.choice(["prod", "staging"]),
                "instance": f"instance-{random.randint(1, 5)}",
                "namespace": "default"
            },
            "annotations": {
                "summary": "High CPU usage detected",
                "description": f"CPU usage above threshold for {base['service']}",
                "value": f"{value}%",
                "threshold": "80%"
            },
            "startsAt": base["startsAt"],
            "endsAt": base["endsAt"],
            "status": base["status"],
            "generatorURL": "http://observability-agent-alert-publisher"
        }

    def _generate_memory_alert(self, service=None, resolved=False, status=None):
        """Generate a memory usage alert"""
        base = self._generate_alert_base("memory", service, resolved, status)
        value = random.randint(85, 100)
        
        return {
            "id": base["id"],
            "labels": {
                "alertname": "HighMemoryUsage",
                "service": base["service"],
                "severity": "warning",
                "environment": random.choice(["prod", "staging"]),
                "instance": f"instance-{random.randint(1, 5)}",
                "namespace": "default"
            },
            "annotations": {
                "summary": "High memory usage detected",
                "description": f"Memory usage above threshold for {base['service']}",
                "value": f"{value}%",
                "threshold": "85%"
            },
            "startsAt": base["startsAt"],
            "endsAt": base["endsAt"],
            "status": base["status"],
            "generatorURL": "http://observability-agent-alert-publisher"
        }

    def _generate_latency_alert(self, service=None, resolved=False, status=None):
        """Generate a latency alert"""
        base = self._generate_alert_base("latency", service, resolved, status)
        value = random.uniform(1.5, 3.0)
        
        return {
            "id": base["id"],
            "labels": {
                "alertname": "HighLatency",
                "service": base["service"],
                "severity": "warning",
                "environment": random.choice(["prod", "staging"]),
                "endpoint": random.choice(["/api/v1/payments", "/api/v1/users", "/api/v1/orders"]),
                "namespace": "default"
            },
            "annotations": {
                "summary": "High latency detected",
                "description": f"Request latency above threshold for {base['service']}",
                "value": f"{value:.2f}s",
                "threshold": "1s"
            },
            "startsAt": base["startsAt"],
            "endsAt": base["endsAt"],
            "status": base["status"],
            "generatorURL": "http://observability-agent-alert-publisher"
        }

    def _generate_error_rate_alert(self, service=None, resolved=False, status=None):
        """Generate an error rate alert"""
        base = self._generate_alert_base("error_rate", service, resolved, status)
        value = random.uniform(5, 20)
        
        return {
            "id": base["id"],
            "labels": {
                "alertname": "HighErrorRate",
                "service": base["service"],
                "severity": "critical",
                "environment": random.choice(["prod", "staging"]),
                "error_type": random.choice(["5xx", "4xx", "timeout"]),
                "namespace": "default"
            },
            "annotations": {
                "summary": "High error rate detected",
                "description": f"Error rate above threshold for {base['service']}",
                "value": f"{value:.2f}%",
                "threshold": "5%"
            },
            "startsAt": base["startsAt"],
            "endsAt": base["endsAt"],
            "status": base["status"],
            "generatorURL": "http://observability-agent-alert-publisher"
        }

    def _generate_deployment_alert(self, service=None, resolved=False, status=None):
        """Generate a deployment alert"""
        base = self._generate_alert_base("deployment", service, resolved, status)
        version = f"v{random.randint(1, 10)}.{random.randint(0, 9)}.{random.randint(0, 9)}"
        
        return {
            "id": base["id"],
            "labels": {
                "alertname": "DeploymentFailed",
                "service": base["service"],
                "severity": "critical",
                "environment": random.choice(["prod", "staging"]),
                "version": version,
                "namespace": "default"
            },
            "annotations": {
                "summary": "Deployment failed",
                "description": f"Deployment of {base['service']} {version} failed",
                "status": "failed"
            },
            "startsAt": base["startsAt"],
            "endsAt": base["endsAt"],
            "status": base["status"],
            "generatorURL": "http://observability-agent-alert-publisher"
        }
        
    def _generate_disk_alert(self, service=None, resolved=False, status=None):
        """Generate a disk usage alert"""
        base = self._generate_alert_base("disk", service, resolved, status)
        value = random.randint(85, 98)
        
        return {
            "id": base["id"],
            "labels": {
                "alertname": "HighDiskUsage",
                "service": base["service"],
                "severity": "warning",
                "environment": random.choice(["prod", "staging"]),
                "instance": f"instance-{random.randint(1, 5)}",
                "namespace": "default"
            },
            "annotations": {
                "summary": "High disk usage detected",
                "description": f"Disk usage above threshold for {base['service']}",
                "value": f"{value}%",
                "threshold": "85%"
            },
            "startsAt": base["startsAt"],
            "endsAt": base["endsAt"],
            "status": base["status"],
            "generatorURL": "http://observability-agent-alert-publisher"
        }
        
    def _generate_network_alert(self, service=None, resolved=False, status=None):
        """Generate a network latency alert"""
        base = self._generate_alert_base("network", service, resolved, status)
        value = random.uniform(100, 500)
        
        return {
            "id": base["id"],
            "labels": {
                "alertname": "NetworkLatency",
                "service": base["service"],
                "severity": "warning",
                "environment": random.choice(["prod", "staging"]),
                "instance": f"instance-{random.randint(1, 5)}",
                "namespace": "default"
            },
            "annotations": {
                "summary": "Network latency detected",
                "description": f"Network latency above threshold for {base['service']}",
                "value": f"{value:.2f}ms",
                "threshold": "100ms"
            },
            "startsAt": base["startsAt"],
            "endsAt": base["endsAt"],
            "status": base["status"],
            "generatorURL": "http://observability-agent-alert-publisher"
        }
        
    def _generate_database_alert(self, service=None, resolved=False, status=None):
        """Generate a database connection issue alert"""
        base = self._generate_alert_base("database", service, resolved, status)
        value = random.uniform(5, 20)
        
        return {
            "id": base["id"],
            "labels": {
                "alertname": "DatabaseConnectionIssue",
                "service": base["service"],
                "severity": "critical",
                "environment": random.choice(["prod", "staging"]),
                "database": random.choice(["postgres", "mysql", "mongodb"]),
                "namespace": "default"
            },
            "annotations": {
                "summary": "Database connection issue detected",
                "description": f"Database connection failures above threshold for {base['service']}",
                "value": f"{value:.2f}%",
                "threshold": "5%"
            },
            "startsAt": base["startsAt"],
            "endsAt": base["endsAt"],
            "status": base["status"],
            "generatorURL": "http://observability-agent-alert-publisher"
        }

    def generate_alert(self, alert_type=None, service=None, resolved=False, status=None):
        """Generate an alert of the specified type or a random type"""
        if alert_type and alert_type in self.alert_types:
            generator = self.alert_types[alert_type]
        else:
            # Pick a random alert type
            alert_type = random.choice(list(self.alert_types.keys()))
            generator = self.alert_types[alert_type]
        
        return generator(service=service, resolved=resolved, status=status)

    async def publish_alert(self, alert):
        """Publish an alert to NATS JetStream"""
        if not self.js:
            raise RuntimeError("Not connected to NATS JetStream")
        
        subject = f"alerts.{alert['labels']['alertname']}"
        await self.js.publish(subject, json.dumps(alert).encode())
        
        status = alert.get('status', 'active')
        resolved_str = " (resolved)" if alert.get('endsAt') else ""
        logger.info(f"Published alert: {alert['id']} - {alert['labels']['alertname']} for {alert['labels']['service']} - Status: {status}{resolved_str}")

async def run_publisher(args):
    """Run the alert publisher with command line arguments"""
    publisher = EnhancedAlertPublisher(args.nats_server)
    
    try:
        await publisher.connect()
        
        # Handle Ctrl+C gracefully
        def signal_handler(sig, frame):
            logger.info("Received interrupt signal, shutting down...")
            asyncio.create_task(publisher.disconnect())
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Generate and publish alerts
        for i in range(args.count):
            # Determine if this should be a resolved alert
            resolved = args.resolved or (args.mixed and random.choice([True, False]))
            
            alert = publisher.generate_alert(
                alert_type=args.alert_type,
                service=args.service,
                resolved=resolved,
                status=args.status
            )
            
            await publisher.publish_alert(alert)
            
            if i < args.count - 1:
                # Wait before sending the next alert
                time.sleep(args.interval)
        
        await publisher.disconnect()
    except Exception as e:
        logger.error(f"Error running alert publisher: {str(e)}")
        if publisher.nats_client:
            await publisher.disconnect()
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enhanced Alert Publisher for Observability Agent")
    parser.add_argument("--nats-server", default="nats://localhost:4222", help="NATS server URL")
    parser.add_argument("--alert-type", choices=["cpu", "memory", "latency", "error_rate", "deployment", "disk", "network", "database"], help="Specific alert type to generate")
    parser.add_argument("--service", help="Specific service to use (overrides random selection)")
    parser.add_argument("--count", type=int, default=1, help="Number of alerts to generate")
    parser.add_argument("--interval", type=int, default=1, help="Interval between alerts in seconds")
    parser.add_argument("--resolved", action="store_true", help="Generate resolved alerts (with end time)")
    parser.add_argument("--mixed", action="store_true", help="Generate a mix of active and resolved alerts")
    parser.add_argument("--status", choices=["open", "acknowledged", "in_progress"], help="Specific status for active alerts")
    
    args = parser.parse_args()
    
    asyncio.run(run_publisher(args))
