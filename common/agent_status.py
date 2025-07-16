"""
Agent Status Publishing Module

This module provides functionality for agents to publish their health status
to the AGENTS stream for UI dashboard consumption.
"""

import asyncio
import json
import logging
import psutil
import time
from datetime import datetime
from typing import Optional, Dict, Any
from common.stream_config import get_publish_subject

logger = logging.getLogger(__name__)


class AgentStatusPublisher:
    """
    Base class for publishing agent status to NATS AGENTS stream.
    
    This class handles:
    - Periodic status publishing
    - Health metrics collection (CPU, memory)
    - Status determination based on agent health
    - Graceful error handling
    """
    
    def __init__(self, agent_id: str, agent_name: str, js, publish_interval: int = 30):
        """
        Initialize the agent status publisher.
        
        Args:
            agent_id: Unique identifier for the agent (e.g., 'metric-agent')
            agent_name: Human-readable name (e.g., 'Metric Agent')
            js: NATS JetStream instance
            publish_interval: How often to publish status in seconds (default: 30)
        """
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.js = js
        self.publish_interval = publish_interval
        self.start_time = time.time()
        self.last_error = None
        self.error_count = 0
        self.is_running = False
        self.status_task = None
        
    async def start_publishing(self):
        """Start the periodic status publishing task."""
        if self.is_running:
            logger.warning(f"Status publishing already running for {self.agent_id}")
            return
            
        self.is_running = True
        self.status_task = asyncio.create_task(self._status_publishing_loop())
        logger.info(f"Started status publishing for {self.agent_id} (interval: {self.publish_interval}s)")
        
    async def stop_publishing(self):
        """Stop the periodic status publishing task."""
        self.is_running = False
        if self.status_task:
            self.status_task.cancel()
            try:
                await self.status_task
            except asyncio.CancelledError:
                pass
        logger.info(f"Stopped status publishing for {self.agent_id}")
        
    def record_error(self, error: Exception):
        """Record an error for status determination."""
        self.last_error = str(error)
        self.error_count += 1
        logger.debug(f"Recorded error for {self.agent_id}: {error}")
        
    def reset_errors(self):
        """Reset error tracking (call when agent recovers)."""
        self.last_error = None
        self.error_count = 0
        
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics for this process."""
        try:
            process = psutil.Process()
            
            # Get memory info
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024  # Convert to MB
            
            # Get CPU percentage (over a short interval)
            cpu_percent = process.cpu_percent(interval=0.1)
            
            # Get uptime
            uptime_seconds = int(time.time() - self.start_time)
            
            return {
                "memory_usage_mb": round(memory_mb, 2),
                "cpu_usage_percent": round(cpu_percent, 2),
                "uptime_seconds": uptime_seconds,
                "error_count": self.error_count
            }
        except Exception as e:
            logger.warning(f"Failed to get system metrics for {self.agent_id}: {e}")
            return {
                "memory_usage_mb": 0,
                "cpu_usage_percent": 0,
                "uptime_seconds": int(time.time() - self.start_time),
                "error_count": self.error_count
            }
            
    def determine_status(self) -> str:
        """
        Determine agent status based on current conditions.
        
        Returns:
            'active': Agent is healthy and functioning normally
            'degraded': Agent has some issues but is still functional
            'inactive': Agent has serious issues or is not responding
        """
        try:
            # Check recent error rate
            if self.error_count > 10:  # More than 10 errors
                return 'inactive'
            elif self.error_count > 3:  # 3-10 errors
                return 'degraded'
                
            # Check system resources
            metrics = self.get_system_metrics()
            
            # Check memory usage (consider degraded if > 1GB)
            if metrics.get("memory_usage_mb", 0) > 1024:
                return 'degraded'
                
            # Check CPU usage (consider degraded if consistently > 90%)
            if metrics.get("cpu_usage_percent", 0) > 90:
                return 'degraded'
                
            # If everything looks good
            return 'active'
            
        except Exception as e:
            logger.warning(f"Failed to determine status for {self.agent_id}: {e}")
            return 'degraded'
            
    async def publish_status(self) -> bool:
        """
        Publish current agent status to NATS.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Collect status data
            status_data = {
                "id": self.agent_id,
                "name": self.agent_name,
                "status": self.determine_status(),
                "timestamp": datetime.now().isoformat(),
                "version": "v1.0.0",  # Could be made configurable
                **self.get_system_metrics(),
                "metadata": {
                    "last_error": self.last_error,
                    "publish_interval": self.publish_interval
                }
            }
            
            # Publish to NATS using centralized subject pattern
            subject = f"{get_publish_subject('agent_status')}.{self.agent_id}"
            
            try:
                # Try JetStream first
                await self.js.publish(subject, json.dumps(status_data).encode())
                logger.debug(f"Published status for {self.agent_id} via JetStream")
            except Exception as js_error:
                # Fallback to regular NATS if JetStream fails
                if hasattr(self.js, '_nc') and self.js._nc:
                    await self.js._nc.publish(subject, json.dumps(status_data).encode())
                    logger.debug(f"Published status for {self.agent_id} via regular NATS")
                else:
                    raise js_error
                    
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish status for {self.agent_id}: {e}")
            self.record_error(e)
            return False
            
    async def _status_publishing_loop(self):
        """Internal loop for periodic status publishing."""
        while self.is_running:
            try:
                success = await self.publish_status()
                if success:
                    # Reset error count on successful publish
                    if self.error_count > 0:
                        logger.info(f"Status publishing recovered for {self.agent_id}")
                        self.error_count = max(0, self.error_count - 1)  # Gradually reduce errors
                        
                await asyncio.sleep(self.publish_interval)
                
            except asyncio.CancelledError:
                logger.info(f"Status publishing cancelled for {self.agent_id}")
                break
            except Exception as e:
                logger.error(f"Error in status publishing loop for {self.agent_id}: {e}")
                self.record_error(e)
                # Wait a bit before retrying
                await asyncio.sleep(min(self.publish_interval, 10))


# Convenience function for easy integration
async def start_agent_status_publishing(agent_id: str, agent_name: str, js, publish_interval: int = 30) -> AgentStatusPublisher:
    """
    Convenience function to start agent status publishing.
    
    Args:
        agent_id: Unique identifier for the agent
        agent_name: Human-readable name
        js: NATS JetStream instance
        publish_interval: Publishing interval in seconds
        
    Returns:
        AgentStatusPublisher instance
    """
    publisher = AgentStatusPublisher(agent_id, agent_name, js, publish_interval)
    await publisher.start_publishing()
    return publisher
