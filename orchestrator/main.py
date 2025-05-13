#!/usr/bin/env python3
import os
import sys

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import OrchestratorAgent

def main():
    # Get NATS server URL from environment variables or use local NATS server
    nats_server = os.environ.get('NATS_URL', 'nats://localhost:4222')
    
    # Initialize the orchestrator agent
    agent = OrchestratorAgent(nats_server=nats_server)
    
    # Run the orchestrator
    agent.run()

if __name__ == "__main__":
    main()
