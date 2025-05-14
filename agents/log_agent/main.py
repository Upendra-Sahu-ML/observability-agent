import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Using explicit import with the full path to the agent module
from agents.log_agent.agent import LogAgent

def main():
    # Load environment variables
    load_dotenv()

    # Initialize the log agent with configuration from env vars or use defaults
    loki_url = os.environ.get("LOKI_URL", "http://loki:3100")
    log_directory = os.environ.get("LOG_DIRECTORY", "/var/log")
    nats_server = os.environ.get("NATS_URL", "nats://localhost:4222")  # Use localhost for local testing
    
    agent = LogAgent(loki_url=loki_url, log_directory=log_directory, nats_server=nats_server)
    
    print("[LogAgent] Starting log agent...")
    
    # Run the async listen method in the event loop
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(agent.listen())
    except KeyboardInterrupt:
        print("[LogAgent] Shutting down...")
    finally:
        if agent.nats_client and agent.nats_client.is_connected:
            loop.run_until_complete(agent.nats_client.close())
        loop.close()

if __name__ == "__main__":
    main()
