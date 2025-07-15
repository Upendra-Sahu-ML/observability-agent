#!/usr/bin/env python3
"""
NATS Utilities for Observability Agent
Replaces Node.js nats_utils.js with Python implementation
"""

import asyncio
import json
import logging
import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

try:
    import nats
    from nats.js.api import StreamConfig, ConsumerConfig
except ImportError:
    print("Please install nats-py: pip install nats-py")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NATSUtils:
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
    
    async def list_streams(self) -> List[str]:
        """List all streams"""
        try:
            streams = await self.js.streams_info()
            return [stream.config.name for stream in streams]
        except Exception as e:
            logger.error(f"Failed to list streams: {e}")
            return []
    
    async def stream_info(self, stream_name: str) -> Optional[Dict]:
        """Get information about a specific stream"""
        try:
            info = await self.js.stream_info(stream_name)
            return {
                "name": info.config.name,
                "subjects": info.config.subjects,
                "messages": info.state.messages,
                "bytes": info.state.bytes,
                "first_seq": info.state.first_seq,
                "last_seq": info.state.last_seq,
                "created": info.created.isoformat() if info.created else None
            }
        except Exception as e:
            logger.error(f"Failed to get stream info for {stream_name}: {e}")
            return None
    
    async def create_stream(self, name: str, subjects: List[str], **kwargs) -> bool:
        """Create a new stream"""
        try:
            config = StreamConfig(
                name=name,
                subjects=subjects,
                max_msgs=kwargs.get('max_msgs', 10000),
                max_bytes=kwargs.get('max_bytes', 100 * 1024 * 1024),  # 100MB
                max_age=kwargs.get('max_age', 7 * 24 * 3600),  # 7 days
                storage=kwargs.get('storage', 'file')
            )
            await self.js.add_stream(config)
            logger.info(f"Created stream {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create stream {name}: {e}")
            return False
    
    async def delete_stream(self, stream_name: str) -> bool:
        """Delete a stream"""
        try:
            await self.js.delete_stream(stream_name)
            logger.info(f"Deleted stream {stream_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete stream {stream_name}: {e}")
            return False
    
    async def purge_stream(self, stream_name: str) -> bool:
        """Purge all messages from a stream"""
        try:
            await self.js.purge_stream(stream_name)
            logger.info(f"Purged stream {stream_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to purge stream {stream_name}: {e}")
            return False
    
    async def publish_message(self, subject: str, data: Any, headers: Optional[Dict] = None) -> bool:
        """Publish a message to a subject"""
        try:
            if isinstance(data, dict):
                data = json.dumps(data)
            if isinstance(data, str):
                data = data.encode()
            
            await self.js.publish(subject, data, headers=headers)
            logger.debug(f"Published message to {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish to {subject}: {e}")
            return False
    
    async def subscribe_to_subject(self, subject: str, callback, durable_name: str = None):
        """Subscribe to a subject and process messages"""
        try:
            if durable_name:
                sub = await self.js.subscribe(subject, durable=durable_name)
            else:
                sub = await self.js.subscribe(subject)
            
            logger.info(f"Subscribed to {subject}")
            
            async for msg in sub.messages:
                try:
                    data = json.loads(msg.data.decode())
                    await callback(data)
                    await msg.ack()
                except Exception as e:
                    logger.error(f"Error processing message from {subject}: {e}")
                    await msg.nak()
                    
        except Exception as e:
            logger.error(f"Failed to subscribe to {subject}: {e}")
    
    async def get_messages(self, stream_name: str, subject: str = None, limit: int = 100) -> List[Dict]:
        """Get messages from a stream"""
        try:
            messages = []
            
            # Create a temporary consumer
            consumer_config = ConsumerConfig(
                durable_name=f"temp-consumer-{int(datetime.now().timestamp())}",
                deliver_policy="all",
                max_deliver=1
            )
            
            consumer = await self.js.add_consumer(stream_name, consumer_config)
            
            # Fetch messages
            msgs = await consumer.fetch(limit, timeout=5)
            
            for msg in msgs:
                try:
                    data = json.loads(msg.data.decode())
                    messages.append({
                        "subject": msg.subject,
                        "data": data,
                        "timestamp": msg.headers.get("timestamp") if msg.headers else None
                    })
                    await msg.ack()
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    await msg.nak()
            
            # Clean up temporary consumer
            await self.js.delete_consumer(stream_name, consumer_config.durable_name)
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get messages from {stream_name}: {e}")
            return []
    
    async def setup_observability_streams(self):
        """Setup all required streams for observability agent"""
        streams = {
            "ALERTS": ["alerts", "alert_responses"],
            "METRICS": ["metrics.*", "metric_analysis"],
            "LOGS": ["logs.*", "log_analysis"],
            "DEPLOYMENTS": ["deployments.*", "deployment_analysis"],
            "AGENTS": ["agent_status", "agent_responses"],
            "RUNBOOKS": ["runbooks.*", "runbook_execution"],
            "NOTIFICATIONS": ["notifications.*", "notification_status"],
            "ROOT_CAUSE": ["root_cause_analysis", "root_cause_results"]
        }
        
        success_count = 0
        for stream_name, subjects in streams.items():
            if await self.create_stream(stream_name, subjects):
                success_count += 1
        
        logger.info(f"Successfully created {success_count}/{len(streams)} streams")
        return success_count == len(streams)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the NATS system"""
        try:
            # Check connection
            if not self.nc or not self.nc.is_connected:
                return {"status": "unhealthy", "reason": "Not connected to NATS"}
            
            # Check JetStream
            if not self.js:
                return {"status": "unhealthy", "reason": "JetStream not available"}
            
            # List streams
            streams = await self.list_streams()
            
            return {
                "status": "healthy",
                "nats_url": self.nats_url,
                "streams": streams,
                "stream_count": len(streams),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {"status": "unhealthy", "reason": str(e)}

async def main():
    """Main function for CLI usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NATS Utilities for Observability Agent')
    parser.add_argument('--nats-url', default='nats://localhost:4222', help='NATS server URL')
    parser.add_argument('command', choices=['setup', 'list', 'info', 'health', 'purge', 'delete'], 
                       help='Command to execute')
    parser.add_argument('--stream', help='Stream name for stream-specific operations')
    
    args = parser.parse_args()
    
    utils = NATSUtils(args.nats_url)
    
    try:
        await utils.connect()
        
        if args.command == 'setup':
            success = await utils.setup_observability_streams()
            if success:
                print("✅ All streams created successfully")
            else:
                print("❌ Some streams failed to create")
                
        elif args.command == 'list':
            streams = await utils.list_streams()
            print(f"📋 Found {len(streams)} streams:")
            for stream in streams:
                print(f"  - {stream}")
                
        elif args.command == 'info':
            if args.stream:
                info = await utils.stream_info(args.stream)
                if info:
                    print(f"📊 Stream info for {args.stream}:")
                    print(json.dumps(info, indent=2))
                else:
                    print(f"❌ Stream {args.stream} not found")
            else:
                print("❌ --stream parameter required for info command")
                
        elif args.command == 'health':
            health = await utils.health_check()
            print(f"🏥 Health check result:")
            print(json.dumps(health, indent=2))
            
        elif args.command == 'purge':
            if args.stream:
                success = await utils.purge_stream(args.stream)
                if success:
                    print(f"✅ Stream {args.stream} purged successfully")
                else:
                    print(f"❌ Failed to purge stream {args.stream}")
            else:
                print("❌ --stream parameter required for purge command")
                
        elif args.command == 'delete':
            if args.stream:
                success = await utils.delete_stream(args.stream)
                if success:
                    print(f"✅ Stream {args.stream} deleted successfully")
                else:
                    print(f"❌ Failed to delete stream {args.stream}")
            else:
                print("❌ --stream parameter required for delete command")
                
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    finally:
        await utils.disconnect()

if __name__ == "__main__":
    asyncio.run(main())