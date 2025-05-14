import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Using explicit import with the full path to the agent module
from agents.metric_agent.agent import MetricAgent

def main():
    # Load environment variables
    load_dotenv()

    # Initialize the metric agent with Prometheus URL and NATS server from env vars or use defaults
    prometheus_url = os.environ.get("PROMETHEUS_URL", "http://prometheus:9090")
    nats_server = os.environ.get("NATS_URL", "nats://localhost:4222")  # Use localhost for local testing
    
    agent = MetricAgent(prometheus_url=prometheus_url, nats_server=nats_server)
    
    print("[MetricAgent] Starting metric agent...")
    
    # Run the async listen method in the event loop
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(agent.listen())
    except KeyboardInterrupt:
        print("[MetricAgent] Shutting down...")
    finally:
        if agent.nats_client and agent.nats_client.is_connected:
            loop.run_until_complete(agent.nats_client.close())
        loop.close()

if __name__ == "__main__":
    main()