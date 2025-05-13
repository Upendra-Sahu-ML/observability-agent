import asyncio
from orchestrator.agent import OrchestratorAgent
import os

def main():
    # Get NATS server URL from environment variables or use default
    nats_server = os.environ.get('NATS_URL', 'nats://nats:4222')
    
    # Initialize the orchestrator agent
    agent = OrchestratorAgent(nats_server=nats_server)
    
    # Run the orchestrator
    agent.run()

if __name__ == "__main__":
    main()
