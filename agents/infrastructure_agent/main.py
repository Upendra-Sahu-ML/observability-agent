#!/usr/bin/env python3
"""
Main entry point for the Consolidated Infrastructure Agent.

This agent replaces the separate deployment_agent and runbook_agent
with a single efficient implementation that provides comprehensive infrastructure
management from deployment analysis to automated runbook execution.
"""
import asyncio
import logging
import signal
import sys
from agent import InfrastructureAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GracefulShutdown:
    """Handle graceful shutdown of the agent"""
    def __init__(self):
        self.shutdown = False
        self.agent = None
        
    def exit_gracefully(self, signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown = True
        
        if self.agent and self.agent.status_publisher:
            try:
                # Stop status publishing
                asyncio.create_task(self.agent.status_publisher.stop_publishing())
                logger.info("Status publishing stopped")
            except Exception as e:
                logger.warning(f"Error stopping status publisher: {e}")
        
        logger.info("Infrastructure agent shutdown complete")
        sys.exit(0)

async def main():
    """Main function to run the Infrastructure Agent"""
    
    # Set up graceful shutdown
    shutdown_handler = GracefulShutdown()
    signal.signal(signal.SIGINT, shutdown_handler.exit_gracefully)
    signal.signal(signal.SIGTERM, shutdown_handler.exit_gracefully)
    
    logger.info("=== Starting Consolidated Infrastructure Agent ===")
    logger.info("This agent provides unified deployment analysis and runbook execution")
    
    try:
        # Create and configure the agent
        agent = InfrastructureAgent()
        shutdown_handler.agent = agent
        
        logger.info("Infrastructure agent initialized successfully")
        logger.info("Capabilities: Deployment analysis, Configuration management, Runbook execution")
        
        # Start listening for infrastructure requests
        await agent.listen()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error in infrastructure agent: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Infrastructure agent stopped")

if __name__ == "__main__":
    asyncio.run(main())