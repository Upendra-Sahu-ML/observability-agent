from agent import LogAgent
import os
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize the log agent with env vars or use defaults
    loki_url = os.environ.get("LOKI_URL", "http://loki:3100")
    log_directory = os.environ.get("LOG_DIRECTORY", "/var/log")
    
    agent = LogAgent(loki_url=loki_url, log_directory=log_directory)
    
    print("[LogAgent] Starting log agent...")
    # Start listening for messages from orchestrator
    agent.listen()

if __name__ == "__main__":
    main()
