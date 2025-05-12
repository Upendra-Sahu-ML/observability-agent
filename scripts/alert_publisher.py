#!/usr/bin/env python3

import json
import redis
import time
import random
import argparse
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AlertPublisher:
    def __init__(self, redis_host='localhost', redis_port=6379):
        """Initialize the alert publisher with Redis connection"""
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True
        )
        self.alert_types = {
            'cpu': self._generate_cpu_alert,
            'memory': self._generate_memory_alert,
            'latency': self._generate_latency_alert,
            'error_rate': self._generate_error_rate_alert,
            'deployment': self._generate_deployment_alert
        }

    def _generate_cpu_alert(self):
        """Generate a CPU usage alert"""
        return {
            "alert_id": f"cpu-{int(time.time())}",
            "service": random.choice(["payment-service", "api-gateway", "user-service"]),
            "metric": "cpu_usage",
            "value": f"{random.randint(80, 100)}%",
            "threshold": "80%",
            "timestamp": datetime.utcnow().isoformat(),
            "labels": {
                "severity": random.choice(["warning", "critical"]),
                "environment": random.choice(["prod", "staging"]),
                "instance": f"instance-{random.randint(1, 5)}"
            }
        }

    def _generate_memory_alert(self):
        """Generate a memory usage alert"""
        return {
            "alert_id": f"memory-{int(time.time())}",
            "service": random.choice(["payment-service", "api-gateway", "user-service"]),
            "metric": "memory_usage",
            "value": f"{random.randint(85, 100)}%",
            "threshold": "85%",
            "timestamp": datetime.utcnow().isoformat(),
            "labels": {
                "severity": random.choice(["warning", "critical"]),
                "environment": random.choice(["prod", "staging"]),
                "instance": f"instance-{random.randint(1, 5)}"
            }
        }

    def _generate_latency_alert(self):
        """Generate a latency alert"""
        return {
            "alert_id": f"latency-{int(time.time())}",
            "service": random.choice(["payment-service", "api-gateway", "user-service"]),
            "metric": "p95_latency",
            "value": f"{random.uniform(1.5, 3.0):.2f}s",
            "threshold": "1s",
            "timestamp": datetime.utcnow().isoformat(),
            "labels": {
                "severity": random.choice(["warning", "critical"]),
                "environment": random.choice(["prod", "staging"]),
                "endpoint": random.choice(["/api/v1/payments", "/api/v1/users", "/api/v1/orders"])
            }
        }

    def _generate_error_rate_alert(self):
        """Generate an error rate alert"""
        return {
            "alert_id": f"error-{int(time.time())}",
            "service": random.choice(["payment-service", "api-gateway", "user-service"]),
            "metric": "error_rate",
            "value": f"{random.uniform(5, 20):.2f}%",
            "threshold": "5%",
            "timestamp": datetime.utcnow().isoformat(),
            "labels": {
                "severity": random.choice(["warning", "critical"]),
                "environment": random.choice(["prod", "staging"]),
                "error_type": random.choice(["5xx", "4xx", "timeout"])
            }
        }

    def _generate_deployment_alert(self):
        """Generate a deployment alert"""
        return {
            "alert_id": f"deploy-{int(time.time())}",
            "service": random.choice(["payment-service", "api-gateway", "user-service"]),
            "metric": "deployment_status",
            "value": random.choice(["failed", "stuck"]),
            "timestamp": datetime.utcnow().isoformat(),
            "labels": {
                "severity": "critical",
                "environment": random.choice(["prod", "staging"]),
                "version": f"v{random.randint(1, 10)}.{random.randint(0, 9)}.{random.randint(0, 9)}"
            }
        }

    def publish_alert(self, alert_type):
        """Publish a single alert of the specified type"""
        if alert_type not in self.alert_types:
            raise ValueError(f"Unknown alert type: {alert_type}")

        alert = self.alert_types[alert_type]()
        self.redis_client.publish('alerts', json.dumps(alert))
        logger.info(f"Published {alert_type} alert: {alert['alert_id']}")
        return alert

    def publish_random_alert(self):
        """Publish a random alert"""
        alert_type = random.choice(list(self.alert_types.keys()))
        return self.publish_alert(alert_type)

def main():
    parser = argparse.ArgumentParser(description='Publish sample alerts to Redis')
    parser.add_argument('--redis-host', default='localhost', help='Redis host')
    parser.add_argument('--redis-port', type=int, default=6379, help='Redis port')
    parser.add_argument('--alert-type', choices=['cpu', 'memory', 'latency', 'error_rate', 'deployment', 'random'],
                      default='random', help='Type of alert to publish')
    parser.add_argument('--interval', type=int, default=5, help='Interval between alerts in seconds')
    parser.add_argument('--count', type=int, default=1, help='Number of alerts to publish')

    args = parser.parse_args()

    publisher = AlertPublisher(args.redis_host, args.redis_port)

    try:
        for i in range(args.count):
            if args.alert_type == 'random':
                publisher.publish_random_alert()
            else:
                publisher.publish_alert(args.alert_type)
            
            if i < args.count - 1:  # Don't sleep after the last alert
                time.sleep(args.interval)
    except KeyboardInterrupt:
        logger.info("Alert publishing stopped by user")
    except Exception as e:
        logger.error(f"Error publishing alerts: {str(e)}")

if __name__ == '__main__':
    main() 