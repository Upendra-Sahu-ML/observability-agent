from agent import MetricAgent
import os
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()

    # Initialize the metric agent with Prometheus URL from env var or use default
    prometheus_url = os.environ.get("PROMETHEUS_URL", "http://prometheus:9090")
    agent = MetricAgent(prometheus_url=prometheus_url)
    
    print("[MetricAgent] Starting metric agent...")
    # Start listening for messages from orchestrator
    agent.listen()

if __name__ == "__main__":
    main()